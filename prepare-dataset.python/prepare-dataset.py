import os
import json
import glob
from pathlib import Path
from typing import List, Dict
import librosa
import soundfile as sf

def split_audio_by_silence(audio_path: str, output_dir: str, 
                           min_silence_len: float = 0.5,
                           silence_thresh: float = -40) -> List[str]:
    """تقسیم فایل صوتی بر اساس سکوت
    
    Returns: لیست مسیرهای فایل‌های کوچک تقسیم شده
    """
    from pydub import AudioSegment
    from pydub.silence import split_on_silence
    
    # بارگذاری فایل
    audio = AudioSegment.from_file(audio_path)
    
    # تقسیم بر اساس سکوت
    chunks = split_on_silence(
        audio,
        min_silence_len=int(min_silence_len * 1000),  # به میلی‌ثانیه
        silence_thresh=silence_thresh,
        keep_silence=200  # نگه داشتن 200ms سکوت
    )
    
    # ذخیره قطعات
    output_paths = []
    base_name = Path(audio_path).stem
    
    for i, chunk in enumerate(chunks):
        if len(chunk) < 500:  # کمتر از 0.5 ثانیه رد میشه
            continue
        if len(chunk) > 30000:  # بیشتر از 30 ثانیه رد میشه
            continue
            
        output_path = os.path.join(output_dir, f"{base_name}_chunk_{i:04d}.wav")
        chunk.export(output_path, format="wav")
        output_paths.append(output_path)
    
    return output_paths

def create_dataset_structure(
    wav_directory: str,
    output_base_dir: str = "./whisper_dataset",
    split_audio: bool = True
):
    """ساخت ساختار دیتاست برای Fine-tuning Whisper
    
    ساختار خروجی:
    whisper_dataset/
    ├── audio/           # فایل‌های صوتی
    ├── transcripts/     # متن‌های خام (برای ویرایش دستی)
    └── metadata.jsonl   # فایل نهایی دیتاست
    """
    
    # ساخت دایرکتوری‌ها
    audio_dir = os.path.join(output_base_dir, "audio")
    transcript_dir = os.path.join(output_base_dir, "transcripts")
    os.makedirs(audio_dir, exist_ok=True)
    os.makedirs(transcript_dir, exist_ok=True)
    
    # پیدا کردن فایل‌های WAV
    wav_files = glob.glob(os.path.join(wav_directory, "**/*.wav"), recursive=True)
    print(f"📁 تعداد {len(wav_files)} فایل WAV پیدا شد")
    
    all_segments = []
    
    for idx, wav_file in enumerate(wav_files):
        print(f"⚙️  پردازش {idx+1}/{len(wav_files)}: {Path(wav_file).name}")
        
        if split_audio:
            # تقسیم به قطعات کوچک
            try:
                chunks = split_audio_by_silence(wav_file, audio_dir)
                print(f"   ✂️  {len(chunks)} قطعه ایجاد شد")
            except Exception as e:
                print(f"   ❌ خطا در تقسیم: {e}")
                chunks = []
        else:
            # کپی مستقیم
            import shutil
            dest = os.path.join(audio_dir, Path(wav_file).name)
            shutil.copy2(wav_file, dest)
            chunks = [dest]
        
        # ایجاد فایل متنی برای هر قطعه
        for chunk_path in chunks:
            chunk_name = Path(chunk_path).stem
            transcript_path = os.path.join(transcript_dir, f"{chunk_name}.txt")
            
            # ایجاد فایل متنی خالی برای ویرایش دستی
            with open(transcript_path, 'w', encoding='utf-8') as f:
                f.write("")  # خالی - باید دستی پر بشه
            
            all_segments.append({
                "audio": chunk_path,
                "transcript": transcript_path,
                "duration": librosa.get_duration(path=chunk_path)
            })
    
    # ذخیره metadata
    metadata_path = os.path.join(output_base_dir, "segments_info.json")
    with open(metadata_path, 'w', encoding='utf-8') as f:
        json.dump(all_segments, f, ensure_ascii=False, indent=2)
    
    print(f"\n✅ ساختار دیتاست آماده شد!")
    print(f"📂 مسیر: {output_base_dir}")
    print(f"🎵 تعداد قطعات: {len(all_segments)}")
    print(f"\n⚠️  مرحله بعدی:")
    print(f"   1. فایل‌های TXT در {transcript_dir} را با متن صحیح پر کنید")
    print(f"   2. اسکریپت بعدی را اجرا کنید: prepare_for_training.py")

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser()
    parser.add_argument("--wav-dir", required=True, help="پوشه حاوی فایل‌های WAV")
    parser.add_argument("--output-dir", default="./whisper_dataset", help="پوشه خروجی دیتاست")
    parser.add_argument("--no-split", action="store_true", help="تقسیم نکردن فایل‌ها")
    
    args = parser.parse_args()
    
    create_dataset_structure(
        args.wav_dir,
        args.output_dir,
        split_audio=not args.no_split
    )