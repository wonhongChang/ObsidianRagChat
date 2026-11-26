from unittest.mock import Mock

import pytest
from elasticsearch import NotFoundError


def test_lexical_query_preserves_late_evidence_and_filename_boost(services, monkeypatch):
    from rag import generator
    from rag.context import note_context
    from search import document_index
    monkeypatch.delenv("OPENAI_EMBEDDING_API_KEY")
    monkeypatch.setattr(generator, "embed_texts", Mock(side_effect=AssertionError("embedding called")))
    fragments = ["Renew at the counter.", "The exam lasts 80 minutes."]
    hit = {"_id": "file", "_score": 6.5, "_source": {
        "path": "guide.md", "hash": "example", "filename": "AI-102.md", "tags": ["Study"],
        "text": "introduction " * 500 + " ".join(fragments),
    }, "highlight": {"text": [*fragments, fragments[0]]}}
    search = Mock(return_value={"hits": {"hits": [hit, hit]}})
    monkeypatch.setattr(document_index.es, "search", search)
    results = generator.search_relevant_notes("#Study AI-102 renewal", limit=2, filter_tags=["Study"])
    assert len(results) == 1
    assert results[0].id == "guide.md" and results[0].payload["chunk_text"] == fragments[0]
    assert note_context(results[0].payload) == "\n\n".join(fragments)
    request = search.call_args.kwargs["query"]["bool"]
    assert request["filter"] == [{"terms": {"tags": ["Study", "study"]}}]
    assert request["must"][0]["multi_match"] == {"query": "AI-102 renewal", "fields": ["filename^3", "text"]}


@pytest.mark.parametrize("query", ["#Study", "Study 태그"])
def test_lexical_tag_only_returns_bounded_excerpt(services, monkeypatch, query):
    from search import document_index
    search = Mock(return_value={"hits": {"hits": [{"_source": {"path": "note.md", "text": "x"*2500}}]}})
    monkeypatch.setattr(document_index.es, "search", search)
    hit, = document_index.search_lexical_notes(query, 3, ["Study"])
    assert hit.payload["chunk_text"] == "x"*1600
    assert "must" not in search.call_args.kwargs["query"]["bool"]


def test_absent_es_index_is_empty_but_error_is_not_suppressed(services, monkeypatch):
    from search import document_index
    err = NotFoundError("missing", meta=Mock(status=404), body={"error": {"type":"index_not_found_exception"}})
    search = Mock(side_effect=err)
    monkeypatch.setattr(document_index.es, "search", search)
    assert document_index.search_lexical_notes("anything", 1) == []
    search.side_effect = RuntimeError("ES unavailable")
    with pytest.raises(RuntimeError, match="ES unavailable"):
        document_index.search_lexical_notes("#tag", 1, ["tag"])


def test_only_explicit_embedding_key_reaches_sdk(monkeypatch):
    from embed import embedder
    from scripts.evaluate_rag import retrieval_report
    monkeypatch.setattr(embedder, "load_dotenv", lambda: None)
    monkeypatch.setenv("OPENAI_API_KEY", "test-generation-only")
    monkeypatch.delenv("OPENAI_EMBEDDING_API_KEY", raising=False)
    sdk = Mock()
    monkeypatch.setattr(embedder, "OpenAI", sdk)
    with pytest.raises(ValueError, match="OPENAI_EMBEDDING_API_KEY"):
        embedder.embedding_client()
    with pytest.raises(ValueError, match="OPENAI_EMBEDDING_API_KEY"):
        retrieval_report([], [], 1)
    sdk.assert_not_called()
    monkeypatch.setenv("OPENAI_EMBEDDING_API_KEY", "test-embedding-only")
    embedder.embedding_client()
    sdk.assert_called_once_with(api_key="test-embedding-only")
