# راهنمای انتقال Export Job موفق بین Instance ها

این راهنما برای کپی یک export job موفق و embedding models مرتبط با آن از یک instance به instance دیگر است.

## ویژگی‌ها

- ✅ **تست Connection:** اول connection به source و destination را تست می‌کند
- ✅ **لیست Jobs:** فقط export jobs موفق (completed) را نمایش می‌دهد
- ✅ **انتخاب تعاملی:** کاربر می‌تواند job مورد نظر را انتخاب کند
- ✅ **جزئیات کامل:** اطلاعات کامل job و embedding models مرتبط را نمایش می‌دهد
- ✅ **کپی هوشمند:** job و embedding models مرتبط را کپی می‌کند
- ✅ **Backup خودکار:** قبل از کپی، از destination backup می‌گیرد

## استفاده

### حالت تعاملی (پیشنهادی)

```bash
cd export-sql-chromadb

python copy_export_job.py \
    --source-path /path/to/staging/export-sql-chromadb \
    --dest-path /path/to/production/export-sql-chromadb
```

**مثال واقعی:**
```bash
python copy_export_job.py \
    --source-path ~/saberprojects/automated-dev/export-sql-chromadb \
    --dest-path ~/saberprojects/automated-Multi-Step-Content-Processing-and-SEO-Optimization-System/export-sql-chromadb
```

```bash
python3 copy_export_job.py \
    --source-path ~/saberprojects/automated-Multi-Step-Content-Processing-and-SEO-Optimization-System/export-sql-chromadb \
    --dest-path ~/saberprojects/automated-dev/export-sql-chromadb 
```

### حالت مستقیم (با Job ID)

اگر می‌دانید کدام job را می‌خواهید:

```bash
python copy_export_job.py \
    --source-path /path/to/staging/export-sql-chromadb \
    --dest-path /path/to/production/export-sql-chromadb \
    --job-id 42
```

### بدون Backup

اگر نمی‌خواهید backup ایجاد شود:

```bash
python copy_export_job.py \
    --source-path /path/to/staging/export-sql-chromadb \
    --dest-path /path/to/production/export-sql-chromadb \
    --no-backup
```

### بدون تست Connection

اگر می‌خواهید تست connection را skip کنید:

```bash
python copy_export_job.py \
    --source-path /path/to/staging/export-sql-chromadb \
    --dest-path /path/to/production/export-sql-chromadb \
    --no-connection-test
```

## مراحل اجرا

### 1. تست Connection

اسکریپت اول connection به source و destination را تست می‌کند:

```
🔍 Testing connections...
✅ Source: Connection successful (found 15 export jobs)
✅ Destination: Connection successful (found 8 export jobs)
✅ Both connections successful!
```

### 2. نمایش لیست Jobs

لیست export jobs موفق نمایش داده می‌شود:

```
====================================================================================================
📋 Completed Export Jobs in Source (15 jobs)
====================================================================================================
#    ID     Collection                Provider     Model                          Completed
----------------------------------------------------------------------------------------------------
1    45     book_pages_stage          openai       text-embedding-3-small         2024-01-15 10:30:00
2    42     book_pages_mini           openai       text-embedding-3-small         2024-01-14 15:20:00
3    38     book_pages_full           huggingface  HooshvareLab/bert-base-pars... 2024-01-13 09:10:00
...
====================================================================================================
```

### 3. انتخاب Job

کاربر job مورد نظر را انتخاب می‌کند:

```
Select job number (1-15) or 'q' to quit: 2
```

### 4. نمایش جزئیات

جزئیات کامل job و embedding models مرتبط نمایش داده می‌شود:

```
====================================================================================================
📊 Job Details
====================================================================================================
ID:                    42
Collection:            book_pages_mini
Embedding Provider:    openai
Embedding Model:       text-embedding-3-small
Started At:            2024-01-14 14:00:00
Completed At:          2024-01-14 15:20:00
Duration:              4800.00 seconds
Total Records:         5000
Total Books:           50
Total Segments:        12000
Documents in Collection: 12000

📋 Related Embedding Models (1):
  - openai/text-embedding-3-small (Collection: book_pages_mini) ✅ Active
====================================================================================================
```

### 5. تایید و کپی

کاربر تایید می‌کند و job کپی می‌شود:

```
Copy this job and related models to destination? (y/n): y
📦 Creating backup: /path/to/production/export-sql-chromadb/search_history_backup_20240115_120000.db
✅ Backup created
✅ Copied export job: 42 -> 43
📋 Found 1 embedding model(s) to copy
  ✅ Copied embedding model: openai/text-embedding-3-small
🎉 Successfully copied job 42 and related models!
✅ Operation completed successfully!
```

## نحوه کار

### 1. Export Job

- اگر job در destination وجود نداشته باشد، با ID جدید کپی می‌شود
- اگر job در destination وجود داشته باشد، skip می‌شود (overwrite نمی‌شود)

### 2. Embedding Models

- اگر model در destination وجود نداشته باشد، با job_id جدید کپی می‌شود
- اگر model در destination وجود داشته باشد:
  - `job_id` به job جدید به‌روزرسانی می‌شود
  - `last_completed_job_at` به‌روزرسانی می‌شود
  - سایر فیلدها حفظ می‌شوند

### 3. Foreign Keys

Foreign key constraints رعایت می‌شوند:
- `embedding_models.job_id` به job جدید در destination اشاره می‌کند

## مثال‌های کاربردی

### مثال 1: انتقال Job از Staging به Production

```bash
# 1. اجرای اسکریپت
python copy_export_job.py \
    --source-path ~/staging/export-sql-chromadb \
    --dest-path ~/production/export-sql-chromadb

# 2. انتخاب job از لیست
# 3. تایید و کپی
```

### مثال 2: کپی Job خاص

```bash
python copy_export_job.py \
    --source-path ~/staging/export-sql-chromadb \
    --dest-path ~/production/export-sql-chromadb \
    --job-id 42
```

### مثال 3: کپی بدون Backup

```bash
python copy_export_job.py \
    --source-path ~/staging/export-sql-chromadb \
    --dest-path ~/production/export-sql-chromadb \
    --job-id 42 \
    --no-backup
```

## عیب‌یابی

### خطا: Database file not found

```bash
# بررسی مسیر
ls -la /path/to/staging/export-sql-chromadb/search_history.db
```

### خطا: No completed jobs found

این خطا زمانی رخ می‌دهد که:
- هیچ export job موفق در source وجود ندارد
- یا همه jobs با status='failed' یا 'running' هستند

**راه‌حل:** ابتدا یک export job موفق در source ایجاد کنید.

### خطا: Connection failed

```bash
# بررسی دسترسی
chmod 644 /path/to/staging/export-sql-chromadb/search_history.db
```

### خطا: Database is locked

این خطا زمانی رخ می‌دهد که database در حال استفاده است:
- سرویس web را متوقف کنید
- یا از `--no-backup` استفاده کنید

## تفاوت با `copy_sqlite_db.py`

| ویژگی | `copy_export_job.py` | `copy_sqlite_db.py` |
|--------|---------------------|---------------------|
| **محدوده** | فقط یک export job + models | کل database |
| **انتخاب** | تعاملی (کاربر انتخاب می‌کند) | خودکار (همه یا merge) |
| **هدف** | کپی job خاص | کپی/merge کل database |
| **استفاده** | زمانی که فقط یک job می‌خواهید | زمانی که همه داده‌ها را می‌خواهید |

## خلاصه

1. ✅ **تست Connection:** اول connection ها را تست می‌کند
2. ✅ **لیست Jobs:** فقط jobs موفق را نمایش می‌دهد
3. ✅ **انتخاب تعاملی:** کاربر job را انتخاب می‌کند
4. ✅ **جزئیات:** اطلاعات کامل نمایش داده می‌شود
5. ✅ **کپی هوشمند:** job و models مرتبط کپی می‌شوند
6. ✅ **Backup:** قبل از کپی backup می‌گیرد

**پیشنهاد:** همیشه از حالت تعاملی استفاده کنید تا بتوانید job مورد نظر را انتخاب کنید.

