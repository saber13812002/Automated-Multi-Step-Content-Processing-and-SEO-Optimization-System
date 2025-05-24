import whisper
import subprocess
import glob
import os
import sys
import datetime
from pathlib import Path
import torch
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List

def format_timestamp(seconds: float) -> str:
    return str(datetime.timedelta(seconds=seconds)).replace('.', ',')[:11]

def check_audio_file(filepath: str) -> bool:
    try:
        result = subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration",
             "-of", "default=noprint_wrappers=1:nokey=1", filepath],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=10
        )
        duration = float(result.stdout.strip())
        return duration > 0
    except Exception as e:
        print(f"خطا در بررسی فایل {filepath}: {e}")
        return False

def find_valid_media_files(directory: str, extensions: List[str]) -> List[str]:
    all_files = []
    for ext in extensions:
        all_files.extend(glob.glob(os.path.join(directory, f"**/{ext}"), recursive=True))
    print(f"کل فایل‌های پیدا شده: {len(all_files)}")
    valid_files = [f for f in all_files if check_audio_file(f)]
    print(f"فایل‌های معتبر برای پردازش: {len(valid_files)}")
    return valid_files

def process_file(video_file: str, model, language: str, gpu_id: int) -> bool:
    try:
        torch.cuda.set_device(gpu_id)
        print(f"شروع پردازش فایل {video_file} روی GPU {gpu_id}")
        result = model.transcribe(video_file, language=language)
        output_file = Path(video_file).with_suffix('.srt')
        with open(output_file, 'w', encoding='utf-8') as srt_file:
            for i, segment in enumerate(result['segments'], 1):
                start_time = format_timestamp(segment['start'])
                end_time = format_timestamp(segment['end'])
                text = segment['text'].strip()
                srt_file.write(f"{i}\n{start_time} --> {end_time}\n{text}\n\n")
        print(f"پایان پردازش فایل {video_file} روی GPU {gpu_id} - زیرنویس ذخیره شد.")
        return True
    except Exception as e:
        print(f"خطا در پردازش فایل {video_file} روی GPU {gpu_id}: {e}")
        with open("failed_files.log", "a", encoding='utf-8') as logf:
            logf.write(f"{video_file}\n")
        return False

def retry_failed_files(model, language: str, available_gpus: List[int]):
    failed_path = Path("failed_files.log")
    if not failed_path.exists():
        print("فایل خطا (failed_files.log) وجود ندارد. موردی برای تلاش مجدد نیست.")
        return
    with open(failed_path, encoding='utf-8') as f:
        files = [line.strip() for line in f if line.strip()]
    if not files:
        print("هیچ فایل خطایی برای تلاش مجدد وجود ندارد.")
        return
    print(f"تلاش مجدد برای پردازش {len(files)} فایل ناموفق قبلی...")
    # پاک کردن فایل خطا برای ثبت خطاهای جدید
    failed_path.unlink()
    max_workers = len(available_gpus) if available_gpus else 1
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = []
        for i, file in enumerate(files):
            gpu_id = available_gpus[i % len(available_gpus)] if available_gpus else -1
            futures.append(executor.submit(process_file, file, model, language, gpu_id))
        for future in as_completed(futures):
            future.result()

def main(directory: str, model_name: str, language: str):
    extensions = ['*.mp4', '*.mp3', '*.m4a', '*.wav', '*.aac', '*.flac', '*.ogg', '*.mkv', '*.webm', '*.avi', '*.mov', '*.mpg']
    available_gpus = list(range(torch.cuda.device_count()))
    if not available_gpus:
        print("هیچ GPU فعال نیست، پردازش روی CPU انجام می‌شود.")
        available_gpus = [-1]  # CPU
    else:
        print(f"GPU های فعال: {available_gpus}")

    valid_files = find_valid_media_files(directory, extensions)
    if not valid_files:
        print("هیچ فایل معتبر برای پردازش یافت نشد.")
        return

    print(f"بارگذاری مدل {model_name} ...")
    model = whisper.load_model(model_name)
    print("مدل بارگذاری شد.")

    max_workers = len(available_gpus) if available_gpus else 1
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = []
        for i, file in enumerate(valid_files):
            gpu_id = available_gpus[i % len(available_gpus)]
            futures.append(executor.submit(process_file, file, model, language, gpu_id))
        for future in as_completed(futures):
            future.result()

    print("پردازش فایل‌ها به پایان رسید.")
    retry_failed_files(model, language, available_gpus)
    print("تلاش مجدد برای فایل‌های ناموفق انجام شد.")

if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description='تبدیل فایل‌های صوتی و ویدیویی به زیرنویس با استفاده از Whisper')
    parser.add_argument('--directory', default='.', help='مسیر پوشه فایل‌های صوتی و ویدیویی')
    parser.add_argument('--model', default='large', help='نام مدل Whisper')
    parser.add_argument('--language', default='ar', help='کد زبان (مثلاً fa یا ar)')
    args = parser.parse_args()

    main(args.directory, args.model, args.language)
