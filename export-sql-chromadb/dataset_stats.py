"""
Utility script to inspect SQL dumps (book_pages) and estimate embedding cost.

The collector uses the existing parsing/segmenting logic from
`export-sql-backup-to-chromadb.py`. Because that module's filename contains a
hyphen, we dynamically load it via importlib to avoid code duplication.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import statistics
import sys
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List, Optional, Tuple

import re


EXPORTER_MODULE_NAME = "chromadb_sql_exporter"
EXPORTER_FILENAME = "export-sql-backup-to-chromadb.py"


@dataclass
class ParagraphStats:
    raw_total: int = 0
    raw_line_counts: List[int] = None  # type: ignore
    raw_char_counts: List[int] = None  # type: ignore
    merged_total: int = 0
    merged_line_counts: List[int] = None  # type: ignore
    merged_char_counts: List[int] = None  # type: ignore

    def __post_init__(self) -> None:
        if self.raw_line_counts is None:
            self.raw_line_counts = []
        if self.raw_char_counts is None:
            self.raw_char_counts = []
        if self.merged_line_counts is None:
            self.merged_line_counts = []
        if self.merged_char_counts is None:
            self.merged_char_counts = []


@dataclass
class SegmentStats:
    total: int = 0
    char_counts: List[int] = None  # type: ignore
    page_level_segments: int = 0

    def __post_init__(self) -> None:
        if self.char_counts is None:
            self.char_counts = []


@dataclass
class DatasetStats:
    sql_path: str
    total_records: int
    total_books: int
    total_pages: int
    paragraph_stats: ParagraphStats
    segment_stats: SegmentStats
    short_paragraphs: int
    title_like_paragraphs: int
    merged_from_short: int
    segments_per_second: float
    estimated_seconds: Optional[float]


def load_exporter_module():
    """Dynamically import export-sql-backup-to-chromadb."""
    current_dir = Path(__file__).resolve().parent
    target = current_dir / EXPORTER_FILENAME
    spec = importlib.util.spec_from_file_location(EXPORTER_MODULE_NAME, target)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Cannot load exporter module from {target}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)  # type: ignore[attr-defined]
    return module


EXPORTER = load_exporter_module()


def iter_paragraphs_with_lines(text: str) -> Iterable[Tuple[str, int]]:
    """
    Yield cleaned paragraph text together with its line count.

    Paragraph boundaries follow `normalize_paragraphs` from the exporter
    (split on blank lines). Line counts are computed BEFORE collapsing whitespace
    and ignore blank lines so 1–10 line assumptions remain meaningful.
    """
    if not text:
        return []
    raw_paragraphs = re.split(r"\n\s*\n+", text)
    for raw in raw_paragraphs:
        cleaned = re.sub(r"\s+", " ", raw).strip()
        if not cleaned:
            continue
        non_empty_lines = [ln for ln in raw.split("\n") if ln.strip()]
        line_count = len(non_empty_lines) if non_empty_lines else 1
        yield cleaned, line_count


def compute_basic_stats(data: List[int]) -> dict:
    if not data:
        return {
            "min": 0,
            "max": 0,
            "avg": 0.0,
            "median": 0.0,
        }
    return {
        "min": min(data),
        "max": max(data),
        "avg": statistics.fmean(data),
        "median": statistics.median(data),
    }


def summarize_counts(line_counts: List[int]) -> dict:
    buckets = Counter()
    for value in line_counts:
        bucket = value if value <= 10 else ">10"
        buckets[bucket] += 1
    return {str(k): v for k, v in sorted(buckets.items(), key=lambda item: str(item[0]))}


def analyze_sql_dump(
    sql_path: Path,
    *,
    max_length: int,
    context_length: int,
    min_paragraph_lines: int,
    title_weight: float,
    include_page_level_docs: bool,
    segments_per_second: float,
    record_limit: Optional[int] = None,
) -> DatasetStats:
    paragraph_stats = ParagraphStats()
    segment_stats = SegmentStats()
    total_records = 0
    unique_books = set()
    unique_pages = set()
    short_paragraphs = 0
    title_like_paragraphs = 0
    merged_from_short = 0

    for record in EXPORTER.iter_book_pages(sql_path):
        total_records += 1
        if record_limit and total_records > record_limit:
            break

        unique_books.add(record.book_id)
        unique_pages.add((record.book_id, record.page_id))

        text = EXPORTER.html_to_text(record.page_text_html)
        for cleaned, line_count in iter_paragraphs_with_lines(text):
            paragraph_stats.raw_total += 1
            paragraph_stats.raw_line_counts.append(line_count)
            paragraph_stats.raw_char_counts.append(len(cleaned))
            if line_count < 3:
                short_paragraphs += 1
            if EXPORTER.looks_like_title(cleaned):
                title_like_paragraphs += 1

        merged_payloads = EXPORTER.prepare_paragraphs(text, min_paragraph_lines)
        paragraph_stats.merged_total += len(merged_payloads)
        paragraph_stats.merged_line_counts.extend(p.line_count for p in merged_payloads)
        paragraph_stats.merged_char_counts.extend(len(p.text) for p in merged_payloads)
        merged_from_short += sum(max(0, len(p.source_indices) - 1) for p in merged_payloads)

        segments = EXPORTER.build_segments(
            record,
            max_length=max_length,
            context_length=context_length,
            min_paragraph_lines=min_paragraph_lines,
            title_weight=title_weight,
            include_page_level=include_page_level_docs,
        )
        segment_stats.total += len(segments)
        segment_stats.char_counts.extend(len(segment.text) for segment in segments)
        segment_stats.page_level_segments += sum(
            1 for segment in segments if segment.metadata.get("page_level")
        )

    estimated_seconds = (
        segment_stats.total / segments_per_second if segments_per_second > 0 else None
    )

    return DatasetStats(
        sql_path=str(sql_path),
        total_records=total_records,
        total_books=len(unique_books),
        total_pages=len(unique_pages),
        paragraph_stats=paragraph_stats,
        segment_stats=segment_stats,
        short_paragraphs=short_paragraphs,
        title_like_paragraphs=title_like_paragraphs,
        merged_from_short=merged_from_short,
        segments_per_second=segments_per_second,
        estimated_seconds=estimated_seconds,
    )


def render_report(stats: DatasetStats) -> dict:
    raw_line_stats = compute_basic_stats(stats.paragraph_stats.raw_line_counts)
    raw_char_stats = compute_basic_stats(stats.paragraph_stats.raw_char_counts)
    merged_line_stats = compute_basic_stats(stats.paragraph_stats.merged_line_counts)
    merged_char_stats = compute_basic_stats(stats.paragraph_stats.merged_char_counts)
    segment_summary = compute_basic_stats(stats.segment_stats.char_counts)
    line_histogram = summarize_counts(stats.paragraph_stats.raw_line_counts)

    report = {
        "sql_path": stats.sql_path,
        "records": stats.total_records,
        "books": stats.total_books,
        "pages": stats.total_pages,
        "paragraphs": {
            "raw": {
                "count": stats.paragraph_stats.raw_total,
                "lines": raw_line_stats,
                "line_histogram": line_histogram,
                "chars": raw_char_stats,
            },
            "merged": {
                "count": stats.paragraph_stats.merged_total,
                "lines": merged_line_stats,
                "chars": merged_char_stats,
            },
            "shorter_than_three_lines": stats.short_paragraphs,
            "title_like": stats.title_like_paragraphs,
            "merged_from_short": stats.merged_from_short,
        },
        "segments": {
            "count": stats.segment_stats.total,
            "chars": segment_summary,
            "page_level": stats.segment_stats.page_level_segments,
        },
        "segments_per_second": stats.segments_per_second,
        "estimated_seconds": stats.estimated_seconds,
    }
    return report


def print_human_report(report: dict) -> None:
    paras = report["paragraphs"]
    segs = report["segments"]
    print(f"📄 فایل: {report['sql_path']}")
    print(
        f"   • رکوردها: {report['records']:,} | کتاب‌ها: {report['books']:,} | صفحات: {report['pages']:,}"
    )
    print(
        f"   • پاراگراف‌های خام: {paras['raw']['count']:,} (میانگین خطوط: {paras['raw']['lines']['avg']:.2f}, "
        f"کمینه: {paras['raw']['lines']['min']}, بیشینه: {paras['raw']['lines']['max']})"
    )
    print(
        f"   • پاراگراف‌های بعد از ادغام: {paras['merged']['count']:,} (میانگین خطوط: {paras['merged']['lines']['avg']:.2f})"
    )
    print(
        f"   • پاراگراف کوتاه (<3 خط): {paras['shorter_than_three_lines']:,} | تیتر گونه: {paras['title_like']:,} | ادغام از کوتاه: {paras['merged_from_short']:,}"
    )
    print(
        f"   • قطعات: {segs['count']:,} (میانگین حروف: {segs['chars']['avg']:.1f}, "
        f"کمینه: {segs['chars']['min']}, بیشینه: {segs['chars']['max']})"
    )
    if segs["page_level"]:
        print(f"   • اسناد صفحه کامل: {segs['page_level']:,}")
    if report["estimated_seconds"] is not None:
        minutes = report["estimated_seconds"] / 60.0
        print(
            f"   • زمان تقریبی (بر اساس {report['segments_per_second']} seg/s): "
            f"{minutes:.1f} دقیقه"
        )
    print("   • هیستوگرام خطوط (۱ تا ۱۰+):")
    for bucket, count in report["paragraphs"]["raw"]["line_histogram"].items():
        print(f"      - {bucket}: {count:,}")


def parse_args(argv: Optional[Iterable[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Analyze book_pages SQL dump and estimate embedding workload.",
    )
    parser.add_argument(
        "--sql-path",
        default="books_pages_mini.sql",
        help="مسیر فایل SQL.",
    )
    parser.add_argument(
        "--max-length",
        type=int,
        default=200,
        help="حداکثر طول کاراکتر هر سگمنت (همان پارامتر exporter).",
    )
    parser.add_argument(
        "--context",
        type=int,
        default=100,
        help="طول همپوشانی کاراکتر بین سگمنت‌ها.",
    )
    parser.add_argument(
        "--min-paragraph-lines",
        type=int,
        default=3,
        help="حداقل خطوط برای ادغام پاراگراف‌های کوتاه.",
    )
    parser.add_argument(
        "--title-weight",
        type=float,
        default=1.5,
        help="وزن تیترها (برای هماهنگی با exporter).",
    )
    parser.add_argument(
        "--disable-page-level-docs",
        action="store_true",
        help="اگر تنظیم شود سند کامل صفحه در آمار لحاظ نمی‌شود.",
    )
    parser.add_argument(
        "--segments-per-second",
        type=float,
        default=48.0,
        help="نرخ واقعی پردازش جهت تخمین زمان.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="در صورت نیاز فقط n رکورد اول پردازش شود (برای تست).",
    )
    parser.add_argument(
        "--json-out",
        type=Path,
        help="اگر مشخص شود گزارش به صورت JSON در این مسیر ذخیره می‌شود.",
    )
    return parser.parse_args(argv)


def main(argv: Optional[Iterable[str]] = None) -> None:
    args = parse_args(argv)
    sql_path = Path(args.sql_path).expanduser().resolve()
    if not sql_path.exists():
        print(f"❌ فایل SQL پیدا نشد: {sql_path}", file=sys.stderr)
        sys.exit(1)

    stats = analyze_sql_dump(
        sql_path,
        max_length=args.max_length,
        context_length=args.context,
        min_paragraph_lines=args.min_paragraph_lines,
        title_weight=args.title_weight,
        include_page_level_docs=not args.disable_page_level_docs,
        segments_per_second=args.segments_per_second,
        record_limit=args.limit,
    )
    report = render_report(stats)
    print_human_report(report)

    if args.json_out:
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        args.json_out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"   • گزارش JSON ذخیره شد: {args.json_out}")


if __name__ == "__main__":
    main()

