from types import SimpleNamespace
from unittest.mock import Mock

from qdrant_client.models import ScoredPoint

from rag.context import MAX_NOTE_TOKENS, note_context
from rag.retrieval import filename_keywords, filename_match_score, path_match_score, fuse_document_ranks, group_evidence


def point(number, path, score, text):
    return ScoredPoint(id=number, version=1, score=score, payload={
        "path": path, "filename": path, "chunk_text": text,
        "parent_text": "Old introduction.", "tags": [],
    })


def test_secondary_evidence_survives_document_deduplication():
    chunks = [point(1, "guide.md", .8, "The exam lasts 80 minutes."),
              point(2, "guide.md", .79, "Renewal requires an online assessment.")]
    result = group_evidence(chunks, 1)
    assert len(result) == 1
    assert result[0].score == .8
    assert "Renewal requires" in note_context(result[0].payload)
    assert "retrieved_chunks" not in chunks[0].payload


def test_duplicate_chunks_and_document_limit():
    chunks = [point(i, "same.md", 1 - i * .01, f"fact {i}") for i in range(1, 8)]
    chunks.insert(1, point(50, "same.md", .98, "fact 1"))
    chunks.append(point(60, "other.md", .9, "Other fact"))
    result = group_evidence(chunks, 2)
    assert len(result) == 2
    assert len(result[0].payload["retrieved_chunks"]) == 4
    assert [e["text"] for e in result[0].payload["retrieved_chunks"]] == [f"fact {i}" for i in range(1, 5)]


def test_code_indentation_is_not_treated_as_duplicate_evidence():
    first = "if ready:\n    send()\nclose()"
    second = "if ready:\n    send()\n    close()"
    result = group_evidence([point(1, "guide.md", .8, first), point(2, "guide.md", .7, second)], 1)
    assert len(result[0].payload["retrieved_chunks"]) == 2
    context = note_context(result[0].payload)
    assert first in context and second in context


def test_filename_keywords_do_not_split_latin_words():
    keywords = filename_keywords("ExampleService AI-204 와인추천 中目黒")
    assert "exampleservice" in keywords and "ai-204" in keywords
    assert "am" not in keywords and "ice" not in keywords
    assert "와인" in keywords and "中目黒" in keywords


def test_title_matches_whole_latin_terms_and_cjk_substrings():
    assert filename_match_score("ram setup", "program.md") == 0
    assert filename_match_score("Kafka 설정", "JG_Configure_Kafka.md") == 5
    assert filename_match_score("와인 추천", "와인추천.md") == 4
    assert filename_match_score("AI-204 준비", "Azure AI-204.md") == 6


def test_generic_question_words_are_not_title_signals():
    query = "어떤 방식으로 사용자 정보를 알려줘"
    assert filename_match_score(query, "어떤 업무와 사용자 정보.md") == 0
    assert filename_match_score(query, "사용법.md") == 0


def test_explicit_folder_name_scopes_project_without_substring_matching():
    assert path_match_score("AtlasBoard cache policy", "Projects/AtlasBoard/cache.md") == 10
    assert path_match_score("AtlasBoard cache policy", "Resources/Interview/atlas.md") == 0
    assert path_match_score("board settings", "Projects/AtlasBoard/cache.md") == 0
    assert path_match_score("AtlasBoard cache policy", "Projects\\AtlasBoard\\cache.md") == 10


def test_rank_fusion_restores_title_signal_without_changing_vector_scores():
    chunks = [point(1, "a.md", .8, "a"), point(2, "b.md", .7, "b"), point(3, "title.md", .3, "c")]
    result = fuse_document_ranks(chunks, ["a.md", "b.md"], ["title.md"], 2)
    assert [r.payload["path"] for r in result] == ["a.md", "title.md"]
    assert [r.score for r in result] == [.8, .3]
    assert all("retrieval_score" in r.payload for r in result)


def test_exact_document_copies_do_not_get_extra_votes_or_slots():
    first, copy, other = point(1, "a.md", .8, "same"), point(2, "copy.md", .79, "same"), point(3, "b.md", .7, "different")
    first.payload["hash"] = copy.payload["hash"] = "same-full-document-hash"
    result = fuse_document_ranks([first, copy, other], ["a.md", "copy.md", "b.md"], [], 2)
    assert [r.payload["path"] for r in result] == ["a.md", "b.md"]
    assert result[0].payload["equivalent_paths"] == ["copy.md"]
    assert result[0].payload["retrieval_score"] == 1 / 61


def test_similar_versions_with_different_hashes_are_not_merged():
    old, new = point(1, "old.md", .8, "Limit 10"), point(2, "new.md", .79, "Limit 20")
    old.payload["hash"], new.payload["hash"] = "old", "new"
    assert len(fuse_document_ranks([old, new], ["old.md", "new.md"], [], 2)) == 2


def test_context_preserves_evidence_before_bounded_parent():
    import tiktoken
    payload = {"retrieved_chunks": [{"text": "First fact."}, {"text": "Second fact."}],
               "parent_text": "First fact. " + "background " * 10000}
    context = note_context(payload)
    assert context.startswith("First fact.\n\nSecond fact.")
    assert context.count("First fact.") == 1
    assert len(tiktoken.encoding_for_model("gpt-4o-mini").encode(context)) <= MAX_NOTE_TOKENS


def test_filename_candidate_cannot_displace_more_relevant_document(services, monkeypatch):
    from rag import generator
    from search import document_index
    relevant = point(1, "auth.md", .8, "Passwords use a one-way hash.")
    unrelated = point(2, "ExampleService_plan.md", .2, "A future plan.")
    search = Mock(side_effect=[SimpleNamespace(points=[relevant]), SimpleNamespace(points=[unrelated])])
    monkeypatch.setattr(services.store, "client", SimpleNamespace(query_points=search))
    monkeypatch.setattr(generator, "embed_texts", lambda texts: [[1, 0, 0]])
    monkeypatch.setattr(document_index, "es", SimpleNamespace(search=Mock(return_value={
        "hits": {"hits": [{"_source": {"path": "ExampleService_plan.md", "filename": "ExampleService_plan.md"}}]}
    })))
    results = generator.search_relevant_notes("ExampleService password storage", limit=1)
    assert results[0].payload["path"] == "auth.md"
    assert results[0].score == .8
    assert unrelated.score == .2
