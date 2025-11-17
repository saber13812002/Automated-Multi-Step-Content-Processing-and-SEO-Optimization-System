# راهنمای راه‌اندازی محیط Stage

این راهنما برای تنظیم محیط Stage (تست و توسعه) کنار محیط Production است.

## مشکلات رایج و راه‌حل‌ها

### مشکل 1: Collection پیدا نشد

**خطا:**
```
❌ Collection 'book_pages' not found in ChromaDB. 
Available collections: book_pages_full_embedding_provider_none_01, book_pages_full_embedding_provider_none, book_pages_mini
```

**راه‌حل:**

#### گزینه 1: استفاده از Collection موجود (سریع)

فایل `.env` را ویرایش کنید و یکی از collections موجود را انتخاب کنید:

```bash
cd ~/saberprojects/automated-dev/export-sql-chromadb
nano .env
```

مقدار `CHROMA_COLLECTION` را تغییر دهید:

```env
# استفاده از collection موجود
CHROMA_COLLECTION=book_pages_mini
# یا
CHROMA_COLLECTION=book_pages_full_embedding_provider_none
```

#### گزینه 2: ایجاد Collection جدید برای Stage (پیشنهادی)

برای جداسازی کامل Stage از Production، یک collection جدید بسازید:

```bash
# استفاده از یکی از collections موجود به عنوان منبع
# یا scrape جدید با مدل قوی‌تر
python export-sql-backup-to-chromadb.py \
  --sql-path book_pages.sql \
  --collection book_pages_stage \
  --host localhost \
  --port 8000 \
  --embedding-provider openai \
  --reset
```

سپس در `.env`:
```env
CHROMA_COLLECTION=book_pages_stage
```

### مشکل 2: OPENAI_API_KEY تنظیم نشده

**خطا:**
```
❌ OPENAI_API_KEY is not set. Please set OPENAI_API_KEY in your .env file to enable embedding generation.
```

**راه‌حل:**

1. کلید OpenAI خود را دریافت کنید (از https://platform.openai.com/api-keys)

2. در فایل `.env` اضافه کنید:

```bash
nano .env
```

```env
OPENAI_API_KEY=sk-your-api-key-here
```

3. یا به صورت موقت در shell:

```bash
export OPENAI_API_KEY=sk-your-api-key-here
```

## تنظیم کامل فایل `.env` برای Stage

نمونه فایل `.env` کامل برای محیط Stage:

```env
# App Configuration
APP_HOST=0.0.0.0
APP_PORT=8081
APP_LOG_LEVEL=INFO

# ChromaDB Configuration
CHROMA_HOST=localhost
CHROMA_PORT=8000
CHROMA_SSL=false
CHROMA_API_KEY=
CHROMA_COLLECTION=book_pages_stage
CHROMA_ANONYMIZED_TELEMETRY=False

# Embedding Configuration
EMBEDDING_PROVIDER=openai
EMBEDDING_MODEL=text-embedding-3-small
OPENAI_API_KEY=sk-your-api-key-here

# Redis Configuration (اختیاری)
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0
REDIS_PASSWORD=
# یا
# REDIS_URL=redis://localhost:6379/0
```

## مراحل راه‌اندازی Stage Environment

### 1. Clone پروژه (اگر هنوز انجام نشده)

```bash
cd ~/saberprojects
git clone <repo-url> automated-dev
cd automated-dev/export-sql-chromadb
```

### 2. ایجاد Virtual Environment

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r web_service/requirements.txt
```

### 3. تنظیم فایل `.env`

```bash
# کپی از production (اگر وجود دارد) یا ایجاد جدید
cp ../automated-Multi-Step-Content-Processing-and-SEO-Optimization-System/export-sql-chromadb/.env .env

# ویرایش برای Stage
nano .env
```

تغییرات مهم:
- `APP_PORT=8081` (متفاوت از production که 8080 است)
- `CHROMA_COLLECTION=book_pages_stage` (collection جداگانه)
- `OPENAI_API_KEY=...` (مطمئن شوید تنظیم شده)

### 4. ایجاد Collection برای Stage (اختیاری)

اگر می‌خواهید collection جداگانه داشته باشید:

```bash
# استفاده از داده‌های موجود (کپی از production collection)
# یا scrape جدید با مدل قوی‌تر

python export-sql-backup-to-chromadb.py \
  --sql-path book_pages.sql \
  --collection book_pages_stage \
  --host localhost \
  --port 8000 \
  --embedding-provider openai \
  --reset
```

### 5. تست سرویس

```bash
# تست دستی
uvicorn web_service.app:app --host 0.0.0.0 --port 8081 --reload

# یا با systemd service
sudo systemctl start chroma-search-api-stage.service
sudo systemctl status chroma-search-api-stage.service
```

### 6. بررسی Health Check

```bash
curl http://localhost:8081/health
```

## تفاوت‌های Stage و Production

| تنظیمات | Production | Stage |
|---------|-----------|-------|
| **Port** | 8080 | 8081 |
| **Collection** | `book_pages` | `book_pages_stage` |
| **Path** | `~/saberprojects/automated-Multi-Step-Content-Processing-and-SEO-Optimization-System/export-sql-chromadb` | `~/saberprojects/automated-dev/export-sql-chromadb` |
| **Service Name** | `chroma-search-api-uvicorn.service` | `chroma-search-api-stage.service` |

## Migration از Stage به Production

بعد از تست موفق در Stage، برای انتقال داده‌ها به Production:

### روش 1: استفاده از Collection مشترک (ساده)

اگر می‌خواهید Stage و Production از همان collection استفاده کنند:

```env
# در Stage .env
CHROMA_COLLECTION=book_pages_mini  # یا هر collection موجود
```

### روش 2: کپی Collection (پیشرفته)

برای کپی کامل collection از Stage به Production، از ChromaDB API یا script مخصوص استفاده کنید.

## عیب‌یابی

### بررسی Collection‌های موجود

```bash
python check_chroma_config.py --list-collections \
  --host localhost \
  --port 8000
```

### بررسی تنظیمات

```bash
python check_chroma_config.py --print-config
```

### تست اتصال

```bash
curl http://localhost:8000/api/v2/heartbeat
```

## نکات مهم

1. **Collection مشترک**: اگر Stage و Production از همان ChromaDB استفاده می‌کنند، می‌توانند collection مشترک داشته باشند (فقط خواندنی)
2. **Port متفاوت**: حتماً port Stage (8081) را متفاوت از Production (8080) نگه دارید
3. **API Key**: مطمئن شوید `OPENAI_API_KEY` در `.env` تنظیم شده
4. **Service Name**: برای Stage یک service جداگانه با نام `chroma-search-api-stage.service` بسازید

