import re
import hashlib
import tiktoken

MAX_CHUNK_TOKENS = 512
OVERLAP_TOKENS = 50
MIN_CHUNK_TOKENS = 30

_encoding = tiktoken.encoding_for_model("gpt-4o-mini")


def _count_tokens(text: str) -> int:
    return len(_encoding.encode(text))


def _sliding_window_split(text: str, max_tokens: int, overlap: int) -> list:
    tokens = _encoding.encode(text)
    if len(tokens) <= max_tokens:
        return [text]
    step = max_tokens - overlap
    chunks = []
    for i in range(0, len(tokens), step):
        chunk_tokens = tokens[i:i + max_tokens]
        chunks.append(_encoding.decode(chunk_tokens))
    return chunks


def _extract_section_title(text: str) -> str:
    match = re.match(r'^#{1,6}\s+(.+)', text.strip())
    return match.group(1).strip() if match else ""


def _chunk_by_headers(text: str, max_chunk_tokens: int) -> list:
    sections = re.split(r'\n(?=#{1,3} )', text)
    chunks = []
    for section in sections:
        if not section.strip():
            continue
        if _count_tokens(section) <= max_chunk_tokens:
            chunks.append(section.strip())
        else:
            chunks.extend(_sliding_window_split(section, max_chunk_tokens, OVERLAP_TOKENS))
    return chunks


def chunk_document(doc: dict) -> list:
    """
    문서를 Qdrant 업로드용 청크 리스트로 변환.
    각 청크는 point_id가 포함된 dict.
    """
    text = doc["text"]
    raw_chunks = _chunk_by_headers(text, MAX_CHUNK_TOKENS)

    result = []
    for i, chunk_text in enumerate(raw_chunks):
        if not chunk_text.strip():
            continue
        if _count_tokens(chunk_text) < MIN_CHUNK_TOKENS:
            continue

        chunk_id_str = f"{doc['path']}::chunk::{i}"
        point_id = int(hashlib.md5(chunk_id_str.encode()).hexdigest(), 16) % (2 ** 63)

        result.append({
            "path": doc["path"],
            "filename": doc["filename"],
            "tags": doc["tags"],
            "mtime": doc["mtime"],
            "hash": doc["hash"],
            "section": _extract_section_title(chunk_text),
            "chunk_index": i,
            "chunk_text": chunk_text,
            "parent_text": text[:4000],
            "point_id": point_id,
        })
    return result
