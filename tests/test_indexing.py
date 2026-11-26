from unittest.mock import Mock

import pytest


def test_es_partial_bulk_failure_is_reported(services, monkeypatch):
    from search import document_index
    monkeypatch.setattr(document_index, "ensure_index_exists", lambda: None)
    monkeypatch.setattr("elasticsearch.helpers.bulk", lambda *a, **k: (0, [{"index": {"status": 503}}]))
    with pytest.raises(RuntimeError, match="1 documents"):
        document_index.index_documents_bulk([{
            "path": "example.md", "filename": "example.md", "text": "text",
            "tags": [], "mtime": 0, "hash": "v1",
        }])


def test_es_read_failure_is_not_an_empty_index(services, monkeypatch):
    from search import document_index
    client = Mock()
    client.indices.exists.side_effect = RuntimeError("ES unavailable")
    monkeypatch.setattr(document_index, "es", client)
    with pytest.raises(RuntimeError, match="ES unavailable"):
        document_index.get_indexed_documents()


def test_unreadable_source_aborts_scan(tmp_path, monkeypatch):
    from embed.document_loader import load_markdown_files
    import builtins
    path = tmp_path / "unreadable.md"
    path.write_text("A note", encoding="utf-8")
    real_open = builtins.open
    def unreadable(file, *args, **kwargs):
        if str(file) == str(path):
            raise PermissionError("locked")
        return real_open(file, *args, **kwargs)
    monkeypatch.setattr(builtins, "open", unreadable)
    with pytest.raises(RuntimeError, match="Markdown scan failed"):
        load_markdown_files(str(tmp_path))
