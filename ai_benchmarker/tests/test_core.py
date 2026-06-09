from pathlib import Path

from ai_benchmarker.core import AIBenchmark


def test_normalize_text_removes_punctuation_and_extra_spaces():
    result = AIBenchmark._normalize_text("  Hello,   World!  ")
    assert result == "hello world"


def test_calculate_wer_known_case():
    wer = AIBenchmark.calculate_wer("hello world", "hello word")
    assert wer == 0.5


def test_calculate_wer_empty_reference():
    assert AIBenchmark.calculate_wer("", "hello") == 1.0
    assert AIBenchmark.calculate_wer("", "") == 0.0


def test_calculate_ngram_similarity_bigram():
    score = AIBenchmark.calculate_ngram_similarity("one two three", "one two four", n=2)
    assert 0.0 < score < 1.0


def test_calculate_ngram_similarity_identical():
    text = "alpha beta gamma"
    assert AIBenchmark.calculate_ngram_similarity(text, text, n=2) == 1.0


def test_calculate_lcs_similarity_identical():
    text = "alpha beta gamma"
    assert AIBenchmark.calculate_lcs_similarity(text, text) == 1.0


def test_calculate_lcs_similarity_disjoint():
    assert AIBenchmark.calculate_lcs_similarity("one two", "three four") == 0.0


def test_evaluate_reads_files(tmp_path: Path):
    ref_file = tmp_path / "ref.txt"
    hyp_file = tmp_path / "hyp.txt"
    ref_file.write_text("hello world", encoding="utf-8")
    hyp_file.write_text("hello word", encoding="utf-8")

    result = AIBenchmark().evaluate(ref_file, hyp_file)

    assert result["wer"] == 0.5
    assert "ngram_bigram" in result
    assert "ngram_trigram" in result
    assert "lcs_score" in result
    assert result["reference_normalized"] == "hello world"
    assert result["hypothesis_normalized"] == "hello word"
