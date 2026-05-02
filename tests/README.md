# 테스트

이 폴더에는 프로젝트의 테스트 파일들이 포함되어 있습니다.

## 📝 테스트 파일 목록

### test_multi_line_tags.py
**용도**: 여러 줄 태그 추출 함수 테스트

**테스트 케이스**:
1. 1줄 태그 추출 (3개)
2. 다중 줄 태그 블록
3. 빈 줄로 구분된 태그
4. 마크다운 제목(##)으로 구분된 태그
5. 실제 사례:
   - 인터뷰 문서
   - 공유기 가이드
   - Redis 캐싱 문서

**실행 방법**:
```bash
# 로컬에서 실행
python tests/test_multi_line_tags.py

# Docker에서 실행
docker-compose exec web python tests/test_multi_line_tags.py
```

**기대 결과**:
```
✅ 테스트 1 통과: 1줄 태그 (3개)
✅ 테스트 2 통과: 다중 줄 태그
✅ 테스트 3 통과: 빈 줄 구분
✅ 테스트 4 통과: 마크다운 제목 구분
✅ 테스트 5 통과: 실제 사례 (인터뷰)
✅ 테스트 6 통과: 실제 사례 (공유기)
✅ 테스트 7 통과: 실제 사례 (Redis)

모든 테스트 통과! ✅
```

---

## 🚀 향후 계획

### 테스트 프레임워크 도입 검토
현재는 간단한 assert 기반 테스트지만, 향후 pytest 도입 고려:

```bash
# pytest 설치 (requirements-dev.txt)
pytest==7.4.0
pytest-cov==4.1.0
pytest-asyncio==0.21.0

# 실행
pytest tests/ -v --cov=.
```

### 추가 예정 테스트
- [ ] `test_embedder.py` - 임베딩 생성 테스트
- [ ] `test_qdrant_search.py` - 벡터 검색 테스트
- [ ] `test_elasticsearch.py` - 전문 검색 테스트
- [ ] `test_redis_cache.py` - 캐싱 로직 테스트
- [ ] `test_rag_engine.py` - RAG 엔진 테스트
- [ ] `test_api.py` - FastAPI 엔드포인트 테스트

---

## 📊 테스트 커버리지 목표

| 모듈 | 현재 커버리지 | 목표 |
|------|--------------|------|
| embed/loader.py | 100% ✅ | 100% |
| embed/embedder.py | 0% | 80% |
| embed/qdrant_client.py | 0% | 70% |
| search/elasticsearch_client.py | 0% | 70% |
| search/redis_cache.py | 0% | 80% |
| rag/gpt_rag.py | 0% | 60% |
| app.py | 0% | 50% |

---

## ⚡ CI/CD 통합 (향후)

GitHub Actions 예시:

```yaml
name: Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      - run: pip install -r requirements.txt -r requirements-dev.txt
      - run: pytest tests/ -v --cov=. --cov-report=xml
      - uses: codecov/codecov-action@v3
```
