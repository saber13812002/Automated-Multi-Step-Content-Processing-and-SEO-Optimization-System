from pydub import AudioSegment
import re
from pathlib import Path

def timestamp_to_ms(timestamp: str) -> int:
    """تبدیل timestamp به میلی‌ثانیه"""
    # فرمت: 00:01:23,456
    h, m, s = timestamp.split(':')
    s, ms = s.split(',')
    
    total_ms = (
        int(h) * 3600000 +
        int(m) * 60000 +
        int(s) * 1000 +
        int(ms)
    )
    return total_ms

def split_audio_by_srt(
    audio_path: str,
    srt_path: str,
    output_dir: str,
    min_duration_ms: int = 1000,
    max_duration_ms: int = 30000
):
    """برش فایل صوتی بر اساس SRT"""
    
    # بارگذاری فایل صوتی
    print(f"🎵 بارگذاری فایل صوتی...")
    audio = AudioSegment.from_file(audio_path)
    
    # خواندن SRT
    with open(srt_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    pattern = r'(\d+)\n(\d{2}:\d{2}:\d{2},\d{3}) --> (\d{2}:\d{2}:\d{2},\d{3})\n(.*?)(?=\n\n|\Z)'
    matches = re.findall(pattern, content, re.DOTALL)
    
    # ساخت دایرکتوری خروجی
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    audio_dir = Path(output_dir) / "audio"
    transcript_dir = Path(output_dir) / "transcripts"
    audio_dir.mkdir(exist_ok=True)
    transcript_dir.mkdir(exist_ok=True)
    
    base_name = Path(audio_path).stem
    
    valid_segments = []
    
    for match in matches:
        idx = int(match[0])
        start_time = timestamp_to_ms(match[1])
        end_time = timestamp_to_ms(match[2])
        text = match[3].strip()
        
        duration = end_time - start_time
        
        # فیلتر کردن بر اساس طول
        if duration < min_duration_ms or duration > max_duration_ms:
            continue
        
        if not text:
            continue
        
        # برش صوت
        segment_audio = audio[start_time:end_time]
        
        # نام فایل
        segment_name = f"{base_name}_seg_{idx:04d}"
        audio_file = audio_dir / f"{segment_name}.wav"
        text_file = transcript_dir / f"{segment_name}.txt"
        
        # ذخیره صوت
        segment_audio.export(audio_file, format="wav")
        
        # ذخیره متن
        with open(text_file, 'w', encoding='utf-8') as f:
            f.write(text)
        
        valid_segments.append({
            'audio': str(audio_file),
            'text': text,
            'duration': duration / 1000.0
        })
    
    print(f"✅ تعداد {len(valid_segments)} قطعه ایجاد شد")
    print(f"📂 صوت: {audio_dir}")
    print(f"📂 متن: {transcript_dir}")
    
    # ذخیره metadata
    import json
    metadata_path = Path(output_dir) / "metadata.json"
    with open(metadata_path, 'w', encoding='utf-8') as f:
        json.dump(valid_segments, f, ensure_ascii=False, indent=2)
    
    print(f"💾 Metadata: {metadata_path}")

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser()
    parser.add_argument('--audio', required=True)
    parser.add_argument('--srt', required=True)
    parser.add_argument('--output-dir', required=True)
    
    args = parser.parse_args()
    
    split_audio_by_srt(args.audio, args.srt, args.output_dir)