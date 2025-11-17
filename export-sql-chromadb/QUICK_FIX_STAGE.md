# راهنمای سریع حل مشکل Stage Environment

## مشکل فعلی شما

از لاگ‌ها مشخص است:
1. ❌ Collection `book_pages` پیدا نشده
2. ❌ `OPENAI_API_KEY` تنظیم نشده

## راه‌حل سریع (2 دقیقه)

### مرحله 1: تنظیم Collection

```bash
cd ~/saberprojects/automated-dev/export-sql-chromadb
nano .env
```

یکی از این گزینه‌ها را انتخاب کنید:

**گزینه A: استفاده از collection موجود (سریع‌ترین)**
```env
CHROMA_COLLECTION=book_pages_mini
```

**گزینه B: استفاده از collection بزرگتر**
```env
CHROMA_COLLECTION=book_pages_full_embedding_provider_none
```

### مرحله 2: تنظیم OpenAI API Key

در همان فایل `.env`:

```env
OPENAI_API_KEY=sk-your-actual-api-key-here
```

> **نکته:** کلید OpenAI را از https://platform.openai.com/api-keys دریافت کنید

### مرحله 3: ذخیره و تست

```bash
# ذخیره فایل (Ctrl+X, سپس Y, سپس Enter)

# تست سرویس
source .venv/bin/activate
uvicorn web_service.app:app --host 0.0.0.0 --port 8081
```

## فایل `.env` کامل (نمونه)

```env
# App
APP_HOST=0.0.0.0
APP_PORT=8081
APP_LOG_LEVEL=INFO

# ChromaDB
CHROMA_HOST=localhost
CHROMA_PORT=8000
CHROMA_SSL=false
CHROMA_API_KEY=
CHROMA_COLLECTION=book_pages_mini
CHROMA_ANONYMIZED_TELEMETRY=False

# Embedding
EMBEDDING_PROVIDER=openai
EMBEDDING_MODEL=text-embedding-3-small
OPENAI_API_KEY=sk-your-key-here

# Redis
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0
```

## بررسی موفقیت

بعد از راه‌اندازی، باید این پیام را ببینید:

```
✅ ChromaDB heartbeat successful
✅ Collection 'book_pages_mini' found with X documents
✅ Redis connection successful
✅ Embedding configuration valid
```

سپس تست کنید:

```bash
curl http://localhost:8081/health
```

## اگر هنوز خطا دارید

1. **بررسی فایل `.env`:**
   ```bash
   cat .env | grep -E "CHROMA_COLLECTION|OPENAI_API_KEY"
   ```

2. **بررسی collections موجود:**
   ```bash
   python check_chroma_config.py --list-collections --host localhost --port 8000
   ```

3. **تست دستی:**
   ```bash
   source .venv/bin/activate
   python -c "from web_service.config import get_settings; s = get_settings(); print(f'Collection: {s.chroma_collection}')"
   ```

## بعد از حل مشکل

برای راه‌اندازی با systemd service، به [STAGE_SETUP.md](STAGE_SETUP.md) مراجعه کنید.

