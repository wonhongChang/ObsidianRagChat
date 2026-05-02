# 유틸리티 스크립트

이 폴더에는 관리 및 유지보수를 위한 일회성 스크립트들이 포함되어 있습니다.

## 📜 스크립트 목록

### clear_cache.py
**용도**: Redis 캐시 전체 삭제

**사용법**:
```bash
docker-compose exec web python scripts/clear_cache.py
```

**언제 사용하나요?**
- 캐시를 초기화하고 싶을 때
- 코드 변경 후 이전 캐시를 제거하고 싶을 때
- 테스트 후 정리할 때

---

### clear_qdrant.py
**용도**: Qdrant 컬렉션 초기화 (모든 벡터 데이터 삭제)

**사용법**:
```bash
docker-compose exec web python scripts/clear_qdrant.py
```

**주의사항**:
- ⚠️ 모든 벡터 데이터가 삭제됩니다
- 다음 sync 실행 시 자동으로 재생성됨

**언제 사용하나요?**
- 벡터 데이터를 처음부터 다시 생성하고 싶을 때
- Qdrant 구조를 변경한 후

---

### migrate_qdrant_payload.py
**용도**: Qdrant payload 최소화 (저장 공간 절감)

**사용법**:
```bash
docker-compose exec web python scripts/migrate_qdrant_payload.py
```

**기능**:
- 기존 payload에서 불필요한 필드 제거 (text, tags, mtime, hash)
- path, filename만 유지
- 저장 공간 약 46% 절감

**주의사항**:
- ⚠️ 일회성 마이그레이션 스크립트
- 이미 실행했다면 다시 실행할 필요 없음

---

### add_qdrant_index.py
**용도**: Qdrant path 필드 인덱싱 (검색 성능 향상)

**사용법**:
```bash
docker-compose exec web python scripts/add_qdrant_index.py
```

**기능**:
- path 필드에 keyword 인덱스 추가
- MatchAny 필터 성능 향상
- 데이터는 변경되지 않음

**주의사항**:
- ⚠️ 일회성 최적화 스크립트
- 이미 실행했다면 다시 실행할 필요 없음

---

## 📊 실행 순서 (처음 설정 시)

초기 설정 시 권장 실행 순서:

```bash
# 1. Qdrant payload 최소화 (선택사항)
docker-compose exec web python scripts/migrate_qdrant_payload.py

# 2. Qdrant 인덱스 추가 (성능 향상)
docker-compose exec web python scripts/add_qdrant_index.py

# 3. 캐시 초기화 (필요 시)
docker-compose exec web python scripts/clear_cache.py
```

---

## ⚠️ 주의사항

- 모든 스크립트는 **Docker 컨테이너 내부**에서 실행되어야 합니다
- 프로덕션 환경에서는 백업 후 실행하세요
- 대부분의 스크립트는 일회성이므로 반복 실행 불필요
