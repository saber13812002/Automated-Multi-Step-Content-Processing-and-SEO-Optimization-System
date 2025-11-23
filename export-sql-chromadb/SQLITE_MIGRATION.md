# راهنمای انتقال SQLite Database بین Instance ها

این راهنما برای کپی یا merge کردن داده‌های SQLite (`search_history.db`) از یک instance به instance دیگر است.

## بررسی ساختار

هر instance در پوشه خودش SQLite database دارد:
- **مسیر:** `export-sql-chromadb/search_history.db`
- **محتوای:** 
  - تاریخچه جستجوها (`search_history`)
  - Export jobs (`export_jobs`)
  - Query approvals (`query_approvals`)
  - Embedding models (`embedding_models`)
  - Search votes (`search_votes`)
  - API users و tokens (`api_users`, `api_tokens`, `api_token_usage`)

## استفاده از اسکریپت `copy_sqlite_db.py`

### حالت 1: Merge داده‌ها (پیشنهادی)

این حالت داده‌های source را به destination اضافه می‌کند بدون اینکه داده‌های موجود را overwrite کند:

```bash
cd export-sql-chromadb

python copy_sqlite_db.py \
    --source-path /path/to/staging/export-sql-chromadb \
    --dest-path /path/to/production/export-sql-chromadb \
    --mode merge
```

**مثال واقعی:**
```bash
python copy_sqlite_db.py \
    --source-path ~/saberprojects/automated-dev/export-sql-chromadb \
    --dest-path ~/saberprojects/automated-Multi-Step-Content-Processing-and-SEO-Optimization-System/export-sql-chromadb \
    --mode merge
```

### حالت 2: کپی کامل (Overwrite)

این حالت کل database را overwrite می‌کند (⚠️ داده‌های موجود در destination از بین می‌روند):

```bash
python copy_sqlite_db.py \
    --source-path /path/to/staging/export-sql-chromadb \
    --dest-path /path/to/production/export-sql-chromadb \
    --mode copy
```

**نکته:** به صورت پیش‌فرض قبل از overwrite، یک backup از destination ایجاد می‌شود.

### حالت 3: فقط Backup

برای ایجاد backup از database موجود:

```bash
python copy_sqlite_db.py \
    --dest-path /path/to/production/export-sql-chromadb \
    --mode backup
```

### حالت 4: نمایش اطلاعات

برای دیدن اطلاعات database (تعداد ردیف‌ها در هر table):

```bash
# اطلاعات destination
python copy_sqlite_db.py \
    --dest-path /path/to/production/export-sql-chromadb \
    --mode info

# اطلاعات source و destination
python copy_sqlite_db.py \
    --source-path /path/to/staging/export-sql-chromadb \
    --dest-path /path/to/production/export-sql-chromadb \
    --mode info
```

یا با استفاده از flag های جداگانه:

```bash
python copy_sqlite_db.py \
    --source-path /path/to/staging/export-sql-chromadb \
    --dest-path /path/to/production/export-sql-chromadb \
    --show-source-info \
    --show-dest-info
```

## گزینه‌های اضافی

### بدون Backup

اگر می‌خواهید backup ایجاد نشود:

```bash
python copy_sqlite_db.py \
    --source-path /path/to/staging/export-sql-chromadb \
    --dest-path /path/to/production/export-sql-chromadb \
    --mode merge \
    --no-backup
```

## نحوه کار Merge

در حالت merge:
- ✅ داده‌های جدید از source به destination اضافه می‌شوند
- ✅ داده‌های تکراری (بر اساس ID) skip می‌شوند
- ✅ داده‌های موجود در destination حفظ می‌شوند
- ✅ برای tables بدون ID، از `INSERT OR IGNORE` استفاده می‌شود

**مثال:**
- Source: 1000 ردیف در `search_history`
- Destination: 500 ردیف در `search_history` (200 تای آن مشترک با source)
- بعد از merge: 1300 ردیف (500 موجود + 800 جدید از source)

## نکات مهم

### 1. Backup خودکار

به صورت پیش‌فرض، قبل از هر عملیات (copy یا merge)، یک backup از destination ایجاد می‌شود:
- نام فایل: `search_history_backup_YYYYMMDD_HHMMSS.db`
- محل: همان پوشه‌ای که database اصلی است

### 2. ایجاد Tables

اگر destination database وجود نداشته باشد، tables به صورت خودکار ایجاد می‌شوند.

### 3. Foreign Keys

در merge، foreign key constraints رعایت می‌شوند. اگر `export_jobs` را merge می‌کنید، باید `embedding_models` را هم merge کنید.

### 4. Performance

- برای database های بزرگ (بیش از 100,000 ردیف)، merge ممکن است چند دقیقه طول بکشد
- برای database های کوچک (کمتر از 10,000 ردیف)، معمولاً کمتر از 10 ثانیه

## مثال‌های کاربردی

### مثال 1: انتقال داده‌های Staging به Production

```bash
# 1. بررسی داده‌های موجود
python copy_sqlite_db.py \
    --source-path ~/staging/export-sql-chromadb \
    --dest-path ~/production/export-sql-chromadb \
    --show-source-info \
    --show-dest-info

# 2. Merge داده‌ها
python copy_sqlite_db.py \
    --source-path ~/staging/export-sql-chromadb \
    --dest-path ~/production/export-sql-chromadb \
    --mode merge

# 3. بررسی نتیجه
python copy_sqlite_db.py \
    --dest-path ~/production/export-sql-chromadb \
    --mode info
```

### مثال 2: Backup قبل از تغییرات

```bash
# ایجاد backup
python copy_sqlite_db.py \
    --dest-path ~/production/export-sql-chromadb \
    --mode backup
```

### مثال 3: Restore از Backup

```bash
# Restore از backup (استفاده از copy mode)
python copy_sqlite_db.py \
    --source-path ~/production/export-sql-chromadb/search_history_backup_20240101_120000.db \
    --dest-path ~/production/export-sql-chromadb \
    --mode copy \
    --no-backup
```

## عیب‌یابی

### خطا: Source database not found

```bash
# بررسی مسیر
ls -la /path/to/staging/export-sql-chromadb/search_history.db
```

### خطا: Permission denied

```bash
# بررسی دسترسی
chmod 644 /path/to/staging/export-sql-chromadb/search_history.db
```

### خطا: Database is locked

این خطا زمانی رخ می‌دهد که database در حال استفاده است:
- سرویس web را متوقف کنید
- یا از `--no-backup` استفاده کنید (اگر backup در حال نوشتن است)

## خلاصه

1. ✅ **Merge (پیشنهادی):** داده‌ها را اضافه می‌کند، overwrite نمی‌کند
2. ✅ **Copy:** کل database را overwrite می‌کند (با backup)
3. ✅ **Backup:** فقط backup می‌گیرد
4. ✅ **Info:** اطلاعات database را نمایش می‌دهد

**پیشنهاد:** همیشه از `--mode merge` استفاده کنید مگر اینکه واقعاً بخواهید کل database را overwrite کنید.

