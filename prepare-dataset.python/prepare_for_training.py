import json
import os
from datasets import Dataset, Audio
from pathlib import Path


def _load_segments(dataset_dir: str) -> list:
    """Load segments from segments_info.json or legacy metadata.json."""
    for filename in ("segments_info.json", "metadata.json"):
        path = os.path.join(dataset_dir, filename)
        if os.path.isfile(path):
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
    raise FileNotFoundError(
        f"No segments_info.json or metadata.json found in {dataset_dir}"
    )


def _resolve_text(seg: dict) -> str:
    """Extract transcript text from segment, supporting both schema formats."""
    if "text" in seg and seg["text"]:
        return str(seg["text"]).strip()

    transcript_path = seg.get("transcript")
    if not transcript_path:
        return ""

    with open(transcript_path, "r", encoding="utf-8") as f:
        return f.read().strip()


def create_hf_dataset(dataset_dir: str, output_dir: str = "./hf_dataset"):
    """Convert dataset directory to Hugging Face Dataset format."""

    segments = _load_segments(dataset_dir)

    valid_data = []
    for seg in segments:
        text = _resolve_text(seg)
        if not text:
            continue

        valid_data.append({
            "audio": seg["audio"],
            "text": text,
            "duration": seg.get("duration", 0.0),
        })

    print(f"✅ تعداد نمونه‌های معتبر: {len(valid_data)}")

    dataset = Dataset.from_dict({
        "audio": [d["audio"] for d in valid_data],
        "text": [d["text"] for d in valid_data],
        "duration": [d["duration"] for d in valid_data],
    })

    dataset = dataset.cast_column("audio", Audio(sampling_rate=16000))
    dataset = dataset.train_test_split(test_size=0.1, seed=42)
    dataset.save_to_disk(output_dir)

    print(f"💾 دیتاست ذخیره شد در: {output_dir}")
    print(f"📊 Train: {len(dataset['train'])} نمونه")
    print(f"📊 Test: {len(dataset['test'])} نمونه")

    return dataset


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset-dir", required=True)
    parser.add_argument("--output-dir", default="./hf_dataset")

    args = parser.parse_args()

    create_hf_dataset(args.dataset_dir, args.output_dir)
