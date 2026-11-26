from scripts.evaluate_rag import load_cases, context_report, ranking_metrics


def test_fixture_retains_all_30_known_evidence_spans():
    documents, cases = load_cases()
    report = context_report(documents, cases)
    assert len(documents) == 10
    assert report["cases"] == 30
    assert report["baseline_retained"] == 10
    assert report["current_retained"] == 30
    assert report["legacy_payload_retained"] == 30
    assert {language: sum(c["language"] == language for c in cases)
            for language in ("ko", "en", "ja")} == {"ko": 10, "en": 10, "ja": 10}


def test_retrieval_metrics_count_relevance_and_rank():
    assert ranking_metrics(["a", "b", "c"], ["b", "d"]) == (0.5, 0.5)
    assert ranking_metrics(["a", "a"], ["a"]) == (1.0, 1.0)
    assert ranking_metrics([], ["a"]) == (0.0, 0.0)
