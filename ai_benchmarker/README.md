# AI Benchmarker

ماژول پایتونی مستقل برای بنچ‌مارک و ارزیابی خروجی‌های Transcription هوش مصنوعی.

## قابلیت‌ها

- محاسبه **WER** (Word Error Rate)
- شباهت **N-gram** (بی‌گرام و تری‌گرام)
- شباهت **LCS** (Longest Common Subsequence)
- ذخیره‌سازی نتایج با **SQLAlchemy** (SQLite پیش‌فرض)
- API با **FastAPI**

## نصب

```bash
cd ai_benchmarker
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

یا:

```bash
pip install -r requirements.txt
pip install -e .
```

## پیکربندی

فایل `.env` را از نمونه بسازید:

```bash
cp .env.example .env
```

| متغیر | پیش‌فرض | توضیح |
|-------|---------|-------|
| `DATABASE_URL` | `sqlite:///./ai_benchmarker.db` | آدرس دیتابیس |
| `APP_HOST` | `0.0.0.0` | آدرس bind سرور |
| `APP_PORT` | `8090` | پورت سرور |
| `APP_LOG_LEVEL` | `INFO` | سطح لاگ |

## اجرای API

```bash
uvicorn ai_benchmarker.app:app --host 0.0.0.0 --port 8090 --reload
```

## Seed اولیه AudioMaster

قبل از ثبت Transcription، رکورد `AudioMaster` باید وجود داشته باشد:

```python
from ai_benchmarker.database import get_session_factory, init_db, seed_audio_master

init_db()
session = get_session_factory()()
seed_audio_master(
    session,
    audio_guid="audio-001",
    file_name="lecture-01.wav",
    approved_text="متن تأییدشده مرجع",
)
session.close()
```

## مثال‌های API

### ثبت Transcription

```bash
curl -X POST http://localhost:8090/api/v1/transcription \
  -H "Content-Type: application/json" \
  -d '{
    "audio_guid": "audio-001",
    "model_name": "whisper-large-v3",
    "raw_text": "متن تولیدشده توسط مدل"
  }'
```

### مقایسه دو Transcription

```bash
curl -X POST http://localhost:8090/api/v1/compare \
  -H "Content-Type: application/json" \
  -d '{
    "ref_id": 1,
    "hyp_id": 2
  }'
```

### Health check

```bash
curl http://localhost:8090/health
```

## استفاده از هسته (بدون API)

```python
from ai_benchmarker import AIBenchmark

benchmarker = AIBenchmark()
metrics = benchmarker.evaluate("reference.txt", "hypothesis.txt")
print(metrics)
```

## تست

```bash
pytest
```

## ساختار پروژه

```
ai_benchmarker/
├── ai_benchmarker/
│   ├── core.py       # AIBenchmark
│   ├── storage.py    # مدل‌های SQLAlchemy
│   ├── database.py   # engine و session
│   ├── config.py     # تنظیمات
│   ├── schemas.py    # Pydantic models
│   └── app.py        # FastAPI
└── tests/
```
