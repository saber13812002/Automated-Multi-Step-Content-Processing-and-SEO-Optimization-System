<!-- 474b973b-ab78-42a3-a9c3-41baf5a6ee7f 454d0df5-699b-4ec3-8065-8e4745f2b102 -->
# پلان پیاده‌سازی: بهبود Admin Panel و Authentication

## 1. Admin Panel - باکس تنظیمات ChromaDB

### 1.1. API Endpoints (`app.py`)

- `GET /admin/chroma/collections`: لیست تمام کالکشن‌های موجود در ChromaDB
- `POST /admin/chroma/test-connection`: تست اتصال به ChromaDB
- `POST /admin/chroma/generate-export-command`: تولید دستور export با پارامترهای قابل تنظیم
- `POST /admin/chroma/generate-uvicorn-command`: تولید دستور uvicorn با override collection

### 1.2. Schema (`schemas.py`)

- `ChromaCollectionInfo`: اطلاعات کالکشن (name, count, metadata)
- `ChromaTestResponse`: نتیجه تست اتصال
- `ExportCommandRequest`: پارامترهای تولید دستور export
- `ExportCommandResponse`: دستور تولید شده
- `UvicornCommandRequest`: پارامترهای تولید دستور uvicorn

### 1.3. UI (`admin.html`)

- باکس "تنظیمات ChromaDB" با:
- دکمه "تست اتصال"
- لیست کالکشن‌ها با تعداد مستندات
- فرم تولید دستور export (با فیلدهای: sql_path, collection, embedding_provider, reset, ...)
- فرم تولید دستور uvicorn (با فیلد collection override)
- نمایش دستورات تولید شده با امکان copy

## 2. سیستم مدیریت سوابق جستجو

### 2.1. Database Schema (`database.py`)

- جدول جدید `query_approvals`:
- `id`: PRIMARY KEY
- `query`: TEXT (unique)
- `status`: TEXT (approved/rejected/pending) - پیش‌فرض: approved
- `approved_at`: DATETIME
- `rejected_at`: DATETIME
- `notes`: TEXT
- `search_count`: INTEGER (تعداد تکرار)
- `last_searched_at`: DATETIME

### 2.2. Database Functions (`database.py`)

- `init_query_approvals_table()`: ایجاد جدول
- `get_query_approvals(limit, min_count)`: دریافت query‌های تایید شده
- `approve_query(query)`: تایید query
- `reject_query(query)`: رد query
- `delete_query(query)`: حذف query
- `get_query_stats()`: آمار query‌ها (تکرار، تایید شده، رد شده)
- `update_query_search_count(query)`: به‌روزرسانی تعداد تکرار

### 2.3. API Endpoints (`app.py`)

- `GET /admin/queries`: لیست query‌ها با فیلتر (status, min_count)
- `POST /admin/queries/{query}/approve`: تایید query
- `POST /admin/queries/{query}/reject`: رد query
- `DELETE /admin/queries/{query}`: حذف query
- `GET /admin/queries/stats`: آمار query‌ها

### 2.4. Configuration (`config.py`)

- `SHOW_APPROVED_QUERIES`: bool (پیش‌فرض: true) - نمایش query‌های تایید شده در صفحه اصلی
- `APPROVED_QUERIES_MIN_COUNT`: int (پیش‌فرض: 4) - حداقل تعداد تکرار برای نمایش
- `APPROVED_QUERIES_LIMIT`: int (پیش‌فرض: 10) - تعداد query‌های نمایش داده شده

### 2.5. Integration با Search (`app.py`)

- در `save_search()`: به‌روزرسانی `query_approvals` (افزایش search_count)
- در `GET /` (index.html): نمایش query‌های تایید شده در بالای صفحه
- در `POST /search`: بررسی وضعیت query (اگر rejected باشد، warning)

### 2.6. UI (`admin.html`)

- باکس "مدیریت سوابق جستجو" با:
- لیست query‌ها با status badges
- فیلتر بر اساس status و min_count
- دکمه‌های تایید/رد/حذف برای هر query
- نمایش تعداد تکرار و آخرین جستجو
- آمار کلی (تایید شده، رد شده، pending)

### 2.7. UI (`index.html`)

- بخش "سوابق جستجوی تایید شده" در بالای صفحه
- نمایش query‌های تایید شده با تعداد تکرار بالا
- قابل کنترل از طریق feature flag

## 3. مستندات API (Swagger-like)

### 3.1. بهبود OpenAPI Docs (`app.py`)

- اضافه کردن `description` و `example` به تمام endpoints
- اضافه کردن `tags` برای دسته‌بندی
- اضافه کردن `responses` با مثال‌های واقعی
- اضافه کردن `summary` برای هر endpoint

### 3.2. Custom Documentation Page

- `GET /api-docs`: صفحه HTML سفارشی برای مستندات API
- یا استفاده از `/docs` (Swagger UI) و `/redoc` (ReDoc) که FastAPI به صورت خودکار می‌سازد
- اضافه کردن examples و defaults در schemas

### 3.3. API Documentation File

- ایجاد `API_DOCUMENTATION.md` با:
- لیست تمام endpoints
- مقادیر پیش‌فرض
- مثال‌های request/response
- Authentication requirements
- Rate limiting info

## 4. سیستم Authentication و Rate Limiting

### 4.1. Database Schema (`database.py`)

- جدول `api_users`:
- `id`: PRIMARY KEY
- `username`: TEXT (unique)
- `email`: TEXT
- `created_at`: DATETIME
- `is_active`: BOOLEAN

- جدول `api_tokens`:
- `id`: PRIMARY KEY
- `user_id`: INTEGER (FK to api_users)
- `token`: TEXT (unique, hashed)
- `name`: TEXT (نام توکن)
- `rate_limit_per_day`: INTEGER (پیش‌فرض: 1000)
- `created_at`: DATETIME
- `expires_at`: DATETIME (nullable)
- `is_active`: BOOLEAN
- `last_used_at`: DATETIME

- جدول `api_token_usage`:
- `id`: PRIMARY KEY
- `token_id`: INTEGER (FK to api_tokens)
- `date`: DATE
- `request_count`: INTEGER
- `last_request_at`: DATETIME

### 4.2. Database Functions (`database.py`)

- `init_auth_tables()`: ایجاد جداول
- `create_api_user(username, email)`: ایجاد کاربر
- `create_api_token(user_id, name, rate_limit, expires_at)`: ایجاد توکن
- `get_api_token(token_hash)`: دریافت توکن
- `increment_token_usage(token_id)`: افزایش تعداد استفاده
- `get_token_usage_today(token_id)`: دریافت استفاده امروز
- `reset_daily_usage()`: ریست استفاده روزانه (cron job)
- `get_all_tokens(user_id)`: لیست توکن‌های یک کاربر
- `revoke_token(token_id)`: غیرفعال کردن توکن

### 4.3. Authentication Middleware (`app.py`)

- `verify_api_token(request)`: Dependency برای بررسی توکن
- `check_rate_limit(token_id)`: بررسی rate limit
- اعمال middleware به endpoints (به جز `/`, `/health`, `/docs`, `/admin`)

### 4.4. API Endpoints (`app.py`)

- `POST /admin/auth/users`: ایجاد کاربر جدید
- `GET /admin/auth/users`: لیست کاربران
- `POST /admin/auth/tokens`: ایجاد توکن جدید
- `GET /admin/auth/tokens`: لیست توکن‌ها
- `DELETE /admin/auth/tokens/{token_id}`: حذف/غیرفعال کردن توکن
- `GET /admin/auth/tokens/{token_id}/usage`: آمار استفاده توکن

### 4.5. UI (`admin.html`)

- باکس "مدیریت کاربران و توکن‌ها" با:
- لیست کاربران
- فرم ایجاد کاربر جدید
- لیست توکن‌ها برای هر کاربر
- فرم ایجاد توکن (با تنظیمات rate limit)
- نمایش آمار استفاده (امروز، این ماه)
- دکمه revoke برای توکن‌ها

### 4.6. Configuration (`config.py`)

- `ENABLE_API_AUTH`: bool (پیش‌فرض: false) - فعال/غیرفعال کردن authentication
- `DEFAULT_RATE_LIMIT_PER_DAY`: int (پیش‌فرض: 1000) - حد پیش‌فرض rate limit

### 4.7. Rate Limiting Logic

- استفاده از Redis برای tracking (اگر موجود باشد) یا SQLite
- بررسی تعداد درخواست در 24 ساعت گذشته
- برگرداندن `429 Too Many Requests` در صورت تجاوز
- Header `X-RateLimit-Limit`, `X-RateLimit-Remaining`, `X-RateLimit-Reset`

## 5. فایل‌های تغییر یافته/جدید

1. `export-sql-chromadb/web_service/database.py` - جداول و توابع جدید
2. `export-sql-chromadb/web_service/schemas.py` - models جدید
3. `export-sql-chromadb/web_service/app.py` - endpoints و middleware جدید
4. `export-sql-chromadb/web_service/config.py` - تنظیمات جدید
5. `export-sql-chromadb/web_service/static/admin.html` - باکس‌های جدید
6. `export-sql-chromadb/web_service/static/index.html` - نمایش query‌های تایید شده
7. `export-sql-chromadb/API_DOCUMENTATION.md` - مستندات API (جدید)
8. `export-sql-chromadb/.env.example` - متغیرهای جدید

## 6. ترتیب پیاده‌سازی

1. **Phase 1**: باکس تنظیمات ChromaDB و تولید دستورات
2. **Phase 2**: سیستم مدیریت سوابق جستجو
3. **Phase 3**: بهبود مستندات API
4. **Phase 4**: سیستم Authentication و Rate Limiting

## 7. نکات مهم

- تمام تنظیمات از طریق environment variables قابل کنترل است
- پیش‌فرض‌ها طوری تنظیم شده‌اند که backward compatible باشند
- Authentication به صورت optional است (می‌توان غیرفعال کرد)
- Rate limiting با Redis (اگر موجود باشد) یا SQLite پیاده‌سازی می‌شود
- تمام endpoint‌ها باید مستندات کامل داشته باشند

### To-dos

- [ ] ایجاد باکس تنظیمات ChromaDB در admin panel با تست اتصال، لیست کالکشن‌ها و تولید دستورات
- [ ] پیاده‌سازی سیستم تایید/رد query‌ها با جدول query_approvals و API endpoints
- [ ] نمایش query‌های تایید شده در صفحه اصلی با فیلتر بر اساس تعداد تکرار
- [ ] بهبود OpenAPI docs و ایجاد فایل API_DOCUMENTATION.md با examples و defaults
- [ ] ایجاد جداول api_users, api_tokens, api_token_usage در database
- [ ] پیاده‌سازی authentication middleware و rate limiting
- [ ] ایجاد باکس مدیریت کاربران و توکن‌ها در admin panel