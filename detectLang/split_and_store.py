import argparse
import json
import sqlite3
import subprocess
from pathlib import Path
from typing import Dict, List, Optional

try:
    from .db import ensure_connection, get_or_create_audio_file
except ImportError:  # pragma: no cover - direct execution fallback
    from db import ensure_connection, get_or_create_audio_file  # type: ignore


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


def insert_language_segment(
    conn: sqlite3.Connection,
    audio_file_id: int,
    legacy_segment_id: Optional[int],
    language: str,
    start_time: float,
    end_time: float,
    text: str,
    report_path: Path,
    segment_audio: Path,
) -> None:
    conn.execute(
        """
        INSERT INTO language_segments (
            audio_file_id,
            legacy_segment_id,
            language,
            start_time,
            end_time,
            text,
            report_path,
            segment_audio
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            audio_file_id,
            legacy_segment_id,
            language,
            start_time,
            end_time,
            text,
            str(report_path),
            str(segment_audio),
        ),
    )
    conn.commit()


def process_report(
    conn: sqlite3.Connection,
    report_path: Path,
    out_audio_dir: Path,
) -> int:
    data = load_interval_json(report_path)
    source_audio = Path(data["audio"]).resolve()
    intervals = data.get("intervals", [])
    if not intervals:
        return 0

    duration = float(intervals[-1]["end_time"])
    audio_file_id = get_or_create_audio_file(conn, str(source_audio), duration)

    inserted_count = 0
    for idx, it in enumerate(intervals, start=1):
        start_s = float(it["start_time"])
        end_s = float(it["end_time"])
        lang = (it.get("language") or "und").strip() or "und"
        text = str(it.get("text", "")).strip()

        seg_name = f"{source_audio.stem}_seg{idx:04d}_{lang}.m4a"
        seg_path = out_audio_dir / seg_name
        ffmpeg_trim(source_audio, start_s, end_s, seg_path)

        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO segments (
                source_audio,
                segment_audio,
                language,
                start_time,
                end_time,
                text
            ) VALUES (?, ?, ?, ?, ?, ?)
            """,
            (str(source_audio), str(seg_path), lang, start_s, end_s, text),
        )
        legacy_id = cur.lastrowid
        conn.commit()

        insert_language_segment(
            conn=conn,
            audio_file_id=audio_file_id,
            legacy_segment_id=legacy_id,
            language=lang,
            start_time=start_s,
            end_time=end_s,
            text=text,
            report_path=report_path,
            segment_audio=seg_path,
        )
        inserted_count += 1

    return inserted_count


def gather_reports(report_file: Optional[str], reports_dir: Optional[str]) -> List[Path]:
    paths: List[Path] = []
    seen = set()

    def add_path(p: Path) -> None:
        resolved = str(p.resolve())
        if resolved not in seen:
            seen.add(resolved)
            paths.append(p)

    if report_file:
        path_obj = Path(report_file)
        if path_obj.is_file():
            add_path(path_obj)
        else:
            print(f"Report file not found: {report_file}")
    if reports_dir:
        for p in sorted(Path(reports_dir).glob("*.language_intervals.json")):
            add_path(p)
    return paths


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Split audio by language interval JSONs and store metadata in SQLite."
    )
    parser.add_argument(
        "--report-file",
        type=str,
        help="Single JSON report file to process.",
    )
    parser.add_argument(
        "--reports-dir",
        type=str,
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

    if not args.report_file and not args.reports_dir:
        parser.error("Provide --report-file for single run, --reports-dir for batch, or both.")

    out_audio_dir = Path(args.output_audio_dir)
    db_path = Path(args.db_path)

    conn = ensure_connection(db_path)

    report_paths = gather_reports(args.report_file, args.reports_dir)
    if not report_paths:
        print("No report files found.")
        return

    for rp in report_paths:
        print(f"Processing report: {rp}")
        try:
            count = process_report(conn, rp, out_audio_dir)
            print(f"  Inserted {count} segments")
        except Exception as e:
            print(f"  Failed: {e}")


if __name__ == "__main__":
    main()


