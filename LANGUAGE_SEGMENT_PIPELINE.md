## Language Segmentation & Subtitle Pipeline

این سند خلاصه‌ای از جریان کاری ماژول `detectLang` را در سطح پروژه اصلی ارائه می‌دهد تا بتوانید هم روی یک فایل صوتی و هم روی پوشه‌ای از فایل‌ها پردازش انجام دهید و خروجی‌ها را به پایگاه‌داده و زیرنویس نهایی متصل کنید.

### پیش‌نیازها
- Python 3.9+
- پکیج‌ها: `faster-whisper`, `langid`, `ffmpeg` در PATH سیستم، (اختیاری) `torch` با CUDA برای GPU

### 1. تشخیص بازه‌های زبانی
```bash
cd detectLang
python detectLanguage.py --audio-file "C:/audio/clip.wav" --output-dir "C:/reports"
# یا
python detectLanguage.py --directory "C:/audio/batch" --output-dir "C:/reports"
```
- پارامترهای مهم: `--device`, `--device-id`, `--model-size`, `--compute-type`, `--no-vad`
- خروجی: برای هر فایل، یک `*.language_intervals.json`

### 2. برش صوت و درج در SQLite
```bash
python split_and_store.py --reports-dir "C:/reports" --output-audio-dir "C:/segments/audio" --db-path "C:/segments/segments.db"
# اجرای تکی: --report-file "path/to/file.language_intervals.json"
```
- هر بازه با `ffmpeg` برش می‌شود.
- جداول: `audio_files` (فایل اصلی)، `segments` (سازگاری قدیمی)، `language_segments` (جدید)
- در `language_segments`، مسیر تکه صوتی، زبان، بازه زمانی و مسیر گزارش ثبت می‌شود.

### 3. خروجی جاب‌های زیرنویس
```bash
python export_jobs.py --db-path "C:/segments/segments.db" --source-like "%clip%" --out-jsonl "C:/jobs/clip.jsonl"
# خروجی CSV: --out-csv "C:/jobs/clip.csv"
# فیلتر زبان: --lang fa
```
- هر ردیف شامل مسیر تکه صوتی، زمان‌بندی و متن پیوسته است.
- این فایل را می‌توانید به سرویس/اسکریپت زیرنویس‌ساز بدهید (مثلاً ماژول `Subtitle-Generator` یا n8n).

### 4. تولید زیرنویس‌های هر تکه
- خارج از این ماژول انجام می‌شود؛ برای هر فایل صوتی در `segments/audio` یک فایل `.srt` تولید کنید و در پوشه‌ای (مثلاً `C:/segments/srts`) قرار دهید.

### 5. تجمیع SRT نهایی
```bash
python merge_srt.py --db-path "C:/segments/segments.db" --source-like "%clip%" --srt-dir "C:/segments/srts" --out-srt "C:/segments/clip.final.srt"
```
- از `language_segments` زمان شروع را گرفته و آفست صحیح اعمال می‌کند تا یک فایل SRT یکپارچه بسازد.

### یادآوری‌ها
- اجرای تکی یا دسته‌ای در تمام مراحل امکان‌پذیر است.
- برای موازی‌سازی می‌توانید چند فرآیند با فیلترهای مختلف (`--source-like`) یا GPUهای متفاوت (`--device-id`) اجرا کنید.
- دیتابیس SQLite را می‌توان با ابزارهای استاندارد (مثل DB Browser) بررسی و مانیتور کرد.

