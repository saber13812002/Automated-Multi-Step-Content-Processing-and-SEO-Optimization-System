# فهرست ویژگی‌ها (Features List)

این فایل شامل لیست کامل تمام ویژگی‌ها و قابلیت‌های پیاده‌سازی شده در پروژه `export-sql-chromadb` است.

> 📖 برای راهنمای کامل نصب و استفاده، به [README.md](README.md) مراجعه کنید.

---

## 📋 فهرست مطالب

- [Export و Import](#export-و-import)
- [Web Service API](#web-service-api)
- [Admin Panel](#admin-panel)
- [Search Features](#search-features)
- [Multi-Model Search](#multi-model-search)
- [Embedding Models Management](#embedding-models-management)
- [User Feedback System](#user-feedback-system)
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

#### Search Endpoints
- **`POST /search`**: جستجوی معنایی در ChromaDB
  - پشتیبانی از pagination
  - نمایش total documents
  - تخمین تعداد نتایج
  - ذخیره خودکار نتایج در history (اختیاری)
- **`POST /search/multi`**: جستجوی چند مدلی
  - جستجوی همزمان در چند مدل
  - ترکیب نتایج به صورت یکی در میان
  - مدیریت خطا برای مدل‌های ناموفق
  - Redis caching

#### Health Check
- **`GET /health`**: بررسی وضعیت سرویس‌ها
  - ChromaDB connectivity
  - Collection status و document count
  - Redis connectivity

#### Search History
- **`GET /history`**: لیست تاریخچه جستجوها با pagination
- **`GET /history/{search_id}`**: جزئیات یک جستجوی خاص

#### Embedding Models
- **`GET /admin/models`**: لیست مدل‌های امبدینگ (حداکثر 10)
- **`POST /admin/models/{model_id}/toggle`**: تغییر وضعیت فعال/غیرفعال
- **`PUT /admin/models/{model_id}/color`**: تغییر رنگ مدل
- **`GET /models/active`**: دریافت مدل‌های فعال برای صفحه جستجو

#### User Feedback
- **`POST /search/vote`**: ثبت رای (لایک/دیسلایک)
- **`GET /admin/search/votes`**: لیست رای‌های ثبت شده
- **`GET /admin/search/votes/summary`**: آمار کلی رای‌ها

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

## Multi-Model Search

### ✅ جستجوی چند مدلی (Multi-Model Search)

- **انتخاب چند مدل**: امکان انتخاب تا 3 مدل امبدینگ برای جستجوی همزمان
- **جستجوی موازی**: اجرای جستجو در تمام مدل‌های انتخابی به صورت موازی
- **ترکیب نتایج**: نمایش نتایج به صورت یکی در میان (interleaved) از مدل‌های مختلف
- **محدودیت نتایج**: 
  - در صورت انتخاب یک مدل: نمایش تا `top_k` نتیجه
  - در صورت انتخاب چند مدل: حداکثر 20 نتیجه کل (تقسیم شده بین مدل‌ها)
- **مدیریت خطا**: 
  - در صورت خطای یک مدل، جستجو در مدل‌های دیگر ادامه می‌یابد
  - نمایش پیام خطا برای مدل‌های ناموفق
  - نمایش نتایج مدل‌های موفق
- **Redis Caching**: ذخیره نتایج جستجوی چند مدلی در Redis برای بهبود عملکرد
- **Model Tags**: نمایش برچسب مدل و رنگ اختصاصی برای هر نتیجه

### ✅ API Endpoint

- **`POST /search/multi`**: جستجوی چند مدلی
  - پارامترها: `query`, `model_ids` (لیست ID مدل‌ها), `top_k`, `save`
  - پاسخ: نتایج ترکیبی با تگ مدل و رنگ، لیست خطاها (در صورت وجود)

---

## Embedding Models Management

### ✅ مدیریت مدل‌های امبدینگ

- **همگام‌سازی خودکار**: 
  - شناسایی خودکار مدل‌هایی که آخرین job موفق را کامل کرده‌اند
  - نمایش حداکثر 10 مدل غیرتکراری (بر اساس provider, model, collection)
  - به‌روزرسانی خودکار در startup
- **فعال/غیرفعال کردن**: امکان فعال یا غیرفعال کردن هر مدل توسط ادمین
- **رنگ‌بندی اختصاصی**: 
  - اختصاص رنگ پیش‌فرض منحصر به فرد برای هر مدل
  - امکان تغییر رنگ توسط ادمین در پنل مدیریت
  - نمایش رنگ در نتایج جستجو
- **نمایش در Admin Panel**: 
  - لیست تمام مدل‌های شناسایی شده
  - نمایش اطلاعات job (تاریخ تکمیل، آمار مستندات)
  - دکمه‌های فعال/غیرفعال و تغییر رنگ
- **نمایش در Search Page**: 
  - لیست مدل‌های فعال با checkbox
  - انتخاب حداکثر 3 مدل
  - تیک پیش‌فرض روی همه مدل‌های فعال

### ✅ Database Schema

- **جدول `embedding_models`**:
  - `id`, `embedding_provider`, `embedding_model`, `collection`
  - `job_id`, `is_active`, `color`
  - `created_at`, `updated_at`, `last_completed_job_at`
- **توابع مدیریت**:
  - `sync_embedding_models_from_jobs()`: همگام‌سازی از export_jobs
  - `get_embedding_models()`: دریافت لیست مدل‌ها
  - `get_active_embedding_models()`: دریافت فقط مدل‌های فعال
  - `set_embedding_model_active()`: تغییر وضعیت فعال/غیرفعال
  - `update_embedding_model_color()`: تغییر رنگ مدل

### ✅ API Endpoints

- **`GET /admin/models`**: دریافت لیست مدل‌ها (حداکثر 10)
- **`POST /admin/models/{model_id}/toggle`**: تغییر وضعیت فعال/غیرفعال
- **`PUT /admin/models/{model_id}/color`**: تغییر رنگ مدل
- **`GET /models/active`**: دریافت مدل‌های فعال برای صفحه جستجو

---

## User Feedback System

### ✅ سیستم لایک/دیسلایک

- **رای‌دهی به نتایج**: 
  - دکمه لایک/دیسلایک برای هر نتیجه جستجو
  - دکمه لایک/دیسلایک کلی برای کل نتایج یک مدل
  - بازخورد فوری به کاربر
- **Guest User System**: 
  - شناسایی کاربر مهمان با `localStorage`
  - تولید خودکار `guest_user_id` منحصر به فرد
  - ذخیره در `localStorage` برای ردیابی بین جلسات
  - امکان override در آینده با سیستم احراز هویت
- **ذخیره‌سازی رای‌ها**: 
  - ذخیره در جدول `search_votes` در SQLite
  - ثبت query، model_id، result_id، vote_type
  - ثبت timestamp برای هر رای
- **نمایش در Admin Panel**: 
  - لیست تمام رای‌ها با فیلتر بر اساس query و model
  - آمار کلی رای‌ها (likes/dislikes) به تفکیک query و model
  - نمایش تاریخ آخرین رای

### ✅ Database Schema

- **جدول `search_votes`**:
  - `id`, `guest_user_id`, `query`
  - `search_id`, `result_id`, `model_id`
  - `vote_type` (like/dislike)
  - `created_at`
- **توابع مدیریت**:
  - `record_search_vote()`: ثبت رای جدید
  - `get_search_votes()`: دریافت لیست رای‌ها با فیلتر
  - `get_search_vote_summary()`: دریافت آمار کلی رای‌ها

### ✅ API Endpoints

- **`POST /search/vote`**: ثبت رای (لایک/دیسلایک)
  - پارامترها: `query`, `model_id`, `result_id`, `vote_type`, `guest_user_id`
- **`GET /admin/search/votes`**: دریافت لیست رای‌ها
  - فیلتر بر اساس `query` و `model_id`
- **`GET /admin/search/votes/summary`**: دریافت آمار کلی رای‌ها

### ✅ UI Features

- **دکمه‌های رای‌دهی**: 
  - استایل متمایز برای لایک (سبز) و دیسلایک (قرمز)
  - بازخورد فوری پس از ثبت رای
  - نمایش پیام تأیید
- **بخش رای کلی**: 
  - نمایش در پایین نتایج جستجو
  - امکان رای دادن به کل نتایج یک مدل

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

- **Embedding Models Table**: ذخیره اطلاعات مدل‌های امبدینگ
  - Provider, Model, Collection
  - Job ID (آخرین job موفق)
  - Status (active/inactive)
  - Color (رنگ اختصاصی)
  - Timestamps (created, updated, last_completed_job)

- **Search Votes Table**: ذخیره رای‌های کاربران
  - Guest user ID
  - Query, Search ID, Result ID
  - Model ID
  - Vote type (like/dislike)
  - Timestamp

### ✅ Database Functions

- `init_database()`: ایجاد جداول در صورت عدم وجود
- `save_search()`: ذخیره جستجو در history
- `get_search_history()`: دریافت تاریخچه با pagination
- `get_search_results()`: دریافت جزئیات یک جستجو
- `create_export_job()`: ایجاد job record جدید
- `update_export_job()`: به‌روزرسانی وضعیت job
- `get_export_jobs()`: دریافت لیست jobs (50 اخیر)
- `get_export_job()`: دریافت جزئیات یک job
- `get_latest_completed_model_jobs()`: دریافت آخرین job موفق برای هر مدل
- `sync_embedding_models_from_jobs()`: همگام‌سازی مدل‌ها از jobs
- `get_embedding_models()`: دریافت لیست مدل‌ها
- `get_active_embedding_models()`: دریافت مدل‌های فعال
- `set_embedding_model_active()`: تغییر وضعیت فعال/غیرفعال
- `update_embedding_model_color()`: تغییر رنگ مدل
- `record_search_vote()`: ثبت رای کاربر
- `get_search_votes()`: دریافت لیست رای‌ها
- `get_search_vote_summary()`: دریافت آمار رای‌ها

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

- **Model Selection**:
  - نمایش مدل‌های فعال با checkbox
  - انتخاب حداکثر 3 مدل
  - تیک پیش‌فرض روی همه
  - نمایش رنگ هر مدل

- **Multi-Model Results Display**:
  - نمایش نتایج به صورت یکی در میان
  - برچسب مدل با رنگ اختصاصی
  - نمایش خطاهای مدل‌های ناموفق (در صورت وجود)
  - پیام راهنما برای مدل‌های ناموفق

- **Vote Buttons**:
  - دکمه لایک/دیسلایک برای هر نتیجه
  - دکمه رای کلی برای کل نتایج
  - بازخورد فوری پس از ثبت رای
  
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

- **Embedding Models Management**:
  - لیست مدل‌های شناسایی شده (حداکثر 10)
  - نمایش اطلاعات job و آمار
  - دکمه فعال/غیرفعال
  - انتخاب رنگ برای هر مدل
  - پیام راهنما در صورت عدم وجود مدل

- **Search Votes Management**:
  - لیست تمام رای‌های ثبت شده
  - فیلتر بر اساس query و model
  - آمار کلی رای‌ها (likes/dislikes)
  - نمایش تاریخ و جزئیات هر رای
  
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

### Version 1.1.0 (Current)

#### Multi-Model Search
- ✅ جستجوی چند مدلی (تا 3 مدل همزمان)
- ✅ ترکیب نتایج به صورت یکی در میان
- ✅ مدیریت خطا برای مدل‌های ناموفق
- ✅ Redis caching برای نتایج چند مدلی
- ✅ نمایش برچسب و رنگ مدل در نتایج

#### Embedding Models Management
- ✅ همگام‌سازی خودکار مدل‌ها از export_jobs
- ✅ فعال/غیرفعال کردن مدل‌ها توسط ادمین
- ✅ اختصاص و تغییر رنگ برای هر مدل
- ✅ نمایش در admin panel و search page
- ✅ محدودیت 10 مدل و انتخاب حداکثر 3 مدل

#### User Feedback System
- ✅ سیستم لایک/دیسلایک برای نتایج
- ✅ Guest user tracking با localStorage
- ✅ ذخیره رای‌ها در database
- ✅ نمایش آمار رای‌ها در admin panel

#### Database Enhancements
- ✅ جدول `embedding_models` برای مدیریت مدل‌ها
- ✅ جدول `search_votes` برای ذخیره رای‌ها
- ✅ توابع مدیریت مدل‌ها و رای‌ها

#### UI Enhancements
- ✅ انتخاب مدل در صفحه جستجو
- ✅ نمایش خطاهای مدل‌های ناموفق
- ✅ دکمه‌های رای‌دهی در نتایج
- ✅ بخش مدیریت مدل‌ها در admin panel
- ✅ بخش آمار رای‌ها در admin panel

### Version 1.0.0

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

**آخرین به‌روزرسانی**: 2025-01-22

