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

اجرای پردازش یک پوشه از فایل‌های صوتی (تشخیص خودکار CPU/GPU):
```bash
python detectLanguage.py --directory "C:/path/to/audio"
```

نمونه با GPU، انتخاب کارت 0 و مدل دقیق‌تر:
```bash
python detectLanguage.py --directory "C:/path/to/audio" --device cuda --device-id 0 --model-size large-v3 --compute-type float16
```

ذخیره خروجی JSON در مسیر دلخواه:
```bash
python detectLanguage.py --directory "C:/path/to/audio" --output-dir "C:/path/to/reports"
```

غیرفعال‌کردن VAD (در صورت نیاز):
```bash
python detectLanguage.py --directory "C:/path/to/audio" --no-vad
```

پارامترهای مهم:
- `--model-size`: اندازه/نسخه مدل (tiny/base/small/medium/large-v2/large-v3)
- `--device`: `cuda` یا `cpu` (پیش‌فرض: تشخیص خودکار)
- `--device-id`: شماره GPU هنگام استفاده از CUDA (پیش‌فرض: 0)
- `--compute-type`: نوع محاسبات (`float16` روی GPU معمولاً بهترین توازن دقت/سرعت)
- `--beam-size`: اندازه بیم برای دیکودینگ (پیش‌فرض: 5)
- `--no-vad`: خاموش کردن VAD
- `--output-dir`: مسیر ذخیره گزارش‌های JSON

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


