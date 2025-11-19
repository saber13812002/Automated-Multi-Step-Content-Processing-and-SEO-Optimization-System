import argparse
import csv
import json
import sqlite3
from pathlib import Path
from typing import Any, Dict, List, Optional


def fetch_segments(
    conn: sqlite3.Connection,
    source_filter: Optional[str],
    lang_filter: Optional[str],
) -> List[Dict[str, Any]]:
    q = """
        SELECT
            ls.id,
            af.source_path AS source_audio,
            ls.segment_audio,
            ls.language,
            ls.start_time,
            ls.end_time,
            ls.text,
            ls.report_path
        FROM language_segments ls
        JOIN audio_files af ON ls.audio_file_id = af.id
    """
    conds: List[str] = []
    params: List[Any] = []
    if source_filter:
        conds.append("af.source_path LIKE ?")
        params.append(source_filter)
    if lang_filter:
        conds.append("ls.language = ?")
        params.append(lang_filter)
    if conds:
        q += " WHERE " + " AND ".join(conds)
    q += " ORDER BY ls.start_time ASC, ls.id ASC"
    cur = conn.cursor()
    cur.execute(q, params)
    rows = cur.fetchall()
    cols = [d[0] for d in cur.description]
    return [dict(zip(cols, r)) for r in rows]


def write_jsonl(rows: List[Dict[str, Any]], out_path: Path) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")


def write_csv(rows: List[Dict[str, Any]], out_path: Path) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        with out_path.open("w", encoding="utf-8", newline="") as f:
            pass
        return
    with out_path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Export per-segment subtitle jobs from SQLite segments table"
    )
    parser.add_argument("--db-path", type=str, required=True, help="Path to segments.db")
    parser.add_argument(
        "--source-like",
        type=str,
        default=None,
        help="Filter source_audio by LIKE pattern, e.g. %example%.",
    )
    parser.add_argument(
        "--lang",
        type=str,
        default=None,
        help="Filter by language code (e.g., fa or ar)",
    )
    parser.add_argument(
        "--out-jsonl",
        type=str,
        default=None,
        help="Path to write JSONL jobs (one job per line)",
    )
    parser.add_argument(
        "--out-csv",
        type=str,
        default=None,
        help="Path to write CSV jobs",
    )

    args = parser.parse_args()

    conn = sqlite3.connect(args.db_path)
    rows = fetch_segments(conn, args.source_like, args.lang)
    print(f"Exporting {len(rows)} jobs")

    if args.out_jsonl:
        write_jsonl(rows, Path(args.out_jsonl))
        print(f"  Wrote JSONL: {args.out_jsonl}")
    if args.out_csv:
        write_csv(rows, Path(args.out_csv))
        print(f"  Wrote CSV: {args.out_csv}")

    if not args.out_jsonl and not args.out_csv:
        # print to stdout as JSONL
        for r in rows:
            print(json.dumps(r, ensure_ascii=False))


if __name__ == "__main__":
    main()


