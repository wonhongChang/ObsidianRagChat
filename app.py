from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import List, Literal
from rag.generator import generate_answer_with_rag, generate_followup_answer, generate_answer_stream, generate_followup_stream
from search.cache import get_cached_rag, set_cached_rag, clear_all_cache, get_cache_stats, normalize_query
from search.question_detector import is_independent_question, save_query
import uvicorn
import hashlib
import json
import logging

logger = logging.getLogger(__name__)

app = FastAPI(title="Obsidian RAG Search")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],  # Vite dev server
    allow_methods=["*"],
    allow_headers=["*"],
)

class Message(BaseModel):
    role: str  # 'user' or 'assistant'
    content: str

ResponseLanguage = Literal["auto", "ko", "en", "ja"]

class QueryRequest(BaseModel):
    query: str = Field(min_length=1, max_length=4000)
    top_k: int = Field(default=5, ge=1, le=50)  # 기본값 5개 (성능 최적화)
    ignore_token_limit: bool = False  # 토큰 제한 무시 옵션
    model: Literal["gpt-4o-mini", "gpt-5-mini"] = "gpt-4o-mini"  # 사용할 모델
    response_language: ResponseLanguage = "auto"  # auto=질문 언어, ko/en/ja=고정 응답 언어
    history: List[Message] = Field(default_factory=list)


@app.post("/api/search")
async def search(query_request: QueryRequest):
    """RAG 검색 API (Redis 캐싱 + GPT 독립 질문 감지)"""
    try:
        import hashlib
        import json
        import time

        # 시작 시간 측정
        start_time = time.time()

        # 1. 독립 질문 감지 (history가 있을 때만)
        effective_history = query_request.history
        is_independent = False

        if query_request.history and len(query_request.history) > 0:
            # GPT-4o-mini로 독립 질문 감지
            is_independent = is_independent_question(query_request.query, query_request.history)

            # 독립 질문이면 history 무시
            if is_independent:
                print(f"✅ 독립 질문으로 감지됨 - history 무시하고 캐싱")
                effective_history = []

        # 2. 캐시 키 생성 - effective_history 기준
        cache_key_parts = [
            normalize_query(query_request.query),
            str(query_request.top_k),
            str(query_request.ignore_token_limit),
            query_request.model,
            query_request.response_language
        ]

        # Follow-up인 경우만 history 포함
        if effective_history and len(effective_history) > 0:
            # history를 JSON 문자열로 변환 후 해시
            history_dicts = []
            for msg in effective_history:
                if isinstance(msg, dict):
                    history_dicts.append(msg)
                else:
                    # Pydantic Message 객체인 경우
                    history_dicts.append({"role": msg.role, "content": msg.content})

            history_str = json.dumps(history_dicts, ensure_ascii=False, sort_keys=True)
            history_hash = hashlib.md5(history_str.encode('utf-8')).hexdigest()
            cache_key_parts.append(f"history:{history_hash}")

        cache_key = "|".join(cache_key_parts)

        # 3. 캐시 체크
        cached_result = get_cached_rag(cache_key)

        # 4. 캐시 히트 시 즉시 반환
        if cached_result:
            # 캐시 조회 실제 시간 계산
            cache_elapsed_time = time.time() - start_time

            # 캐시된 결과를 복사하여 수정
            result_data = cached_result.copy()

            # 실제 걸린 시간으로 덮어쓰기
            result_data['elapsed_time'] = cache_elapsed_time

            # 토큰 사용량을 0으로 설정 (GPT 호출 안 했으므로)
            result_data['usage'] = {
                'prompt_tokens': 0,
                'completion_tokens': 0,
                'total_tokens': 0
            }

            # 최근 질문 저장 (rephrase 감지용, 캐시 히트 시에도 저장)
            save_query(query_request.query)

            return {
                "success": True,
                "data": result_data,
                "cached": True,
                "independent_question": is_independent  # 디버깅용
            }

        # 5. 캐시 미스 - 실제 RAG 실행
        # 독립 질문으로 감지되었으면 원래 history 사용 안 함
        if effective_history and len(effective_history) > 0:
            # Follow-up 답변 생성
            result = generate_followup_answer(
                query=query_request.query,
                history=effective_history,
                top_k=query_request.top_k,
                ignore_token_limit=query_request.ignore_token_limit,
                model=query_request.model,
                response_language=query_request.response_language
            )
        else:
            # 독립 질문 답변 생성
            result = generate_answer_with_rag(
                query=query_request.query,
                top_k=query_request.top_k,
                ignore_token_limit=query_request.ignore_token_limit,
                model=query_request.model,
                response_language=query_request.response_language
            )

        # 6. 결과를 Redis에 저장 (TTL: 30분)
        set_cached_rag(cache_key, result)

        # 7. 최근 질문 저장 (rephrase 감지용)
        save_query(query_request.query)

        # 8. 응답 반환
        return {
            "success": True,
            "data": result,
            "cached": False,
            "independent_question": is_independent  # 디버깅용
        }
    except Exception as e:
        logger.exception("RAG search failed")
        raise HTTPException(status_code=500, detail="RAG search failed") from e

@app.post("/api/search/stream")
async def search_stream(query_request: QueryRequest):
    """SSE streaming RAG search — first token arrives within ~1s."""
    import time

    start_time = time.time()

    effective_history = query_request.history
    is_independent = False
    if query_request.history and len(query_request.history) > 0:
        is_independent = is_independent_question(query_request.query, query_request.history)
        if is_independent:
            effective_history = []

    cache_key_parts = [
        normalize_query(query_request.query),
        str(query_request.top_k),
        str(query_request.ignore_token_limit),
        query_request.model,
        query_request.response_language
    ]
    if effective_history and len(effective_history) > 0:
        history_dicts = []
        for msg in effective_history:
            if isinstance(msg, dict):
                history_dicts.append(msg)
            else:
                history_dicts.append({"role": msg.role, "content": msg.content})
        history_str = json.dumps(history_dicts, ensure_ascii=False, sort_keys=True)
        history_hash = hashlib.md5(history_str.encode('utf-8')).hexdigest()
        cache_key_parts.append(f"history:{history_hash}")
    cache_key = "|".join(cache_key_parts)

    cached_result = get_cached_rag(cache_key)
    if cached_result:
        save_query(query_request.query)
        cache_elapsed = time.time() - start_time

        def cache_gen():
            answer = cached_result.get('answer', '')
            yield f'data: {json.dumps({"type": "token", "content": answer})}\n\n'
            yield f'data: {json.dumps({"type": "sources", "sources": cached_result.get("sources", [])})}\n\n'
            yield f'data: {json.dumps({"type": "done", "usage": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}, "elapsed_time": cache_elapsed, "cached": True, "response_language": query_request.response_language})}\n\n'

        return StreamingResponse(cache_gen(), media_type="text/event-stream")

    if effective_history and len(effective_history) > 0:
        gen = generate_followup_stream(
            query=query_request.query,
            history=effective_history,
            top_k=query_request.top_k,
            ignore_token_limit=query_request.ignore_token_limit,
            model=query_request.model,
            response_language=query_request.response_language
        )
    else:
        gen = generate_answer_stream(
            query=query_request.query,
            top_k=query_request.top_k,
            ignore_token_limit=query_request.ignore_token_limit,
            model=query_request.model,
            response_language=query_request.response_language
        )

    def stream_and_cache():
        full_answer = ""
        final_sources = []
        final_usage = {}
        final_elapsed = 0.0

        for event_str in gen:
            yield event_str
            if event_str.startswith('data: '):
                try:
                    data = json.loads(event_str[6:])
                    if data['type'] == 'token':
                        full_answer += data['content']
                    elif data['type'] == 'sources':
                        final_sources = data['sources']
                    elif data['type'] == 'done':
                        final_usage = data.get('usage', {})
                        final_elapsed = data.get('elapsed_time', 0.0)
                except Exception:
                    pass

        set_cached_rag(cache_key, {
            'answer': full_answer,
            'sources': final_sources,
            'query': query_request.query,
            'usage': final_usage,
            'elapsed_time': final_elapsed,
            'response_language': query_request.response_language
        })
        save_query(query_request.query)

    return StreamingResponse(stream_and_cache(), media_type="text/event-stream")


@app.get("/health")
async def health():
    """헬스 체크"""
    return {"status": "healthy"}

@app.delete("/api/cache")
async def clear_cache():
    """모든 캐시 삭제"""
    try:
        clear_all_cache()
        return {
            "success": True,
            "message": "모든 캐시가 삭제되었습니다."
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }

@app.get("/api/cache/stats")
async def cache_stats():
    """캐시 통계 조회"""
    try:
        stats = get_cache_stats()

        # 캐시 히트율 계산
        total_requests = stats.get("hits", 0) + stats.get("misses", 0)
        hit_rate = (stats.get("hits", 0) / total_requests * 100) if total_requests > 0 else 0

        return {
            "success": True,
            "stats": {
                "total_keys": stats.get("total_keys", 0),
                "hits": stats.get("hits", 0),
                "misses": stats.get("misses", 0),
                "hit_rate": f"{hit_rate:.1f}%",
                "memory_used": stats.get("memory_used", "0")
            }
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }

@app.get("/api/notes/count")
async def get_notes_count():
    """전체 노트 개수 조회"""
    try:
        from search.document_index import es, INDEX_NAME

        # Elasticsearch에서 전체 문서 개수 조회
        count_result = es.count(index=INDEX_NAME)
        total_count = count_result["count"]

        return {
            "success": True,
            "count": total_count
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "count": 0
        }

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
