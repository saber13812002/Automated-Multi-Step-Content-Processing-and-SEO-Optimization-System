## تشخیص بازه‌های زبانی (فارسی/عربی) در فایل‌های صوتی

این ابزار با استفاده از ASR مدل‌های Whisper (نسخه سریع‌تر: faster-whisper) گفتار را به متن با تایم‌استمپ بخش‌بندی می‌کند، سپس با `langid` زبان هر بخش را تشخیص داده و بازه‌های زمانی هم‌زبان را ادغام می‌کند.

- ورودی: پوشه‌ای شامل فایل‌های صوتی (`.wav`, `.mp3`, `.m4a`, `.flac`, `.ogg`, `.webm`, `.aac`)
- خروجی: چاپ بازه‌های زمانی زبان در ترمینال و در صورت نیاز، فایل JSON برای هر ورودی

---

### پیش‌نیازها

- Python 3.9+ پیشنهاد می‌شود
- اینترنت برای دانلود وزن‌های مدل در بار اول
- کارت گرافیک NVIDIA (اختیاری، برای سرعت بالاتر)

---

### نصب (Windows/Linux)

1) (اختیاری) ساخت محیط مجازی

Windows (PowerShell):
```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
```

Linux:
```bash
python3 -m venv .venv
source .venv/bin/activate
```

2) نصب PyTorch (در صورت استفاده از GPU)

- ویندوز (CUDA 12.1 نمونه):
```powershell
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121
```

- لینوکس: دستور مناسب کارت گرافیک و نسخه CUDA خود را از وب‌سایت PyTorch دریافت کنید.

3) نصب پکیج‌های لازم

```bash
pip install faster-whisper langid
```

نکته: اگر GPU ندارید یا نمی‌خواهید از آن استفاده کنید، نصب PyTorch CUDA لازم نیست و `faster-whisper` روی CPU نیز کار می‌کند (البته آهسته‌تر).

---

### اجرای سریع

پوشه پروژه:
```bash
cd detectLang
```

اجرای تکی روی یک فایل:
```bash
python detectLanguage.py --audio-file "C:/path/to/file.wav" --output-dir "C:/reports"
```

اجرای دسته‌ای روی یک پوشه (تشخیص خودکار CPU/GPU):
```bash
python detectLanguage.py --directory "C:/path/to/audio" --output-dir "C:/reports"
```

نمونه با GPU، انتخاب کارت 0 و مدل دقیق‌تر:
```bash
python detectLanguage.py --directory "C:/path/to/audio" --device cuda --device-id 0 --model-size large-v3 --compute-type float16
```

غیرفعال‌کردن VAD (در صورت نیاز):
```bash
python detectLanguage.py --directory "C:/path/to/audio" --no-vad
```

پارامترهای مهم:
- `--audio-file`: پردازش تک‌فایل (قابل ترکیب با `--directory`)
- `--directory`: پردازش دسته‌ای یک پوشه
- `--model-size`: اندازه/نسخه مدل (tiny/base/small/medium/large-v2/large-v3)
- `--device`: `cuda` یا `cpu` (پیش‌فرض: تشخیص خودکار)
- `--device-id`: شماره GPU هنگام استفاده از CUDA (پیش‌فرض: 0)
- `--compute-type`: نوع محاسبات (`float16` روی GPU معمولاً بهترین توازن دقت/سرعت)
- `--beam-size`: اندازه بیم برای دیکودینگ (پیش‌فرض: 5)
- `--no-vad`: خاموش کردن VAD
- `--output-dir`: مسیر ذخیره گزارش‌های JSON (اگر تعیین نشود کنار فایل ورودی ذخیره می‌شود)

---

### قالب خروجی JSON

برای هر فایل صوتی، یک فایل مانند `example.language_intervals.json` تولید می‌شود:

```json
{
  "audio": "C:/path/to/audio/example.mp3",
  "intervals": [
    {
      "language": "fa",
      "start_time": 0.0,
      "end_time": 12.34,
      "text": "..."
    },
    {
      "language": "ar",
      "start_time": 12.34,
      "end_time": 25.68,
      "text": "..."
    }
  ]
}
```

---

### نکات و عیب‌یابی

- برای بهترین دقت فارسی/عربی از `--model-size large-v3` روی GPU استفاده کنید.
- اگر سرعت مهم است، مدل‌های کوچک‌تر (مثلاً `small`/`base`) سریع‌تر هستند.
- اولین اجرا مدل را دانلود می‌کند؛ اطمینان از دسترسی اینترنت.
- چند GPU: در حال حاضر می‌توانید چند فرآیند همزمان با `--device-id`های متفاوت اجرا کنید.
- اگر خطای CUDA گرفتید، نسخه PyTorch و درایور/Runtime CUDA را بررسی کنید.

---

## پایگاه‌داده و ساختار جداول

- `audio_files`: مسیر فایل اصلی، مدت زمان، وضعیت پردازش.
- `segments`: جدول قدیمی برای پشتیبانی قبلی (در هر عملیات همچنان پر می‌شود).
- `language_segments`: جدول جدیدی که به `audio_files` ارجاع می‌دهد و در صورت نیاز با `segments` لینک می‌شود (`legacy_segment_id`).

هر بار که گزارشی پردازش می‌شود، یک رکورد در `audio_files` ثبت/به‌روزرسانی شده و تمام بازه‌ها در `language_segments` (به همراه مسیر تکه صوتی و مسیر گزارش) ذخیره می‌شوند. کلیدهای خارجی فعال هستند و می‌توانید روی `audio_file_id` یا `language` ایندکس بگیرید.

---

## جریان کامل (تک‌فایل یا دسته‌ای)

### 1) تشخیص بازه‌های زبانی
```bash
python detectLanguage.py --audio-file "C:/audio/clip.wav" --output-dir "C:/reports"
# یا
python detectLanguage.py --directory "C:/audio/batch" --output-dir "C:/reports"
```

### 2) برش صوت و درج دیتابیس

- اجرای تکی:
```bash
python split_and_store.py --report-file "C:/reports/clip.language_intervals.json" --output-audio-dir "C:/segments/audio" --db-path "C:/segments/segments.db"
```

- اجرای دسته‌ای:
```bash
python split_and_store.py --reports-dir "C:/reports" --output-audio-dir "C:/segments/audio" --db-path "C:/segments/segments.db"
```

این اسکریپت برای هر بازه‌، تکه صوتی را با `ffmpeg` می‌سازد و رکوردهای جداول `segments` و `language_segments` را درج می‌کند.

### 3) خروجی جاب‌های زیرنویس
```bash
python export_jobs.py --db-path "C:/segments/segments.db" --source-like "%clip%" --out-jsonl "C:/jobs/clip.jsonl"
```
خروجی JSONL/CSV برای ارسال به سیستم زیرنویس‌ساز. می‌توانید فیلتر زبان (`--lang fa`) نیز اضافه کنید.

### 4) تولید زیرنویس‌های هر تکه
- این مرحله در خارج از این پوشه انجام می‌شود (مثلاً با اسکریپت `Subtitle-Generator`). فرض می‌کنیم برای هر فایل صوتی تکه‌شده یک `.srt` تولید می‌شود (نام فایل SRT همان نام فایل صوتی + `.srt`).

### 5) تجمیع SRT نهایی
```bash
python merge_srt.py --db-path "C:/segments/segments.db" --source-like "%clip%" --srt-dir "C:/segments/srts" --out-srt "C:/segments/clip.final.srt"
```
این اسکریپت بر اساس `start_time` اصلی، آفست‌ها را اعمال کرده و یک SRT مرتب و یکپارچه تولید می‌کند.

---

## نکات تکمیلی

- `ffmpeg` باید در PATH سیستم باشد تا برش صوتی کار کند.
- برای پردازش به صورت موازی می‌توانید:
  - چند بار `detectLanguage.py` را با GPUهای مختلف (`--device-id`) اجرا کنید.
  - مرحله برش و خروجی جاب‌ها را در چند فرآیند جدا با فیلترهای متفاوت (`--source-like`) تقسیم کنید.
- دیتابیس SQLite قابل مشاهده با هر ابزار (مثلاً `DB Browser for SQLite`) است تا بتوانید رکوردها را بررسی یا گزارش‌های سفارشی تولید کنید.


