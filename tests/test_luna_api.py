import json
from unittest.mock import Mock

import pytest
from fastapi.testclient import TestClient


@pytest.mark.parametrize("method,path", [
    ("delete", "/api/cache"), ("get", "/api/cache/stats"), ("get", "/api/notes/count"),
])
def test_storage_errors_do_not_disclose_provider_details(services, monkeypatch, method, path, caplog):
    import app
    from search import document_index

    marker = "private-backend-diagnostic"
    failure = Mock(side_effect=RuntimeError(marker))
    monkeypatch.setattr(app, "clear_all_cache", failure)
    monkeypatch.setattr(app, "get_cache_stats", failure)
    monkeypatch.setattr(document_index.es, "count", failure)
    response = TestClient(app.app).request(method, path)
    assert response.status_code == 503
    assert marker not in response.text and marker not in caplog.text


@pytest.mark.parametrize("endpoint", ["/api/search", "/api/search/stream"])
@pytest.mark.parametrize("model", ["gpt-4o-mini", "gpt-5-mini", "text-embedding-3-small"])
def test_rejects_other_models_before_cache_or_provider(services, monkeypatch, endpoint, model):
    import app
    cache = Mock(side_effect=AssertionError("Invalid model reached cache"))
    monkeypatch.setattr(app, "get_cached_rag", cache)
    response = TestClient(app.app).post(endpoint, json={"query": "hello", "model": model})
    assert response.status_code == 422
    assert response.json()["detail"][0]["loc"] == ["body", "model"]
    cache.assert_not_called()


def test_cache_keys_separate_retrieval_modes_and_match_across_transports(services, monkeypatch):
    import app
    read = Mock(return_value={"answer": "cached note", "sources": []})
    monkeypatch.setattr(app, "get_cached_rag", read)
    monkeypatch.setattr(app, "save_query", Mock())
    client = TestClient(app.app)
    keys = []
    for embedding_key, mode in [("", "lexical"), ("test-embedding-key", "hybrid")]:
        monkeypatch.setenv("OPENAI_EMBEDDING_API_KEY", embedding_key)
        assert client.get("/health").json() == {
            "status": "healthy", "model": "gpt-6-luna", "retrieval_mode": mode,
        }
        assert client.post("/api/search", json={"query": "hello"}).status_code == 200
        key = read.call_args.args[0]
        client.post("/api/search/stream", json={"query": "hello", "model": "gpt-6-luna"}).raise_for_status()
        assert key == read.call_args.args[0]
        keys.append(key)
    assert keys[0] != keys[1]


@pytest.mark.parametrize("ending", ["missing_done", "error_event", "exception"])
def test_aborted_stream_is_never_cached(services, monkeypatch, ending):
    import app

    def interrupted(**kwargs):
        yield 'data: {"type":"token","content":"partial"}\n\n'
        if ending == "exception":
            raise RuntimeError("Provider stream interrupted")
        if ending == "error_event":
            yield 'data: {"type":"error","message":"Incomplete answer"}\n\n'

    write = Mock()
    monkeypatch.setattr(app, "get_cached_rag", lambda _: None)
    monkeypatch.setattr(app, "set_cached_rag", write)
    monkeypatch.setattr(app, "generate_answer_stream", interrupted)
    response = TestClient(app.app).post("/api/search/stream", json={"query": "hello"})
    events = [json.loads(line[6:])["type"] for line in response.text.splitlines() if line]
    assert events == ["token", "error"]
    write.assert_not_called()
