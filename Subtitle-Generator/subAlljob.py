import whisper
from pydub import AudioSegment
import datetime
import sys
import argparse
from pathlib import Path
import glob
import os

def format_timestamp(seconds):
    return str(datetime.timedelta(seconds=seconds)).replace('.', ',')[:11]

def process_video(input_file, model_name='large', language='ar'):
    try:
        # ... existing code ...
        result = model.transcribe(input_file, language=language)
        output_file = Path(input_file).stem + '.srt'
        
        with open(output_file, 'w', encoding='utf-8') as srt_file:
            total_segments = len(result['segments'])
            for i, segment in enumerate(result['segments'], start=1):
                # ... existing code ...
                sys.stdout.write(f'\rپیشرفت: {i}/{total_segments} ({int(i/total_segments*100)}%)')
                sys.stdout.flush()
        
        print(f'\nزیرنویس در فایل {output_file} ذخیره شد.')
        
    except Exception as e:
        print(f'خطا در پردازش {input_file}: {str(e)}')
        return False
    return True

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
        print("هیچ فایل mp4 یا mp3 بدون زیرنویس پیدا نشد.")
        return
    
    print(f"تعداد {len(files_to_process)} فایل برای پردازش پیدا شد.")
    
    for i, video_file in enumerate(files_to_process, 1):
        print(f"\nپردازش فایل {i}/{len(files_to_process)}: {video_file}")
        try:
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
            continue

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='تبدیل فایل‌های ویدیویی و صوتی به زیرنویس با استفاده از Whisper')
    parser.add_argument('--directory', default='.', help='مسیر پوشه حاوی فایل‌های ویدیویی و صوتی (پیش‌فرض: پوشه فعلی)')
    parser.add_argument('--model', default='large', help='نام مدل (پیش‌فرض: large)')
    parser.add_argument('--language', default='ar', help='کد زبان (پیش‌فرض: ar)')
    
    args = parser.parse_args()
    
    process_directory(args.directory, args.model, args.language)