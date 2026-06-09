from __future__ import annotations

import re
import string
from pathlib import Path
from typing import Dict, List, Set, Tuple, Union


class AIBenchmark:
    """Benchmark and evaluate AI transcription outputs."""

    @staticmethod
    def _normalize_text(text: str) -> str:
        """Clean text by removing punctuation and normalizing whitespace."""
        lowered = text.lower()
        translator = str.maketrans("", "", string.punctuation + "،؛؟!«»")
        cleaned = lowered.translate(translator)
        return re.sub(r"\s+", " ", cleaned).strip()

    @staticmethod
    def _tokenize(text: str) -> List[str]:
        normalized = AIBenchmark._normalize_text(text)
        if not normalized:
            return []
        return normalized.split()

    @staticmethod
    def calculate_wer(reference: str, hypothesis: str) -> float:
        """Calculate Word Error Rate between reference and hypothesis."""
        ref_words = AIBenchmark._tokenize(reference)
        hyp_words = AIBenchmark._tokenize(hypothesis)

        if not ref_words:
            return 1.0 if hyp_words else 0.0

        rows = len(ref_words) + 1
        cols = len(hyp_words) + 1
        dp = [[0] * cols for _ in range(rows)]

        for i in range(1, rows):
            dp[i][0] = i
        for j in range(1, cols):
            dp[0][j] = j

        for i in range(1, rows):
            for j in range(1, cols):
                cost = 0 if ref_words[i - 1] == hyp_words[j - 1] else 1
                dp[i][j] = min(
                    dp[i - 1][j] + 1,
                    dp[i][j - 1] + 1,
                    dp[i - 1][j - 1] + cost,
                )

        return dp[rows - 1][cols - 1] / len(ref_words)

    @staticmethod
    def _word_ngrams(words: List[str], n: int) -> Set[Tuple[str, ...]]:
        if len(words) < n:
            return set()
        return {tuple(words[i : i + n]) for i in range(len(words) - n + 1)}

    @staticmethod
    def calculate_ngram_similarity(reference: str, hypothesis: str, n: int = 2) -> float:
        """Calculate Jaccard similarity of word-level n-grams."""
        ref_ngrams = AIBenchmark._word_ngrams(AIBenchmark._tokenize(reference), n)
        hyp_ngrams = AIBenchmark._word_ngrams(AIBenchmark._tokenize(hypothesis), n)

        if not ref_ngrams and not hyp_ngrams:
            return 1.0
        if not ref_ngrams or not hyp_ngrams:
            return 0.0

        intersection = len(ref_ngrams & hyp_ngrams)
        union = len(ref_ngrams | hyp_ngrams)
        return intersection / union

    @staticmethod
    def calculate_lcs_similarity(reference: str, hypothesis: str) -> float:
        """Calculate normalized longest common subsequence similarity."""
        ref_words = AIBenchmark._tokenize(reference)
        hyp_words = AIBenchmark._tokenize(hypothesis)

        if not ref_words and not hyp_words:
            return 1.0
        if not ref_words or not hyp_words:
            return 0.0

        rows = len(ref_words) + 1
        cols = len(hyp_words) + 1
        dp = [[0] * cols for _ in range(rows)]

        for i in range(1, rows):
            for j in range(1, cols):
                if ref_words[i - 1] == hyp_words[j - 1]:
                    dp[i][j] = dp[i - 1][j - 1] + 1
                else:
                    dp[i][j] = max(dp[i - 1][j], dp[i][j - 1])

        lcs_len = dp[rows - 1][cols - 1]
        return min(1.0, (2 * lcs_len) / (len(ref_words) + len(hyp_words)))

    def evaluate(
        self,
        ref_path: Union[Path, str],
        hyp_path: Union[Path, str],
    ) -> Dict[str, Union[float, str]]:
        """Read two text files and return all benchmark metrics."""
        reference = Path(ref_path).read_text(encoding="utf-8")
        hypothesis = Path(hyp_path).read_text(encoding="utf-8")

        reference_normalized = self._normalize_text(reference)
        hypothesis_normalized = self._normalize_text(hypothesis)

        return {
            "wer": self.calculate_wer(reference_normalized, hypothesis_normalized),
            "ngram_bigram": self.calculate_ngram_similarity(
                reference_normalized, hypothesis_normalized, n=2
            ),
            "ngram_trigram": self.calculate_ngram_similarity(
                reference_normalized, hypothesis_normalized, n=3
            ),
            "lcs_score": self.calculate_lcs_similarity(
                reference_normalized, hypothesis_normalized
            ),
            "reference_normalized": reference_normalized,
            "hypothesis_normalized": hypothesis_normalized,
        }
