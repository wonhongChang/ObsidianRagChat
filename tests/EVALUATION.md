# RAG Verification

This project separates implementation regression tests, context retention, and retrieval ranking. None of these alone measures generated-answer accuracy.

## Regression Suite

From a local Python 3.11 virtual environment at the repository root (or a dedicated CI test environment), not from the runtime web image:

```bash
python -m pip install -r requirements-dev.txt
python -m pytest tests -q
```

Private-vault scenarios are kept outside this public test directory. The suite uses synthetic documents, mocked external APIs, and in-memory Qdrant; no production index or paid API is used. The first `tiktoken` run may download tokenizer data. Qdrant local mode may warn that payload indexes have no effect.

The suite covers all four answer paths (standalone/follow-up, streaming/non-streaming), evidence retention, token windows, partial uploads, failed ES writes and deletions, unreadable source files, cache outages, and language/history cache isolation. The server uses one model, `gpt-6-luna`. Tests using mocked Responses events verify application behavior, not live model availability or answer accuracy.

## Reproducible Fixture

[`fixtures/rag_cases.json`](fixtures/rag_cases.json) defines 10 synthetic English notes and 30 questions: 10 Korean, 10 English, and 10 Japanese. Each question has one expected document and an exact supporting sentence. The script places sentences at the beginning, middle, and end of padded documents to reproduce the old 4,000-character context-prefix defect.

### Context Retention (No API Key)

```bash
python -m scripts.evaluate_rag
```

The evaluator supplies a known relevant chunk and checks whether its supporting sentence survives context assembly. The baseline reconstructs the previous `parent_text = document[:4000]` behavior; it is not a run of the entire old application.

| Context construction | Evidence retained |
|---|---:|
| Previous document-prefix baseline | 10 / 30 |
| Matched chunk first + neighboring chunks | 30 / 30 |
| New assembly with legacy prefix payloads | 30 / 30 |

These deliberately constructed cases demonstrate the regression fix, not a general 3x improvement in answer quality. Legacy points work without a forced re-embedding; neighboring context is populated as documents are indexed again.

### Isolated Vector Retrieval (Optional Paid API)

Skip this step for a free, offline regression run or a lexical-only deployment. To opt into the paid vector benchmark, set an authorized `OPENAI_EMBEDDING_API_KEY` in the environment or local `.env`. A dedicated key is recommended; to explicitly reuse a chat key that permits embeddings, use the unquoted line `OPENAI_EMBEDDING_API_KEY=${OPENAI_API_KEY}` below `OPENAI_API_KEY`. Then run locally:

```bash
python -m scripts.evaluate_rag --retrieval --top-k 5
```

Only synthetic fixture chunks and questions are sent to the [OpenAI embeddings API](https://developers.openai.com/api/docs/guides/embeddings). Retrieval uses an ephemeral in-memory Qdrant collection, never the configured production database. No LLM answers are generated. Use `--output path/to/result.json` to retain per-case results.

| Metric | Historical fixture result |
|---|---:|
| Embedding model | text-embedding-3-small |
| Questions | 30 |
| Recall@5 (expected file present) | 1.000 |
| MRR@5 (reciprocal rank of expected file) | 0.907 |
| Supporting sentence in assembled context | 30 / 30 |
| Embedding input tokens | 17,170 |

The evaluator retrieves `3 * k` chunks, keeps the highest-scoring hit per file, and takes up to `k` files. These scores were recorded in a previous vector-only run. They do not evaluate Elasticsearch-only retrieval, the deployed hybrid pipeline, or answers from `gpt-6-luna`. The README screenshots are demo fixtures, not evaluation transcripts.

## Limits and Next Checks

- This is a small, answerable-only synthetic set, not a held-out real-world benchmark. Repetitive padding and a ten-document corpus make retrieval relatively easy.
- The optional ranking test is a **vector-only baseline**. It does not run the application's filename/vector rank fusion, tag filtering, question classification, query rewriting, cache, or answer generation.

Additional offline regressions in `test_retrieval.py` verify title matching, reciprocal rank fusion without rewriting vector scores, exact-copy deduplication, version separation, and multiple evidence chunks under a token budget. `test_answer_policy.py` checks language selection and preservation of a follow-up's user topic. Run the full suite with `python -m pytest tests -q`. These tests do not establish live answer accuracy; that requires source-grounded review of generated answers.
- It does not measure citation correctness, hallucinations, abstention, legal-domain quality, real multilingual corpus quality, latency, or concurrent-user capacity.
- Next: collect representative queries and failures, add unanswerable/hard-negative cases, check generated answers against evidence, and compare BM25 fusion or reranking on that same set.

## Operational Boundaries

With no embedding key, sync and search use Elasticsearch without calling embeddings or Qdrant. A live, uncached answer can still incur generation charges. The application reads `OPENAI_API_KEY` for answers and follow-up rewriting; there is no automatic fallback to it for embeddings. With an authorized embedding key and Qdrant configured, sync reuses compatible `text-embedding-3-small` 1536-dimensional vectors and reconciles changes incrementally; changing the answer model does not require clearing an index.

New vectors are uploaded before stale vectors are deleted. Qdrant and ES are reconciled independently on the next sync, including incomplete chunk generations. This is retryable reconciliation, **not an atomic transaction**: mixed generations can be visible briefly, and multiple simultaneous sync workers are not supported.

Redis failures no longer discard an answer. Invalidation is best effort and scoped to `rag:*`; if invalidation fails, stale answers may survive until their TTL. A versioned index/cache protocol would be needed for stricter consistency. Authentication, document-level access control, and load testing remain prerequisites for a public multi-user deployment.
