import json
import os
from datasets import Dataset, Audio, Features, Value
from pathlib import Path

def create_hf_dataset(dataset_dir: str, output_dir: str = "./hf_dataset"):
    """تبدیل به فرمت Hugging Face Dataset"""
    
    # خواندن metadata
    metadata_path = os.path.join(dataset_dir, "segments_info.json")
    with open(metadata_path, 'r', encoding='utf-8') as f:
        segments = json.load(f)
    
    # فیلتر کردن فایل‌های دارای متن
    valid_data = []
    for seg in segments:
        transcript_path = seg["transcript"]
        
        # خواندن متن
        with open(transcript_path, 'r', encoding='utf-8') as f:
            text = f.read().strip()
        
        # فقط اگر متن پر شده باشد
        if text:
            valid_data.append({
                "audio": seg["audio"],
                "text": text,
                "duration": seg["duration"]
            })
    
    print(f"✅ تعداد نمونه‌های معتبر: {len(valid_data)}")
    
    # ساخت Dataset
    dataset = Dataset.from_dict({
        "audio": [d["audio"] for d in valid_data],
        "text": [d["text"] for d in valid_data],
        "duration": [d["duration"] for d in valid_data]
    })
    
    # تبدیل فیلد audio به Audio feature
    dataset = dataset.cast_column("audio", Audio(sampling_rate=16000))
    
    # تقسیم به train/test (90/10)
    dataset = dataset.train_test_split(test_size=0.1, seed=42)
    
    # ذخیره
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