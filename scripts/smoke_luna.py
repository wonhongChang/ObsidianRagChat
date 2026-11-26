"""Opt-in live smoke test: one generation request, synthetic evidence, no vault or DB."""
import argparse
import json
from types import SimpleNamespace
from unittest.mock import patch


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--live", action="store_true", help="Allow one billable OpenAI response")
    if not parser.parse_args().live:
        parser.error("Requires --live (one billable request)")

    from rag import generator
    from rag.model_config import CHAT_MODEL

    hit = SimpleNamespace(id="smoke", score=1.0, payload={
        "filename": "synthetic.md", "chunk_text": "The label on the test card is AZURE-17.", "tags": [],
    })
    client = generator.openai_client.with_options(base_url="https://api.openai.com/v1", max_retries=0, timeout=45)
    with patch.object(generator, "openai_client", client), patch.object(
        generator, "search_relevant_notes", return_value=[hit]
    ):
        events = [json.loads(event.removeprefix("data: ")) for event in generator.generate_answer_stream(
            "What label is on the test card?", top_k=1, response_language="en",
        )]
    deltas = [e["content"] for e in events if e["type"] == "token"]
    sources = [s["filename"] for e in events if e["type"] == "sources" for s in e["sources"]]
    if (not deltas or "AZURE-17" not in "".join(deltas) or sources != ["synthetic.md"]
            or events[-1]["type"] != "done" or not events[-1]["usage"]):
        raise RuntimeError("Synthetic streaming smoke test failed (no retry)")
    print(json.dumps({"model": CHAT_MODEL, "synthetic_only": True, "token_events": len(deltas),
                      "completed": True, "usage": events[-1]["usage"]}))


if __name__ == "__main__":
    main()
