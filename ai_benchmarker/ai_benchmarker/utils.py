from __future__ import annotations

import re
import uuid


def generate_audio_guid() -> str:
    return str(uuid.uuid4())


def parse_subtitle_text(content: str, file_name: str = "") -> str:
    """Extract spoken text from plain text or SRT/VTT subtitle files."""
    lowered = file_name.lower()
    if lowered.endswith((".srt", ".vtt")):
        return _parse_srt_or_vtt(content)
    return content.strip()


def _parse_srt_or_vtt(content: str) -> str:
    lines: list[str] = []
    for raw_line in content.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        if line.upper() == "WEBVTT":
            continue
        if re.fullmatch(r"\d+", line):
            continue
        if "-->" in line:
            continue
        lines.append(line)
    return " ".join(lines)
