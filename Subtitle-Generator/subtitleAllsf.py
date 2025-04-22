import whisper
import datetime
import sys
import argparse
from pathlib import Path
import glob
import os
import soundfile as sf

def format_timestamp(seconds):
    return str(datetime.timedelta(seconds=seconds)).replace('.', ',')[:11]

def process_video(input_file, model_name='large', language='ar'):
    try:
        # Load audio data
        audio_data, sample_rate = sf.read(input_file)
        # Process with Whisper
        result = model.transcribe(input_file, language=language)
        output_file = Path(input_file).stem + '.srt'
       
        with open(output_file, 'w', encoding='utf-8') as srt_file:
            total_segments = len(result['segments'])
            for i, segment in enumerate(result['segments'], start=1):
                start_time = format_timestamp(segment['start'])
                end_time = format_timestamp(segment['end'])
                text = segment['text'].strip()
               
                srt_file.write(f"{i}\n{start_time} --> {end_time}\n{text}\n\n")
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
   
    extensions = ['*.mp4', '*.mp3', '*.m4a', '*.wav', '*.aac', '*.flac', '*.ogg', '*.mkv', '*.webm', '*.avi']
    all_files = []
    for ext in extensions:
        all_files.extend(glob.glob(os.path.join(directory_path, f'**/{ext}'), recursive=True))
   
    files_to_process = [media_file for media_file in all_files if not Path(media_file).with_suffix('.srt').exists()]
   
    if not files_to_process:
        print("هیچ فایل mp4 یا mp3 بدون زیرنویس پیدا نشد.")
        return
   
    print(f"تعداد {len(files_to_process)} فایل برای پردازش پیدا شد.")
   
    for i, video_file in enumerate(files_to_process, 1):
        print(f"\nپردازش فایل {i}/{len(files_to_process)}: {video_file}")
        process_video(video_file, model_name, language)

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='تبدیل فایل‌های ویدیویی و صوتی به زیرنویس با استفاده از Whisper')
    parser.add_argument('--directory', default='.', help='مسیر پوشه حاوی فایل‌های ویدیویی و صوتی (پیش‌فرض: پوشه فعلی)')
    parser.add_argument('--model', default='large', help='نام مدل (پیش‌فرض: large)')
    parser.add_argument('--language', default='ar', help='کد زبان (پیش‌فرض: ar)')
   
    args = parser.parse_args()
   
    process_directory(args.directory, args.model, args.language)