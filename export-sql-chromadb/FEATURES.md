# فهرست ویژگی‌ها (Features List)

این فایل شامل لیست کامل تمام ویژگی‌ها و قابلیت‌های پیاده‌سازی شده در پروژه `export-sql-chromadb` است.

> 📖 برای راهنمای کامل نصب و استفاده، به [README.md](README.md) مراجعه کنید.

---

## 📋 فهرست مطالب

- [Export و Import](#export-و-import)
- [Web Service API](#web-service-api)
- [Admin Panel](#admin-panel)
- [Search Features](#search-features)
- [Database و Job Tracking](#database-و-job-tracking)
- [UI و Frontend](#ui-و-frontend)
- [Configuration و Environment](#configuration-و-environment)
- [Monitoring و Health Checks](#monitoring-و-health-checks)

---

## Export و Import

### ✅ Export Script (`export-sql-backup-to-chromadb.py`)

- **پارsing فایل SQL**: خواندن و پارس کردن فایل SQL dump از جدول `book_pages`
- **Segmentation هوشمند**: تقسیم متن به قطعات با طول قابل تنظیم (`max_length`) و context overlap
- **HTML to Text**: تبدیل محتوای HTML به متن خالص با استفاده از BeautifulSoup
- **Batch Processing**: پردازش داده‌ها به صورت batch برای بهینه‌سازی حافظه و سرعت
- **Progress Tracking**: نمایش پیشرفت export به صورت real-time
- **Job Tracking**: ثبت خودکار اطلاعات export job در دیتابیس SQLite
- **Collection Management**: 
  - پشتیبانی از Persistent و HTTP Client
  - افزودن خودکار timestamp به نام کالکشن در صورت تکراری بودن
  - امکان reset کردن کالکشن با فلگ `--reset`
- **Embedding Generation**: 
  - پشتیبانی از OpenAI embeddings (`text-embedding-3-small`, `text-embedding-3-large`)
  - ذخیره‌سازی خودکار مدل استفاده شده در job record
- **Error Handling**: مدیریت خطاها و ثبت در job record
- **UTF-8 Encoding**: پشتیبانی کامل از متن فارسی و کاراکترهای Unicode

### ✅ Command Line Arguments

- `--sql-path`: مسیر فایل SQL
- `--collection`: نام کالکشن ChromaDB
- `--batch-size`: اندازه batch برای پردازش
- `--max-length`: حداکثر طول هر segment
- `--context`: طول context overlap
- `--host`, `--port`, `--ssl`: تنظیمات اتصال ChromaDB
- `--embedding-provider`: انتخاب provider (openai, none)
- `--embedding-model`: انتخاب مدل امبدینگ
- `--reset`: پاک کردن کالکشن قبل از export
- و سایر تنظیمات...

---

## Web Service API

### ✅ FastAPI Application

- **RESTful API**: پیاده‌سازی کامل با FastAPI
- **JSON Responses**: پاسخ‌های JSON با encoding UTF-8
- **CORS Support**: پشتیبانی از CORS برای frontend
- **Structured Logging**: لاگ‌های JSON برای observability
- **Error Handling**: مدیریت خطاها با HTTP status codes مناسب
- **Async Support**: استفاده از async/await برای performance بهتر

### ✅ Endpoints

#### Search Endpoint
- **`POST /search`**: جستجوی معنایی در ChromaDB
  - پشتیبانی از pagination
  - نمایش total documents
  - تخمین تعداد نتایج
  - ذخیره خودکار نتایج در history (اختیاری)

#### Health Check
- **`GET /health`**: بررسی وضعیت سرویس‌ها
  - ChromaDB connectivity
  - Collection status و document count
  - Redis connectivity

#### Search History
- **`GET /history`**: لیست تاریخچه جستجوها با pagination
- **`GET /history/{search_id}`**: جزئیات یک جستجوی خاص

#### Admin Panel
- **`GET /admin`**: صفحه HTML برای admin panel
- **`GET /admin/jobs`**: لیست 50 job اخیر (بدون pagination)
- **`GET /admin/jobs/{job_id}`**: جزئیات کامل یک export job

#### Static Files
- **`GET /`**: صفحه اصلی جستجو (index.html)
- **`GET /static/*`**: فایل‌های استاتیک

---

## Admin Panel

### ✅ Export Jobs Management

- **لیست Jobs**: نمایش 50 job اخیر (جدیدترین اول)
- **Status Badges**: نمایش وضعیت jobs با رنگ‌بندی:
  - 🟡 Pending (در انتظار)
  - 🔵 Running (در حال اجرا)
  - 🟢 Completed (تکمیل شده)
  - 🔴 Failed (ناموفق)
- **Job Details Modal**: نمایش جزئیات کامل هر job شامل:
  - اطلاعات کلی (ID, Status, Collection, زمان‌ها)
  - آمار (رکوردها, کتاب‌ها, قطعات, مستندات)
  - تنظیمات Export (batch size, max length, context, ...)
  - Command line arguments
  - Error messages (در صورت وجود)
- **Auto-refresh**: امکان به‌روزرسانی دستی لیست jobs
- **Responsive Design**: طراحی responsive و RTL برای فارسی

---

## Search Features

### ✅ Semantic Search

- **Query Embedding**: تبدیل query به embedding با همان مدل استفاده شده در export
- **Similarity Search**: جستجوی بر اساس شباهت معنایی
- **Score و Distance**: نمایش امتیاز شباهت و فاصله بردار
- **Metadata Filtering**: نمایش کامل metadata برای هر نتیجه

### ✅ Pagination

- **Page-based Navigation**: پیمایش نتایج به صورت صفحه‌ای
- **Configurable Page Size**: اندازه صفحه قابل تنظیم (پیش‌فرض: 20)
- **Next/Previous Controls**: دکمه‌های صفحه بعدی/قبلی
- **Estimated Results**: تخمین تعداد کل نتایج (با حداکثر 1000+)
- **Feature Flag**: قابل فعال/غیرفعال کردن از طریق environment variable

### ✅ Search Statistics

- **Total Documents**: نمایش تعداد کل مستندات در کالکشن
- **Estimated Total Results**: تخمین تعداد نتایج برای query
- **Execution Time**: نمایش زمان اجرای جستجو
- **Feature Flags**: قابل کنترل از طریق environment variables

---

## Database و Job Tracking

### ✅ SQLite Database

- **Search History Table**: ذخیره تاریخچه جستجوها
  - Query text
  - Result count
  - Execution time
  - Collection, Provider, Model
  - Full results (JSON)
  
- **Export Jobs Table**: ذخیره اطلاعات export jobs
  - Status tracking (pending, running, completed, failed)
  - Start/End times
  - Duration calculation
  - Statistics (records, books, segments, documents)
  - Configuration (batch size, max length, context, ...)
  - Embedding model و provider
  - Error messages
  - Command line arguments (JSON)

### ✅ Database Functions

- `init_database()`: ایجاد جداول در صورت عدم وجود
- `save_search()`: ذخیره جستجو در history
- `get_search_history()`: دریافت تاریخچه با pagination
- `get_search_results()`: دریافت جزئیات یک جستجو
- `create_export_job()`: ایجاد job record جدید
- `update_export_job()`: به‌روزرسانی وضعیت job
- `get_export_jobs()`: دریافت لیست jobs (50 اخیر)
- `get_export_job()`: دریافت جزئیات یک job

### ✅ Job Tracking Features

- **Automatic Logging**: ثبت خودکار job در ابتدای export
- **Status Updates**: به‌روزرسانی خودکار وضعیت (running → completed/failed)
- **Statistics Collection**: جمع‌آوری آمار در پایان export
- **Error Logging**: ثبت خطاها در صورت failure
- **Duration Calculation**: محاسبه خودکار مدت زمان اجرا

---

## UI و Frontend

### ✅ Search Interface (`index.html`)

- **Modern Design**: طراحی مدرن با gradient background
- **RTL Support**: پشتیبانی کامل از راست‌چین برای فارسی
- **Search Form**: 
  - فیلد جستجو
  - انتخاب تعداد نتایج (top_k)
  - دکمه جستجو
  
- **Results Display**:
  - نمایش نتایج با score و distance
  - نمایش کامل متن document
  - نمایش metadata با ترجمه فارسی
  - Info icons با tooltips برای توضیحات
  - Shortened source links (نمایش ID و anchor)
  
- **Pagination Controls**:
  - دکمه‌های صفحه بعدی/قبلی
  - نمایش شماره صفحه
  - نمایش estimated results
  
- **Search History**:
  - لیست تاریخچه جستجوها
  - Deduplication (گروه‌بندی بر اساس query)
  - Click to reuse query
  
- **Config Info**: نمایش collection و embedding model در header

### ✅ Admin Panel (`admin.html`)

- **Jobs Table**: جدول با ستون‌های:
  - ID, Status, Collection
  - Start time, Duration
  - Statistics (Records, Books, Segments, Documents)
  - Actions (دکمه جزئیات)
  
- **Job Details Modal**: 
  - اطلاعات کامل job
  - آمار و تنظیمات
  - Command line arguments
  - Error messages
  
- **Auto-refresh**: امکان به‌روزرسانی دستی
- **Responsive Design**: طراحی responsive

---

## Configuration و Environment

### ✅ Environment Variables

تمام تنظیمات از طریق environment variables قابل کنترل است:

- **ChromaDB**: `CHROMA_HOST`, `CHROMA_PORT`, `CHROMA_SSL`, `CHROMA_API_KEY`, `CHROMA_COLLECTION`, ...
- **Embedding**: `EMBEDDING_PROVIDER`, `EMBEDDING_MODEL`, `OPENAI_API_KEY`
- **Redis**: `REDIS_URL` یا `REDIS_HOST`/`REDIS_PORT`/...
- **Web Service**: `APP_HOST`, `APP_PORT`, `APP_LOG_LEVEL`
- **Feature Flags**: `ENABLE_TOTAL_DOCUMENTS`, `ENABLE_ESTIMATED_RESULTS`, `ENABLE_PAGINATION`, `MAX_ESTIMATED_RESULTS`

### ✅ Configuration Files

- **`.env`**: فایل تنظیمات اصلی (در gitignore)
- **`.env.example`**: نمونه فایل تنظیمات با تمام متغیرها
- **Pydantic Settings**: استفاده از Pydantic-Settings برای validation

### ✅ Feature Flags

- `ENABLE_TOTAL_DOCUMENTS`: نمایش تعداد کل مستندات در کالکشن
- `ENABLE_ESTIMATED_RESULTS`: نمایش تخمین تعداد نتایج
- `ENABLE_PAGINATION`: فعال/غیرفعال کردن pagination
- `MAX_ESTIMATED_RESULTS`: حداکثر تعداد نتایج برای تخمین (پیش‌فرض: 1000)

---

## Monitoring و Health Checks

### ✅ Health Check Endpoint

- **ChromaDB Status**: بررسی اتصال و heartbeat
- **Collection Status**: بررسی وجود کالکشن و تعداد مستندات
- **Redis Status**: بررسی اتصال Redis
- **Latency Metrics**: اندازه‌گیری زمان پاسخ هر سرویس
- **Overall Status**: وضعیت کلی (ok/degraded)

### ✅ Logging

- **Structured Logging**: لاگ‌های JSON برای easy parsing
- **Log Levels**: پشتیبانی از تمام سطوح (DEBUG, INFO, WARNING, ERROR, CRITICAL)
- **Request Logging**: لاگ تمام درخواست‌ها
- **Error Logging**: لاگ کامل خطاها با stack trace
- **Performance Logging**: لاگ زمان اجرای عملیات

### ✅ Pre-startup Validation

- **Connection Checks**: بررسی اتصال به ChromaDB قبل از startup
- **Collection Validation**: بررسی وجود کالکشن
- **Redis Validation**: بررسی اتصال Redis (اختیاری)
- **Embedding Config Validation**: بررسی تنظیمات embedding
- **Fail Fast**: جلوگیری از startup در صورت خطای critical

---

## Technical Details

### ✅ Technologies Used

- **FastAPI**: Web framework
- **ChromaDB**: Vector database
- **OpenAI API**: Embedding generation
- **SQLite**: Local database برای history و jobs
- **Pydantic**: Data validation
- **BeautifulSoup**: HTML parsing
- **Uvicorn**: ASGI server

### ✅ Code Quality

- **Type Hints**: استفاده کامل از type hints
- **Error Handling**: مدیریت جامع خطاها
- **Documentation**: Docstrings برای تمام توابع
- **Code Organization**: ساختار منظم و modular
- **Async/Await**: استفاده از async برای I/O operations

---

## Changelog

### Version 1.0.0 (Current)

#### Export Script
- ✅ پیاده‌سازی export script با segmentation
- ✅ پشتیبانی از OpenAI embeddings
- ✅ Job tracking در SQLite
- ✅ Collection name با timestamp در صورت تکراری
- ✅ Progress tracking و statistics

#### Web Service
- ✅ FastAPI application با تمام endpoints
- ✅ Search با pagination و statistics
- ✅ Admin panel برای jobs
- ✅ Search history
- ✅ Health checks

#### UI
- ✅ Search interface با RTL support
- ✅ Admin panel با responsive design
- ✅ Pagination controls
- ✅ Search history display

#### Configuration
- ✅ Environment variables
- ✅ Feature flags
- ✅ `.env.example` file

---

## Links

- 📖 [README.md](README.md) - راهنمای کامل نصب و استفاده
- 📖 [README.web_service.md](README.web_service.md) - راهنمای سرویس وب
- 📖 [IMPROVEMENTS.md](IMPROVEMENTS.md) - پیشنهادات بهبود و بهینه‌سازی
- 🔧 [.env.example](.env.example) - نمونه فایل تنظیمات

---

**آخرین به‌روزرسانی**: 2025-01-16

