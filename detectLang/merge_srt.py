import argparse
import re
import sqlite3
from datetime import timedelta
from pathlib import Path
from typing import List, Tuple


TIMECODE_RE = re.compile(r"^(\d\d:\d\d:\d\d,\d\d\d)\s+-->\s+(\d\d:\d\d:\d\d,\d\d\d)")


def parse_timecode(tc: str) -> timedelta:
    h, m, rest = tc.split(":")
    s, ms = rest.split(",")
    return timedelta(hours=int(h), minutes=int(m), seconds=int(s), milliseconds=int(ms))


def fmt_timecode(td: timedelta) -> str:
    total_ms = int(td.total_seconds() * 1000)
    if total_ms < 0:
        total_ms = 0
    h = total_ms // 3_600_000
    total_ms %= 3_600_000
    m = total_ms // 60_000
    total_ms %= 60_000
    s = total_ms // 1000
    ms = total_ms % 1000
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def read_srt_adjusted(srt_path: Path, offset: timedelta) -> List[Tuple[timedelta, timedelta, List[str]]]:
    entries: List[Tuple[timedelta, timedelta, List[str]]] = []
    if not srt_path.exists():
        return entries
    with srt_path.open("r", encoding="utf-8") as f:
        lines = [ln.rstrip("\n") for ln in f]
    i = 0
    while i < len(lines):
        # skip index line
        if lines[i].strip().isdigit():
            i += 1
        if i >= len(lines):
            break
        m = TIMECODE_RE.match(lines[i])
        if not m:
            i += 1
            continue
        start = parse_timecode(m.group(1)) + offset
        end = parse_timecode(m.group(2)) + offset
        i += 1
        text_lines: List[str] = []
        while i < len(lines) and lines[i].strip() != "":
            text_lines.append(lines[i])
            i += 1
        # skip blank line
        while i < len(lines) and lines[i].strip() == "":
            i += 1
        entries.append((start, end, text_lines))
    return entries


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Merge per-segment SRTs into one, adjusting by absolute start_time from DB."
        )
    )
    parser.add_argument("--db-path", type=str, required=True, help="Path to segments.db")
    parser.add_argument(
        "--source-like",
        type=str,
        required=True,
        help="Filter which source_audio to merge, e.g. %example%.",
    )
    parser.add_argument(
        "--srt-dir",
        type=str,
        required=True,
        help="Directory containing per-segment SRTs named like segment file base + .srt",
    )
    parser.add_argument(
        "--out-srt",
        type=str,
        required=True,
        help="Path to final merged SRT",
    )

    args = parser.parse_args()

    conn = sqlite3.connect(args.db_path)
    cur = conn.cursor()
    cur.execute(
        """
        SELECT ls.id, ls.segment_audio, ls.start_time, ls.end_time
        FROM language_segments ls
        JOIN audio_files af ON ls.audio_file_id = af.id
        WHERE af.source_path LIKE ?
        ORDER BY ls.start_time ASC, ls.id ASC
        """,
        (args.source_like,),
    )
    rows = cur.fetchall()

    srt_dir = Path(args.srt_dir)
    merged: List[Tuple[timedelta, timedelta, List[str]]] = []

    for seg_id, seg_audio, start_s, end_s in rows:
        seg_path = Path(seg_audio)
        seg_srt = srt_dir / (seg_path.stem + ".srt")
        offset = timedelta(seconds=float(start_s))
        merged.extend(read_srt_adjusted(seg_srt, offset))

    # write final SRT
    out_path = Path(args.out_srt)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", encoding="utf-8") as f:
        for idx, (st, et, tl) in enumerate(merged, start=1):
            f.write(f"{idx}\n")
            f.write(f"{fmt_timecode(st)} --> {fmt_timecode(et)}\n")
            for line in tl:
                f.write(line + "\n")
            f.write("\n")

    print(f"Merged {len(merged)} subtitle entries -> {out_path}")


if __name__ == "__main__":
    main()


