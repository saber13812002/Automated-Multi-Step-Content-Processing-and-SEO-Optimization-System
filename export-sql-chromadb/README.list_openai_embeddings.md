# راهنمای استفاده از `list_openai_embeddings.py`

این اسکریپت برای لیست کردن و نمایش اطلاعات تمام کالکشن‌های امبدینگ OpenAI در ChromaDB طراحی شده است.

> 📖 برای راهنمای کامل پروژه، به [README.md](README.md) مراجعه کنید.

## 📋 فهرست مطالب

- [نصب و راه‌اندازی](#نصب-و-راه‌اندازی)
- [استفاده پایه](#استفاده-پایه)
- [گزینه‌های خط فرمان](#گزینه‌های-خط-فرمان)
- [مثال‌های استفاده](#مثال‌های-استفاده)
- [خروجی نمونه](#خروجی-نمونه)
- [نکات مهم](#نکات-مهم)

---

## نصب و راه‌اندازی

### پیش‌نیازها

- Python 3.10 یا جدیدتر
- دسترسی به ChromaDB (لوکال یا از طریق شبکه)
- کتابخانه‌های مورد نیاز (از `requirements.txt` یا `web_service/requirements.txt`)

### نصب وابستگی‌ها

```bash
# فعال‌سازی محیط مجازی (اگر دارید)
source .venv/bin/activate  # Linux/Mac
# یا
.venv\Scripts\activate     # Windows

# نصب وابستگی‌ها (اگر قبلاً نصب نشده)
pip install chromadb
```

---

## استفاده پایه

### ساده‌ترین حالت

```bash
python3 list_openai_embeddings.py
```

این دستور تمام کالکشن‌هایی که نام آن‌ها شامل "openai" است را در ChromaDB پیدا می‌کند و نمایش می‌دهد.

### استفاده با اطلاعات دیتابیس (پیشنهادی)

```bash
python3 list_openai_embeddings.py --include-db-info
```

این دستور اطلاعات کامل از دیتابیس SQLite (جداول `embedding_models` و `export_jobs`) را نیز نمایش می‌دهد و اطلاعات دقیق‌تری ارائه می‌کند.

---

## گزینه‌های خط فرمان

### گزینه‌های اتصال به ChromaDB

| گزینه | توضیحات | پیش‌فرض |
|-------|---------|---------|
| `--host` | آدرس سرور ChromaDB | از متغیر محیطی `CHROMA_HOST` یا `localhost` |
| `--port` | پورت ChromaDB | از متغیر محیطی `CHROMA_PORT` یا `8000` |
| `--persist-directory` | مسیر دایرکتوری برای Persistent Client | - |
| `--api-key` | کلید API برای ChromaDB | از متغیر محیطی `CHROMA_API_KEY` |
| `--ssl` | استفاده از HTTPS | `false` |

### گزینه‌های نمایش

| گزینه | توضیحات |
|-------|---------|
| `--include-db-info` | نمایش اطلاعات از دیتابیس (مدل‌ها و jobها) |
| `--active-only` | نمایش فقط مدل‌های فعال |
| `--detailed` | نمایش اطلاعات تفصیلی metadata |

---

## مثال‌های استفاده

### مثال 1: لیست ساده

```bash
python3 list_openai_embeddings.py
```

**خروجی:**
- لیست کالکشن‌هایی که نام آن‌ها شامل "openai" است
- تعداد مستندات هر کالکشن

### مثال 2: با اطلاعات کامل از دیتابیس

```bash
python3 list_openai_embeddings.py --include-db-info
```

**خروجی:**
- لیست کامل کالکشن‌های OpenAI
- اطلاعات مدل (provider, model name)
- وضعیت فعال/غیرفعال
- رنگ اختصاصی
- اطلاعات آخرین job
- آمار کلی

### مثال 3: اتصال به ChromaDB راه‌دور

```bash
python3 list_openai_embeddings.py \
  --host 192.168.1.68 \
  --port 8000 \
  --include-db-info
```

### مثال 4: فقط مدل‌های فعال

```bash
python3 list_openai_embeddings.py \
  --include-db-info \
  --active-only
```

### مثال 5: با اطلاعات تفصیلی

```bash
python3 list_openai_embeddings.py \
  --include-db-info \
  --detailed
```

### مثال 6: استفاده از Persistent Client

```bash
python3 list_openai_embeddings.py \
  --persist-directory ./chroma-store \
  --include-db-info
```

### مثال 7: با کلید API

```bash
python3 list_openai_embeddings.py \
  --host 192.168.1.68 \
  --port 8000 \
  --api-key "your-api-key" \
  --include-db-info
```

---

## خروجی نمونه

### خروجی با `--include-db-info`

```
🔍 Connecting to ChromaDB...
✅ Connected to ChromaDB

📋 Listing all collections in ChromaDB...
   Found 9 collection(s)

📊 Getting OpenAI embedding information from database...
   Found 2 OpenAI model(s) in database

================================================================================
📊 Found 2 OpenAI Embedding Collection(s)

================================================================================

[1] Collection: book_pages_mini_openai
    Documents: 107
    Provider: openai
    Model: text-embedding-3-small
    Status: 🟢 Active
    Color: #3B82F6
    Last Completed: 2025-01-22 10:30:45
    Total Documents (from job): 107
    Latest Job ID: 13
    Job Status: completed
    Job Started: 2025-01-22 10:25:12
--------------------------------------------------------------------------------

[2] Collection: book_pages_openai_3large
    Documents: 247,229
    Provider: openai
    Model: text-embedding-3-large
    Status: 🟢 Active
    Color: #10B981
    Last Completed: 2025-01-22 15:45:30
    Total Documents (from job): 247,229
    Latest Job ID: 15
    Job Status: completed
    Job Started: 2025-01-22 14:20:00
--------------------------------------------------------------------------------

📈 Summary:
   Total Collections: 2
   Active Collections: 2
   Total Documents: 247,336
```

### خروجی ساده (بدون `--include-db-info`)

```
🔍 Connecting to ChromaDB...
✅ Connected to ChromaDB

📋 Listing all collections in ChromaDB...
   Found 9 collection(s)

🔍 Identifying OpenAI collections...

================================================================================
📊 Found 2 OpenAI Embedding Collection(s)

================================================================================

[1] Collection: book_pages_mini_openai
    Documents: 107
--------------------------------------------------------------------------------

[2] Collection: book_pages_openai_3large
    Documents: 247,229
--------------------------------------------------------------------------------

📈 Summary:
   Total Collections: 2
   Active Collections: 0
   Total Documents: 247,336
```

---

## نکات مهم

### 1. استفاده از `--include-db-info`

- **توصیه می‌شود** همیشه از `--include-db-info` استفاده کنید
- این گزینه اطلاعات دقیق‌تری از دیتابیس SQLite می‌گیرد
- شامل اطلاعات مدل، وضعیت فعال/غیرفعال، و jobها می‌شود

### 2. شناسایی کالکشن‌های OpenAI

- **بدون `--include-db-info`**: فقط کالکشن‌هایی که نام آن‌ها شامل "openai" است شناسایی می‌شوند
- **با `--include-db-info`**: از جدول `embedding_models` در دیتابیس استفاده می‌کند که دقیق‌تر است

### 3. متغیرهای محیطی

می‌توانید تنظیمات را در فایل `.env` یا environment variables قرار دهید:

```bash
export CHROMA_HOST=192.168.1.68
export CHROMA_PORT=8000
export CHROMA_API_KEY="your-api-key"
```

### 4. خطاهای احتمالی

- **خطای اتصال**: مطمئن شوید ChromaDB در حال اجرا است
- **خطای دیتابیس**: اگر `--include-db-info` استفاده می‌کنید، مطمئن شوید فایل `search_history.db` وجود دارد
- **کالکشن خالی**: اگر کالکشنی پیدا نشد، ممکن است هنوز export انجام نشده باشد

### 5. کارایی

- برای تعداد زیاد کالکشن‌ها، ممکن است کمی زمان ببرد
- استفاده از `--active-only` می‌تواند خروجی را محدود کند

---

## استفاده در اسکریپت‌ها

می‌توانید از این اسکریپت در اسکریپت‌های bash یا Python استفاده کنید:

```bash
#!/bin/bash
# Get list of OpenAI collections
collections=$(python3 list_openai_embeddings.py --include-db-info --active-only | grep "Collection:" | awk '{print $2}')

for collection in $collections; do
    echo "Processing: $collection"
    # Your processing logic here
done
```

---

## عیب‌یابی

### مشکل: "Could not import web_service modules"

**راه حل:**
- مطمئن شوید در پوشه `export-sql-chromadb` هستید
- یا از `--include-db-info` استفاده نکنید

### مشکل: "Failed to connect to ChromaDB"

**راه حل:**
- بررسی کنید ChromaDB در حال اجرا است
- آدرس و پورت را بررسی کنید
- اگر از API key استفاده می‌کنید، آن را بررسی کنید

### مشکل: "No OpenAI embeddings found"

**راه حل:**
- مطمئن شوید export با OpenAI انجام شده است
- از `--include-db-info` استفاده کنید
- بررسی کنید نام کالکشن شامل "openai" است یا در دیتابیس ثبت شده است

---

## لینک‌های مرتبط

- [README.md](README.md) - راهنمای اصلی پروژه
- [FEATURES.md](FEATURES.md) - فهرست ویژگی‌ها
- [README.web_service.md](README.web_service.md) - راهنمای Web Service
- [HUGGINGFACE_MODELS.md](HUGGINGFACE_MODELS.md) - راهنمای مدل‌های HuggingFace

---

**آخرین به‌روزرسانی**: 2025-01-22

