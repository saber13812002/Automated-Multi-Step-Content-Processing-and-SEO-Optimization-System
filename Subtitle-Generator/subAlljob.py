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
import subprocess
import tempfile
from typing import List, Tuple, Optional

def format_timestamp(seconds):
    return str(datetime.timedelta(seconds=seconds)).replace('.', ',')[:11]

def get_available_gpus() -> List[int]:
    """برگرداندن لیست GPU های موجود"""
    return list(range(torch.cuda.device_count()))

def extract_audio_with_ffmpeg(input_path: str) -> Optional[str]:
    """استخراج صوت به WAV با تلاش‌های جایگزین برای فایل‌های معیوب/غیرمعمول.

    برمی‌گرداند مسیر فایل WAV موقت در صورت موفقیت؛ وگرنه None
    """
    input_path_str = str(input_path)
    tmp_wav_path = str(Path(input_path_str).with_suffix('.whisper.tmp.wav'))

    def run_ffmpeg(cmd: List[str]) -> bool:
        try:
            result = subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, check=False)
            return result.returncode == 0
        except Exception:
            return False

    # تلاش اول: پارامترهای تحلیل بیشتر و نادیده گرفتن خطاهای زمانی
    base_args = [
        'ffmpeg', '-y', '-hide_banner', '-loglevel', 'error', '-nostdin',
        '-analyzeduration', '100M', '-probesize', '100M',
        '-fflags', '+igndts+discardcorrupt', '-err_detect', 'ignore_err',
        '-i', input_path_str,
        '-vn', '-ac', '1', '-ar', '16000', tmp_wav_path
    ]
    if run_ffmpeg(base_args):
        return tmp_wav_path

    # تلاش دوم: اگر فایل مانند TS باشد اما پسوند MP4 داشته باشد، فرمت ورودی را mpegts فرض کن
    ts_args = [
        'ffmpeg', '-y', '-hide_banner', '-loglevel', 'error', '-nostdin',
        '-analyzeduration', '200M', '-probesize', '200M',
        '-fflags', '+igndts+discardcorrupt', '-err_detect', 'ignore_err',
        '-f', 'mpegts', '-i', input_path_str,
        '-vn', '-ac', '1', '-ar', '16000', tmp_wav_path
    ]
    if run_ffmpeg(ts_args):
        return tmp_wav_path

    # تلاش سوم: با demuxing ساده‌تر
    simple_args = [
        'ffmpeg', '-y', '-hide_banner', '-loglevel', 'error', '-nostdin',
        '-i', input_path_str, '-vn', '-ac', '1', '-ar', '16000', tmp_wav_path
    ]
    if run_ffmpeg(simple_args):
        return tmp_wav_path

    # ناموفق
    return None

def process_file_with_gpu(args: Tuple[str, str, str, int]) -> bool:
    """پردازش یک فایل با GPU مشخص شده"""
    video_file, model_name, language, gpu_id = args
    try:
        # تنظیم GPU فقط اگر GPU معتبر است
        if gpu_id != -1:
            torch.cuda.set_device(gpu_id)
        model = whisper.load_model(model_name)
        
        # ابتدا تلاش برای استخراج صوت با ffmpeg (برای فایل‌های ناقص/TS/استریم)
        extracted_wav = extract_audio_with_ffmpeg(video_file)
        transcribe_input = extracted_wav if extracted_wav else video_file

        result = model.transcribe(transcribe_input, language=language)
        output_file = Path(video_file).with_suffix('.srt')
        
        with open(output_file, 'w', encoding='utf-8') as srt_file:
            for j, segment in enumerate(result['segments'], start=1):
                start_time = format_timestamp(segment['start'])
                end_time = format_timestamp(segment['end'])
                text = segment['text'].strip()
                srt_file.write(f"{j}\n{start_time} --> {end_time}\n{text}\n\n")
        
        print(f'✅ زیرنویس در فایل {output_file} ذخیره شد (GPU {gpu_id})')
        return True
    except Exception as e:
        print(f'❌ خطا در پردازش {video_file} روی GPU {gpu_id}: {str(e)}')
        return False

def process_directory(directory_path='.', model_name='large', language='ar'):
    print("🎬 خوش آمدید! سیستم تولید زیرنویس Whisper شروع به کار کرد...")
    print("=" * 60)
    
    # بررسی GPU های موجود
    available_gpus = get_available_gpus()
    if not available_gpus:
        print("⚠️  هیچ GPU ای یافت نشد. از CPU استفاده می‌شود.")
        available_gpus = [-1]  # CPU
    else:
        print(f"🎮 تعداد {len(available_gpus)} کارت گرافیک یافت شد: {available_gpus}")

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
        print("✅ هیچ فایل مدیای بدون زیرنویس پیدا نشد.")
        return

    print(f"📁 تعداد {len(files_to_process)} فایل برای پردازش پیدا شد.")
    print("=" * 60)

    # آماده‌سازی کارها برای پردازش موازی
    tasks = []
    for i, video_file in enumerate(files_to_process):
        gpu_id = available_gpus[i % len(available_gpus)]
        tasks.append((video_file, model_name, language, gpu_id))

    print(f"🚀 شروع پردازش {len(files_to_process)} فایل...")
    print("=" * 60)

    # پردازش موازی فایل‌ها با گزارش پیشرفت لحظه‌ای
    successful = 0
    completed = 0
    total = len(files_to_process)
    with concurrent.futures.ProcessPoolExecutor(max_workers=len(available_gpus)) as executor:
        futures = [executor.submit(process_file_with_gpu, t) for t in tasks]
        for fut in concurrent.futures.as_completed(futures):
            try:
                ok = fut.result()
            except Exception:
                ok = False
            completed += 1
            if ok:
                successful += 1
            remaining = total - completed
            print(f"📦 پیشرفت: {completed}/{total} انجام شد | باقی‌مانده: {remaining}")
    failed = total - successful
    
    print("=" * 60)
    print(f"🎉 پردازش کامل شد!")
    print(f"✅ موفق: {successful} فایل")
    print(f"❌ ناموفق: {failed} فایل")
    print(f"📊 مجموع: {len(files_to_process)} فایل")
    print("=" * 60)

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='تبدیل فایل‌های ویدیویی و صوتی به زیرنویس با استفاده از Whisper')
    parser.add_argument('--directory', default='.', help='مسیر پوشه حاوی فایل‌های ویدیویی و صوتی (پیش‌فرض: پوشه فعلی)')
    parser.add_argument('--model', default='large', help='نام مدل (پیش‌فرض: large)')
    parser.add_argument('--language', default='ar', help='کد زبان (پیش‌فرض: ar)')
    
    args = parser.parse_args()
    
    process_directory(args.directory, args.model, args.language)