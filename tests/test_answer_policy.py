from types import SimpleNamespace
from unittest.mock import Mock

import pytest


@pytest.mark.parametrize("query,language", [
    ("東京から駅まで", "Japanese"),
    ("인증서 정보를 알려줘", "Korean"),
    ("How many retries are allowed?", "English"),
])
def test_unambiguous_query_script_sets_answer_language(services, query, language):
    from rag import generator
    assert language in generator._answer_system_prompt("auto", query)


def test_explicit_language_overrides_query_script(services):
    from rag import generator
    assert "English" in generator._answer_system_prompt("en", "정보 알려줘")


@pytest.mark.parametrize("error", [False, True])
def test_followup_keeps_user_topic_if_rewrite_omits_it(services, monkeypatch, error):
    from rag import generator
    create = Mock(side_effect=RuntimeError("offline")) if error else Mock(return_value=SimpleNamespace(
        status="completed", output_text="What was my score?"
    ))
    monkeypatch.setattr(generator.openai_client.responses, "create", create)
    history = [{"role": "user", "content": "Tell me about Cloud Certification Z."},
               {"role": "assistant", "content": "Unverified score: 999."}]
    result = generator._rewrite_query_standalone("What was my score?", history)
    assert "Cloud Certification Z" in result
    assert "999" not in result
    assert "What was my score?" in result
    assert create.call_args.kwargs["model"] == generator.CHAT_MODEL
    assert create.call_args.kwargs["store"] is False
    prompt = create.call_args.kwargs["input"][0]["content"]
    assert "equality versus ranges" in prompt
