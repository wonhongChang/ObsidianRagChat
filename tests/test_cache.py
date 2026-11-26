import json
from unittest.mock import Mock

import pytest
import redis


@pytest.mark.parametrize("value", ["not json", "[]", "null"])
def test_invalid_cache_is_a_miss(monkeypatch, value):
    from search import cache
    monkeypatch.setattr(cache, "redis_client", Mock(get=Mock(return_value=value)))
    assert cache.get_cached_rag("query") is None


def test_cache_read_and_write_fail_open(monkeypatch):
    from search import cache
    client = Mock(
        get=Mock(side_effect=redis.ConnectionError()),
        setex=Mock(side_effect=redis.TimeoutError()),
    )
    monkeypatch.setattr(cache, "redis_client", client)
    assert cache.get_cached_rag("query") is None
    assert cache.set_cached_rag("query", {"answer": "ok"}) is False


def test_invalidation_only_deletes_rag_keys(monkeypatch):
    from search import cache
    client = Mock()
    client.scan_iter.return_value = iter(["rag:old", "rag:v2:current"])
    monkeypatch.setattr(cache, "redis_client", client)
    cache.clear_all_cache()
    client.scan_iter.assert_called_once_with(match="rag:*", count=500)
    client.delete.assert_called_once_with("rag:old", "rag:v2:current")
    client.flushdb.assert_not_called()


@pytest.mark.parametrize("streaming", [False, True])
def test_api_still_returns_answer_when_redis_is_down(services, monkeypatch, streaming):
    from fastapi.testclient import TestClient
    import app
    from search import cache
    monkeypatch.setattr(cache, "redis_client", Mock(
        get=Mock(side_effect=redis.ConnectionError()),
        setex=Mock(side_effect=redis.ConnectionError()),
    ))
    result = {"answer": "Known answer", "sources": [], "usage": {}, "elapsed_time": 0}
    monkeypatch.setattr(app, "generate_answer_with_rag", lambda **kwargs: result)
    events = [
        {"type": "token", "content": "Known answer"},
        {"type": "sources", "sources": []},
        {"type": "done", "usage": {}, "elapsed_time": 0},
    ]
    monkeypatch.setattr(app, "generate_answer_stream", lambda **kwargs: (
        f"data: {json.dumps(event)}\n\n" for event in events
    ))
    with TestClient(app.app) as client:
        response = client.post("/api/search/stream" if streaming else "/api/search", json={"query": "test"})
    assert response.status_code == 200
    assert "Known answer" in response.text
    if streaming:
        assert '"type": "done"' in response.text


def test_language_and_history_keep_distinct_cache_keys(services, monkeypatch):
    import asyncio
    import app
    keys = []
    monkeypatch.setattr(app, "get_cached_rag", lambda key: keys.append(key))
    monkeypatch.setattr(app, "set_cached_rag", lambda *args: None)
    monkeypatch.setattr(app, "is_independent_question", lambda *args: False)
    monkeypatch.setattr(app, "generate_answer_with_rag", lambda **kwargs: {"answer": "ok"})
    monkeypatch.setattr(app, "generate_followup_answer", lambda **kwargs: {"answer": "ok"})
    for language, history in [
        ("ko", []), ("ja", []),
        ("ko", [{"role": "user", "content": "Topic A"}]),
        ("ko", [{"role": "user", "content": "Topic B"}]),
    ]:
        asyncio.run(app.search(app.QueryRequest(query="same", response_language=language, history=history)))
    assert len(set(keys)) == 4
