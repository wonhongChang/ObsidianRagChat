# 테스트

## 공개 테스트

### `test_question_detector.py`

Follow-up 감지 로직(`search/question_detector.py`)의 단위 테스트.
외부 서비스 의존 없이 로컬에서 바로 실행 가능합니다.

**실행 방법**

```bash
# 로컬
python -m pytest tests/test_question_detector.py -v

# Docker
docker-compose exec web python -m pytest tests/test_question_detector.py -v
```

**테스트 항목**

- 독립 질문 감지 (대명사 없음, 충분한 길이)
- Follow-up 감지 (대명사 포함, 이전 맥락 참조)
- Rephrase 감지 (포함 관계 — 같은 캐시 키 공유)
- 짧은 쿼리 처리
- 히스토리 없을 때 독립 처리

## 로컬 전용 테스트 (gitignore)

개인 Obsidian 노트 데이터를 기반으로 하는 테스트는 `.gitignore`에 포함되어 공개되지 않습니다.

```
tests/test_example*.py   # 캐시 시나리오 테스트
tests/test_example*.md   # 테스트 시나리오 정의
tests/test_search*.py    # 검색 품질 테스트
```
