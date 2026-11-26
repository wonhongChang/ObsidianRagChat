from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from rag.context import note_context


def test_legacy_prefix_cannot_hide_matched_evidence():
    payload = {"chunk_text": "The answer is DELTA-42.", "parent_text": "Old introduction."}
    assert note_context(payload).startswith("The answer is DELTA-42.")


def test_neighborhood_does_not_duplicate_evidence():
    payload = {"chunk_text": "Evidence.", "parent_text": "Before.\nEvidence.\nAfter."}
    context = note_context(payload)
    assert context.startswith("Evidence.")
    assert context.count("Evidence.") == 1
    assert "Before." in context and "After." in context


def test_legacy_full_document_and_empty_payload():
    assert note_context({"text": "Legacy document."}) == "Legacy document."
    assert note_context({}) == ""


@pytest.mark.parametrize("streaming", [False, True])
@pytest.mark.parametrize("followup", [False, True])
def test_all_answer_paths_include_retrieved_evidence(services, monkeypatch, streaming, followup):
    from rag import generator
    hit = SimpleNamespace(
        id=1, score=0.8,
        payload={"filename": "long.md", "chunk_text": "DELTA-42 is the recovery code.",
                 "parent_text": "An unrelated introduction.", "tags": [],
                 "retrieved_chunks": [{"text": "DELTA-42 is the recovery code."},
                                      {"text": "Recovery needs two approvals."}]},
    )
    monkeypatch.setattr(generator, "search_relevant_notes", lambda *a, **k: [hit])
    monkeypatch.setattr(generator, "_rewrite_query_standalone", lambda query, history: query)
    usage = SimpleNamespace(input_tokens=10, output_tokens=5, total_tokens=15)
    response = SimpleNamespace(
        status="completed", output_text="DELTA-42 [1]",
        usage=usage,
    )
    events = [SimpleNamespace(type="response.output_text.delta", delta="DELTA-42 [1]"),
              SimpleNamespace(type="response.completed", response=response)]
    create = Mock(return_value=iter(events) if streaming else response)
    monkeypatch.setattr(generator.openai_client.responses, "create", create)
    if followup:
        function = generator.generate_followup_stream if streaming else generator.generate_followup_answer
        result = function("What is the code?", [{"role": "user", "content": "Recovery"}])
    else:
        function = generator.generate_answer_stream if streaming else generator.generate_answer_with_rag
        result = function("What is the code?")
    if streaming:
        list(result)
    messages = create.call_args.kwargs["input"]
    assert messages[0]["content"] == generator._answer_system_prompt("auto", "What is the code?")
    assert "DELTA-42 is the recovery code." in messages[-1]["content"]
    assert "Recovery needs two approvals." in messages[-1]["content"]
