"""Document-level ranking without discarding the retrieved supporting chunks."""
import re
from collections import defaultdict


MAX_CHUNKS_PER_DOCUMENT = 4
RRF_K = 60
TITLE_STOPWORDS = set("""what which how when where why please tell give find note notes information
어떤 어떻게 무엇 알려 알려줘 알려주세요 정보 사용자 방법 방식 내용 노트 노트에서 노트의
내 그중 그중에서 그럼 그리고 각각 대해 대해서 있는 없는 정확한 실제
どの どう です ます について 教えて 教えてください""".split())


def filename_keywords(query: str) -> set[str]:
    # Latin fragments such as "am" in "example" are not meaningful title matches.
    keywords = set(re.findall(r"[a-z0-9]+(?:[-_][a-z0-9]+)*", query.casefold()))
    keywords = {word for word in keywords if len(word) >= 3}
    for word in re.findall(r"[가-힣ぁ-ヿ一-鿿㐀-䶿]{2,}", query):
        stem = re.sub(r"(?:으로|에서|은|는|을|를|의|이|가|와|과|로)$", "", word)
        if word in TITLE_STOPWORDS or stem in TITLE_STOPWORDS:
            continue
        keywords.add(word)
        for size in (2, 3):
            keywords.update(word[i:i + size] for i in range(len(word) - size + 1))
    return keywords - TITLE_STOPWORDS


def filename_match_score(query: str, filename: str) -> int:
    """Count covered title characters, not overlapping n-grams or Latin fragments."""
    title = filename.casefold().removesuffix(".md")
    covered = set()
    for word in filename_keywords(query):
        pattern = re.escape(word)
        if word.isascii():
            pattern = rf"(?<![a-z0-9]){pattern}(?![a-z0-9])"
        for match in re.finditer(pattern, title):
            covered.update(range(match.start(), match.end()))
    return len(covered)


def path_match_score(query: str, path: str) -> int:
    """An explicitly named folder is a scope signal, not a mandatory filter."""
    terms = filename_keywords(query)
    folders = set(path.replace("\\", "/").casefold().split("/")[:-1])
    return sum(len(folder) for folder in folders if len(folder) >= 3 and folder in terms)


def group_evidence(points, limit: int):
    """Keep vector scores and up to four distinct evidence chunks per document."""
    groups = defaultdict(list)
    for point in points:
        payload = point.payload or {}
        groups[payload.get("path") or str(point.id)].append(point)

    documents = []
    for chunks in groups.values():
        chunks.sort(key=lambda point: point.score, reverse=True)
        best = chunks[0]
        evidence = []
        seen = set()
        for chunk in chunks:
            payload = chunk.payload or {}
            text = (payload.get("chunk_text") or "").strip()
            key = text
            if not key or key in seen:
                continue
            seen.add(key)
            evidence.append({
                "id": str(chunk.id), "text": text,
                "section": payload.get("section", ""), "score": float(chunk.score),
            })
            if len(evidence) == MAX_CHUNKS_PER_DOCUMENT:
                break
        payload = dict(best.payload or {})
        payload["retrieved_chunks"] = evidence
        documents.append(best.model_copy(update={"payload": payload}))

    return sorted(documents, key=lambda point: point.score, reverse=True)[:limit]


def fuse_document_ranks(points, dense_paths, title_paths, limit: int):
    """Fuse independent ranks; exact content copies receive only one vote per list."""
    documents = group_evidence(points, len(points))
    canonical = {}
    owners = {}
    representatives = {}
    for document in documents:
        path = document.payload.get("path") or str(document.id)
        digest = document.payload.get("hash")
        identity = ("hash", digest) if digest else ("path", path)
        owner = owners.setdefault(identity, path)
        canonical[path] = owner
        representatives.setdefault(owner, document)

    scores = defaultdict(float)
    for ranking in (dense_paths, title_paths):
        unique = list(dict.fromkeys(canonical[path] for path in ranking if path in canonical))
        for rank, path in enumerate(unique, 1):
            scores[path] += 1 / (RRF_K + rank)

    ranked = sorted(scores, key=lambda path: (-scores[path], -representatives[path].score, path))
    results = []
    for path in ranked[:limit]:
        document = representatives[path]
        payload = dict(document.payload)
        payload["retrieval_score"] = scores[path]
        payload["equivalent_paths"] = [p for p, owner in canonical.items() if owner == path and p != path]
        results.append(document.model_copy(update={"payload": payload}))
    return results
