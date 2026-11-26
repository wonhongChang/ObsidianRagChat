from unittest.mock import Mock

import pytest
from qdrant_client.models import PointStruct


def document(version="v1", text=None):
    return {
        "path": "note.md", "filename": "note.md", "tags": ["demo"], "mtime": 0,
        "hash": version, "text": text or "# Note\nAn example note for indexing.",
    }


def test_unchanged_documents_skip_embedding(services):
    services.documents.append(document())
    services.sync.sync_all()
    services.embed.reset_mock()
    assert services.sync.sync_all() == {
        "vector_documents": 0, "es_documents": 0, "deleted_documents": 0,
    }
    services.embed.assert_not_called()


def test_embedding_failure_preserves_old_vectors(services):
    services.documents.append(document())
    services.sync.sync_all()
    old = services.store.get_existing_documents()
    services.documents[:] = [document("v2")]
    services.embed.side_effect = RuntimeError("embedding down")
    with pytest.raises(RuntimeError, match="embedding down"):
        services.sync.sync_all()
    assert services.store.get_existing_documents() == old


def test_partial_vector_upload_is_retried(services, monkeypatch):
    services.documents.append(document())
    services.sync.sync_all()
    old_ids = set(services.store.get_existing_documents()["note.md"]["chunk_ids"])
    services.documents[:] = [document("v2", "# Long\n" + "Some long material. " * 500)]
    real_upsert = services.qdrant.upsert

    def interrupted(**kwargs):
        real_upsert(**{**kwargs, "points": kwargs["points"][:1]})
        raise RuntimeError("interrupted upload")

    with monkeypatch.context() as scoped:
        scoped.setattr(services.qdrant, "upsert", interrupted)
        with pytest.raises(RuntimeError, match="interrupted upload"):
            services.sync.sync_all()
    incomplete = services.store.get_existing_documents()["note.md"]
    assert old_ids.issubset(incomplete["chunk_ids"])
    assert incomplete["hash"] is None
    services.sync.sync_all()
    complete = services.store.get_existing_documents()["note.md"]
    assert complete["hash"] == "v2"
    assert not old_ids.intersection(complete["chunk_ids"])


def test_partial_new_document_detected_by_chunk_count(services, monkeypatch):
    services.documents.append(document("v1", "# Long\n" + "Some long material. " * 500))
    real_upsert = services.qdrant.upsert
    def interrupted(**kwargs):
        real_upsert(**{**kwargs, "points": kwargs["points"][:1]})
        raise RuntimeError("interrupted upload")
    with monkeypatch.context() as scoped:
        scoped.setattr(services.qdrant, "upsert", interrupted)
        with pytest.raises(RuntimeError):
            services.sync.sync_all()
    assert services.store.get_existing_documents()["note.md"]["hash"] is None
    services.sync.sync_all()
    assert services.store.get_existing_documents()["note.md"]["hash"] == "v1"


def test_es_failure_repaired_without_reembedding(services, monkeypatch):
    services.documents.append(document())
    with monkeypatch.context() as scoped:
        scoped.setattr(services.sync, "index_documents_bulk", Mock(side_effect=RuntimeError("ES down")))
        with pytest.raises(RuntimeError, match="ES down"):
            services.sync.sync_all()
    services.embed.reset_mock()
    services.sync.sync_all()
    services.embed.assert_not_called()
    assert services.es_state == {"note.md": "v1"}
    assert services.invalidate.call_count == 2


def test_delete_failure_repaired_from_remaining_es_state(services, monkeypatch):
    services.documents.append(document())
    services.sync.sync_all()
    services.documents.clear()
    with monkeypatch.context() as scoped:
        scoped.setattr(services.sync, "delete_document", Mock(side_effect=RuntimeError("ES down")))
        with pytest.raises(RuntimeError):
            services.sync.sync_all()
    assert services.store.get_existing_documents() == {}
    assert services.es_state
    services.sync.sync_all()
    assert services.es_state == {}


def test_old_payload_does_not_force_full_reembedding(services):
    services.store.ensure_collection_exists(3)
    services.qdrant.upsert(
        collection_name=services.store.COLLECTION_NAME,
        points=[PointStruct(id=42, vector=[1., 0., 0.], payload={"path": "note.md", "hash": "v1"})],
    )
    assert services.store.get_existing_documents()["note.md"]["hash"] == "v1"


def test_index_read_failure_aborts_before_mutation(services, monkeypatch):
    services.documents.append(document())
    services.sync.sync_all()
    monkeypatch.setattr(services.qdrant, "get_collections", Mock(side_effect=RuntimeError("read failed")))
    services.embed.reset_mock()
    with pytest.raises(RuntimeError, match="read failed"):
        services.sync.sync_all()
    services.embed.assert_not_called()


def test_lexical_only_sync_leaves_vectors_untouched_then_hybrid_catches_up(services, monkeypatch):
    services.documents.extend([document(), {**document(), "path":"retired.md"}])
    services.sync.sync_all()
    before = services.store.get_existing_documents()
    services.embed.reset_mock()
    services.documents[:] = [document("v2")]
    with monkeypatch.context() as scoped:
        scoped.delenv("OPENAI_EMBEDDING_API_KEY")
        scoped.setattr(services.store, "client", Mock(side_effect=AssertionError("Qdrant opened")))
        scoped.setattr(services.store, "get_existing_documents", Mock(side_effect=AssertionError("Qdrant read")))
        assert services.sync.sync_all() == {"vector_documents":0,"es_documents":1,"deleted_documents":1}
        assert services.sync.sync_all() == {"vector_documents":0,"es_documents":0,"deleted_documents":0}
        assert not services.store.client.mock_calls
    services.embed.assert_not_called()
    assert services.store.get_existing_documents() == before
    assert services.es_state == {"note.md":"v2"}
    assert services.sync.sync_all() == {"vector_documents":1,"es_documents":0,"deleted_documents":1}
    assert set(services.store.get_existing_documents()) == {"note.md"}
    assert services.store.get_existing_documents()["note.md"]["hash"] == "v2"
