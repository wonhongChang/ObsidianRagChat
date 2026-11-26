import json
from types import SimpleNamespace as Obj
from unittest.mock import Mock

import pytest


def unpack(frame):
    assert frame.startswith("data: ") and frame.endswith("\n\n")
    return json.loads(frame[6:])


def completed(text="One two."):
    return Obj(status="completed", output_text=text,
               usage=Obj(input_tokens=11, output_tokens=4, total_tokens=15))


@pytest.fixture
def rag(services, monkeypatch):
    from rag import generator
    hit = Obj(id=7, score=0.9, payload={"filename": "Research", "chunk_text": "Reference material.",
                                        "tags": ["study"], "section": "Notes"})
    lookup = Mock(return_value=[hit, hit])
    monkeypatch.setattr(generator, "search_relevant_notes", lookup)
    # Never send a request if an unexpected branch is taken.
    monkeypatch.setattr(generator.openai_client.chat.completions, "create", Mock(side_effect=AssertionError))
    return generator, lookup


def test_real_text_deltas_precede_completion_and_rewrite_is_local_to_search(rag, monkeypatch):
    g, lookup = rag
    def chunks():
        yield Obj(type="response.created")
        yield Obj(type="response.reasoning_text.delta", delta="Hidden")
        yield Obj(type="response.output_text.delta", delta="One ")
        yield Obj(type="response.output_text.delta", delta="two.")
        yield Obj(type="response.completed", response=completed())
    create = Mock(side_effect=[completed("Search this #study"), chunks()])
    monkeypatch.setattr(g.openai_client.responses, "create", create)
    stream = g.generate_followup_stream("More #study?", [{"role": "user", "content": "Previous #old"}])
    assert unpack(next(stream)) == {"type": "token", "content": "One "}
    tail = [unpack(frame) for frame in stream]
    assert [part["type"] for part in tail] == ["token", "sources", "done"]
    assert tail[1]["sources"][0]["section"] == "Notes" and len(tail[1]["sources"]) == 1
    assert tail[-1]["answer"] == "One two."
    assert tail[-1]["usage"] == {"prompt_tokens": 11, "completion_tokens": 4, "total_tokens": 15}
    assert lookup.call_count == 1 and lookup.call_args.kwargs["filter_tags"] == ["study"]
    assert "Previous #old" in lookup.call_args.args[0]
    assert [call.kwargs["stream"] for call in create.call_args_list] == [False, True]
    for call in create.call_args_list:
        assert call.kwargs["model"] == "gpt-6-luna"
        assert call.kwargs["store"] is False and call.kwargs["reasoning"] == {"effort": "none"}
        assert 0 < call.kwargs["max_output_tokens"] <= 4000
        assert "temperature" not in call.kwargs and "max_tokens" not in call.kwargs


@pytest.mark.parametrize("failure", ["response.incomplete", "response.failed", "error", "truncated", "network", "mismatch"])
def test_partial_stream_never_emits_success(rag, monkeypatch, failure):
    g, _ = rag
    closed = []
    def chunks():
        try:
            yield Obj(type="response.output_text.delta", delta="Partial")
            if failure == "network":
                raise ConnectionError("offline")
            if failure == "mismatch":
                yield Obj(type="response.completed", response=completed("Different"))
            elif failure != "truncated":
                yield Obj(type=failure)
        finally:
            closed.append(True)
    create = Mock(return_value=chunks())
    monkeypatch.setattr(g.openai_client.responses, "create", create)
    stream = g.generate_answer_stream("Q")
    assert unpack(next(stream))["type"] == "token"
    with pytest.raises((RuntimeError, ConnectionError)):
        next(stream)
    assert closed and create.call_count == 1


@pytest.mark.parametrize("status,text", [("incomplete", "Partial"), ("failed", ""), ("completed", " ")])
def test_sync_refuses_partial_or_blank(rag, monkeypatch, status, text):
    g, _ = rag
    create = Mock(return_value=Obj(status=status, output_text=text))
    monkeypatch.setattr(g.openai_client.responses, "create", create)
    with pytest.raises(RuntimeError):
        g.generate_answer_with_rag("Q")


def test_reject_other_models_before_retrieval(rag, monkeypatch):
    g, lookup = rag
    create = Mock(side_effect=AssertionError)
    monkeypatch.setattr(g.openai_client.responses, "create", create)
    with pytest.raises(ValueError):
        g.generate_answer_with_rag("Q", model="unsupported")
    create.assert_not_called()
    lookup.assert_not_called()
