import importlib
from types import SimpleNamespace
from unittest.mock import Mock, patch

import pytest
from qdrant_client import QdrantClient


# Match the gitignored personal vault experiments; never collect them by default.
collect_ignore_glob = ["test_example*.py", "test_search*.py"]


@pytest.fixture
def services(monkeypatch):
    """Real in-memory Qdrant, isolated ES state, no external service credentials."""
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    monkeypatch.setenv("OPENAI_EMBEDDING_API_KEY", "test-embedding-key")
    monkeypatch.setenv("QDRANT_URL", "http://127.0.0.1:6333")
    monkeypatch.setenv("QDRANT_API_KEY", "")
    monkeypatch.setenv("ELASTICSEARCH_HOST", "http://127.0.0.1:9200")
    monkeypatch.setenv("REDIS_HOST", "127.0.0.1")
    qdrant = QdrantClient(":memory:")
    with patch("qdrant_client.QdrantClient", return_value=qdrant):
        store = importlib.import_module("embed.vector_store")
        sync = importlib.import_module("sync_documents")
    monkeypatch.setattr(store, "client", qdrant)
    documents = []
    es_state = {}
    embed = Mock(side_effect=lambda texts: [[1.0, 0.0, 0.0] for _ in texts])
    invalidate = Mock()

    def index(docs):
        for doc in docs:
            es_state[doc["path"]] = doc["hash"]

    monkeypatch.setattr(sync, "load_markdown_files", lambda: list(documents))
    monkeypatch.setattr(sync, "get_indexed_documents", lambda: dict(es_state))
    monkeypatch.setattr(sync, "index_documents_bulk", index)
    monkeypatch.setattr(sync, "delete_document", lambda path: es_state.pop(path, None))
    monkeypatch.setattr(sync, "embed_texts", embed)
    monkeypatch.setattr(sync, "clear_cache_safely", invalidate)
    yield SimpleNamespace(
        qdrant=qdrant, store=store, sync=sync, documents=documents,
        es_state=es_state, embed=embed, invalidate=invalidate, index=index,
    )
    qdrant.close()
