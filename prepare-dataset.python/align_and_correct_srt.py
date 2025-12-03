import re
from pathlib import Path
from typing import List, Tuple
from rapidfuzz import fuzz, process
import datetime

def parse_srt(srt_path: str) -> List[dict]:
    """پارس کردن فایل SRT"""
    with open(srt_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # الگوی regex برای SRT
    pattern = r'(\d+)\n(\d{2}:\d{2}:\d{2},\d{3}) --> (\d{2}:\d{2}:\d{2},\d{3})\n(.*?)(?=\n\n|\Z)'
    matches = re.findall(pattern, content, re.DOTALL)
    
    segments = []
    for match in matches:
        segments.append({
            'index': int(match[0]),
            'start': match[1],
            'end': match[2],
            'text': match[3].strip()
        })
    
    return segments

def normalize_text(text: str) -> str:
    """نرمال‌سازی متن برای مقایسه بهتر"""
    # حذف علائم نگارشی
    text = re.sub(r'[^\w\s]', '', text)
    # حذف فاصله‌های اضافی
    text = re.sub(r'\s+', ' ', text)
    return text.strip()

def align_srt_with_reference(
    srt_path: str,
    reference_txt_path: str,
    output_srt_path: str,
    threshold: int = 70
):
    """تطبیق و تصحیح SRT با متن مرجع
    
    Args:
        srt_path: مسیر فایل SRT اولیه (خروجی Whisper)
        reference_txt_path: مسیر فایل متن مرجع (از Word)
        output_srt_path: مسیر فایل SRT تصحیح شده
        threshold: حداقل درصد تشابه برای تطبیق (0-100)
    """
    
    # خواندن SRT اولیه
    segments = parse_srt(srt_path)
    print(f"📄 تعداد بخش‌های SRT: {len(segments)}")
    
    # خواندن متن مرجع
    with open(reference_txt_path, 'r', encoding='utf-8') as f:
        reference_text = f.read()
    
    # تقسیم متن مرجع به جملات
    reference_sentences = re.split(r'[.!؟۔]\s+', reference_text)
    reference_sentences = [s.strip() for s in reference_sentences if s.strip()]
    
    print(f"📚 تعداد جملات مرجع: {len(reference_sentences)}")
    
    # نرمال‌سازی برای جستجو
    normalized_refs = [normalize_text(s) for s in reference_sentences]
    
    # تصحیح هر بخش
    corrected_segments = []
    matched_count = 0
    
    for i, seg in enumerate(segments):
        whisper_text = seg['text']
        whisper_normalized = normalize_text(whisper_text)
        
        # جستجوی بهترین تطبیق
        result = process.extractOne(
            whisper_normalized,
            normalized_refs,
            scorer=fuzz.ratio
        )
        
        if result and result[1] >= threshold:
            # تطبیق یافت شد
            best_match_idx = result[2]
            corrected_text = reference_sentences[best_match_idx]
            matched_count += 1
            
            corrected_segments.append({
                'index': seg['index'],
                'start': seg['start'],
                'end': seg['end'],
                'text': corrected_text,
                'original': whisper_text,
                'similarity': result[1]
            })
        else:
            # تطبیق نیافت - از متن اصلی استفاده می‌کنیم
            corrected_segments.append({
                'index': seg['index'],
                'start': seg['start'],
                'end': seg['end'],
                'text': whisper_text,
                'original': whisper_text,
                'similarity': 0
            })
    
    # ذخیره SRT تصحیح شده
    with open(output_srt_path, 'w', encoding='utf-8') as f:
        for seg in corrected_segments:
            f.write(f"{seg['index']}\n")
            f.write(f"{seg['start']} --> {seg['end']}\n")
            f.write(f"{seg['text']}\n\n")
    
    print(f"✅ SRT تصحیح شده ذخیره شد: {output_srt_path}")
    print(f"📊 تطبیق یافته: {matched_count}/{len(segments)} ({matched_count/len(segments)*100:.1f}%)")
    
    # ذخیره گزارش تفصیلی
    report_path = output_srt_path.replace('.srt', '_report.txt')
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write("گزارش تصحیح SRT\n")
        f.write("=" * 80 + "\n\n")
        
        for seg in corrected_segments:
            if seg['text'] != seg['original']:
                f.write(f"⏱️  زمان: {seg['start']} --> {seg['end']}\n")
                f.write(f"🔴 قبل: {seg['original']}\n")
                f.write(f"🟢 بعد: {seg['text']}\n")
                f.write(f"📊 شباهت: {seg['similarity']:.1f}%\n")
                f.write("-" * 80 + "\n\n")
    
    print(f"📋 گزارش تفصیلی: {report_path}")

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='تصحیح SRT با استفاده از متن مرجع')
    parser.add_argument('--srt', required=True, help='فایل SRT اولیه')
    parser.add_argument('--reference', required=True, help='فایل متن مرجع (TXT)')
    parser.add_argument('--output', required=True, help='فایل SRT خروجی')
    parser.add_argument('--threshold', type=int, default=70, help='حداقل درصد تشابه')
    
    args = parser.parse_args()
    
    align_srt_with_reference(
        args.srt,
        args.reference,
        args.output,
        args.threshold
    )