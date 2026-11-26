"""Synthetic context regression; optional isolated live vector-retrieval evaluation."""
import argparse
import hashlib
import json
from pathlib import Path

from embed.chunker import chunk_document
from rag.context import note_context

FIXTURE = Path(__file__).resolve().parents[1] / "tests" / "fixtures" / "rag_cases.json"


def load_cases():
    fixture = json.loads(FIXTURE.read_text(encoding="utf-8"))
    documents, cases = [], []
    padding = "Background detail for this synthetic documentation example. "
    for item in fixture["documents"]:
        sections = []
        for i, section in enumerate(item["sections"]):
            sections.append(
                f"## {section['heading']}\n{section['evidence']}\n"
                + padding * (90 if i < 2 else 3)
            )
            cases.append({**section, "expected_path": item["path"], "tags": item["tags"]})
        text = f"# {item['title']}\n" + "\n".join(sections)
        documents.append({
            "path": item["path"], "filename": item["path"], "tags": item["tags"],
            "text": text, "mtime": 0, "hash": hashlib.md5(text.encode()).hexdigest(),
        })
    return documents, cases


def context_report(documents, cases):
    docs = {doc["path"]: doc for doc in documents}
    chunks = {path: chunk_document(doc) for path, doc in docs.items()}
    rows = []
    for case in cases:
        path, evidence = case["expected_path"], case["evidence"]
        hit = next((chunk for chunk in chunks[path] if evidence in chunk["chunk_text"]), None)
        if hit is None:
            raise ValueError(f"Fixture evidence was lost during chunking: {case['id']}")
        legacy = {**hit, "parent_text": docs[path]["text"][:4000]}
        rows.append({
            "id": case["id"], "language": case["language"],
            "baseline_retained": evidence in legacy["parent_text"],
            "current_retained": evidence in note_context(hit),
            "legacy_payload_retained": evidence in note_context(legacy),
        })
    return {
        "scope": "Known relevant chunk supplied; context retention only, not retrieval or answer accuracy.",
        "cases": len(rows),
        "baseline_retained": sum(row["baseline_retained"] for row in rows),
        "current_retained": sum(row["current_retained"] for row in rows),
        "legacy_payload_retained": sum(row["legacy_payload_retained"] for row in rows),
        "details": rows,
    }


def ranking_metrics(paths, expected_paths):
    expected = set(expected_paths)
    recall = len(set(paths) & expected) / len(expected) if expected else 0.0
    rank = next((i for i, path in enumerate(paths, 1) if path in expected), None)
    return recall, 1 / rank if rank else 0.0


def retrieval_report(documents, cases, top_k):
    """Use real embeddings + in-memory Qdrant. No production DBs or generation."""
    from embed.embedder import EMBEDDING_MODEL, embedding_client
    from qdrant_client import QdrantClient, models
    api = embedding_client(timeout=60, max_retries=1)
    client = QdrantClient(":memory:")
    try:
        chunks = [chunk for doc in documents for chunk in chunk_document(doc)]
        inputs = [f"파일명: {chunk['filename']}\n{chunk['chunk_text']}" for chunk in chunks]
        inputs += [case["query"] for case in cases]
        vectors = []
        input_tokens = 0
        for i in range(0, len(inputs), 100):
            response = api.embeddings.create(
                model=EMBEDDING_MODEL, input=inputs[i:i + 100],
            )
            input_tokens += response.usage.total_tokens
            vectors.extend(item.embedding for item in sorted(response.data, key=lambda item: item.index))
        client.create_collection(
            "evaluation", vectors_config=models.VectorParams(
                size=len(vectors[0]), distance=models.Distance.COSINE,
            ),
        )
        client.upsert("evaluation", points=[
            models.PointStruct(id=i, vector=vectors[i], payload=chunk)
            for i, chunk in enumerate(chunks)
        ])
        rows = []
        for case, vector in zip(cases, vectors[len(chunks):]):
            hits = client.query_points("evaluation", query=vector, limit=top_k * 3).points
            unique = {}
            for hit in hits:
                unique.setdefault(hit.payload["path"], hit)
            selected = list(unique.values())[:top_k]
            recall, reciprocal_rank = ranking_metrics(
                [hit.payload["path"] for hit in selected], [case["expected_path"]],
            )
            rows.append({
                "id": case["id"], "language": case["language"],
                "recall": recall, "reciprocal_rank": reciprocal_rank,
                "evidence_in_context": any(
                    case["evidence"] in note_context(hit.payload) for hit in selected
                ),
            })
        return {
            "scope": "Vector-only baseline with file dedup. No ES filename boost, tag filter, rewrite, cache or LLM generation.",
            "embedding_model": EMBEDDING_MODEL,
            "embedding_input_tokens": input_tokens,
            "top_k": top_k, "cases": len(rows),
            "recall_at_k": sum(row["recall"] for row in rows) / len(rows),
            "mrr_at_k": sum(row["reciprocal_rank"] for row in rows) / len(rows),
            "evidence_in_context": sum(row["evidence_in_context"] for row in rows),
            "details": rows,
        }
    finally:
        client.close()
        api.close()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--retrieval", action="store_true", help="Calls paid OpenAI embeddings on synthetic fixtures only")
    parser.add_argument("--top-k", type=int, default=5)
    parser.add_argument("--output", type=Path, help="Optional JSON result file")
    args = parser.parse_args()
    if not 1 <= args.top_k <= 50:
        parser.error("--top-k must be between 1 and 50")
    documents, cases = load_cases()
    report = {"fixture": "rag_cases_v1", "context": context_report(documents, cases)}
    if args.retrieval:
        from openai import APIError
        try:
            report["retrieval"] = retrieval_report(documents, cases, args.top_k)
        except (APIError, ValueError) as exc:
            parser.exit(1, f"Live retrieval evaluation failed ({type(exc).__name__}); check API access and configuration.\n")
    serialized = json.dumps(report, ensure_ascii=False, indent=2)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(serialized + "\n", encoding="utf-8")
    print(serialized)


if __name__ == "__main__":
    main()
