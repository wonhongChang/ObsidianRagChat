"""
여러 줄 태그 추출 테스트
"""
import re

def extract_tags(content):
    """
    마크다운 파일의 상단 태그 블록에서 태그 추출 (#태그 형식)
    빈 줄 또는 마크다운 제목(# 제목)이 나올 때까지 모든 태그 추출
    """
    lines = content.split('\n')
    if not lines:
        return []

    tags = []
    for line in lines:
        line = line.strip()

        # 빈 줄이면 태그 블록 끝
        if not line:
            break

        # 마크다운 제목(# 제목, ## 제목 등)이 나오면 태그 블록 끝
        if re.match(r'^#{1,6}\s+', line):
            break

        # 이 줄에서 태그 추출
        line_tags = re.findall(r'#(\w+)', line)
        tags.extend(line_tags)

    return list(set(tags))  # 중복 제거


# 테스트 케이스
test_cases = [
    {
        "name": "1줄에 태그 3개",
        "content": "#tag1 #tag2 #tag3\n\n# 제목\n본문",
        "expected": ["tag1", "tag2", "tag3"]
    },
    {
        "name": "2줄에 걸친 태그",
        "content": "#tag1 #tag2 #tag3\n#tag4 #tag5\n\n# 제목\n본문",
        "expected": ["tag1", "tag2", "tag3", "tag4", "tag5"]
    },
    {
        "name": "3줄에 걸친 태그",
        "content": "#tag1 #tag2\n#tag3 #tag4\n#tag5 #tag6\n\n# 제목",
        "expected": ["tag1", "tag2", "tag3", "tag4", "tag5", "tag6"]
    },
    {
        "name": "빈 줄 전까지만 추출",
        "content": "#tag1 #tag2\n\n본문에 #tag3 있어도 무시",
        "expected": ["tag1", "tag2"]
    },
    {
        "name": "제목 전까지만 추출",
        "content": "#tag1 #tag2\n# 제목\n본문에 #tag3",
        "expected": ["tag1", "tag2"]
    },
    {
        "name": "태그가 많아서 여러 줄 (실제 사례)",
        "content": "#interview #python #coding #javascript #backend\n#frontend #database #api #rest #graphql\n\n# 이력서\n경력...",
        "expected": ["interview", "python", "coding", "javascript", "backend", "frontend", "database", "api", "rest", "graphql"]
    },
    {
        "name": "공유기 예시",
        "content": "#공유기 #iptime\n\n## iptime 설정\n본문...",
        "expected": ["공유기", "iptime"]
    },
    {
        "name": "태그 1개만",
        "content": "#embedding\n\n# 배치 임베딩\n본문...",
        "expected": ["embedding"]
    }
]

print("🧪 여러 줄 태그 추출 테스트\n")
print("=" * 70)

passed = 0
failed = 0

for test in test_cases:
    result = extract_tags(test["content"])
    expected_set = set(test["expected"])
    result_set = set(result)

    is_passed = expected_set == result_set
    status = "✅ PASS" if is_passed else "❌ FAIL"

    if is_passed:
        passed += 1
    else:
        failed += 1

    print(f"\n{status} {test['name']}")
    print(f"   예상: {sorted(test['expected'])}")
    print(f"   결과: {sorted(result)}")

    if not is_passed:
        print(f"   ⚠️  누락: {expected_set - result_set}")
        print(f"   ⚠️  추가: {result_set - expected_set}")

print("\n" + "=" * 70)
print(f"\n📊 결과: {passed} PASS, {failed} FAIL")

if failed == 0:
    print("✅ 모든 테스트 통과!")
else:
    print(f"❌ {failed}개 테스트 실패")
