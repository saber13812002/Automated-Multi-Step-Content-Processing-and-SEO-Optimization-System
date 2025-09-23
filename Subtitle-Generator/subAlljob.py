import whisper
from pydub import AudioSegment
import datetime
import sys
import argparse
from pathlib import Path
import glob
import os
import torch
import concurrent.futures
from typing import List, Tuple

def format_timestamp(seconds):
    return str(datetime.timedelta(seconds=seconds)).replace('.', ',')[:11]

def get_available_gpus() -> List[int]:
    """برگرداندن لیست GPU های موجود"""
    return list(range(torch.cuda.device_count()))

def process_file_with_gpu(args: Tuple[str, str, str, int]) -> bool:
    """پردازش یک فایل با GPU مشخص شده"""
    video_file, model_name, language, gpu_id = args
    try:
        # تنظیم GPU فقط اگر GPU معتبر است
        if gpu_id != -1:
            torch.cuda.set_device(gpu_id)
        model = whisper.load_model(model_name)
        
        result = model.transcribe(video_file, language=language)
        output_file = Path(video_file).with_suffix('.srt')
        
        with open(output_file, 'w', encoding='utf-8') as srt_file:
            for j, segment in enumerate(result['segments'], start=1):
                start_time = format_timestamp(segment['start'])
                end_time = format_timestamp(segment['end'])
                text = segment['text'].strip()
                srt_file.write(f"{j}\n{start_time} --> {end_time}\n{text}\n\n")
        
        print(f'\nزیرنویس در فایل {output_file} ذخیره شد (GPU {gpu_id})')
        return True
    except Exception as e:
        print(f'خطا در پردازش {video_file} روی GPU {gpu_id}: {str(e)}')
        return False

def process_directory(directory_path='.', model_name='large', language='ar'):
    # بررسی GPU های موجود
    available_gpus = get_available_gpus()
    if not available_gpus:
        print("هیچ GPU ای یافت نشد. از CPU استفاده می‌شود.")
        available_gpus = [-1]  # CPU
    else:
        print(f"تعداد {len(available_gpus)} GPU یافت شد: {available_gpus}")

    # پیدا کردن فایل‌های مدیا - شامل فرمت‌های سازمانی و ماهواره‌ای
    extensions = [
        # فرمت‌های معمولی
        '*.mp4', '*.mp3', '*.m4a', '*.wav', '*.aac', '*.flac', '*.ogg', '*.mkv', '*.webm', '*.avi', '*.mov', '*.mpg',
        # فرمت‌های ماهواره‌ای و پخش
        '*.ts', '*.mts', '*.m2ts', '*.trp', '*.tp',
        # فرمت‌های حرفه‌ای پخش
        '*.mxf', '*.gxf',
        # فرمت‌های DVD و ضبط
        '*.vob', '*.ifo', '*.vro', '*.vdr',
        # فرمت‌های موبایل و ماهواره
        '*.3gp', '*.3g2',
        # فرمت‌های مایکروسافت
        '*.asf', '*.wmv', '*.wma',
        # فرمت‌های RealMedia
        '*.rm', '*.rmvb', '*.ra', '*.ram',
        # فرمت‌های ضبط تلویزیون
        '*.dvr-ms', '*.wtv', '*.rec', '*.pvr',
        # فرمت‌های کامکورد
        '*.mod', '*.tod',
        # فرمت‌های MPEG اضافی
        '*.m2v', '*.m1v', '*.mp2', '*.mpa',
        # فرمت‌های صوتی حرفه‌ای
        '*.ac3', '*.eac3', '*.dts', '*.dtshd',
        '*.thd', '*.mlp', '*.aiff', '*.au', '*.snd',
        # فرمت‌های Audible و کتاب صوتی
        '*.aa', '*.aax', '*.m4b', '*.m4p',
        # فرمت‌های صوتی فشرده‌سازی بالا
        '*.opus', '*.spx', '*.tta', '*.tak',
        '*.wv', '*.ape', '*.shn'
    ]
    all_files = []
    for ext in extensions:
        all_files.extend(glob.glob(os.path.join(directory_path, f'**/{ext}'), recursive=True))
    
    # فیلتر کردن فایل‌های پردازش نشده
    files_to_process = [f for f in all_files if not Path(f).with_suffix('.srt').exists()]
    
    if not files_to_process:
        print("هیچ فایل مدیای بدون زیرنویس پیدا نشد.")
        return

    print(f"تعداد {len(files_to_process)} فایل برای پردازش پیدا شد.")

    # آماده‌سازی کارها برای پردازش موازی
    tasks = []
    for i, video_file in enumerate(files_to_process):
        gpu_id = available_gpus[i % len(available_gpus)]
        tasks.append((video_file, model_name, language, gpu_id))

    # پردازش موازی فایل‌ها
    with concurrent.futures.ProcessPoolExecutor(max_workers=len(available_gpus)) as executor:
        results = list(executor.map(process_file_with_gpu, tasks))

    # نمایش نتایج نهایی
    successful = sum(1 for r in results if r)
    print(f"\nپردازش کامل شد. {successful} فایل از {len(files_to_process)} فایل با موفقیت پردازش شدند.")

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='تبدیل فایل‌های ویدیویی و صوتی به زیرنویس با استفاده از Whisper')
    parser.add_argument('--directory', default='.', help='مسیر پوشه حاوی فایل‌های ویدیویی و صوتی (پیش‌فرض: پوشه فعلی)')
    parser.add_argument('--model', default='large', help='نام مدل (پیش‌فرض: large)')
    parser.add_argument('--language', default='ar', help='کد زبان (پیش‌فرض: ar)')
    
    args = parser.parse_args()
    
    process_directory(args.directory, args.model, args.language)