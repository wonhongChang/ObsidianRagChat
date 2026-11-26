from embed.chunker import chunk_document, _count_tokens, _sliding_window_split


def _doc(text: str) -> dict:
    return {
        "text": text,
        "filename": "short.md",
        "path": "notes/short.md",
        "tags": ["test"],
        "mtime": 0,
        "hash": "hash",
    }


def test_short_note_still_creates_chunk():
    chunks = chunk_document(_doc("# Idea\nTiny note."))

    assert len(chunks) == 1
    assert chunks[0]["chunk_index"] == 0
    assert chunks[0]["chunk_text"] == "# Idea\nTiny note."
    assert chunks[0]["section"] == "Idea"


def test_empty_note_creates_no_chunks():
    assert chunk_document(_doc("   \n")) == []


def test_long_sections_respect_size_and_overlap():
    from embed.chunker import _encoding
    text = "Repeatable token window. " * 500
    windows = _sliding_window_split(text, 512, 50)
    tokens = _encoding.encode(text)
    assert len(windows) > 1
    for i, window in enumerate(windows):
        assert window == _encoding.decode(tokens[i * 462:i * 462 + 512])
        assert _count_tokens(window) <= 512


def test_late_evidence_and_adjacent_chunks_in_parent():
    text = "# Overview\n" + "Background information. " * 800
    text += "\n## Recovery\nThe recovery code is DELTA-42. " + "Recovery procedure. " * 50
    chunks = chunk_document(_doc(text))
    target = next(c for c in chunks if "DELTA-42" in c["chunk_text"])
    assert "DELTA-42" not in text[:4000]
    assert target["chunk_text"] in target["parent_text"]
    assert target["section"] == "Recovery"
    assert all(c["chunk_count"] == len(chunks) for c in chunks)
    assert all(_count_tokens(c["chunk_text"]) <= 512 for c in chunks)


def test_ids_are_stable_per_content_generation():
    doc = _doc("# Short\nA small note.")
    same = chunk_document(doc)[0]["point_id"]
    assert chunk_document(dict(doc))[0]["point_id"] == same
    assert chunk_document({**doc, "hash": "changed"})[0]["point_id"] != same
