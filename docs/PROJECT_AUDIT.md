# ObsidianRagChat 프로젝트 점검 보고서

> 점검 일자: 2026-05-02

---

## 1. 아키텍처 개요

```
사용자 질문
    │
    ▼
[app.py] FastAPI :8001
    ├─ 질문 유형 감지 (독립 / Follow-up)
    ├─ Redis 캐시 조회 (TTL 30분)
    │
    ▼
[rag/generator.py] RAG 파이프라인
    ├─ 쿼리 임베딩 (text-embedding-3-small)
    ├─ 태그 필터 → Elasticsearch 경로 필터링
    ├─ Qdrant 벡터 검색 (COSINE)
    ├─ 토큰 기반 컨텍스트 구성 (max 110K)
    └─ GPT-4o-mini 답변 생성
    │
    ▼
[sync_documents.py] 10분 주기 배치
    ├─ MD5 해시 기반 변경 감지
    ├─ Qdrant upsert
    └─ Elasticsearch bulk index
```

---

## 2. 발견된 버그 / 문제점

### 2-1. 심각 (즉시 수정 필요)

#### [BUG-1] Qdrant delete 파라미터 타입 오류
**파일**: `embed/vector_store.py:106-109`

```python
# 현재 (오류)
client.delete(
    collection_name=COLLECTION_NAME,
    points_selector=delete_ids   # list[int] → 타입 오류
)

# 수정
from qdrant_client.models import PointIdsList
client.delete(
    collection_name=COLLECTION_NAME,
    points_selector=PointIdsList(ids=delete_ids)
)
```

**영향**: 파일 삭제 시 항상 실패 → 삭제된 파일이 Qdrant에 좀비로 남음. 검색 결과에 존재하지 않는 파일 경로가 포함됨.

---

### 2-2. 중요 (기능 영향)

#### [BUG-2] 문서 수정 시 캐시 무효화 없음
**파일**: `sync_documents.py`, `search/cache.py`

`sync_documents.py`가 문서를 갱신해도 Redis에 아무 알림이 없음. TTL 30분이 지나야 캐시 만료되어 최대 30분간 오래된 답변 반환.

```python
# sync_documents.py - 변경 감지 후 캐시 무효화 추가
if new_files or updated_files or deleted_files:
    from search.cache import clear_all_cache
    clear_all_cache()
    print("🗑️  문서 변경 감지 → 캐시 전체 초기화")
```

또는 TTL을 sync 주기(10분)에 맞춰 단축:
```bash
CACHE_TTL=600  # .env
```

**영향**: 노트 수정 후에도 최대 30분간 수정 전 내용 기반 답변 반환.

---

#### [BUG-3] Qdrant scroll 10,000개 하드코딩
**파일**: `embed/vector_store.py:44`

```python
# 현재
result = client.scroll(collection_name=COLLECTION_NAME, limit=10000, ...)
# next_page_offset 무시 → 10,001번째 문서부터 누락

# 수정: 페이지네이션 처리
all_points = []
offset = None
while True:
    result, offset = client.scroll(
        collection_name=COLLECTION_NAME,
        limit=1000,
        offset=offset,
        with_payload=True,
        with_vectors=False
    )
    all_points.extend(result)
    if offset is None:
        break
```

**영향**: 노트가 10,000개 초과 시 변경 감지 누락 → 오래된 임베딩 유지.

---

#### [BUG-3] ES `bulk()` 반환값 처리 불완전
**파일**: `search/document_index.py:76-83`

```python
# 현재
success, failed = bulk(es, actions, raise_on_error=False)
# failed 항목의 에러 메시지를 무시함

# 수정: 실패 내용 로깅
if failed:
    for err in failed[:3]:  # 처음 3개만 출력
        print(f"  ❌ 실패 문서: {err}")
```

**영향**: 인덱싱 실패 원인 파악 불가.

---

#### [BUG-4] `get_path_id()` 해시 충돌 가능성
**파일**: `embed/vector_store.py:18`

```python
# 현재: MD5 헥스의 앞 8자리 → 최대 약 43억 가지
int(hashlib.md5(path.encode('utf-8')).hexdigest()[:8], 16)

# 약 9,000개 파일에서 50% 이상 확률로 충돌 발생 (Birthday Problem)
# 수정: 전체 해시 사용
int(hashlib.md5(path.encode('utf-8')).hexdigest(), 16) % (2**63)
```

**영향**: 두 파일의 ID가 겹치면 한 파일의 벡터가 덮어씌워짐.

---

### 2-3. 경미 (개선 권장)

#### [OPT-1] `embedder.py` 배치 인덱스 불일치 ✅ 완료
**파일**: `embed/embedder.py`

빈 텍스트가 중간에 있으면 반환되는 임베딩 배열 인덱스가 원본 `texts` 배열 인덱스와 어긋남.
`valid_indices` 추적 방식으로 수정: 결과 배열 길이는 항상 입력과 동일, 빈 텍스트 위치는 `None`.

#### [OPT-2] ES 태그 필터 normalizer 적용 ✅ 완료
**파일**: `search/document_index.py`, `rag/generator.py`

`lowercase_normalizer`를 ES 인덱스 설정에 추가, `tags` 필드에 적용.
`generator.py` 태그 변형 생성 코드를 `{tag.lower() for tag in filter_tags}` 한 줄로 단순화.

> **주의**: 기존 ES 인덱스에는 소급 적용되지 않음. 인덱스 재생성 필요 (`DELETE /obsidian_notes` 후 sync 재실행).

#### [OPT-3] `question_detector.py` 한국어/일본어 대명사 정규식 누락
**파일**: `search/question_detector.py:67-69`

**한국어 문제**: 조사 축약형(`건`=것은, `게`=것이)과 일부 조사(`도`, `만`, `랑`, `로`)가 목록에 없어서 Follow-up 미감지.

```python
# 현재: 감지 안 되는 케이스
"그건 뭐야?"    # (그) + 건  → 조사 목록 없음
"이건 어때?"    # (이것) + 건 → 조사 목록 없음
"그게 맞아?"    # (그) + 게  → 조사 목록 없음
"그것도 알려줘" # (그것) + 도 → 조사 목록 없음
"해당 문서는?"  # GPT 프롬프트엔 있으나 규칙에 없음
```

**일본어 문제**: 소유 지시어 `その`/`この`/`あの`가 누락됨.

```python
# 수정
if (re.match(r'^\s*(그것|이것|저것|그거|이거|그게|이게|저게|그건|이건|저건|해당)(?:\s|을|를|이|가|은|는|에|의|도|만|로|랑|까지)', query) or
    re.match(r'^\s*(それ|これ|あれ|その|この|あの)', query) or
    re.match(r'^\s*(it|that|this)\s', query, re.IGNORECASE)):
```

#### [OPT-4] 캐시 키 쿼리 정규화 없음
**파일**: `app.py:68-73`, `search/cache.py`

대소문자·공백 차이가 있으면 동일 질문도 다른 캐시 키로 처리됨.

```python
# "redis란?" vs "Redis란?" → 별도 캐시

# 수정: cache.py에 정규화 함수 추가
import re
def normalize_query(query: str) -> str:
    return re.sub(r'\s+', ' ', query.strip().lower())

# app.py 캐시 키 생성 시 적용
cache_key_parts = [
    normalize_query(query_request.query),  # 원본 대신 정규화값 사용
    str(query_request.top_k),
    str(query_request.ignore_token_limit),
    query_request.model
]
```

#### [ARCH-1] question_detector GPT 의존성 제거 ✅ 완료

`question_detector.py`에서 GPT-4o-mini 호출 및 OpenAI 클라이언트를 완전히 제거.

- GPT 실패 시 `True` (독립 질문) 반환하던 fallback → 오답 유발 가능성
- 규칙 미결정 시 `False` (Follow-up) 로 변경 — 오답 방지 우선
- `openai` import 제거로 모듈 로딩 속도 개선 및 API key 불필요
- `[를을]` 변형 추가, `그게/이게/그건/이건` 등 조사 축약형 보강

---

#### [OPT-5] Follow-up 질문 standalone rewrite 없음
**파일**: `rag/generator.py` `generate_followup_answer()`

Follow-up 질문("더 자세히", "예시는?")을 그대로 임베딩해서 Qdrant에 보내고 있어 벡터 검색 품질 저하. 모호한 쿼리로 엉뚱한 문서가 검색될 수 있음.

```
# 현재
"더 자세히 설명해줘" → 임베딩 → Qdrant (검색 부정확)

# 개선
"더 자세히 설명해줘" + history → GPT rewrite
→ "Obsidian RAG Chat의 동기화 방식을 자세히 설명해줘" → 임베딩 → Qdrant (정확)
```

삽입 위치: `generate_followup_answer()` 진입 직후, `embed_texts()` 호출 전.
GPT 호출 1회 추가되므로 비용과 품질 트레이드오프 고려 필요.

#### [OPT-6] `recent_queries` 서버 메모리 저장
**파일**: `search/question_detector.py:20`

```python
recent_queries = deque(maxlen=10)  # 프로세스 메모리 → 서버 재시작 시 초기화
```

서버 재시작 후 Rephrase 감지가 초기화되어 동일 질문 캐시 히트 불가.

```python
# 개선: Redis에 저장
def save_query(query: str):
    redis_client.lpush("recent_queries", query)
    redis_client.ltrim("recent_queries", 0, 9)  # 최근 10개만 유지
```

#### [OPT-8] `clear_cache.py` import 경로 오류
**파일**: `clear_cache.py`

```python
# 실제 모듈명: search.cache
from search.cache import ...
```

---

## 3. 코드 품질 이슈

| 항목 | 위치 | 내용 |
|------|------|------|
| 이중 중복 제거 | `generator.py:136-148`, `generator.py:199-210` | `search_relevant_notes()`와 `generate_answer_with_rag()` 양쪽에서 중복 제거 실행 |
| 토큰 재계산 | `generator.py:242-260` | `count_tokens(note_text)` 동일 텍스트에 대해 같은 루프 내 2회 호출 |
| ES size 역제한 | `generator.py:79-84` | `limit > 200`이면 `es_size = limit * 2`로 오히려 작아짐 |
| `.env` API 키 | `.env` | `OPENAI_API_KEY`, `QDRANT_API_KEY` 파일에 평문 저장 → `.gitignore` 확인 필수 |

---

## 4. 청킹 전략

### 현황 및 문제

현재 구조는 **파일 단위 임베딩**:

```
note.md (전체 파일)
    └─ 최대 8000자 잘라서 embed_texts() 호출
       → 1 파일 = 1 벡터
```

**문제**:
- 8000자 이상 노트는 후반부 내용이 완전히 버려짐
- 하나의 벡터로 긴 문서의 다양한 주제를 표현 → 검색 정밀도 저하
- `top_k=5`라면 5개 파일 전체를 컨텍스트에 넣어야 해서 토큰이 급증

---

### 권장 청킹 전략: 계층형 청킹 (Hierarchical Chunking)

Obsidian 노트의 특성(마크다운 헤더 계층, 짧은 메모 ~ 긴 글 혼재)에 맞춘 전략.

#### 전략 1: 헤더 기반 청킹 (Primary)

```python
def chunk_by_headers(text: str, max_chunk_tokens: int = 512) -> list[dict]:
    import re
    sections = re.split(r'\n(?=#{1,3} )', text)
    chunks = []
    for section in sections:
        tokens = count_tokens(section)
        if tokens <= max_chunk_tokens:
            chunks.append(section.strip())
        else:
            chunks.extend(sliding_window_split(section, max_chunk_tokens, overlap=50))
    return chunks
```

#### 전략 2: 슬라이딩 윈도우 (Fallback)

헤더가 없는 노트 또는 헤더 섹션이 너무 긴 경우.

```python
def sliding_window_split(text: str, max_tokens: int = 512, overlap: int = 50) -> list[str]:
    tokens = encoding.encode(text)
    step = max_tokens - overlap
    chunks = []
    for i in range(0, len(tokens), step):
        chunk_tokens = tokens[i:i + max_tokens]
        chunks.append(encoding.decode(chunk_tokens))
    return chunks
```

#### 전략 3: Small-to-Big 검색

청크를 임베딩/검색에 사용하되, 실제 컨텍스트는 상위 문서를 포함.

```
인덱싱: 청크 단위로 임베딩 저장
검색:   청크로 유사도 계산 → 해당 파일 전체(또는 인접 섹션) 반환

payload:
  chunk_text: "설치 방법\n1. pip install..."   # 임베딩 대상
  full_text:  전체 노트 or 상위 섹션 텍스트     # 컨텍스트에 삽입
  source_path: "projects/A.md"
  section: "## 설치 방법"
  chunk_index: 3
```

---

### 구현 로드맵

#### Phase 1: 즉시 적용 가능 (임베딩 재구축 필요)

**신규 파일**: `embed/chunker.py`

```python
MAX_CHUNK_TOKENS = 512
OVERLAP_TOKENS = 50

def chunk_document(doc: dict) -> list[dict]:
    text = doc["text"]
    chunks = chunk_by_headers(text, MAX_CHUNK_TOKENS)

    result = []
    for i, chunk_text in enumerate(chunks):
        if not chunk_text.strip():
            continue
        result.append({
            "path": doc["path"],
            "filename": doc["filename"],
            "tags": doc["tags"],
            "mtime": doc["mtime"],
            "hash": doc["hash"],
            "section": extract_section_title(chunk_text),
            "chunk_index": i,
            "chunk_text": chunk_text,           # 임베딩/검색용
            "parent_text": text[:4000],          # 컨텍스트 삽입용
        })
    return result
```

**Qdrant payload 변경**:

| 필드 | 현재 | 변경 후 |
|------|------|---------|
| `text` | 전체 파일 | 청크 텍스트 |
| `parent_text` | 없음 | 파일 상단 4000자 |
| `section` | 없음 | 섹션 제목 |
| `chunk_index` | 없음 | 청크 순서 |

**ID 생성 변경** (BUG-4 해결과 동시에 적용):
```python
chunk_id = f"{doc['path']}::chunk::{chunk_index}"
point_id = int(hashlib.md5(chunk_id.encode()).hexdigest(), 16) % (2**63)
```

---

#### Phase 2: 검색 로직 개선

같은 파일의 여러 청크가 검색됐을 때 파일 단위로 병합 처리:

```python
from collections import defaultdict
file_scores = defaultdict(list)
for r in results:
    file_scores[r.payload["path"]].append(r.score)

best_chunks = {
    path: max(chunks, key=lambda x: x.score)
    for path, chunks in ...
}
```

---

#### Phase 3: 컨텍스트 구성 전략

| 방식 | 컨텍스트 내용 | 토큰 절약 |
|------|-------------|---------|
| **청크만** | 매칭된 청크 텍스트만 | 최대 (80% 절약) |
| **섹션 확장** | 매칭 섹션 + 앞뒤 섹션 | 중간 (50% 절약) |
| **Small-to-Big** | 매칭 청크로 검색, 부모 문서 삽입 | 낮음 (20% 절약) |

권장: **섹션 확장** 방식 (정밀도와 컨텍스트 품질 균형)

---

### 청킹 파라미터 권장값

| 파라미터 | 권장값 | 근거 |
|---------|--------|------|
| `max_chunk_tokens` | 512 | text-embedding-3-small 최적 범위 |
| `overlap_tokens` | 50 | 청크 경계 문장 단절 방지 |
| `min_chunk_tokens` | 30 | 제목만 있는 청크 제외 |
| `parent_text_limit` | 4000자 | 컨텍스트용 상위 문서 크기 |
| `top_k` (검색) | 10~20 청크 | 파일 단위 5개 → 청크 단위로 확장 |
| `top_k` (컨텍스트) | 파일 5개 | 중복 파일 병합 후 상위 5개 |

---

## 5. 우선순위 요약

| 순위 | 항목 | 공수 | 영향 | 상태 |
|------|------|------|------|------|
| 1 | BUG-1: Qdrant delete 수정 | 5분 | 삭제 기능 복구 | ✅ 완료 |
| 2 | BUG-5: 해시 ID 충돌 수정 | 10분 | 데이터 무결성 | ✅ 완료 |
| 3 | BUG-2: 문서 수정 시 캐시 무효화 | 15분 | 오래된 답변 반환 방지 | ✅ 완료 |
| 4 | OPT-3: 대명사 정규식 수정 | 10분 | Follow-up 오감지 수정 | ✅ 완료 |
| 5 | OPT-4: 캐시 키 쿼리 정규화 | 20분 | 캐시 히트율 개선 | ✅ 완료 |
| 6 | BUG-3: scroll 페이지네이션 | 30분 | 대용량 노트 지원 | ✅ 완료 |
| 7 | BUG-4: ES bulk 실패 로깅 | 30분 | 인덱싱 오류 파악 | ✅ 완료 |
| 8 | ARCH-1: question_detector GPT 제거 | 1시간 | 안정성·비용·오답 방지 | ✅ 완료 |
| 9 | OPT-5: standalone rewrite | 1일 | Follow-up 검색 품질 향상 | ✅ 완료 |
| 10 | 청킹 Phase 1 (chunker.py) | 2~3일 | 검색 품질 대폭 향상 | ✅ 완료 |
| 11 | 청킹 Phase 2 (검색 로직) | 1일 | 토큰 효율 개선 | ✅ 완료 |
| 12 | OPT-1: embedder 인덱스 불일치 | 30분 | 빈 청크 시 임베딩 오프셋 방지 | ✅ 완료 |
| 12 | OPT-2: ES 태그 normalizer | 30분 | 태그 대소문자 검색 정확도 개선 | ✅ 완료 |
| 12 | OPT-6: recent_queries Redis 이전 | 30분 | 재시작 후 rephrase 감지 유지 | ⏸️ 보류 (효과 대비 복잡도 높음) |
| 12 | OPT-7 | — | 항목 없음 (번호 오류로 누락됨) | N/A |
| 12 | OPT-8: clear_cache.py import 오류 | 5분 | 스크립트 정상 실행 | ✅ 완료 |
| 13 | README 업데이트 | 30분 | 아키텍처·설정 문서 최신화 | - |

---

## 6. README 업데이트 항목

모든 수정 완료 후 반영:

| 항목 | 내용 |
|------|------|
| 아키텍처 설명 | 청킹 전략 적용 시 파일 단위 → 청크 단위 임베딩으로 변경 반영 |
| `.env` 설정 항목 | 추가/변경된 환경변수 반영 (`CACHE_TTL` 등) |
| 시스템 요구사항 | 변경된 의존성 반영 |
| 일본어 README | 한국어 README와 동기화 |
