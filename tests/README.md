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

**테스트 항목 (24개)**

| 분류 | 테스트 |
|------|--------|
| Rephrase 감지 | 정확 일치 / 유사도 90%+ / 포함 관계 / 낮은 유사도 |
| 규칙 기반 독립 판정 | #태그 시작 / 파일명 언급 / 의문사 시작 / X에 대해서 패턴 / 긴 질문(15단어+) / 정의·개념 키워드 |
| 규칙 기반 Follow-up 판정 | 한국어·일본어·영어 대명사 / 대명사 + 에 대해서 |
| 엣지 케이스 | 빈 히스토리 / 공백 처리 / 대소문자 무시 / 다국어 혼합 |
| 저장/조회 | 질문 저장 및 조회 / 최대 10개 제한 / 초기화 |
| 시나리오 | 다국어 전환 캐싱 / Follow-up 흐름 |

## 로컬 전용 테스트 (gitignore)

개인 Obsidian 노트 데이터를 기반으로 하는 테스트는 `.gitignore`에 포함되어 공개되지 않습니다.

```
tests/test_example*.py   # 캐시 시나리오 테스트
tests/test_example*.md   # 테스트 시나리오 정의
tests/test_search*.py    # 검색 품질 테스트
```
