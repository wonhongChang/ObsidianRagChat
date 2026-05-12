from openai import OpenAI
from dotenv import load_dotenv
import os
import logging
from datetime import datetime
import tiktoken
from functools import lru_cache
from embed.embedder import embed_texts
from embed.vector_store import client, COLLECTION_NAME

load_dotenv()
openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# tiktoken 인코더 초기화 (GPT-4 모델용)
encoding = tiktoken.encoding_for_model("gpt-4o-mini")

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('rag_query.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

@lru_cache(maxsize=2048)
def count_tokens(text: str) -> int:
    """
    텍스트의 토큰 수를 계산합니다.
    LRU 캐시를 사용하여 동일한 텍스트의 반복 계산을 방지합니다.

    Args:
        text: 토큰 수를 계산할 텍스트

    Returns:
        토큰 개수
    """
    return len(encoding.encode(text))

def search_relevant_notes(query: str, limit: int = 5, filter_tags: list = None):
    """
    쿼리와 관련된 노트를 검색

    Args:
        query: 검색 쿼리
        limit: 반환할 결과 개수
        filter_tags: 필터링할 태그 리스트 (옵션)
    """
    from search.document_index import es, INDEX_NAME

    query_vector = embed_texts([query])[0]

    # 태그 필터가 있으면 ES에서 먼저 필터링
    filtered_paths = None
    if filter_tags:
        logger.info(f"🔍 태그 필터링: {filter_tags}")

        # normalizer 유무 관계없이 소문자 + 원본 케이스 모두 전달
        tag_variants = list({tag.lower() for tag in filter_tags} | set(filter_tags))

        es_query = {
            "bool": {
                "must": [
                    {"terms": {"tags": tag_variants}}
                ]
            }
        }

        try:
            # ES에서 태그 필터링된 문서를 사용자 지정 limit만큼 가져오기
            # 동적 크기 조정: 작은 limit일 때 불필요한 큰 요청 방지
            if limit <= 50:
                es_size = limit * 5  # 여유롭게
            elif limit <= 200:
                es_size = limit * 3
            else:
                es_size = limit * 2

            es_results = es.search(
                index=INDEX_NAME,
                query=es_query,
                _source=["path"],
                size=es_size
            )

            filtered_paths = [hit["_source"]["path"] for hit in es_results["hits"]["hits"]]
            logger.info(f"   → ES에서 {len(filtered_paths)}개 파일 필터링됨 (요청: {limit}개)")

            if not filtered_paths:
                logger.warning("⚠️  태그 필터 조건에 맞는 파일이 없습니다.")
                return []
        except Exception as e:
            logger.error(f"❌ ES 태그 필터링 오류: {e}")
            # 오류 시 필터 없이 진행
            filtered_paths = None

    # Qdrant 벡터 검색 (청크 환경에서 충분한 후보 확보를 위해 limit * 3으로 요청)
    chunk_limit = limit * 3
    if filtered_paths:
        from qdrant_client.models import Filter, FieldCondition, MatchAny

        results = client.query_points(
            collection_name=COLLECTION_NAME,
            query=query_vector,
            query_filter=Filter(
                must=[
                    FieldCondition(
                        key="path",
                        match=MatchAny(any=filtered_paths)
                    )
                ]
            ),
            limit=chunk_limit
        ).points
        logger.info(f"   → Qdrant path 필터 검색 결과: {len(results)}개 청크")
    else:
        results = client.query_points(
            collection_name=COLLECTION_NAME,
            query=query_vector,
            limit=chunk_limit
        ).points

    # 경로 기준 중복 제거: 파일당 최고 점수 청크만 유지 후 limit개 반환
    if not results:
        return results

    logger.info(f"🔍 Qdrant 원본 검색 결과: {len(results)}개 청크")

    seen_paths = {}
    for r in results:
        path = r.payload.get("path", str(r.id))
        if path not in seen_paths or r.score > seen_paths[path].score:
            seen_paths[path] = r

    unique_results = sorted(seen_paths.values(), key=lambda x: x.score, reverse=True)[:limit]
    logger.info(f"🔀 파일 단위 병합: {len(results)}개 청크 → {len(unique_results)}개 파일")

    # 파일명 키워드 보강: dedup 후 top-k에 없는 파일 중 파일명 keyword 매칭 파일을 강제 포함
    # (한국어 복합어 + 일본어/CJK 대응: bigram/trigram 분해 → substring 매칭)
    if not filter_tags:
        try:
            import re as _re
            words = _re.findall(r'[가-힣a-zA-Z぀-ヿ一-鿿㐀-䶿]{2,}', query)
            keywords = set()
            for w in words:
                keywords.add(w)
                for i in range(len(w) - 1):
                    keywords.add(w[i:i + 2])
                for i in range(len(w) - 2):
                    keywords.add(w[i:i + 3])
            keywords = {k for k in keywords if len(k) >= 2}

            if keywords:
                all_resp = es.search(
                    index=INDEX_NAME,
                    query={"match_all": {}},
                    _source=["path", "filename"],
                    size=1000
                )
                top_paths = {r.payload.get("path") for r in unique_results}
                extra_paths = [
                    h["_source"]["path"] for h in all_resp["hits"]["hits"]
                    if h["_source"]["path"] not in top_paths
                    and any(kw in h["_source"]["filename"] for kw in keywords)
                ]
                if extra_paths:
                    from qdrant_client.models import Filter, FieldCondition, MatchAny
                    extra_chunks = client.query_points(
                        collection_name=COLLECTION_NAME,
                        query=query_vector,
                        query_filter=Filter(
                            must=[FieldCondition(key="path", match=MatchAny(any=extra_paths))]
                        ),
                        limit=len(extra_paths) * 3
                    ).points
                    extra_seen = {}
                    for r in extra_chunks:
                        path = r.payload.get("path", str(r.id))
                        if path not in extra_seen or r.score > extra_seen[path].score:
                            extra_seen[path] = r
                    # 외부 추가 파일: top_score + 0.01
                    # 이미 top-k 안에 있는 키워드 매칭 파일: top_score + 0.02 (더 높게)
                    # → 이미 관련성 있어서 top-k에 든 파일이 외부 추가 파일보다 항상 우선
                    base = (unique_results[0].score if unique_results else 0.9)
                    external_score = base + 0.01
                    present_score  = base + 0.02

                    boosted = []
                    for r in extra_seen.values():
                        try:
                            boosted.append(r.model_copy(update={"score": external_score}))
                        except Exception:
                            boosted.append(r)

                    reboosted = []
                    for r in unique_results:
                        filename = r.payload.get("filename", "")
                        if any(kw in filename for kw in keywords):
                            try:
                                reboosted.append(r.model_copy(update={"score": present_score}))
                            except Exception:
                                reboosted.append(r)
                        else:
                            reboosted.append(r)

                    all_candidates = reboosted + boosted
                    all_candidates.sort(key=lambda x: x.score, reverse=True)
                    unique_results = all_candidates[:limit]
                    logger.info(f"   → 파일명 키워드 보강: 외부 {list(extra_seen.keys())} 추가, present_score={present_score:.3f}, external_score={external_score:.3f}")
        except Exception as _e:
            logger.warning(f"⚠️ 파일명 키워드 보강 실패 (무시): {_e}")

    logger.info(f"📄 최종 반환 파일: {[r.payload.get('filename') for r in unique_results]}")
    return unique_results


def _extract_responses_text(response, label: str = "Responses API") -> str:
    """Responses API 응답에서 출력 텍스트만 안전하게 추출."""
    if hasattr(response, 'output_text') and response.output_text:
        return response.output_text

    output = getattr(response, 'output', None)
    if output:
        for item in output:
            if getattr(item, 'type', None) != 'message':
                continue

            content = getattr(item, 'content', None)
            if isinstance(content, str) and content:
                return content
            if isinstance(content, list):
                for part in content:
                    text = getattr(part, 'text', None)
                    if text:
                        return text

    logger.error(f"❌ {label}에서 답변 텍스트를 찾을 수 없습니다.")
    return "⚠️ GPT-5-mini 응답을 파싱할 수 없습니다."


def generate_answer_with_rag(query: str, top_k: int = 5, ignore_token_limit: bool = False, model: str = "gpt-4o-mini"):
    """
    Qdrant에서 관련 노트를 검색하고 GPT를 사용해 답변 생성

    Args:
        query: 사용자 질문
        top_k: 검색할 관련 노트 개수 (기본값 5)

    Returns:
        dict: {
            'answer': GPT-4의 답변,
            'sources': 참조한 노트들,
            'usage': 토큰 사용량 정보
        }
    """
    start_time = datetime.now()
    logger.info(f"=== 새로운 쿼리 시작 ===")
    logger.info(f"📝 쿼리: {query}")
    logger.info(f"🔢 검색할 노트 개수: {top_k}")
    
    # 쿼리에서 태그 추출 (예: "#painpoint" 또는 "painpoint 태그")
    import re
    tag_pattern = re.findall(r'#(\w+)', query)
    tag_keywords = re.findall(r'(\w+)\s*태그', query)
    filter_tags = list(set(tag_pattern + tag_keywords))
    
    # 1. 관련 노트 검색
    if filter_tags:
        logger.info(f"🏷️  태그 필터 적용: {filter_tags}")
        # 태그 필터가 있으면 해당 태그 문서만 검색 (일반 검색 추가 안 함)
        results = search_relevant_notes(query, limit=top_k, filter_tags=filter_tags)
        logger.info(f"   → 태그 필터 결과: {len(results)}개 (일반 검색 추가 안 함)")
    else:
        results = search_relevant_notes(query, limit=top_k)
    
    logger.info(f"📚 검색된 노트 개수: {len(results)}")
    
    if not results:
        logger.warning("⚠️  검색 결과 없음")
        return {
            'answer': "관련된 노트를 찾을 수 없습니다.",
            'sources': [],
            'usage': None
        }
    
    # 중복 제거 (같은 ID의 노트는 하나만 유지)
    seen_ids = set()
    unique_results = []
    for r in results:
        if r.id not in seen_ids:
            seen_ids.add(r.id)
            unique_results.append(r)
    
    if len(unique_results) < len(results):
        logger.warning(f"⚠️  중복 제거: {len(results)}개 → {len(unique_results)}개")
    
    results = unique_results
    
    # 2. 토큰 기반 컨텍스트 구성 (최대 토큰 + 노트 개수 제한)
    # 최대 토큰 모드가 활성화되면 180K, 아니면 110K 사용
    max_context_tokens = 180000 if ignore_token_limit else 110000
    context_parts = []
    sources = []
    current_tokens = 0
    notes_added = 0
    
    for i, result in enumerate(results, 1):
        if notes_added >= top_k:  # 노트 개수 상한선
            logger.info(f"⚠️  노트 개수 상한 도달 ({top_k}개)")
            break
            
        filename = result.payload.get('filename', 'Unknown')
        tags = result.payload.get('tags', [])
        note_text = result.payload.get('parent_text') or result.payload.get('text', '')
        
        # 노트 헤더 구성
        note_header = f"[노트 {i}: {filename}]\n태그: {', '.join(['#' + t for t in tags]) if tags else '없음'}\n"
        header_tokens = count_tokens(note_header)
        
        # 노트 본문 토큰 계산
        note_tokens = count_tokens(note_text)
        total_note_tokens = header_tokens + note_tokens
        
        # 토큰이 남은 공간보다 크면 처리
        if current_tokens + total_note_tokens > max_context_tokens:
            # 최대 토큰 모드든 일반 모드든 max_context_tokens를 넘으면 처리 필요
            remaining_tokens = max_context_tokens - current_tokens - header_tokens
            if remaining_tokens < 100:  # 너무 적으면 추가 안함
                logger.info(f"⚠️  토큰 제한 도달 (사용: {current_tokens}/{max_context_tokens})")
                break
            
            # 텍스트를 토큰 제한에 맞게 자르기
            tokens = encoding.encode(note_text)
            truncated_text = encoding.decode(tokens[:remaining_tokens])
            note_text = truncated_text + "...(생략)"
            total_note_tokens = header_tokens + count_tokens(note_text)
        
        # 컨텍스트에 추가
        context_parts.append(f"{note_header}{note_text}\n")
        sources.append({
            'id': i,
            'filename': filename,
            'text': (result.payload.get('chunk_text') or result.payload.get('text', ''))[:500],
            'section': result.payload.get('section', ''),
            'score': float(result.score),
            'tags': tags
        })
        
        current_tokens += total_note_tokens
        notes_added += 1
        logger.info(f"  ✓ 노트 {i} 추가: {filename} ({total_note_tokens} 토큰)")
    
    context = "\n".join(context_parts)
    
    # 컨텍스트 통계 로깅
    # 모델별 비용 계산
    if model == "gpt-5-mini":
        input_price = 0.250
        output_price = 2.000
    else:  # gpt-4o-mini
        input_price = 0.150
        output_price = 0.600
    
    input_cost = (current_tokens / 1_000_000) * input_price
    estimated_output_tokens = 1000  # 예상 출력 토큰 (평균)
    output_cost = (estimated_output_tokens / 1_000_000) * output_price
    total_cost = input_cost + output_cost
    
    logger.info(f"📊 컨텍스트 통계:")
    logger.info(f"   - 사용 모델: {model}")
    logger.info(f"   - 사용된 노트: {notes_added}개")
    logger.info(f"   - 문자 수: {len(context)}")
    logger.info(f"   - 토큰 수: {current_tokens}")
    logger.info(f"💰 예상 비용:")
    logger.info(f"   - 입력: ${input_cost:.6f} ({current_tokens} 토큰 × ${input_price}/1M)")
    logger.info(f"   - 출력: ${output_cost:.6f} (예상 {estimated_output_tokens} 토큰 × ${output_price}/1M)")
    logger.info(f"   - 총계: ${total_cost:.6f}")
    logger.info(f"📄 사용된 노트 파일: {[s['filename'] for s in sources]}")
    
    # 3. GPT-4에게 질문
    system_prompt = """당신은 사용자의 개인 노트를 기반으로 질문에 답하는 AI 어시스턴트입니다.
제공된 노트 내용을 바탕으로 정확하고 유용한 답변을 제공하세요.
노트에 없는 내용은 추측하지 말고, 노트 기반으로만 답변하세요.
답변 시 어떤 노트를 참조했는지 [노트 번호]를 명시하세요."""

    user_prompt = f"""다음은 사용자의 노트 내용입니다:

{context}

사용자 질문: {query}

위 노트 내용을 바탕으로 질문에 답변해주세요."""

    logger.info(f"🤖 OpenAI API 호출 시작 (모델: {model})")
    
    # GPT-5-mini는 Responses API 사용
    if model == "gpt-5-mini":
        logger.info(f"🔄 GPT-5-mini detected: Using Responses API instead of Chat Completions")
        
        # Responses API 파라미터 (reasoning_tokens + output_tokens 고려)
        response = openai_client.responses.create(
            model=model,
            reasoning={"effort": "medium"},  # low, medium, high
            input=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            max_output_tokens=4000  # reasoning_tokens(~1000) + 실제 답변(~3000)
        )
        
        logger.info(f"🔍 [Responses API] response type: {type(response).__name__}")
        
    else:
        # GPT-4o-mini는 Chat Completions API 사용
        completion_params = {
            "model": model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            "max_tokens": 800,
            "temperature": 0.7
        }
        
        response = openai_client.chat.completions.create(**completion_params)
    
    # 응답 처리 - API별로 다른 구조
    if model == "gpt-5-mini":
        answer = _extract_responses_text(response, "Responses API")
        usage = response.usage if hasattr(response, 'usage') else None
        
    else:
        # Chat Completions API 응답 처리 (GPT-4o-mini)
        logger.info(f"🔍 [Chat Completions API] 응답 구조:")
        logger.info(f"   - choices 개수: {len(response.choices)}")
        
        answer = response.choices[0].message.content
        usage = response.usage
    
    logger.info(f"🔍 최종 추출 답변: '{answer[:100] if answer else ''}...' (길이: {len(answer) if answer else 0})")
    
    # 토큰 사용량 로깅
    if usage:
        logger.info(f"💰 토큰 사용량:")
        
        # Responses API의 usage 구조
        if model == "gpt-5-mini":
            # input_tokens, output_tokens 구조
            input_tokens = usage.input_tokens if hasattr(usage, 'input_tokens') else usage.prompt_tokens
            output_tokens = usage.output_tokens if hasattr(usage, 'output_tokens') else usage.completion_tokens
            total_tokens = usage.total_tokens if hasattr(usage, 'total_tokens') else (input_tokens + output_tokens)
            
            logger.info(f"   - Input 토큰: {input_tokens}")
            logger.info(f"   - Output 토큰: {output_tokens}")
            
            # reasoning_tokens 확인
            if hasattr(usage, 'output_tokens_details'):
                details = usage.output_tokens_details
                if hasattr(details, 'reasoning_tokens'):
                    logger.info(f"   - Reasoning 토큰: {details.reasoning_tokens}")
        else:
            # Chat Completions API 구조
            input_tokens = usage.prompt_tokens
            output_tokens = usage.completion_tokens
            total_tokens = usage.total_tokens
            
            logger.info(f"   - Prompt 토큰: {input_tokens}")
            logger.info(f"   - Completion 토큰: {output_tokens}")
        
        logger.info(f"   - 총 토큰: {total_tokens}")
    else:
        logger.warning(f"⚠️ usage 정보 없음")
        input_tokens = output_tokens = total_tokens = 0
    
    # 처리 시간 계산
    elapsed_time = (datetime.now() - start_time).total_seconds()
    logger.info(f"⏱️  처리 시간: {elapsed_time:.2f}초")
    logger.info(f"=== 쿼리 완료 ===\n")
    
    return {
        'answer': answer,
        'sources': sources,
        'query': query,
        'usage': {
            'prompt_tokens': input_tokens,
            'completion_tokens': output_tokens,
            'total_tokens': total_tokens
        },
        'elapsed_time': elapsed_time
    }

def _prepare_context(results, top_k: int, ignore_token_limit: bool):
    """Shared context building for streaming and non-streaming paths."""
    max_context_tokens = 180000 if ignore_token_limit else 110000
    context_parts = []
    sources = []
    current_tokens = 0
    notes_added = 0

    for i, result in enumerate(results, 1):
        if notes_added >= top_k:
            break
        filename = result.payload.get('filename', 'Unknown')
        tags = result.payload.get('tags', [])
        note_text = result.payload.get('parent_text') or result.payload.get('text', '')
        note_header = f"[노트 {i}: {filename}]\n태그: {', '.join(['#' + t for t in tags]) if tags else '없음'}\n"
        header_tokens = count_tokens(note_header)
        total_note_tokens = header_tokens + count_tokens(note_text)

        if current_tokens + total_note_tokens > max_context_tokens:
            remaining = max_context_tokens - current_tokens - header_tokens
            if remaining < 100:
                break
            note_text = encoding.decode(encoding.encode(note_text)[:remaining]) + "...(생략)"
            total_note_tokens = header_tokens + count_tokens(note_text)

        context_parts.append(f"{note_header}{note_text}\n")
        sources.append({
            'id': i,
            'filename': filename,
            'text': (result.payload.get('chunk_text') or result.payload.get('text', ''))[:500],
            'section': result.payload.get('section', ''),
            'score': float(result.score),
            'tags': tags
        })
        current_tokens += total_note_tokens
        notes_added += 1

    return "\n".join(context_parts), sources, current_tokens


def _rewrite_query_standalone(query: str, history: list) -> str:
    """Follow-up 쿼리를 벡터 검색용 standalone 쿼리로 rewrite"""
    recent = history[-4:] if len(history) >= 4 else history
    history_text = "\n".join([
        f"{msg.get('role', 'user')}: {msg.get('content', '')[:200]}"
        if isinstance(msg, dict)
        else f"{msg.role}: {msg.content[:200]}"
        for msg in recent
    ])

    prompt = f"""대화 히스토리를 참고하여 아래 Follow-up 질문을 독립적인 검색 쿼리로 바꿔주세요.
검색 엔진에 입력할 간결한 한 문장으로 작성하세요. 다른 설명은 하지 마세요.

대화 히스토리:
{history_text}

Follow-up 질문: {query}

독립적인 검색 쿼리:"""

    try:
        response = openai_client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=100,
            temperature=0
        )
        rewritten = response.choices[0].message.content.strip()
        logger.info(f"🔄 쿼리 rewrite: '{query}' → '{rewritten}'")
        return rewritten
    except Exception as e:
        logger.warning(f"⚠️  쿼리 rewrite 실패, 원본 사용: {e}")
        return query


def generate_followup_answer(query: str, history: list, top_k: int = 5, ignore_token_limit: bool = False, model: str = "gpt-4o-mini"):
    """
    이전 대화 히스토리를 바탕으로 follow-up 질문에 답변

    Args:
        query: 사용자의 follow-up 질문
        history: 이전 대화 히스토리 [{"role": "user|assistant", "content": "..."}]
        top_k: 검색할 관련 노트 개수 (기본값 5개)

    Returns:
        dict: 답변 및 관련 정보
    """
    start_time = datetime.now()
    logger.info(f"=== Follow-up 쿼리 시작 ===")
    logger.info(f"📝 쿼리: {query}")
    logger.info(f"💬 히스토리 길이: {len(history)}개 메시지")
    
    # 태그 추출 (현재 query만 — history 상속 없음)
    import re
    tag_pattern = re.findall(r'#(\w+)', query)
    tag_keywords = re.findall(r'(\w+)\s*태그', query)
    filter_tags = list(set(tag_pattern + tag_keywords))

    # Follow-up 쿼리를 standalone 검색 쿼리로 rewrite
    search_query = _rewrite_query_standalone(query, history)

    # 노트 검색
    if filter_tags:
        logger.info(f"🏷️  태그 필터 적용: {filter_tags}")
        results = search_relevant_notes(search_query, limit=top_k, filter_tags=filter_tags)
        logger.info(f"   → 태그 필터 결과: {len(results)}개 (일반 검색 추가 안 함)")
    else:
        results = search_relevant_notes(search_query, limit=top_k)

    logger.info(f"📚 검색된 노트 개수: {len(results)}")
    
    # 중복 제거 (같은 ID의 노트는 하나만 유지)
    seen_ids = set()
    unique_results = []
    for r in results:
        if r.id not in seen_ids:
            seen_ids.add(r.id)
            unique_results.append(r)
    
    if len(unique_results) < len(results):
        logger.warning(f"⚠️  중복 제거: {len(results)}개 → {len(unique_results)}개")
    
    results = unique_results
    
    # 토큰 기반 컨텍스트 구성
    sources = []
    # 최대 토큰 모드가 활성화되면 180K, 아니면 110K 사용
    max_context_tokens = 180000 if ignore_token_limit else 110000
    
    if results:
        context_parts = []
        current_tokens = 0
        notes_added = 0
        
        for i, result in enumerate(results, 1):
            if notes_added >= top_k:  # 노트 개수 상한선
                logger.info(f"⚠️  노트 개수 상한 도달 ({top_k}개)")
                break
                
            filename = result.payload.get('filename', 'Unknown')
            tags = result.payload.get('tags', [])
            note_text = result.payload.get('parent_text') or result.payload.get('text', '')
            
            # 노트 헤더 구성
            note_header = f"[노트 {i}: {filename}]\n태그: {', '.join(['#' + t for t in tags]) if tags else '없음'}\n"
            header_tokens = count_tokens(note_header)
            
            # 노트 본문 토큰 계산
            note_tokens = count_tokens(note_text)
            total_note_tokens = header_tokens + note_tokens
            
            # 토큰이 남은 공간보다 크면 처리
            if current_tokens + total_note_tokens > max_context_tokens:
                # 최대 토큰 모드든 일반 모드든 max_context_tokens를 넘으면 처리 필요
                remaining_tokens = max_context_tokens - current_tokens - header_tokens
                if remaining_tokens < 100:  # 너무 적으면 추가 안함
                    logger.info(f"⚠️  토큰 제한 도달 (사용: {current_tokens}/{max_context_tokens})")
                    break
                
                # 텍스트를 토큰 제한에 맞게 자르기
                tokens = encoding.encode(note_text)
                truncated_text = encoding.decode(tokens[:remaining_tokens])
                note_text = truncated_text + "...(생략)"
                total_note_tokens = header_tokens + count_tokens(note_text)
            
            # 컨텍스트에 추가
            context_parts.append(f"{note_header}{note_text}\n")
            sources.append({
                'id': i,
                'filename': filename,
                'text': (result.payload.get('chunk_text') or result.payload.get('text', ''))[:500],
                'section': result.payload.get('section', ''),
                'score': float(result.score),
                'tags': tags
            })
            
            current_tokens += total_note_tokens
            notes_added += 1
            logger.info(f"  ✓ 노트 {i} 추가: {filename} ({total_note_tokens} 토큰)")
        
        context = "\n".join(context_parts)
        
        # 모델별 비용 계산
        if model == "gpt-5-mini":
            input_price = 0.250
            output_price = 2.000
        else:  # gpt-4o-mini
            input_price = 0.150
            output_price = 0.600
        
        input_cost = (current_tokens / 1_000_000) * input_price
        estimated_output_tokens = 1000  # 예상 출력 토큰 (평균)
        output_cost = (estimated_output_tokens / 1_000_000) * output_price
        total_cost = input_cost + output_cost
        
        logger.info(f"📊 컨텍스트 통계:")
        logger.info(f"   - 사용 모델: {model}")
        logger.info(f"   - 사용된 노트: {notes_added}개")
        logger.info(f"   - 문자 수: {len(context)}")
        logger.info(f"   - 토큰 수: {current_tokens}")
        logger.info(f"💰 예상 비용:")
        logger.info(f"   - 입력: ${input_cost:.6f} ({current_tokens} 토큰 × ${input_price}/1M)")
        logger.info(f"   - 출력: ${output_cost:.6f} (예상 {estimated_output_tokens} 토큰 × ${output_price}/1M)")
        logger.info(f"   - 총계: ${total_cost:.6f}")
    else:
        context = "(관련 노트를 찾지 못했습니다)"
    
    # GPT 메시지 구성
    messages = [
        {"role": "system", "content": """당신은 사용자의 개인 노트를 기반으로 질문에 답하는 AI 어시스턴트입니다.
이전 대화 내용을 참고하여 자연스럽게 대화를 이어가세요.
노트 내용과 이전 대화를 바탕으로 정확하고 유용한 답변을 제공하세요."""}
    ]
    
    # 히스토리 추가 (최근 15개 대화로 확장 - 긴 대화 컨텍스트 유지)
    for msg in history[-15:]:
        # Pydantic 모델이므로 속성으로 접근
        if isinstance(msg, dict):
            messages.append({"role": msg.get("role"), "content": msg.get("content")})
        else:
            # Pydantic Message 객체인 경우
            messages.append({"role": msg.role, "content": msg.content})
    
    # 현재 쿼리와 노트 컨텍스트 추가
    user_message = f"""관련 노트:

{context}

질문: {query}"""
    
    messages.append({"role": "user", "content": user_message})
    
    logger.info(f"🤖 OpenAI API 호출 시작 (모델: {model}, follow-up mode)")
    
    # GPT-5-mini는 Responses API 사용
    if model == "gpt-5-mini":
        logger.info(f"🔄 [Follow-up] GPT-5-mini detected: Using Responses API")
        
        response = openai_client.responses.create(
            model=model,
            reasoning={"effort": "medium"},
            input=messages,  # 전체 대화 히스토리 포함
            max_output_tokens=4000  # reasoning_tokens(~1000) + 실제 답변(~3000)
        )
        
    else:
        # GPT-4o-mini는 Chat Completions API 사용
        completion_params = {
            "model": model,
            "messages": messages,
            "max_tokens": 800,
            "temperature": 0.7
        }
        
        response = openai_client.chat.completions.create(**completion_params)
    
    # 응답 처리 - API별로 다른 구조 (generate_answer_with_rag와 동일)
    if model == "gpt-5-mini":
        answer = _extract_responses_text(response, "Follow-up Responses API")
        usage = response.usage if hasattr(response, 'usage') else None
        
    else:
        # Chat Completions API 응답 처리
        answer = response.choices[0].message.content
        usage = response.usage
    
    logger.info(f"🔍 [Follow-up] 최종 추출 답변: '{answer[:100] if answer else ''}...' (길이: {len(answer) if answer else 0})")
    
    # 토큰 사용량 로깅
    if usage:
        logger.info(f"💰 토큰 사용량:")
        
        if model == "gpt-5-mini":
            input_tokens = usage.input_tokens if hasattr(usage, 'input_tokens') else usage.prompt_tokens
            output_tokens = usage.output_tokens if hasattr(usage, 'output_tokens') else usage.completion_tokens
            total_tokens = usage.total_tokens if hasattr(usage, 'total_tokens') else (input_tokens + output_tokens)
            
            logger.info(f"   - Input 토큰: {input_tokens}")
            logger.info(f"   - Output 토큰: {output_tokens}")
            
            if hasattr(usage, 'output_tokens_details'):
                details = usage.output_tokens_details
                if hasattr(details, 'reasoning_tokens'):
                    logger.info(f"   - Reasoning 토큰: {details.reasoning_tokens}")
        else:
            input_tokens = usage.prompt_tokens
            output_tokens = usage.completion_tokens
            total_tokens = usage.total_tokens
            
            logger.info(f"   - Prompt 토큰: {input_tokens}")
            logger.info(f"   - Completion 토큰: {output_tokens}")
        
        logger.info(f"   - 총 토큰: {total_tokens}")
    else:
        logger.warning(f"⚠️ usage 정보 없음")
        input_tokens = output_tokens = total_tokens = 0
    
    elapsed_time = (datetime.now() - start_time).total_seconds()
    logger.info(f"⏱️  처리 시간: {elapsed_time:.2f}초")
    logger.info(f"=== Follow-up 쿼리 완료 ===\n")

    return {
        'answer': answer,
        'sources': sources,
        'query': query,
        'usage': {
            'prompt_tokens': input_tokens,
            'completion_tokens': output_tokens,
            'total_tokens': total_tokens
        },
        'elapsed_time': elapsed_time
    }


# ---------------------------------------------------------------------------
# Streaming variants
# ---------------------------------------------------------------------------

def generate_answer_stream(query: str, top_k: int = 5, ignore_token_limit: bool = False, model: str = "gpt-4o-mini"):
    """Sync generator yielding SSE data strings for a standalone RAG query."""
    import json
    import re
    start_time = datetime.now()

    tag_pattern = re.findall(r'#(\w+)', query)
    tag_keywords = re.findall(r'(\w+)\s*태그', query)
    filter_tags = list(set(tag_pattern + tag_keywords))

    if filter_tags:
        results = search_relevant_notes(query, limit=top_k, filter_tags=filter_tags)
    else:
        results = search_relevant_notes(query, limit=top_k)

    if not results:
        yield f'data: {json.dumps({"type": "token", "content": "관련된 노트를 찾을 수 없습니다."})}\n\n'
        yield f'data: {json.dumps({"type": "sources", "sources": []})}\n\n'
        yield f'data: {json.dumps({"type": "done", "usage": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}, "elapsed_time": 0, "answer": "관련된 노트를 찾을 수 없습니다."})}\n\n'
        return

    seen_ids = set()
    unique = []
    for r in results:
        if r.id not in seen_ids:
            seen_ids.add(r.id)
            unique.append(r)

    context, sources, _ = _prepare_context(unique, top_k, ignore_token_limit)

    system_prompt = """당신은 사용자의 개인 노트를 기반으로 질문에 답하는 AI 어시스턴트입니다.
제공된 노트 내용을 바탕으로 정확하고 유용한 답변을 제공하세요.
노트에 없는 내용은 추측하지 말고, 노트 기반으로만 답변하세요.
답변 시 어떤 노트를 참조했는지 [노트 번호]를 명시하세요."""

    user_prompt = f"""다음은 사용자의 노트 내용입니다:

{context}

사용자 질문: {query}

위 노트 내용을 바탕으로 질문에 답변해주세요."""

    if model == "gpt-5-mini":
        result = generate_answer_with_rag(query, top_k, ignore_token_limit, model)
        yield f'data: {json.dumps({"type": "token", "content": result["answer"]})}\n\n'
        yield f'data: {json.dumps({"type": "sources", "sources": result["sources"]})}\n\n'
        yield f'data: {json.dumps({"type": "done", "usage": result["usage"], "elapsed_time": result["elapsed_time"], "answer": result["answer"]})}\n\n'
        return

    full_answer = ""
    usage_data = {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}

    stream = openai_client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        max_tokens=800,
        temperature=0.7,
        stream=True,
        stream_options={"include_usage": True}
    )

    for chunk in stream:
        if chunk.choices and chunk.choices[0].delta.content:
            content = chunk.choices[0].delta.content
            full_answer += content
            yield f'data: {json.dumps({"type": "token", "content": content})}\n\n'
        if chunk.usage:
            usage_data = {
                "prompt_tokens": chunk.usage.prompt_tokens,
                "completion_tokens": chunk.usage.completion_tokens,
                "total_tokens": chunk.usage.total_tokens
            }

    elapsed_time = (datetime.now() - start_time).total_seconds()
    logger.info(f"⏱️ [stream] {elapsed_time:.2f}s, {usage_data['total_tokens']} tokens")

    yield f'data: {json.dumps({"type": "sources", "sources": sources})}\n\n'
    yield f'data: {json.dumps({"type": "done", "usage": usage_data, "elapsed_time": elapsed_time, "answer": full_answer})}\n\n'


def generate_followup_stream(query: str, history: list, top_k: int = 5, ignore_token_limit: bool = False, model: str = "gpt-4o-mini"):
    """Sync generator yielding SSE data strings for a follow-up RAG query."""
    import json
    import re
    start_time = datetime.now()

    tag_pattern = re.findall(r'#(\w+)', query)
    tag_keywords = re.findall(r'(\w+)\s*태그', query)
    filter_tags = list(set(tag_pattern + tag_keywords))
    # history 태그 상속 없음: 현재 쿼리에 명시된 태그만 사용
    # (상속 시 무관한 후속 쿼리에도 이전 태그가 오염되는 문제 방지)

    search_query = _rewrite_query_standalone(query, history)

    if filter_tags:
        results = search_relevant_notes(search_query, limit=top_k, filter_tags=filter_tags)
    else:
        results = search_relevant_notes(search_query, limit=top_k)

    if not results:
        yield f'data: {json.dumps({"type": "token", "content": "관련된 노트를 찾을 수 없습니다."})}\n\n'
        yield f'data: {json.dumps({"type": "sources", "sources": []})}\n\n'
        yield f'data: {json.dumps({"type": "done", "usage": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}, "elapsed_time": 0, "answer": "관련된 노트를 찾을 수 없습니다."})}\n\n'
        return

    seen_ids = set()
    unique = []
    for r in results:
        if r.id not in seen_ids:
            seen_ids.add(r.id)
            unique.append(r)

    context, sources, _ = _prepare_context(unique, top_k, ignore_token_limit)

    messages = [
        {"role": "system", "content": """당신은 사용자의 개인 노트를 기반으로 질문에 답하는 AI 어시스턴트입니다.
이전 대화 내용을 참고하여 자연스럽게 대화를 이어가세요.
노트 내용과 이전 대화를 바탕으로 정확하고 유용한 답변을 제공하세요."""}
    ]
    for msg in history[-15:]:
        if isinstance(msg, dict):
            messages.append({"role": msg.get("role"), "content": msg.get("content")})
        else:
            messages.append({"role": msg.role, "content": msg.content})
    messages.append({"role": "user", "content": f"관련 노트:\n\n{context}\n\n질문: {query}"})

    if model == "gpt-5-mini":
        result = generate_followup_answer(query, history, top_k, ignore_token_limit, model)
        yield f'data: {json.dumps({"type": "token", "content": result["answer"]})}\n\n'
        yield f'data: {json.dumps({"type": "sources", "sources": result["sources"]})}\n\n'
        yield f'data: {json.dumps({"type": "done", "usage": result["usage"], "elapsed_time": result["elapsed_time"], "answer": result["answer"]})}\n\n'
        return

    full_answer = ""
    usage_data = {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}

    stream = openai_client.chat.completions.create(
        model=model,
        messages=messages,
        max_tokens=800,
        temperature=0.7,
        stream=True,
        stream_options={"include_usage": True}
    )

    for chunk in stream:
        if chunk.choices and chunk.choices[0].delta.content:
            content = chunk.choices[0].delta.content
            full_answer += content
            yield f'data: {json.dumps({"type": "token", "content": content})}\n\n'
        if chunk.usage:
            usage_data = {
                "prompt_tokens": chunk.usage.prompt_tokens,
                "completion_tokens": chunk.usage.completion_tokens,
                "total_tokens": chunk.usage.total_tokens
            }

    elapsed_time = (datetime.now() - start_time).total_seconds()
    logger.info(f"⏱️ [stream follow-up] {elapsed_time:.2f}s, {usage_data['total_tokens']} tokens")

    yield f'data: {json.dumps({"type": "sources", "sources": sources})}\n\n'
    yield f'data: {json.dumps({"type": "done", "usage": usage_data, "elapsed_time": elapsed_time, "answer": full_answer})}\n\n'
