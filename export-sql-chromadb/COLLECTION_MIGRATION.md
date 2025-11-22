# راهنمای انتقال Collection های ChromaDB بین Instance ها

این راهنما برای زمانی است که شما دو instance از این پروژه دارید (مثلاً staging و production) و می‌خواهید collection های ChromaDB را از یکی به دیگری منتقل کنید.

## بررسی ساختار Instance ها

### 1. SQLite Database

هر instance در پوشه خودش SQLite database خودش را دارد:

- **مسیر:** `export-sql-chromadb/search_history.db`
- **محتوای:** تاریخچه جستجوها، export jobs، query approvals، embedding models، و غیره
- **نتیجه:** هر instance SQLite مستقل خودش را دارد ✅

### 2. ChromaDB Collections

ChromaDB collection ها بسته به تنظیمات می‌توانند:

#### حالت 1: استفاده از ChromaDB Server (HttpClient)
- Collection ها در سرور ChromaDB ذخیره می‌شوند
- هر دو instance می‌توانند به همان سرور متصل شوند
- یا می‌توانند به سرورهای مختلف متصل شوند

#### حالت 2: استفاده از PersistentClient
- Collection ها در پوشه محلی ذخیره می‌شوند (`CHROMA_PERSIST_DIR`)
- هر instance می‌تواند پوشه persist خودش را داشته باشد

## روش انتقال Collection ها

### روش 1: استفاده از اسکریپت `copy_collections.py` (پیشنهادی)

این اسکریپت collection ها را از source به destination کپی می‌کند بدون اینکه روی داده‌های موجود تأثیر بگذارد.

#### مثال 1: کپی از Staging به Production (هر دو از HttpClient استفاده می‌کنند)

```bash
cd export-sql-chromadb

python copy_collections.py \
    --source-host localhost \
    --source-port 8000 \
    --dest-host localhost \
    --dest-port 8000 \
    --collection book_pages_stage \
    --dest-collection book_pages_prod \
    --batch-size 1000
```

#### مثال 2: کپی از PersistentClient به HttpClient

```bash
python copy_collections.py \
    --source-persist-dir /path/to/staging/chroma \
    --dest-host localhost \
    --dest-port 8000 \
    --collection book_pages \
    --dest-collection book_pages_prod
```

#### مثال 3: کپی از HttpClient به PersistentClient

```bash
python copy_collections.py \
    --source-host localhost \
    --source-port 8000 \
    --dest-persist-dir /path/to/production/chroma \
    --collection book_pages_stage \
    --dest-collection book_pages_prod
```

#### مثال 4: کپی بین دو PersistentClient

```bash
python copy_collections.py \
    --source-persist-dir /path/to/staging/chroma \
    --dest-persist-dir /path/to/production/chroma \
    --collection book_pages \
    --dest-collection book_pages_prod
```

### بررسی Collection های موجود

قبل از کپی، می‌توانید collection های موجود را بررسی کنید:

```bash
# لیست collection های source
python copy_collections.py \
    --source-host localhost \
    --source-port 8000 \
    --list-source

# لیست collection های destination
python copy_collections.py \
    --dest-host localhost \
    --dest-port 8000 \
    --list-dest
```

### استفاده از API Key (اگر نیاز باشد)

```bash
python copy_collections.py \
    --source-host localhost \
    --source-port 8000 \
    --source-api-key your-source-api-key \
    --dest-host localhost \
    --dest-port 8000 \
    --dest-api-key your-dest-api-key \
    --collection book_pages_stage \
    --dest-collection book_pages_prod
```

## روش 2: استفاده از ChromaDB API مستقیم

اگر می‌خواهید از API استفاده کنید:

```python
import chromadb

# Source client
source_client = chromadb.HttpClient(host="localhost", port=8000)
source_collection = source_client.get_collection("book_pages_stage")

# Destination client
dest_client = chromadb.HttpClient(host="localhost", port=8000)
dest_collection = dest_client.get_collection("book_pages_prod")

# Copy data
results = source_collection.get(include=["documents", "metadatas", "embeddings"])
dest_collection.add(
    ids=results["ids"],
    documents=results["documents"],
    metadatas=results["metadatas"],
    embeddings=results["embeddings"],
)
```

## نکات مهم

### 1. جدا بودن SQLite Database ها

✅ **تایید شده:** هر instance SQLite database خودش را دارد:
- Staging: `~/staging/export-sql-chromadb/search_history.db`
- Production: `~/production/export-sql-chromadb/search_history.db`

این database ها شامل:
- تاریخچه جستجوها
- Export jobs
- Query approvals
- Embedding models metadata
- API tokens و users

**نتیجه:** نیازی به کپی SQLite نیست، هر instance داده‌های خودش را دارد.

### 2. Collection های ChromaDB

Collection های ChromaDB شامل:
- Documents (متن صفحات)
- Embeddings (بردارهای معنایی)
- Metadatas (اطلاعات اضافی)

**نکته:** اگر می‌خواهید collection ها را به اشتراک بگذارید، می‌توانید هر دو instance را به همان ChromaDB server متصل کنید.

### 3. بدون Side Effect

اسکریپت `copy_collections.py`:
- ✅ فقط داده‌ها را کپی می‌کند
- ✅ روی collection های موجود در destination تأثیر نمی‌گذارد (اضافه می‌کند، نه overwrite)
- ✅ اگر collection در destination وجود داشته باشد، داده‌ها به آن اضافه می‌شوند
- ✅ Source collection را تغییر نمی‌دهد

### 4. Performance

- برای collection های بزرگ، از `--batch-size` استفاده کنید
- پیشنهاد: `--batch-size 1000` برای collection های متوسط
- برای collection های خیلی بزرگ: `--batch-size 5000`

## سناریوهای رایج

### سناریو 1: Staging و Production از همان ChromaDB Server استفاده می‌کنند

در این حالت، نیازی به کپی نیست. فقط collection name را در `.env` تنظیم کنید:

**Staging `.env`:**
```env
CHROMA_COLLECTION=book_pages_stage
```

**Production `.env`:**
```env
CHROMA_COLLECTION=book_pages_prod
```

### سناریو 2: Staging و Production از ChromaDB Server های مختلف استفاده می‌کنند

از اسکریپت `copy_collections.py` استفاده کنید:

```bash
python copy_collections.py \
    --source-host staging-chroma-server \
    --source-port 8000 \
    --dest-host production-chroma-server \
    --dest-port 8000 \
    --collection book_pages_stage \
    --dest-collection book_pages_prod
```

### سناریو 3: Staging از PersistentClient و Production از HttpClient استفاده می‌کند

```bash
python copy_collections.py \
    --source-persist-dir /path/to/staging/chroma \
    --dest-host production-chroma-server \
    --dest-port 8000 \
    --collection book_pages \
    --dest-collection book_pages_prod
```

## عیب‌یابی

### خطا: Collection not found

```bash
# بررسی collection های موجود
python copy_collections.py --source-host localhost --source-port 8000 --list-source
```

### خطا: Connection failed

- بررسی کنید که ChromaDB server در حال اجرا باشد
- بررسی کنید که host و port درست باشند
- اگر از SSL استفاده می‌کنید، `--source-ssl` یا `--dest-ssl` را اضافه کنید

### خطا: Permission denied

- بررسی کنید که به پوشه `persist_directory` دسترسی دارید
- اگر از API key استفاده می‌کنید، بررسی کنید که درست باشد

## خلاصه

1. ✅ **SQLite:** هر instance database خودش را دارد - نیازی به کپی نیست
2. ✅ **ChromaDB Collections:** می‌توانید با `copy_collections.py` کپی کنید
3. ✅ **بدون Side Effect:** اسکریپت فقط کپی می‌کند، چیزی را overwrite نمی‌کند
4. ✅ **سریع و ساده:** یک دستور ساده برای کپی کامل collection

