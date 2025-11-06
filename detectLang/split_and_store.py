import argparse
import json
import sqlite3
import subprocess
from pathlib import Path
from typing import Dict, List


SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS segments (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  source_audio TEXT NOT NULL,
  segment_audio TEXT NOT NULL,
  language TEXT NOT NULL,
  start_time REAL NOT NULL,
  end_time REAL NOT NULL,
  text TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_segments_source ON segments(source_audio);
CREATE INDEX IF NOT EXISTS idx_segments_start ON segments(start_time);
"""


def ensure_db(db_path: Path) -> sqlite3.Connection:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db_path))
    conn.executescript(SCHEMA_SQL)
    return conn


def load_interval_json(json_path: Path) -> Dict:
    with json_path.open("r", encoding="utf-8") as f:
        return json.load(f)


def ffmpeg_trim(input_audio: Path, start: float, end: float, out_path: Path) -> None:
    duration = max(0.0, end - start)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        "ffmpeg",
        "-y",
        "-hide_banner",
        "-loglevel",
        "error",
        "-ss",
        str(start),
        "-i",
        str(input_audio),
        "-t",
        str(duration),
        "-c",
        "copy",
        str(out_path),
    ]
    subprocess.run(cmd, check=True)


def process_report(
    conn: sqlite3.Connection,
    report_path: Path,
    out_audio_dir: Path,
) -> List[int]:
    data = load_interval_json(report_path)
    source_audio = Path(data["audio"]).resolve()
    intervals = data.get("intervals", [])

    inserted_ids: List[int] = []
    for idx, it in enumerate(intervals, start=1):
        start_s = float(it["start_time"])  # absolute seconds
        end_s = float(it["end_time"])      # absolute seconds
        lang = str(it["language"]) or "und"
        text = str(it.get("text", "")).strip()

        seg_name = f"{source_audio.stem}_seg{idx:04d}_{lang}.m4a"
        seg_path = out_audio_dir / seg_name

        ffmpeg_trim(source_audio, start_s, end_s, seg_path)

        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO segments (source_audio, segment_audio, language, start_time, end_time, text)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (str(source_audio), str(seg_path), lang, start_s, end_s, text),
        )
        inserted_ids.append(cur.lastrowid)
        conn.commit()

    return inserted_ids


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Split audio by language interval JSONs and store metadata in SQLite."
    )
    parser.add_argument(
        "--reports-dir",
        type=str,
        required=True,
        help="Directory containing *.language_intervals.json files",
    )
    parser.add_argument(
        "--output-audio-dir",
        type=str,
        required=True,
        help="Directory to write trimmed segment audio files",
    )
    parser.add_argument(
        "--db-path",
        type=str,
        default=str(Path(__file__).with_name("segments.db")),
        help="Path to SQLite database (will be created if missing)",
    )

    args = parser.parse_args()

    reports_dir = Path(args.reports_dir)
    out_audio_dir = Path(args.output_audio_dir)
    db_path = Path(args.db_path)

    conn = ensure_db(db_path)

    json_reports = sorted(reports_dir.glob("*.language_intervals.json"))
    if not json_reports:
        print("No *.language_intervals.json found.")
        return

    for rp in json_reports:
        print(f"Processing report: {rp}")
        try:
            ids = process_report(conn, rp, out_audio_dir)
            print(f"  Inserted {len(ids)} segments")
        except Exception as e:
            print(f"  Failed: {e}")


if __name__ == "__main__":
    main()


