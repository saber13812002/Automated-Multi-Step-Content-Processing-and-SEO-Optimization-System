import argparse
import json
import os
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import langid

try:
    # faster-whisper provides efficient GPU inference and word/segment timestamps
    from faster_whisper import WhisperModel
except Exception as exc:  # pragma: no cover - import-time environment guard
    raise RuntimeError(
        "faster-whisper is required. Install with: pip install faster-whisper"
    ) from exc


def get_device_and_index(preferred_device: Optional[str], device_id: Optional[int]) -> Tuple[str, int]:
    """Resolve compute device and index.

    - preferred_device: "cuda" | "cpu" | None (auto)
    - device_id: index to select GPU when cuda
    """
    if preferred_device in {"cuda", "cpu"}:
        device = preferred_device
    else:
        # Auto: prefer CUDA if available
        try:
            import torch  # type: ignore

            device = "cuda" if torch.cuda.is_available() else "cpu"
        except Exception:  # torch not installed, fall back to CPU
            device = "cpu"

    if device == "cuda":
        return device, (device_id if device_id is not None else 0)
    return device, 0


def load_asr_model(
    model_size: str,
    device: Optional[str],
    device_id: Optional[int],
    compute_type: str,
) -> WhisperModel:
    resolved_device, resolved_index = get_device_and_index(device, device_id)
    return WhisperModel(
        model_size,
        device=resolved_device,
        device_index=resolved_index,
        compute_type=compute_type,
    )


def transcribe_with_segments(
    model: WhisperModel,
    audio_path: str,
    beam_size: int = 5,
    vad: bool = True,
) -> List[Dict]:
    """Transcribe audio and return a list of segment dicts with start, end, text.

    We classify language per segment later via langid.
    """
    segments, _ = model.transcribe(
        audio_path,
        beam_size=beam_size,
        vad_filter=vad,
        word_timestamps=False,  # segment timestamps are sufficient to group language changes
    )

    result: List[Dict] = []
    for seg in segments:
        # seg.start, seg.end (float seconds), seg.text (string)
        text = (seg.text or "").strip()
        if not text:
            continue
        result.append({
            "start": float(seg.start),
            "end": float(seg.end),
            "text": text,
        })
    return result


def classify_language(text: str) -> str:
    lang, _ = langid.classify(text)
    return lang


def aggregate_language_intervals(segments: List[Dict]) -> List[Dict]:
    """Group contiguous segments by detected language into intervals.

    Each output item: { language, start_time, end_time, text }
    where text is the concatenation for that interval (useful for QA/export).
    """
    intervals: List[Dict] = []
    current_lang: Optional[str] = None
    current_start: Optional[float] = None
    current_end: Optional[float] = None
    current_text_parts: List[str] = []

    for seg in segments:
        seg_lang = classify_language(seg["text"])
        if current_lang is None:
            # start first interval
            current_lang = seg_lang
            current_start = seg["start"]
            current_end = seg["end"]
            current_text_parts = [seg["text"]]
            continue

        if seg_lang == current_lang:
            # extend interval
            current_end = seg["end"]
            current_text_parts.append(seg["text"])
        else:
            # flush previous interval
            intervals.append({
                "language": current_lang,
                "start_time": float(current_start if current_start is not None else seg["start"]),
                "end_time": float(current_end if current_end is not None else seg["end"]),
                "text": " ".join(current_text_parts).strip(),
            })
            # start new interval
            current_lang = seg_lang
            current_start = seg["start"]
            current_end = seg["end"]
            current_text_parts = [seg["text"]]

    # flush tail
    if current_lang is not None:
        intervals.append({
            "language": current_lang,
            "start_time": float(current_start if current_start is not None else 0.0),
            "end_time": float(current_end if current_end is not None else 0.0),
            "text": " ".join(current_text_parts).strip(),
        })

    return intervals


def process_audio_file(
    model: WhisperModel,
    audio_path: str,
) -> List[Dict]:
    segments = transcribe_with_segments(model, audio_path)
    return aggregate_language_intervals(segments)


def write_json_report(audio_path: str, intervals: List[Dict], out_dir: Optional[str]) -> str:
    audio_path_obj = Path(audio_path)
    base_name = audio_path_obj.stem
    target_dir = Path(out_dir) if out_dir else audio_path_obj.parent
    target_dir.mkdir(parents=True, exist_ok=True)
    out_path = target_dir / f"{base_name}.language_intervals.json"
    with out_path.open("w", encoding="utf-8") as f:
        json.dump({
            "audio": str(audio_path_obj),
            "intervals": intervals,
        }, f, ensure_ascii=False, indent=2)
    return str(out_path)


def iter_audio_files(root: str) -> List[str]:
    exts = {".wav", ".mp3", ".m4a", ".flac", ".ogg", ".webm", ".aac"}
    root_path = Path(root)
    files: List[str] = []
    for p in root_path.rglob("*"):
        if p.is_file() and p.suffix.lower() in exts:
            files.append(str(p))
    return sorted(files)


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Detect language changes in audio by ASR segmentation and per-segment language classification."
        )
    )
    parser.add_argument(
        "--directory",
        type=str,
        required=True,
        help="Directory containing audio files (wav, mp3, m4a, flac, ogg, webm, aac)",
    )
    parser.add_argument(
        "--model-size",
        type=str,
        default="large-v3",
        help=(
            "faster-whisper model size (e.g., tiny, base, small, medium, large-v2, large-v3)."
        ),
    )
    parser.add_argument(
        "--device",
        type=str,
        choices=["cuda", "cpu"],
        default=None,
        help="Force device; default is auto (prefer cuda if available).",
    )
    parser.add_argument(
        "--device-id",
        type=int,
        default=None,
        help="GPU index when using CUDA (default: 0).",
    )
    parser.add_argument(
        "--compute-type",
        type=str,
        default="float16",
        help="Compute type for faster-whisper (e.g., float16, float32, int8).",
    )
    parser.add_argument(
        "--beam-size",
        type=int,
        default=5,
        help="Beam size for decoding.",
    )
    parser.add_argument(
        "--no-vad",
        action="store_true",
        help="Disable VAD filtering.",
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default=None,
        help="Optional directory to write JSON reports.",
    )

    args = parser.parse_args()

    model = load_asr_model(
        model_size=args.model_size,
        device=args.device,
        device_id=args.device_id,
        compute_type=args.compute_type,
    )

    files = iter_audio_files(args.directory)
    if not files:
        print("No audio files found.")
        return

    for fp in files:
        print(f"Processing: {fp}")
        try:
            intervals = process_audio_file(model, fp)
        except Exception as e:
            print(f"Failed: {fp} -> {e}")
            continue

        # Print intervals to stdout
        for it in intervals:
            lang = it["language"]
            start_s = it["start_time"]
            end_s = it["end_time"]
            print(f"  Language: {lang} | Start: {start_s:.2f}s | End: {end_s:.2f}s")

        # Optional JSON output
        if args.output_dir is not None:
            out_path = write_json_report(fp, intervals, args.output_dir)
            print(f"  Saved: {out_path}")


if __name__ == "__main__":
    main()


