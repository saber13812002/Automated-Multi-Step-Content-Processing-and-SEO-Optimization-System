import whisper
from pydub import AudioSegment
import datetime
import sys
import argparse
from pathlib import Path
import glob
import os
import threading
import torch
from concurrent.futures import ThreadPoolExecutor

def format_timestamp(seconds):
    return str(datetime.timedelta(seconds=seconds)).replace('.', ',')[:11]

def get_available_gpu():
    """یک GPU آزاد پیدا می‌کند"""
    lock = threading.Lock()
    with lock:
        for i in range(torch.cuda.device_count()):
            if torch.cuda.memory_reserved(i) == 0:
                return i
        return 0

def process_single_file(video_file, model, language):
    """پردازش یک فایل با در نظر گرفتن قفل"""
    lock_file = video_file + '.lock'
    if os.path.exists(lock_file):
        print(f'فایل {video_file} در حال پردازش توسط یک ترد دیگر است.')
        return

    try:
        # ایجاد فایل قفل
        with open(lock_file, 'w') as f:
            f.write('locked')

        gpu_id = get_available_gpu()
        torch.cuda.set_device(gpu_id)
        print(f'پردازش {video_file} روی GPU {gpu_id}')
        
        result = model.transcribe(video_file, language=language)
        output_file = Path(video_file).with_suffix('.srt')
        
        with open(output_file, 'w', encoding='utf-8') as srt_file:
            total_segments = len(result['segments'])
            for j, segment in enumerate(result['segments'], start=1):
                start_time = format_timestamp(segment['start'])
                end_time = format_timestamp(segment['end'])
                text = segment['text'].strip()
                
                srt_file.write(f"{j}\n{start_time} --> {end_time}\n{text}\n\n")
                
                sys.stdout.write(f'\rپیشرفت: {j}/{total_segments} ({int(j/total_segments*100)}%)')
                sys.stdout.flush()
        
        print(f'\nزیرنویس در فایل {output_file} ذخیره شد.')

    except Exception as e:
        print(f'خطا در پردازش {video_file}: {str(e)}')
    finally:
        # حذف فایل قفل
        if os.path.exists(lock_file):
            os.remove(lock_file)

def process_directory(directory_path='.', model_name='large', language='ar'):
    print(f'در حال دانلود مدل {model_name}...')
    model = whisper.load_model(model_name)
    print('مدل دانلود شد.')
    
    # پیدا کردن تمام فایل‌های صوتی و ویدیویی در مسیر (mp4, mp3, m4a, wav, aac, flac, ogg, mkv, webm, avi)

    extensions = ['*.mp4', '*.mp3', '*.m4a', '*.wav', '*.aac', '*.flac', '*.ogg', '*.mkv', '*.webm', '*.avi','*.mov','*.mpg']
    all_files = []
    for ext in extensions:
        all_files.extend(glob.glob(os.path.join(directory_path, f'**/{ext}'), recursive=True))
    
    # فیلتر کردن فایل‌هایی که srt ندارند
    files_to_process = []
    for media_file in all_files:
        srt_file = Path(media_file).with_suffix('.srt')
        if not srt_file.exists():
            files_to_process.append(media_file)
    
    if not files_to_process:
        print("هیچ فایل بدون زیرنویس پیدا نشد.")
        return
    
    print(f"تعداد {len(files_to_process)} فایل برای پردازش پیدا شد.")
    
    # تعداد GPUهای موجود
    num_gpus = torch.cuda.device_count()
    print(f"تعداد GPU های موجود: {num_gpus}")
    
    # ایجاد thread pool به تعداد GPUها
    with ThreadPoolExecutor(max_workers=num_gpus) as executor:
        futures = [
            executor.submit(process_single_file, video_file, model, language)
            for video_file in files_to_process
        ]
        
        # منتظر اتمام همه تردها
        for future in futures:
            future.result()

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='تبدیل فایل‌های ویدیویی و صوتی به زیرنویس با استفاده از Whisper')
    parser.add_argument('--directory', default='.', help='مسیر پوشه حاوی فایل‌های ویدیویی و صوتی (پیش‌فرض: پوشه فعلی)')
    parser.add_argument('--model', default='large', help='نام مدل (پیش‌فرض: large)')
    parser.add_argument('--language', default='ar', help='کد زبان (پیش‌فرض: ar)')
    
    args = parser.parse_args()
    
    process_directory(args.directory, args.model, args.language)
