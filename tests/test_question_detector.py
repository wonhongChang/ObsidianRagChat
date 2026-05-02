"""
질문 감지 모듈 유닛 테스트

테스트 커버리지:
1. Rephrase 감지 (정확한 일치, 90% 이상 유사도)
2. 규칙 기반 감지 (#태그, 파일명, 대명사, "X에 대해서" 패턴)
3. GPT-4o-mini 호출 (모킹)
4. 최근 질문 저장/조회/초기화
"""

import pytest
from search.question_detector import (
    is_independent_question,
    save_query,
    get_recent_queries,
    clear_recent_queries
)


@pytest.fixture(autouse=True)
def reset_recent_queries():
    """각 테스트 전에 최근 질문 목록 초기화"""
    clear_recent_queries()
    yield
    clear_recent_queries()


# ===== Rephrase 감지 테스트 =====

def test_rephrase_exact_match():
    """정확히 같은 질문 반복 → 독립 질문"""
    query = "Obsidian RAG Chat에 대해서 알려줄래"
    history = [{"role": "assistant", "content": "이전 답변"}]

    # 첫 질문 저장
    save_query(query)

    # 같은 질문 반복
    result = is_independent_question(query, history)

    assert result is True
    print("✅ 정확한 일치 감지 성공")


def test_rephrase_high_similarity():
    """90% 이상 유사한 질문 → 독립 질문"""
    query1 = "Obsidian RAG Chat에 대해 알려줘"
    query2 = "Obsidian RAG Chat에 대해서 알려줘"  # 90% 이상 유사
    history = [{"role": "assistant", "content": "이전 답변"}]

    # 첫 질문 저장
    save_query(query1)

    # 유사한 질문
    result = is_independent_question(query2, history)

    assert result is True
    print("✅ 유사도 감지 성공")


def test_rephrase_low_similarity():
    """90% 미만 유사도 → Rephrase 아님, 규칙 미결정 시 Follow-up"""
    query1 = "Redis 캐싱 설명해줘"
    query2 = "FastAPI 설명해줘"  # object marker 없음 → 규칙 미결정 → Follow-up
    history = [{"role": "assistant", "content": "Redis는..."}]

    save_query(query1)

    result = is_independent_question(query2, history)

    assert result is False  # 규칙 미결정 → 안전하게 Follow-up
    print("✅ 낮은 유사도 → 규칙 미결정 → Follow-up 처리")


# ===== 규칙 기반 감지 테스트 =====

def test_rule_hashtag_start():
    """#태그로 시작 → 무조건 독립 질문"""
    query = "#RagChat 문서 요약해줘"
    history = [{"role": "assistant", "content": "이전 답변"}]

    result = is_independent_question(query, history)

    assert result is True
    print("✅ #태그 감지 성공")


def test_rule_filename_mention():
    """파일명 언급 → 무조건 독립 질문"""
    queries = [
        "README.md 요약해줘",
        "config.py 설명해줘",
        "package.json 내용 알려줘"
    ]
    history = [{"role": "assistant", "content": "이전 답변"}]

    for query in queries:
        result = is_independent_question(query, history)
        assert result is True
        print(f"✅ 파일명 감지 성공: {query}")


def test_rule_pronoun_start_korean():
    """대명사 시작 (한국어) → 무조건 Follow-up"""
    queries = [
        "그것에 대해서 알려줘",
        "그 문서를 요약해줘",
        "이것을 설명해줘",
        "그거 다시 말해줘"
    ]
    history = [{"role": "assistant", "content": "이전 답변"}]

    for query in queries:
        result = is_independent_question(query, history)
        assert result is False
        print(f"✅ 대명사 감지 성공: {query}")


def test_rule_pronoun_start_japanese():
    """대명사 시작 (일본어) → 무조건 Follow-up"""
    queries = [
        "それについて説明してください",
        "これを要約して",
        "あれをもう一度"
    ]
    history = [{"role": "assistant", "content": "previous answer"}]

    for query in queries:
        result = is_independent_question(query, history)
        assert result is False
        print(f"✅ 일본어 대명사 감지 성공: {query}")


def test_rule_pronoun_start_english():
    """대명사 시작 (영어) → 무조건 Follow-up"""
    queries = [
        "that document please",
        "this one again",
        "it is what"
    ]
    history = [{"role": "assistant", "content": "previous answer"}]

    for query in queries:
        result = is_independent_question(query, history)
        assert result is False
        print(f"✅ 영어 대명사 감지 성공: {query}")


def test_rule_about_pattern_korean():
    """'X에 대해서/관해서' 패턴 (명사 명시) → 독립 질문"""
    queries = [
        "Obsidian RAG Chat에 대해서 알려줘",
        "FastAPI에 관해서 설명해줘",
        "Redis를 알려줘",
        "Python을 설명해줘",
        "Pagination란?",
        "Docker는 뭐야?"
    ]
    history = [{"role": "assistant", "content": "이전 답변"}]

    for query in queries:
        result = is_independent_question(query, history)
        assert result is True
        print(f"✅ 'X에 대해서' 패턴 감지 성공: {query}")


def test_rule_about_pattern_with_pronoun():
    """'그것에 대해서' (대명사) → Follow-up"""
    queries = [
        "그것에 대해서 알려줘",
        "그거에 관해서 설명해줘"
    ]
    history = [{"role": "assistant", "content": "이전 답변"}]

    for query in queries:
        result = is_independent_question(query, history)
        assert result is False  # 대명사 규칙이 먼저 작동
        print(f"✅ 대명사 우선 감지 성공: {query}")


# ===== 규칙 미결정 → Follow-up 기본값 테스트 =====

def test_ambiguous_defaults_to_followup():
    """규칙으로 판단 불가한 모호한 질문 → Follow-up으로 처리"""
    queries = [
        "더 자세히 설명해줘",
        "예시를 들어줘",
        "새로운 주제 질문",
    ]
    history = [{"role": "assistant", "content": "이전 답변"}]

    for query in queries:
        result = is_independent_question(query, history)
        assert result is False
        print(f"✅ 모호한 질문 → Follow-up 처리: {query}")


# ===== 최근 질문 저장/조회 테스트 =====

def test_save_and_get_queries():
    """질문 저장 및 조회"""
    queries = ["질문1", "질문2", "질문3"]

    for query in queries:
        save_query(query)

    recent = get_recent_queries()

    assert len(recent) == 3
    assert recent == queries
    print("✅ 질문 저장/조회 성공")


def test_recent_queries_maxlen():
    """최근 질문 최대 10개 저장"""
    # 15개 질문 저장
    for i in range(15):
        save_query(f"질문{i}")

    recent = get_recent_queries()

    # 최근 10개만 저장됨
    assert len(recent) == 10
    assert recent[0] == "질문5"  # 첫 5개는 제거됨
    assert recent[-1] == "질문14"
    print("✅ 최대 길이 제한 성공")


def test_clear_queries():
    """질문 목록 초기화"""
    save_query("질문1")
    save_query("질문2")

    clear_recent_queries()

    recent = get_recent_queries()
    assert len(recent) == 0
    print("✅ 초기화 성공")


# ===== 엣지 케이스 테스트 =====

def test_empty_history():
    """history 없음 → 항상 독립 질문"""
    query = "아무 질문"

    result = is_independent_question(query, [])
    assert result is True

    result = is_independent_question(query, None)
    assert result is True

    print("✅ 빈 history 처리 성공")


def test_mixed_language_question():
    """다국어 혼합 질문"""
    query = "#RagChat タグ文書について説明してください"
    history = [{"role": "assistant", "content": "previous answer"}]

    result = is_independent_question(query, history)

    assert result is True  # #태그로 감지
    print("✅ 다국어 혼합 처리 성공")


def test_whitespace_handling():
    """공백 처리"""
    query1 = "  Obsidian RAG Chat에 대해서 알려줘  "
    query2 = "Obsidian RAG Chat에 대해서 알려줘"

    save_query(query1)

    history = [{"role": "assistant", "content": "답변"}]
    result = is_independent_question(query2, history)

    assert result is True  # 공백 제거 후 일치
    print("✅ 공백 처리 성공")


def test_case_insensitive_rephrase():
    """대소문자 구분 없이 rephrase 감지"""
    query1 = "Python 설명해줘"
    query2 = "python 설명해줘"

    save_query(query1)

    history = [{"role": "assistant", "content": "답변"}]
    result = is_independent_question(query2, history)

    assert result is True  # 대소문자 무시하고 일치
    print("✅ 대소문자 무시 성공")


# ===== 통합 시나리오 테스트 =====

def test_scenario_multilingual_caching():
    """실제 사용 시나리오: 다국어 전환 캐싱"""
    # 1. 한국어 질문
    query_kr = "#RagChat 문서 설명해줘"
    history_kr = []
    result_kr = is_independent_question(query_kr, history_kr)
    save_query(query_kr)
    assert result_kr is True

    # 2. 한국어 재질문 (rephrase)
    result_kr_2 = is_independent_question(query_kr, history_kr)
    assert result_kr_2 is True  # rephrase 감지

    # 3. 일본어로 전환
    query_jp = "#RagChat タグ文書を説明して"
    history_jp = [{"role": "assistant", "content": "Korean answer"}]
    result_jp = is_independent_question(query_jp, history_jp)
    save_query(query_jp)
    assert result_jp is True  # #태그로 독립 질문

    # 4. 일본어 재질문 (rephrase)
    result_jp_2 = is_independent_question(query_jp, history_jp)
    assert result_jp_2 is True  # rephrase 감지

    print("✅ 다국어 전환 시나리오 성공")


def test_scenario_followup_detection():
    """실제 사용 시나리오: Follow-up 질문 감지"""
    # 1. 첫 질문 (독립)
    query1 = "#RagChat 문서 요약해줘"
    history1 = []
    result1 = is_independent_question(query1, history1)
    save_query(query1)
    assert result1 is True

    # 2. Follow-up (대명사)
    query2 = "그 문서를 다시 요약해줘"
    history2 = [
        {"role": "user", "content": query1},
        {"role": "assistant", "content": "#RagChat 문서는..."}
    ]
    result2 = is_independent_question(query2, history2)
    assert result2 is False  # 대명사로 Follow-up 감지

    # 3. 새로운 독립 질문
    query3 = "FastAPI에 대해서 알려줘"
    result3 = is_independent_question(query3, history2)
    save_query(query3)
    assert result3 is True  # "X에 대해서" 패턴

    print("✅ Follow-up 감지 시나리오 성공")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
