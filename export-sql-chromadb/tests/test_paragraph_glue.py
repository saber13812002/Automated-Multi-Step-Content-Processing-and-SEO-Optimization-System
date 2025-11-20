import importlib
import importlib.util
from pathlib import Path
from typing import Iterable, List

np = importlib.import_module("numpy")
pytest = importlib.import_module("pytest")


def _load_module(module_name: str, relative: str):
    base_dir = Path(__file__).resolve().parent.parent
    target = base_dir / relative
    spec = importlib.util.spec_from_file_location(module_name, target)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Cannot import {module_name} from {target}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)  # type: ignore[attr-defined]
    return module


dataset_stats = _load_module("dataset_stats", "dataset_stats.py")
EXPORTER = dataset_stats.EXPORTER


def glue_paragraphs(paragraphs: Iterable[str], min_lines: int = 3) -> List[str]:
    """
    Simple heuristic: keep appending short paragraphs until the bundle reaches
    min_lines, then flush. Mirrors the behaviour we plan to ship in the chunker.
    """
    bundles: List[str] = []
    buffer: List[str] = []
    line_budget = 0

    def flush() -> None:
        nonlocal buffer, line_budget
        if buffer:
            bundles.append("\n".join(buffer).strip())
        buffer = []
        line_budget = 0

    for paragraph in paragraphs:
        lines = max(1, len([ln for ln in paragraph.splitlines() if ln.strip()]))
        buffer.append(paragraph.strip())
        line_budget += lines
        if line_budget >= min_lines:
            flush()

    flush()
    return [b for b in bundles if b]


@pytest.mark.skipif(
    not getattr(EXPORTER, "TRANSFORMERS_AVAILABLE", False),
    reason="transformers/torch is required for the glue benchmark test.",
)
def test_glue_reduces_segments_and_improves_similarity() -> None:
    paragraphs = [
        "درس سوم\nشرط انسان زیستن!",
        "مقدمه کوتاه درباره ضرورت پی‌جویی دین.",
        "انسان کمال جو است و باید با عقل رفتار کند.",
        "پرسش: چرا باید دین را جست‌وجو کرد؟",
    ]

    glued = glue_paragraphs(paragraphs, min_lines=3)
    assert len(glued) < len(paragraphs)

    embedder = EXPORTER.HuggingFaceEmbedder(
        model_name="HooshvareLab/bert-base-parsbert-uncased",
        device="cpu",
    )

    query = "شرط انسان زیستن و کمال جویی چیست؟"
    query_vec = np.array(embedder([query]))[0]
    query_norm = np.linalg.norm(query_vec)
    if query_norm == 0:
        pytest.skip("Query embedding norm is zero; cannot evaluate cosine similarity.")

    def best_similarity(candidates: List[str]) -> float:
        vectors = np.array(embedder(candidates))
        candidate_norms = np.linalg.norm(vectors, axis=1)
        norms = np.clip(candidate_norms * query_norm, a_min=1e-9, a_max=None)
        sims = vectors @ query_vec / norms
        return float(np.max(sims))

    baseline_sim = best_similarity(paragraphs)
    glued_sim = best_similarity(glued)

    # Glue should maintain or improve similarity for cross-paragraph queries.
    assert glued_sim >= baseline_sim - 0.02

