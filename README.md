# 🧠 Obsidian RAG Chat

> **개인 노트를 AI 비서로 바꾸는 지능형 검색 시스템**

Obsidian 노트를 RAG(Retrieval-Augmented Generation) 시스템으로 변환하여 GPT와 자연스럽게 대화할 수 있는 웹 인터페이스입니다.

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![Docker](https://img.shields.io/badge/docker-%230db7ed.svg?logo=docker&logoColor=white)](https://www.docker.com/)
[![FastAPI](https://img.shields.io/badge/FastAPI-005571?logo=fastapi)](https://fastapi.tiangolo.com/)

---

## ✨ 주요 특징

### 🎯 핵심 기능
- **🔍 하이브리드 검색**: Elasticsearch + Qdrant 벡터 DB로 정확도와 속도 향상
- **⚡ 스마트 캐싱**: Redis 기반 응답 캐싱으로 ~20배 속도 향상 (비용 100% 절감)
- **🤖 지능형 질문 감지**: 규칙 기반 + GPT-4o-mini로 독립/Follow-up 질문 자동 구분 (90% GPT 호출 제거)
- **🏷️ 태그 필터링**: `#Subway`, `#RagChat` 등 태그 기반 문서 검색
- **💬 대화 맥락 유지**: 이전 대화 히스토리를 활용한 자연스러운 대화
- **🔄 실시간 동기화**: 10분마다 Obsidian vault 변경사항 자동 감지 (증분 업데이트)

### 💡 최적화 (2025-11-11 적용)
- **📊 토큰 카운팅 캐싱**: LRU 캐시로 중복 인코딩 제거 (-70~85% 시간)
- **🎯 규칙 기반 질문 감지**: 90% GPT API 호출 제거 (-0.5~2초)
- **🚀 동적 ES 크기 조정**: 필요한 만큼만 요청 (-60% 검색 시간)
- **⚡ 기본 top_k=5**: 불필요한 노트 제거 (-27.6% 응답 시간, -69% 토큰)
- **💰 비용 투명성**: 실시간 토큰 사용량 및 예상 비용 표시
- **📈 확장성**: 10만+ 노트까지 확장 가능한 아키텍처

---

## 🧠 RAG란?

**RAG (Retrieval-Augmented Generation)** = 검색 기반 생성

```
┌─────────────┐
│ 사용자 질문  │  "#Subway 태그 문서에서 中目黒から東新宿への行き方 알려줘"
└──────┬──────┘
       ↓
┌──────────────────────────────────┐
│  1️⃣ 규칙 기반 질문 감지            │  → #태그 시작 = 독립 질문 (0초)
└──────┬───────────────────────────┘
       ↓
┌──────────────────────────────────┐
│  2️⃣ Redis 캐시 체크               │  → 히트 시 즉시 반환 ⚡ (0.001초)
└──────┬───────────────────────────┘
       ↓ (미스)
┌──────────────────────────────────┐
│  3️⃣ 태그 추출 (#Subway)           │
└──────┬───────────────────────────┘
       ↓
┌──────────────────────────────────┐
│  4️⃣ Elasticsearch 필터링          │  → 1개 문서 (태그 일치, 0.006초)
└──────┬───────────────────────────┘
       ↓
┌──────────────────────────────────┐
│  5️⃣ Query 임베딩 생성              │  → OpenAI API (0.58초)
└──────┬───────────────────────────┘
       ↓
┌──────────────────────────────────┐
│  6️⃣ Qdrant 벡터 검색 (5개)        │  → 유사도 순 정렬 (1.08초)
└──────┬───────────────────────────┘
       ↓
┌──────────────────────────────────┐
│  7️⃣ 토큰 카운팅 (LRU 캐시)         │  → 즉시 완료 (~0초)
└──────┬───────────────────────────┘
       ↓
┌──────────────────────────────────┐
│  8️⃣ GPT-4o-mini 답변 생성         │  → "中目黒에서..." (1.9초)
└──────┬───────────────────────────┘
       ↓
┌──────────────────────────────────┐
│  9️⃣ Redis 캐싱 & 응답             │  → TTL: 30분
└──────────────────────────────────┘

총 처리 시간: 3.58초 (개선 전: 6~16초)
```

---

## 🛠️ 기술 스택

### Backend
- **Framework**: FastAPI (Python 3.11+)
- **Vector DB**: Qdrant Cloud (1GB 무료 티어)
- **Search Engine**: Elasticsearch 8.18
- **Cache**: Redis 7.2 (TTL: 30분)

### AI/ML
- **LLM**: OpenAI GPT-4o-mini / GPT-5-mini
- **Embedding**: text-embedding-3-small (1536차원)
- **Token Counting**: tiktoken (cl100k_base) + LRU 캐시

### Infrastructure
- **Container**: Docker + Docker Compose
- **Sync**: 증분 동기화 (10분 간격, Hash 기반 변경 감지)
- **Storage**: Obsidian vault (마운트)

### Frontend
- **UI**: Vanilla JavaScript (반응형)
- **Templating**: Jinja2
- **Styling**: CSS3 (그라데이션 디자인)

---

## 📦 빠른 시작 (Docker 권장)

### 1️⃣ 저장소 클론

```bash
git clone https://github.com/yourusername/ObsidianRagChat.git
cd ObsidianRagChat
```

### 2️⃣ 환경 변수 설정

`.env` 파일 생성:

```bash
# OpenAI API
OPENAI_API_KEY=sk-your-openai-api-key

# Qdrant Cloud
QDRANT_URL=https://your-cluster.cloud.qdrant.io:6333
QDRANT_API_KEY=your-qdrant-api-key

# Elasticsearch (Docker 내부)
ELASTICSEARCH_HOST=elasticsearch
ELASTICSEARCH_PORT=9200

# Redis (Docker 내부)
REDIS_HOST=redis
REDIS_PORT=6379

# Obsidian Vault
OBSIDIAN_VAULT_PATH=/mnt/vault  # Docker 내부 경로
```

### 3️⃣ Obsidian Vault 경로 설정

`docker-compose.yml`의 volumes 경로 수정:

```yaml
volumes:
  - /path/to/your/obsidian/vault:/mnt/vault:ro  # 실제 경로로 변경
```

### 4️⃣ Docker 실행

```bash
# 컨테이너 빌드 및 실행
docker-compose up -d

# 로그 확인
docker-compose logs -f web
docker-compose logs -f sync
```

### 5️⃣ 웹 인터페이스 접속

```
http://localhost:8001
```

---

## 🚀 사용 방법

### 💬 기본 사용

#### 일반 질문
```
질문: "Obsidian RAG Chat에 대해서 알려줘"
→ 전체 노트에서 관련 내용 검색 (기본 5개)
→ 처리 시간: ~13.7초, 토큰: 25,739개
```

#### 태그 기반 검색 (최고 성능 ⚡)
```
질문: "#Subway 태그 문서에서 中目黒から東新宿への行き方 알려줘"
→ Subway 태그 문서만 검색 (1개)
→ 처리 시간: ~3.6초, 토큰: 273개
```

#### Follow-up 질문
```
질문1: "#interview 문서의 면접 준비사항 알려줘"
질문2: "자기소개는 어떻게 준비해?"
→ 히스토리에서 태그 상속 (#interview)
→ 대화 맥락 유지
```

### ⚙️ UI 컨트롤

#### 최대 노트 개수
- **5개 (권장 ⚡)**: 빠르고 충분한 답변 품질 (기본값)
- **6-20개 (보통)**: 더 많은 컨텍스트 필요 시
- **21-50개 (느림 ⏳)**: 포괄적 검색
- **51개+ (매우 느림 🐌)**: 전체 검색 (경고 표시)

#### AI 모델 선택
- **GPT-4o-mini**: 빠르고 저렴 ($0.15/1M 입력)
- **GPT-5-mini**: 고성능 ($0.25/1M 입력)

#### 최대 컨텍스트 토큰
- **기본**: 110,000 토큰
- **최대**: 180,000 토큰 (활성화 시)

#### 대화 초기화
히스토리 누적 방지 및 캐싱 최적화

---

## 📊 성능 지표

### 🎯 검색 성능 (2025-11-11 측정)

**태그 필터 검색** (최적):
| 항목 | 캐시 미스 | 캐시 히트 | 개선율 |
|------|----------|----------|-------|
| 응답 시간 | 3.58초 | 0.001초 | **3,580배** ⚡ |
| 토큰 사용 | 273 | 0 | **100%** 절감 💰 |
| API 비용 | ~$0.0001 | $0.000 | **무료** ✅ |

**일반 검색** (top_k=5):
| 항목 | 캐시 미스 | 캐시 히트 | 개선율 |
|------|----------|----------|-------|
| 응답 시간 | 13.69초 | 0.001초 | **13,690배** ⚡ |
| 토큰 사용 | 25,739 | 0 | **100%** 절감 💰 |
| API 비용 | ~$0.004 | $0.000 | **무료** ✅ |

**비교** (top_k 영향):
| 설정 | 처리 시간 | 토큰 사용량 | 개선 효과 |
|------|----------|----------|----------|
| top_k=5 (권장) | 13.69초 | 25,739 | **기준** |
| top_k=359 (전체) | 18.91초 | 82,964 | -27.6% 느림 |

### 📈 캐시 통계

| 질문 유형 | 캐시 히트율 | 평균 절감 |
|---------|-----------|---------|
| 독립 질문 | 60-80% | $0.003/쿼리 |
| Follow-up | 20-40% | $0.001/쿼리 |
| **평균** | **~72%** | **$0.002/쿼리** |

### 💰 비용 분석

**월 1000 쿼리 기준** (top_k=5):
- **캐싱 전**: $4.00
- **캐싱 후 (72% 히트)**: $1.12
- **절감액**: $2.88 (72% 절감)

**top_k 비교** (캐싱 전):
- **top_k=5**: $4.00/월
- **top_k=359**: $13.00/월
- **절감액**: $9.00 (69% 절감)

---

## 📁 프로젝트 구조

```
ObsidianRagChat/
├── 📄 app.py                          # FastAPI 웹 서버
├── 📄 sync_documents.py               # 증분 동기화 (10분, Hash 기반)
│
├── 📂 embed/                          # 임베딩 & 벡터 DB
│   ├── embedder.py                    # OpenAI 임베딩
│   ├── document_loader.py             # 마크다운 로더
│   └── vector_store.py                # Qdrant 클라이언트 (증분 업데이트)
│
├── 📂 rag/                            # RAG 엔진
│   └── generator.py                   # 검색 + GPT 생성 (최적화됨)
│
├── 📂 search/                         # 검색 & 캐싱
│   ├── document_index.py              # Elasticsearch 클라이언트
│   ├── cache.py                       # Redis 캐싱 (독립 질문 감지)
│   └── question_detector.py           # 질문 감지 (규칙 + GPT)
│
├── 📂 scripts/                        # 유틸리티
│   ├── clear_cache.py                 # 캐시 삭제
│   ├── clear_qdrant.py                # Qdrant 초기화
│   ├── migrate_qdrant_payload.py      # DB 마이그레이션
│   └── add_qdrant_index.py            # 태그 인덱싱
│
├── 📂 tests/                          # 테스트
│   └── test_question_detector.py      # 질문 감지 테스트 (22개)
│
├── 📂 templates/                      # 프론트엔드
│   └── chat.html                      # 채팅 UI (성능 경고 포함)
│
├── 📄 docker-compose.yml              # Docker 구성
├── 📄 Dockerfile.web                  # 웹 서버 이미지
├── 📄 Dockerfile.sync                 # 동기화 이미지
├── 📄 requirements.txt                # Python 패키지
├── 📄 .env                            # 환경 변수 (비공개)
│
└── 📄 README.md                       # 이 파일
```

---

## 🐳 Docker 서비스

```yaml
services:
  web (FastAPI)      # 포트 8001:8000
  sync (배치)        # 10분마다 실행
  elasticsearch      # 포트 9201:9200
  redis              # 포트 6379:6379
```

### 주요 명령어

```bash
# 전체 재시작
docker-compose restart

# 로그 확인
docker-compose logs -f web
docker-compose logs -f sync

# 캐시 초기화
docker-compose exec web python scripts/clear_cache.py
curl -X DELETE http://localhost:8001/api/cache

# Qdrant 초기화
docker-compose exec web python scripts/clear_qdrant.py

# 캐시 통계
curl http://localhost:8001/api/cache/stats

# 전체 노트 개수
curl http://localhost:8001/api/notes/count

# 컨테이너 상태
docker-compose ps

# 정지
docker-compose down
```

---

## 🔧 고급 설정

### 캐싱 전략

**캐시 키 구조** (`app.py:67-90`):
```python
# 독립 질문
cache_key = f"{query}|{top_k}|{ignore_token_limit}|{model}"

# Follow-up 질문
cache_key = f"{query}|{top_k}|{ignore_token_limit}|{model}|history:{hash}"
```

**독립 질문 감지** (`search/question_detector.py`):
```python
# 규칙 기반 (90% GPT 호출 제거)
if query.startswith('#'):           # #태그 시작 → 독립
    return True
if '파일명.md' in query:            # 파일명 언급 → 독립
    return True
if query.startswith(('그것', '그')): # 대명사 시작 → Follow-up
    return False
if len(words) >= 15:                 # 긴 질문 → 독립
    return True
# ... 7개 규칙

# GPT 호출 (규칙으로 판단 안 될 때만)
return gpt_detect(query, history)
```

**TTL 설정** (`search/cache.py`):
```python
CACHE_TTL = 1800  # 30분 (초 단위)
```

### 동기화 주기

`docker-compose.yml`:
```yaml
sync:
  command: >
    sh -c "while true; do
      python sync_documents.py  # 변경됨 (이전: batch_sync.py)
      sleep 600  # 10분 (초 단위)
    done"
```

### 토큰 한도

`rag/generator.py`:
```python
# 기본: 110K 토큰
max_context_tokens = 110000

# 최대 모드: 180K 토큰
if ignore_token_limit:
    max_context_tokens = 180000
```

### 토큰 카운팅 최적화

`rag/generator.py:28-40`:
```python
from functools import lru_cache

@lru_cache(maxsize=2048)
def count_tokens(text: str) -> int:
    """LRU 캐시로 중복 인코딩 제거 (70-85% 성능 향상)"""
    return len(encoding.encode(text))
```

---

## 📊 로그 및 모니터링

### 로그 파일

```bash
# RAG 쿼리 로그
docker-compose exec web tail -f rag_query.log

# 실시간 로그 (모든 서비스)
docker-compose logs -f
```

### 로그 예시

```log
2025-11-11 13:41:16 - INFO - === 새로운 쿼리 시작 ===
2025-11-11 13:41:16 - INFO - 📝 쿼리: #Subway 태그 문서에서 中目黒から東新宿への行き方 알려줘
2025-11-11 13:41:16 - INFO - 🔢 검색할 노트 개수: 5
2025-11-11 13:41:16 - INFO - 🏷️  태그 필터 적용: ['Subway']
2025-11-11 13:41:17 - INFO -    → ES에서 1개 파일 필터링됨 (요청: 5개)
2025-11-11 13:41:18 - INFO -    → Qdrant path 필터 검색 결과: 1개
2025-11-11 13:41:18 - INFO - 📚 검색된 노트 개수: 1
2025-11-11 13:41:18 - INFO -   ✓ 노트 1 추가: 中目黒から東新宿.md (64 토큰)
2025-11-11 13:41:18 - INFO - 📊 컨텍스트 통계:
2025-11-11 13:41:18 - INFO -    - 사용 모델: gpt-4o-mini
2025-11-11 13:41:18 - INFO -    - 사용된 노트: 1개
2025-11-11 13:41:18 - INFO -    - 토큰 수: 64
2025-11-11 13:41:20 - INFO - 💰 토큰 사용량:
2025-11-11 13:41:20 - INFO -    - Prompt 토큰: 209
2025-11-11 13:41:20 - INFO -    - Completion 토큰: 64
2025-11-11 13:41:20 - INFO -    - 총 토큰: 273
2025-11-11 13:41:20 - INFO - ⏱️  처리 시간: 3.58초
2025-11-11 13:41:20 - INFO - === 쿼리 완료 ===
```

### 캐시 통계

```bash
# API 엔드포인트
curl http://localhost:8001/api/cache/stats

# 응답 예시
{
  "success": true,
  "stats": {
    "total_keys": 1247,
    "hits": 8932,
    "misses": 3421,
    "hit_rate": "72.3%",
    "memory_used": "12.4 MB"
  }
}
```

---

## 🐛 문제 해결

### 캐시가 작동하지 않음

```bash
# Redis 연결 확인
docker-compose exec redis redis-cli ping
# 응답: PONG

# 캐시 삭제 후 재시작
curl -X DELETE http://localhost:8001/api/cache
docker-compose restart web
```

### 검색 결과가 없음

```bash
# Elasticsearch 상태 확인
curl http://localhost:9201/_cluster/health

# 전체 문서 수 확인
curl http://localhost:8001/api/notes/count

# Qdrant 초기화 및 재동기화
docker-compose exec web python scripts/clear_qdrant.py
docker-compose restart sync
```

### 태그 필터링 안 됨

```bash
# Elasticsearch 인덱스 확인
curl http://localhost:9201/obsidian_notes/_search?q=tags:Subway

# 캐시 초기화 (이전 결과 제거)
curl -X DELETE http://localhost:8001/api/cache
```

### 응답이 느림

```bash
# 로그에서 병목 구간 확인
docker-compose logs web | grep "⏱️"

# top_k 줄이기 (UI에서 5개로 설정)
# 캐시 통계 확인 (히트율 낮으면 문제)
curl http://localhost:8001/api/cache/stats
```

### Docker 빌드 실패

```bash
# 캐시 없이 재빌드
docker-compose build --no-cache

# 볼륨 삭제 후 재시작
docker-compose down -v
docker-compose up -d
```

---

## 💡 최적화 팁

### 🎯 비용 절감

1. **캐싱 활용**: 같은 질문 반복 시 무료
2. **top_k=5 사용**: 기본값 유지로 69% 비용 절감
3. **태그 필터링**: 검색 범위 축소로 토큰 90% 절감
4. **GPT-4o-mini 사용**: GPT-4 대비 15배 저렴
5. **대화 초기화**: 히스토리 누적 방지

### ⚡ 속도 향상

1. **태그 활용**: 3.6초 (vs 일반 13.7초)
2. **독립 질문 우선**: Follow-up보다 캐시 히트율 2배
3. **Redis 캐싱**: 3,500배+ 속도 향상
4. **규칙 기반 감지**: GPT 호출 90% 제거 (-0.5~2초)
5. **LRU 캐싱**: 토큰 카운팅 중복 제거 (-70~85%)

### 🎓 정확도 향상

1. **구체적인 질문**: "그것" 대신 명시적 주제 언급
2. **태그 기반 검색**: 관련 문서만 검색
3. **최대 토큰 모드**: 더 많은 컨텍스트 활용
4. **대화 맥락 유지**: Follow-up 질문 활용
5. **적절한 top_k**: 5-20개 권장 (50개 이상 비효율적)

---

## 🔐 보안 및 주의사항

### ⚠️ 필수 확인

- ✅ `.env` 파일은 절대 GitHub에 커밋하지 마세요
- ✅ OpenAI/Qdrant API 키는 비공개로 유지
- ✅ 개인 노트 내용은 공유 금지
- ✅ API 레이트 리밋 준수 (OpenAI: 200K tokens/min)

### 🔒 환경 변수 관리

```bash
# .gitignore에 추가됨
.env
*.log
__pycache__/
.pytest_cache/
```

---

## 📈 향후 계획

### 단기 (1-2주)
- [ ] 스트리밍 응답 (실시간 답변 출력)
- [ ] 캐시 유효성 검증 (문서 변경 시 자동 무효화)
- [ ] 사용 통계 대시보드

### 중기 (1-3개월)
- [ ] MCP (Model Context Protocol) 통합 ([전략 문서](./MCP_INTEGRATION_STRATEGY.md))
- [ ] Hybrid Search (BM25 + Vector)
- [ ] 멀티유저 지원 (테넌트 ID)
- [ ] Reranker 모델 (Cohere)

### 장기 (3-6개월)
- [ ] 로컬 LLM 지원 (Llama 3.1)
- [ ] 임베딩 캐싱 (비용 추가 절감)
- [ ] Prometheus + Grafana 모니터링
- [ ] 마이크로서비스 아키텍처

---

## 📚 관련 문서

- **[인덱싱 & 캐싱 아키텍처](./INDEXING_AND_CACHING_ARCHITECTURE.md)** - 면접 대비 기술 문서 ⭐
- **[성능 분석 보고서](./RAG_PERFORMANCE_ANALYSIS.md)** - 병목 구간 분석 및 개선 방안
- **[MCP 통합 전략](./MCP_INTEGRATION_STRATEGY.md)** - Model Context Protocol 도입 계획
- **[파일명 리팩토링](./FILENAME_REVIEW.md)** - 네이밍 철학 및 변경 히스토리

---

## 🤝 기여하기

이슈와 PR을 환영합니다!

### 개발 환경 설정

```bash
# 저장소 포크 및 클론
git clone https://github.com/your-username/ObsidianRagChat.git

# 브랜치 생성
git checkout -b feature/amazing-feature

# 변경사항 커밋
git commit -m "Add amazing feature"

# PR 생성
git push origin feature/amazing-feature
```

### 코딩 가이드

- Python 3.11+ 사용
- Type hints 필수
- Docstring 작성 권장
- 테스트 추가 (`tests/` 폴더)
- 파일명은 내용을 명확히 표현 (예: `generator.py` > `gpt_rag.py`)

---

## 🧪 테스트

```bash
# 전체 테스트 실행
docker-compose exec web python -m pytest tests/ -v

# 특정 테스트
docker-compose exec web python -m pytest tests/test_question_detector.py -v

# 테스트 결과 (22개 테스트)
============================= test session starts ==============================
collected 22 items

tests/test_question_detector.py::test_rephrase_exact_match PASSED        [  4%]
tests/test_question_detector.py::test_rule_hashtag_start PASSED          [ 18%]
tests/test_question_detector.py::test_rule_pronoun_start_korean PASSED   [ 27%]
...
============================== 22 passed in 3.31s ===============================
```

---

## 📝 라이선스

MIT License - 자유롭게 사용, 수정, 배포 가능

---

## 🙏 감사의 말

이 프로젝트는 다음 오픈소스 프로젝트들 덕분에 가능했습니다:

- **[OpenAI](https://openai.com/)** - GPT 모델 및 임베딩 API
- **[Qdrant](https://qdrant.tech/)** - 고성능 벡터 데이터베이스
- **[Elasticsearch](https://www.elastic.co/)** - 강력한 전문 검색 엔진
- **[Redis](https://redis.io/)** - 빠른 인메모리 캐싱
- **[FastAPI](https://fastapi.tiangolo.com/)** - 현대적인 웹 프레임워크
- **[Docker](https://www.docker.com/)** - 컨테이너 플랫폼
- **[Obsidian](https://obsidian.md/)** - 최고의 지식 관리 도구

---

## 📞 문의 및 지원

- **Issues**: [GitHub Issues](https://github.com/yourusername/ObsidianRagChat/issues)
- **Discussions**: [GitHub Discussions](https://github.com/yourusername/ObsidianRagChat/discussions)

---

<p align="center">
  Made with ❤️ by <a href="https://github.com/yourusername">Your Name</a>
</p>

<p align="center">
  <sub>⭐ 이 프로젝트가 도움이 되었다면 Star를 눌러주세요!</sub>
</p>
