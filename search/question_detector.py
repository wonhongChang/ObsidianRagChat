"""
질문 타입 감지 모듈

- Independent (독립 질문): 새로운 질문, 캐시 키에 history 포함 안 함
- Follow-up (후속 질문): 이전 대화 참조, 캐시 키에 history 포함
- Rephrase (재질문): 최근 질문 반복, 독립 질문으로 처리
"""

from typing import List, Optional
from collections import deque
import difflib
import re

# 최근 질문 저장 (Rephrase 감지용)
recent_queries = deque(maxlen=10)  # 최근 10개 질문 저장


def is_independent_question(query: str, history: List) -> bool:
    """
    질문이 독립적인지 판단 (규칙 기반 + GPT-4o-mini)

    Args:
        query: 현재 질문
        history: 대화 히스토리

    Returns:
        True: 독립 질문 (이전 대화와 무관)
        False: Follow-up 질문 (이전 대화 참조 필요)
    """
    if not history or len(history) == 0:
        return True

    # ===== 0단계: Rephrase 감지 (최근 질문과 비교) =====
    query_normalized = query.strip().lower()
    for prev_query in recent_queries:
        prev_normalized = prev_query.strip().lower()

        # 정확히 같거나 90% 이상 유사하면 rephrase
        if query_normalized == prev_normalized:
            print(f"🔄 Rephrase 감지 (같은 질문 반복) → 독립 질문")
            return True

        similarity = difflib.SequenceMatcher(None, query_normalized, prev_normalized).ratio()
        if similarity >= 0.9:
            print(f"🔄 Rephrase 감지 (유사도 {similarity:.0%}) → 독립 질문")
            return True

    # ===== 규칙 기반 사전 필터 (GPT 호출 전) =====

    # 1. #태그로 시작하면 → 무조건 독립 질문
    if re.match(r'^\s*#\w+', query):
        print(f"✅ 규칙 감지: #태그 시작 → 독립 질문")
        return True

    # 2. 파일명 패턴이 있으면 → 무조건 독립 질문
    if re.search(r'\w+\.(md|py|js|ts|txt|json|yml|yaml)', query, re.IGNORECASE):
        print(f"✅ 규칙 감지: 파일명 언급 → 독립 질문")
        return True

    # 3. 대명사로 시작하면 → 무조건 Follow-up
    # 한국어/영어는 공백 필요, 일본어는 조사(を, に, で 등)가 바로 붙음
    if (re.match(r'^\s*(그|그것|이것|저것|그거|이거|그게|이게|저게|그건|이건|저건|해당)(?:\s|을|를|이|가|은|는|에|의|도|만|로|랑|까지)', query) or
        re.match(r'^\s*(それ|これ|あれ|その|この|あの)', query) or
        re.match(r'^\s*(it|that|this)\s', query, re.IGNORECASE)):
        print(f"❌ 규칙 감지: 대명사 시작 → Follow-up")
        return False

    # 4. "X에 대해서/관해서" 패턴에서 X가 3글자 이상 명사면 → 독립 질문
    about_pattern = re.match(r'^\s*([가-힣a-zA-Z\s]{3,})(에\s*대해서|에\s*관해서|[를을]\s*알려|[를을]\s*설명|란\?|는\s*뭐)', query)
    if about_pattern:
        subject = about_pattern.group(1).strip()
        # 대명사가 아니면 독립 질문
        if subject not in ['그', '그것', '이것', '저것', '그거', '이거']:
            print(f"✅ 규칙 감지: '{subject}'에 대한 질문 → 독립 질문")
            return True

    # 5. 긴 질문 (15단어 이상)은 대부분 독립 질문
    word_count = len(re.findall(r'\S+', query))
    if word_count >= 15:
        print(f"✅ 규칙 감지: 긴 질문 ({word_count}단어) → 독립 질문")
        return True

    # 6. 의문사로 시작 → 독립 질문
    if re.match(r'^\s*(무엇|뭐|어디|왜|언제|누구|어떻게|どこ|何|なぜ|いつ|誰|どう|what|where|why|when|who|how)\s', query, re.IGNORECASE):
        print(f"✅ 규칙 감지: 의문사 시작 → 독립 질문")
        return True

    # 7. 정의/개념 질문 키워드 → 독립 질문
    if re.search(r'(정의|개념|의미|뜻|역사|특징|차이|비교|장점|단점|장단점|定義|概念|意味|歴史|特徴|違い|比較|definition|concept|meaning|history|feature|difference|comparison|advantage|disadvantage)', query, re.IGNORECASE):
        print(f"✅ 규칙 감지: 정의/개념 질문 → 독립 질문")
        return True

    # Rules didn't match → treat as Follow-up to avoid wrong answers
    print(f"↩️  규칙 미결정: Follow-up으로 처리")
    return False


def save_query(query: str):
    """
    질문을 최근 질문 목록에 저장 (Rephrase 감지용)

    Args:
        query: 저장할 질문
    """
    recent_queries.append(query)


def get_recent_queries() -> List[str]:
    """최근 질문 목록 조회 (디버깅용)"""
    return list(recent_queries)


def clear_recent_queries():
    """최근 질문 목록 초기화"""
    recent_queries.clear()
