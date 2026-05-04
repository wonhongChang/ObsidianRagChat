# Obsidian RAG Chat

Obsidian 노트를 RAG 시스템으로 변환해 GPT와 대화하는 웹 인터페이스.

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![Docker](https://img.shields.io/badge/docker-%230db7ed.svg?logo=docker&logoColor=white)](https://www.docker.com/)
[![FastAPI](https://img.shields.io/badge/FastAPI-005571?logo=fastapi)](https://fastapi.tiangolo.com/)

---

## 아키텍처

```
사용자 브라우저 :3000
    │
    ▼
[nginx] React + Vite + TypeScript (frontend)
    │  SSE 프록시 → /api/*
    ▼
[app.py] FastAPI (내부 :8000)
    ├─ 규칙 기반 독립/Follow-up 감지 (포함 관계·유사도·#태그 등)
    ├─ Redis 캐시 조회 → 히트 시 즉시 반환 (TTL 30분)
    │
    ▼ (미스 시)
[rag/generator.py]
    ├─ Follow-up → GPT standalone rewrite → 벡터 검색
    ├─ 태그 추출 → Elasticsearch 경로 필터 (대소문자 모두 매칭)
    ├─ Qdrant 청크 벡터 검색 (limit × 3 → 파일 단위 병합 → top-k)
    ├─ 파일명 키워드 매칭 → 스코어 부스트 (한국어·영어·일본어/CJK 대응)
    ├─ parent_text 기반 컨텍스트 구성 (max 110K 토큰)
    └─ GPT 답변 생성 → SSE 스트리밍 (첫 토큰 ~1초 이내)
    │
    ▼
[sync_documents.py] 10분 주기
    ├─ MD5 해시 기반 변경 감지
    ├─ 헤더 기반 청킹 (512 토큰, 50 overlap)
    ├─ "파일명: {name}\n{text}" 형식으로 임베딩 (파일명 의미 반영)
    ├─ Qdrant 100청크 배치 upsert
    └─ Elasticsearch 파일 단위 bulk index
```

---

## 기술 스택

| 역할 | 기술 |
|------|------|
| Frontend | React 19 + Vite + TypeScript + Tailwind CSS v4 |
| Web Framework | FastAPI (Python 3.11+) |
| Vector DB | Qdrant Cloud |
| Full-text Search | Elasticsearch 8.18 |
| Cache | Redis 7.2 (TTL 30분) |
| LLM | GPT-4o-mini / GPT-5-mini (설정 가능) |
| Embedding | text-embedding-3-small (1536dim, 파일명 prefix 포함) |
| Container | Docker + Docker Compose |

---

## 빠른 시작

### 1. 저장소 클론

```bash
git clone https://github.com/wonhongChang/ObsidianRagChat.git
cd ObsidianRagChat
```

### 2. 환경 변수 설정

`.env` 파일 생성:

```bash
# 필수
OPENAI_API_KEY=sk-...
QDRANT_URL=https://your-cluster.cloud.qdrant.io:6333
QDRANT_API_KEY=your-qdrant-api-key
OBSIDIAN_VAULT_PATH=/path/to/your/obsidian/vault

# Docker 내부 서비스 (변경 불필요)
ELASTICSEARCH_HOST=http://elasticsearch:9200
REDIS_HOST=redis
REDIS_PORT=6379

# 선택
CACHE_TTL=1800        # Redis TTL (초, 기본 30분)
INTERVAL_SECONDS=600  # 동기화 주기 (초, 기본 10분)
```

### 3. 실행

```bash
docker-compose up -d

# 로그 확인
docker-compose logs -f web
docker-compose logs -f sync
```

### 4. 접속

```
http://localhost:3000
```

---

## 사용 방법

#### 일반 질문
```
"Obsidian RAG Chat의 동기화 방식 알려줘"
→ 전체 노트 벡터 검색 (기본 top_k=5)
```

#### 태그 필터
```
"#RagChat 태그 문서에서 내용 요약해줘"
→ RagChat 태그 문서만 검색
```

#### Follow-up
```
질문1: "Redis 캐싱 전략 설명해줘"
질문2: "그럼 TTL은 어떻게 설정해?"
→ 히스토리 기반 standalone rewrite 후 검색
```

---

## API

| Method | Endpoint | 설명 |
|--------|----------|------|
| `POST` | `/api/search` | RAG 검색 (전체 응답 반환) |
| `POST` | `/api/search/stream` | RAG 검색 SSE 스트리밍 |
| `DELETE` | `/api/cache` | 캐시 전체 삭제 |
| `GET` | `/api/cache/stats` | 캐시 통계 |
| `GET` | `/api/notes/count` | 전체 노트 수 |
| `GET` | `/health` | 헬스 체크 |

**POST /api/search 요청 파라미터:**

```json
{
  "query": "질문 내용",
  "top_k": 5,
  "model": "gpt-4o-mini",
  "ignore_token_limit": false,
  "history": []
}
```

---

## 프로젝트 구조

```
ObsidianRagChat/
├── app.py                     # FastAPI 서버, 캐시/질문감지 라우팅
├── sync_documents.py          # 증분 동기화 (Hash 기반)
│
├── frontend/                  # React + Vite + TypeScript UI
│   ├── src/
│   │   ├── api/stream.ts      # SSE async generator
│   │   ├── components/        # ChatMessage, ChatInput, SettingsBar 등
│   │   ├── hooks/useChat.ts   # Zustand 상태 관리
│   │   └── types/index.ts
│   ├── nginx.conf             # SSE 프록시 + Docker DNS resolver
│   └── package.json
│
├── embed/
│   ├── chunker.py             # 헤더 기반 청킹 + 슬라이딩 윈도우
│   ├── embedder.py            # OpenAI 임베딩 (배치 인덱스 안전 처리)
│   ├── document_loader.py     # 마크다운 로더
│   └── vector_store.py        # Qdrant 클라이언트
│
├── rag/
│   └── generator.py           # 검색 + 컨텍스트 구성 + GPT 호출
│
├── search/
│   ├── document_index.py      # Elasticsearch (lowercase_normalizer)
│   ├── cache.py               # Redis 캐싱 + 쿼리 정규화
│   └── question_detector.py   # 독립/Follow-up 감지 (규칙 기반)
│
├── scripts/
│   ├── clear_cache.py
│   └── clear_qdrant.py
│
├── tests/
│   ├── test_question_detector.py  # 질문 감지 유닛 테스트 (24개)
│   └── README.md
│
├── docker-compose.yml
├── Dockerfile.frontend
├── Dockerfile.web
├── Dockerfile.sync
└── requirements.txt
```

---

## 주요 명령어

```bash
# 캐시 초기화
docker-compose exec web python scripts/clear_cache.py
curl -X DELETE http://localhost:3000/api/cache

# Qdrant 초기화 (재동기화 필요 시)
docker-compose run --rm sync python -c "from embed.vector_store import client, COLLECTION_NAME; client.delete_collection(COLLECTION_NAME)"
docker-compose restart sync

# ES 인덱스 재생성 (lowercase_normalizer 적용)
curl -X DELETE http://localhost:9201/obsidian_notes
docker-compose restart sync

# 테스트
docker-compose exec web python -m pytest tests/ -v
```

---

## 트러블슈팅

**검색 결과 없음**
```bash
curl http://localhost:9201/_cluster/health
curl http://localhost:3000/api/notes/count
```

**태그 필터 안 됨** — ES 인덱스 재생성 필요 (위 주요 명령어 참조)

**응답 느림** — `rag_query.log` 에서 병목 확인, top_k 줄이기

**Docker 빌드 실패**
```bash
docker-compose build --no-cache
docker-compose down -v && docker-compose up -d
```

---

## 보안

- `.env` 파일은 절대 커밋하지 마세요 (`.gitignore` 포함됨)
- `OPENAI_API_KEY`, `QDRANT_API_KEY` 외부 노출 금지
