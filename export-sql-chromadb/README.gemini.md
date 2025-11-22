# راهنمای استفاده از Gemini Embeddings

این راهنما نحوه استفاده از مدل‌های Gemini برای تولید embeddings و جستجو را توضیح می‌دهد.

## 📋 فهرست مطالب

- [نصب وابستگی‌ها](#نصب-وابستگی‌ها)
- [تست Gemini](#تست-gemini)
- [تست OpenAI (اطمینان از خراب نشدن)](#تست-openai-اطمینان-از-خراب-نشدن)
- [استفاده در Export](#استفاده-در-export)
- [استفاده در Search](#استفاده-در-search)

---

## نصب وابستگی‌ها

```bash
pip install google-genai
```

---

## تست Gemini

برای تست اینکه Gemini درست کار می‌کند، یک export کوچک با فایل `book_pages_mini.sql` انجام دهید:

```bash
python export-sql-backup-to-chromadb.py \
  --sql-path book_pages_mini.sql \
  --collection book_pages_mini_gemini \
  --host 192.168.1.68 \
  --port 8000 \
  --embedding-provider gemini \
  --embedding-model gemini-embedding-001 \
  --gemini-api-key YOUR_GEMINI_API_KEY \
  --reset
```

**نکته:** `YOUR_GEMINI_API_KEY` را با کلید API واقعی Gemini خود جایگزین کنید.

یا می‌توانید از متغیر محیطی استفاده کنید:

```bash
export GEMINI_API_KEY=your_gemini_api_key_here
python export-sql-backup-to-chromadb.py \
  --sql-path book_pages_mini.sql \
  --collection book_pages_mini_gemini \
  --host 192.168.1.68 \
  --port 8000 \
  --embedding-provider gemini \
  --embedding-model gemini-embedding-001 \
  --reset
```

---

## تست OpenAI (اطمینان از خراب نشدن)

برای اطمینان از اینکه تغییرات OpenAI را خراب نکرده، همان دستور قبلی را با OpenAI اجرا کنید:

```bash
python export-sql-backup-to-chromadb.py \
  --sql-path book_pages_mini.sql \
  --collection book_pages_mini_openai \
  --host 192.168.1.68 \
  --port 8000 \
  --embedding-provider openai \
  --embedding-model text-embedding-3-small \
  --openai-api-key YOUR_OPENAI_API_KEY \
  --reset
```

اگر export با موفقیت انجام شد، یعنی OpenAI هنوز کار می‌کند.

---

## استفاده در Export

### Export کامل با Gemini

```bash
python export-sql-backup-to-chromadb.py \
  --sql-path book_pages.sql \
  --collection book_pages_gemini \
  --host 192.168.1.68 \
  --port 8000 \
  --embedding-provider gemini \
  --embedding-model gemini-embedding-001 \
  --gemini-api-key YOUR_GEMINI_API_KEY \
  --reset
```

### مدل‌های Gemini موجود

- `gemini-embedding-001` - مدل اصلی embedding
- `gemini-2.5-flash` - مدل سریع‌تر
- مدل‌های Gemini 3 (وقتی منتشر شوند)

---

## استفاده در Search

### تنظیمات Environment Variables

در فایل `.env` یا environment variables، این مقادیر را تنظیم کنید:

```bash
EMBEDDING_PROVIDER=gemini
EMBEDDING_MODEL=gemini-embedding-001
GEMINI_API_KEY=your_gemini_api_key_here
```

### استفاده در Web Service

وقتی Web Service را راه‌اندازی می‌کنید، به صورت خودکار از Gemini استفاده می‌کند:

```bash
cd web_service
uvicorn app:app --host 0.0.0.0 --port 8080
```

### استفاده در API Search

هنگام جستجو، سیستم به صورت خودکار از همان embedding provider و model که در export استفاده شده، استفاده می‌کند.

**مثال درخواست Search:**

```bash
curl -X POST http://localhost:8080/search \
  -H "Content-Type: application/json" \
  -d '{
    "query": "متن جستجو",
    "top_k": 10
  }'
```

اگر `model_id` مشخص کنید، از همان مدل Gemini که export شده استفاده می‌کند.

---

## نکات مهم

1. **API Key:** همیشه `GEMINI_API_KEY` را در environment variables یا `.env` تنظیم کنید
2. **مدل یکسان:** برای جستجوی دقیق، از همان مدل Gemini که در export استفاده شده، استفاده کنید
3. **Collection:** هر collection با یک مدل embedding خاص export می‌شود - مطمئن شوید collection درست را جستجو می‌کنید

---

## عیب‌یابی

### خطا: "google-genai library is required"

```bash
pip install google-genai
```

### خطا: "GEMINI_API_KEY is required"

مطمئن شوید که:
- `GEMINI_API_KEY` در environment variables تنظیم شده
- یا `--gemini-api-key` در دستور export مشخص شده

### خطا در Search

مطمئن شوید که:
- `EMBEDDING_PROVIDER=gemini` در `.env` تنظیم شده
- `GEMINI_API_KEY` در `.env` تنظیم شده
- Collection با همان مدل Gemini export شده باشد

---

## مثال کامل

```bash
# 1. تنظیم API Key
export GEMINI_API_KEY=your_key_here

# 2. Export با Gemini
python export-sql-backup-to-chromadb.py \
  --sql-path book_pages_mini.sql \
  --collection book_pages_mini_gemini \
  --host 192.168.1.68 \
  --port 8000 \
  --embedding-provider gemini \
  --embedding-model gemini-embedding-001 \
  --reset

# 3. تنظیم .env برای Web Service
echo "EMBEDDING_PROVIDER=gemini" >> web_service/.env
echo "EMBEDDING_MODEL=gemini-embedding-001" >> web_service/.env
echo "GEMINI_API_KEY=your_key_here" >> web_service/.env

# 4. راه‌اندازی Web Service
cd web_service
uvicorn app:app --host 0.0.0.0 --port 8080
```

---

> 📖 برای راهنمای کامل پروژه، به [README.md](README.md) مراجعه کنید.

