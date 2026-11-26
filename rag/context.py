from functools import lru_cache

import tiktoken


MAX_EVIDENCE_TOKENS = 2400
MAX_NOTE_TOKENS = 4000


@lru_cache(maxsize=1)
def _encoding():
    return tiktoken.get_encoding("o200k_base")


def _truncate(text: str, budget: int) -> str:
    return _encoding().decode(_encoding().encode(text)[:max(0, budget)])


def note_context(payload: dict) -> str:
    """Keep the retrieved evidence first, including for older indexed payloads."""
    chunk = (payload.get("chunk_text") or "").strip()
    parent = (payload.get("parent_text") or payload.get("text") or "").strip()
    retrieved = payload.get("retrieved_chunks") or []
    if retrieved:
        pieces = []
        seen = set()
        for item in retrieved:
            text = item.get("text", "").strip()
            key = text
            if text and key not in seen:
                seen.add(key)
                pieces.append(text)
                parent = parent.replace(text, "")
        evidence = _truncate("\n\n".join(pieces), MAX_EVIDENCE_TOKENS)
        parent = parent.strip()
        return _truncate("\n\n".join(part for part in (evidence, parent) if part), MAX_NOTE_TOKENS)
    if not chunk:
        return parent
    if chunk in parent:
        before, _, after = parent.partition(chunk)
        parent = "\n\n".join(part.strip() for part in (before, after) if part.strip())
    return "\n\n".join(part for part in (chunk, parent) if part)
