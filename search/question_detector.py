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
from openai import OpenAI
import os

# OpenAI 클라이언트
openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

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
    if (re.match(r'^\s*(그|그것|이것|저것|그거|이거)(?:\s|을|를|이|가|은|는|에|의)', query) or
        re.match(r'^\s*(それ|これ|あれ)', query) or
        re.match(r'^\s*(it|that|this)\s', query, re.IGNORECASE)):
        print(f"❌ 규칙 감지: 대명사 시작 → Follow-up")
        return False

    # 4. "X에 대해서/관해서" 패턴에서 X가 3글자 이상 명사면 → 독립 질문
    about_pattern = re.match(r'^\s*([가-힣a-zA-Z\s]{3,})(에\s*대해서|에\s*관해서|를\s*알려|를\s*설명|란\?|는\s*뭐)', query)
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

    # ===== 규칙으로 결정 안 되면 GPT에게 물어봄 =====

    # 최근 2개 대화만 참조 (충분함)
    recent_history = history[-4:] if len(history) >= 4 else history

    # 대화 컨텍스트 구성
    history_text = "\n".join([
        f"{msg.get('role', 'unknown')}: {msg.get('content', '')[:100]}..."
        if isinstance(msg, dict)
        else f"{msg.role}: {msg.content[:100]}..."
        for msg in recent_history
    ])

    prompt = f"""아래 대화 히스토리와 새로운 질문을 보고, 새로운 질문이 독립적인 질문인지 판단해주세요.

**대화 히스토리:**
{history_text}

**새로운 질문:**
{query}

**판단 기준 (순서대로 체크):**

1. **먼저 독립 질문 강제 조건 체크 (다음 중 하나라도 해당하면 무조건 YES):**

   a) **명사 직접 언급 패턴** (최우선!):
      - "X에 대해서", "X에 관해서", "X를/을 설명", "X를/을 알려", "X는/은 뭐", "X란?"
      - 예: "Obsidian RAG Chat에 대해서 알려줘", "FastAPI에 관해서 설명해줘"
      - 예: "Pagination이란?", "Redis는 뭐야?", "Docker 설명해줘"
      - 예: "Python 장점 알려줘", "React를 소개해줘"
      - **핵심: 대명사("그", "그것", "이것") 없이 명사를 직접 명시**

   b) "#태그"로 시작하는 질문 (예: "#Jerrygram", "#RagChat")

   c) 특정 파일명을 명시적으로 언급 (예: "README.md 요약해줘", "config.py 설명해줘")

   d) **이전 대화와 다른 언어로 질문** (예: 히스토리는 한국어인데 새 질문은 일본어/영어)

2. **Follow-up 질문 체크 (다음 중 하나라도 해당하면 NO):**
   - 문장 시작이 대명사: "그", "그것", "이것", "저것", "그거", "이거", "해당" (한국어), "それ", "これ", "あれ" (일본어), "it", "that", "this" (영어)
   - 문장 시작이 연결어: "그럼", "그러면", "그렇다면", "근데", "그런데" (한국어), "では", "それでは", "でも" (일본어)
   - 소유격 + 명사: "그 문서", "이 문서", "그 내용" (한국어), "その文書", "この内容" (일본어)
   - 반복/참조 표현: "다시", "또", "더", "추가로", "계속" (한국어), "また", "もう一度", "さらに" (일본어), "again", "more" (영어)
   - 불완전한 문장: "장점은?", "예시는?", "방법은?"

   예시:
   - "그 문서를 다시 요약해줘" → NO (대명사 "그" + 반복 "다시")
   - "その文書をもう一度要約して" → NO (대명사 "その" + 반복 "もう一度")
   - "그럼 Django는?" → NO (연결어)
   - "더 자세히 설명해줘" → NO (참조 표현)

3. **위 조건에 해당 안 하면 독립 질문 (YES):**
   - 새로운 질문이 그 자체로 완전한 요청 (이전 대화 없이도 이해 가능)

   예시:
   - "Pagination이 뭔지 알려줘" → YES (구체적 기술명 직접 명시)
   - "Obsidian RAG Chat에 대해서 알려줘" → YES (구체적 명사 + 설명 요청)
   - "#RagChat タグ文書について説明してください" → YES (#태그 + 다른 언어)
   - "Redis 캐싱 설명해줘" → YES (구체적 주제)
   - "FastAPI에 관해서 설명해줘" → YES (명사 직접 명시)
   - "Python 장점 알려줘" → YES (완전한 질문)

**핵심 규칙 (우선순위 순):**

🔴 **무조건 NO (Follow-up):**
   - 문장이 대명사로 시작: "그것", "그", "이것", "それ", "これ", "it", "that"
   - 예: "그것에 대해서 알려줘" → NO
   - 예: "그 문서를 요약해줘" → NO

🟢 **무조건 YES (독립 질문):**
   - **구체적인 고유명사/기술명을 직접 언급하는 모든 질문**
   - 예: "Obsidian RAG Chat에 대해서 알려줄래" → YES (고유명사 직접 언급)
   - 예: "FastAPI란?" → YES (기술명 직접 언급)
   - 예: "Python 설명해줘" → YES (언어명 직접 언급)
   - 예: "#RagChat 문서 요약해줘" → YES (#태그 포함)

**답변:** 위 규칙만 보고 "YES" 또는 "NO" 중 하나만 답변 (다른 말 일체 금지)"""

    try:
        response = openai_client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=10,
            temperature=0  # Deterministic
        )

        answer = response.choices[0].message.content.strip().upper()

        # YES 또는 NO로 판단
        is_independent = "YES" in answer

        # 디버깅 로그
        print(f"🔍 독립 질문 감지: query='{query[:50]}...', 판단={answer}, 결과={'독립' if is_independent else 'Follow-up'}")

        return is_independent

    except Exception as e:
        print(f"❌ 독립 질문 감지 실패: {e}")
        # 에러 시 안전하게 독립 질문으로 처리 (캐싱 유리)
        return True


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
