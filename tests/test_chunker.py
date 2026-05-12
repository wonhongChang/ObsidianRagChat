from embed.chunker import chunk_document


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
