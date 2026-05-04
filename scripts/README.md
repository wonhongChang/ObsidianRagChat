# 유틸리티 스크립트

관리 및 유지보수를 위한 스크립트 모음입니다.

---

## clear_cache.py

**용도**: Redis 캐시 전체 삭제

```bash
docker-compose exec web python scripts/clear_cache.py
```

**사용 시점**
- 코드 변경 후 이전 캐시를 제거하고 싶을 때
- 테스트 후 정리할 때

---

## clear_qdrant.py

**용도**: Qdrant 컬렉션 전체 초기화 (벡터 데이터 삭제)

```bash
docker-compose exec web python scripts/clear_qdrant.py
```

> ⚠️ 모든 벡터 데이터가 삭제됩니다. 다음 sync 실행 시 자동 재생성됩니다.

**사용 시점**
- 노트 임베딩을 처음부터 다시 생성하고 싶을 때
- Qdrant 컬렉션 구조를 변경한 후

---

## add_qdrant_index.py

**용도**: Qdrant `path` 필드에 keyword 인덱스 추가 (검색 성능 향상)

```bash
docker-compose exec web python scripts/add_qdrant_index.py
```

> ℹ️ 일회성 최적화 스크립트. 이미 실행했다면 재실행 불필요.

**사용 시점**
- 최초 설치 후 태그 필터 검색 성능을 높이고 싶을 때
- `MatchAny` 필터 오류가 발생할 때


---

## 주의사항

- 모든 스크립트는 **Docker 컨테이너 내부** (`docker-compose exec web`)에서 실행하세요
- `clear_qdrant.py` 실행 후에는 반드시 `docker-compose restart sync`로 재동기화하세요
