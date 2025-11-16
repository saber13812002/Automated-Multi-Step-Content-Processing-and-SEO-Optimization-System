<!-- 474b973b-ab78-42a3-a9c3-41baf5a6ee7f 71380655-fcce-4433-8451-2a81c6b54d7a -->
# Job Tracking، Pagination و نمایش آمار جستجو

## 1. Job Tracking در Export Script

### 1.1. ایجاد جدول Jobs در Database (`database.py`)

- ایجاد جدول `export_jobs` با فیلدها:
- `id` (PRIMARY KEY AUTOINCREMENT)
- `status` (pending, running, completed, failed)
- `started_at` (DATETIME)
- `completed_at` (DATETIME, nullable)
- `duration_seconds` (REAL, nullable)
- `sql_path` (TEXT)
- `collection` (TEXT)
- `batch_size` (INTEGER)
- `max_length` (INTEGER)
- `context_length` (INTEGER)
- `host` (TEXT)
- `port` (INTEGER)
- `ssl` (BOOLEAN)
- `embedding_provider` (TEXT)
- `embedding_model` (TEXT)
- `reset` (BOOLEAN)
- `total_records` (INTEGER, nullable)
- `total_books` (INTEGER, nullable)
- `total_segments` (INTEGER, nullable)
- `total_documents_in_collection` (INTEGER, nullable)
- `error_message` (TEXT, nullable)
- `command_line_args` (TEXT) - JSON string از تمام arguments

### 1.2. توابع Database برای Jobs (`database.py`)

- `create_export_job(args: argparse.Namespace) -> int`: ثبت job جدید در ابتدای export، return job_id
- `update_export_job(job_id: int, status: str, **kwargs) -> None`: به‌روزرسانی وضعیت job
- `get_export_jobs(limit: int, offset: int, status: Optional[str] = None) -> tuple[List[Dict], int]`: دریافت لیست jobs با pagination
- `get_export_job(job_id: int) -> Optional[Dict]`: دریافت جزئیات یک job

### 1.3. تغییرات در `export-sql-backup-to-chromadb.py`

- در ابتدای `export_to_chroma`: ثبت job با `status='running'` و ذخیره `job_id`
- در انتهای موفق: به‌روزرسانی با `status='completed'`، `completed_at`، `duration_seconds` و تمام آمارها
- در صورت خطا: به‌روزرسانی با `status='failed'` و `error_message`
- استفاده از `try/finally` برای اطمینان از به‌روزرسانی وضعیت حتی در صورت خطا
- نمایش `job_id` در لاگ‌ها

## 2. Admin Panel API

### 2.1. Endpoint برای Jobs (`app.py`)

- `GET /admin/jobs`: لیست jobs با pagination
- Query params: `page` (default: 1), `limit` (default: 20), `status` (optional filter)
- Response: لیست jobs با pagination metadata (total, page, limit, has_next, has_previous)
- `GET /admin/jobs/{job_id}`: جزئیات یک job خاص شامل تمام فیلدها

### 2.2. Schema برای Jobs (`schemas.py`)

- `ExportJobItem`: مدل برای نمایش job در لیست (فیلدهای اصلی)
- `ExportJobDetail`: مدل برای نمایش جزئیات کامل job (همه فیلدها)
- `ExportJobsResponse`: response با pagination (jobs, total, page, limit, has_next, has_previous)

## 3. Pagination برای نتایج جستجو

### 3.1. تغییرات در `SearchRequest` (`schemas.py`)

- اضافه کردن `page: int = Field(1, ge=1)` - شماره صفحه، شروع از 1
- اضافه کردن `page_size: int = Field(20, ge=1, le=100)` - تعداد نتایج در هر صفحه

### 3.2. تغییرات در `SearchResponse` (`schemas.py`)

- اضافه کردن `PaginationInfo` model:
- `page: int` - صفحه فعلی
- `page_size: int` - اندازه صفحه
- `total_pages: Optional[int]` - تعداد کل صفحات (null اگر > 1000)
- `has_next_page: bool` - آیا صفحه بعدی وجود دارد
- `has_previous_page: bool` - آیا صفحه قبلی وجود دارد
- `estimated_total_results: Optional[str]` - "1000+" یا عدد دقیق به صورت string
- اضافه کردن `pagination: PaginationInfo` به `SearchResponse`
- اضافه کردن `total_documents: Optional[int] = None` - تعداد کل مستندات در کالکشن

### 3.3. تغییرات در `app.py` - تابع `search_documents`

- محاسبه `n_results = min(page_size, max_estimated_results)` برای query
- Query با `n_results` محاسبه شده
- اگر `enable_total_documents` فعال باشد: `total_docs = await anyio.to_thread.run_sync(collection.count)`
- اگر `enable_estimated_results` فعال باشد:
- اگر `len(results) == max_estimated_results`: `estimated_total = "1000+"` و `has_next_page = True`
- در غیر این صورت: `estimated_total = str(len(results))` و `has_next_page = len(results) == page_size`
- محاسبه `total_pages` فقط اگر `estimated_total` عدد دقیق باشد: `ceil(estimated_total / page_size)`
- محاسبه `has_previous_page = page > 1`
- اضافه کردن pagination info به response

### 3.4. Feature Flags (`config.py`)

- `enable_total_documents: bool = True` (alias: `ENABLE_TOTAL_DOCUMENTS`)
- `enable_estimated_results: bool = True` (alias: `ENABLE_ESTIMATED_RESULTS`)
- `enable_pagination: bool = True` (alias: `ENABLE_PAGINATION`)
- `max_estimated_results: int = 1000` (alias: `MAX_ESTIMATED_RESULTS`)

## 4. Admin Panel UI

### 4.1. صفحه جدید (`admin.html`)

- جدول jobs با ستون‌ها:
- ID
- Status (با رنگ‌بندی: pending=yellow, running=blue, completed=green, failed=red)
- Collection
- Started At
- Duration
- Total Records/Segments
- Actions (دکمه "مشاهده جزئیات")
- Pagination controls (صفحه بعدی/قبلی، شماره صفحات، input برای رفتن به صفحه خاص)
- Filter dropdown برای status
- نمایش جزئیات job در modal یا expandable row
- طراحی responsive و RTL

### 4.2. Route در `app.py`

- `GET /admin` یا `GET /admin/jobs`: serve کردن `admin.html`
- Mount static files برای admin panel (اگر نیاز باشد)

## 5. UI برای Pagination در نتایج جستجو (`index.html`)

### 5.1. Pagination Controls

- دکمه "صفحه قبلی" (غیرفعال در صفحه اول)
- نمایش "صفحه X از Y" یا "صفحه X (بیش از 1000 نتیجه)"
- دکمه "صفحه بعدی" (غیرفعال در صفحه آخر)
- Input برای رفتن به صفحه خاص (با validation)
- نمایش تعداد کل نتایج: "از X مستند" (اگر total_documents موجود باشد)

### 5.2. به‌روزرسانی `performSearch`

- اضافه کردن `page` parameter به request body
- به‌روزرسانی URL با query params (`?page=X`) برای bookmark کردن
- حفظ `page` در state برای navigation
- Reset به صفحه 1 هنگام جستجوی جدید

## 6. تست‌ها

### 6.1. Unit Tests (`tests/test_database.py`)

- تست `create_export_job` - ایجاد job جدید
- تست `update_export_job` - به‌روزرسانی status و fields
- تست `get_export_jobs` - pagination و filtering
- تست `get_export_job` - دریافت job خاص

### 6.2. Integration Tests (`tests/test_app.py`)

- تست `GET /admin/jobs` - لیست jobs با pagination
- تست `GET /admin/jobs/{id}` - جزئیات job
- تست `POST /search` با pagination - صفحه 1، 2، آخر
- تست pagination edge cases:
- صفحه اول (has_previous = false)
- صفحه آخر (has_next = false)
- بیش از 1000 نتیجه (estimated_total = "1000+")
- کمتر از page_size نتیجه (has_next = false)

### 6.3. Test Fixtures

- Helper function برای ایجاد test jobs با status مختلف
- Mock data برای jobs
- Setup/teardown برای database

## 7. فایل‌های تغییر یافته/جدید

1. `export-sql-chromadb/web_service/database.py` - توابع job tracking
2. `export-sql-chromadb/export-sql-backup-to-chromadb.py` - ثبت و به‌روزرسانی jobs
3. `export-sql-chromadb/web_service/config.py` - feature flags
4. `export-sql-chromadb/web_service/schemas.py` - models برای jobs و pagination
5. `export-sql-chromadb/web_service/app.py` - admin endpoints و pagination logic
6. `export-sql-chromadb/web_service/static/admin.html` - صفحه admin panel (جدید)
7. `export-sql-chromadb/web_service/static/index.html` - pagination controls
8. `export-sql-chromadb/.env.example` - ایجاد فایل جدید با تمام متغیرها
9. `export-sql-chromadb/tests/test_database.py` - تست‌های database (جدید)
10. `export-sql-chromadb/tests/test_app.py` - تست‌های API (جدید)
11. `export-sql-chromadb/tests/__init__.py` - package init (جدید)

## 8. نکات پیاده‌سازی

- Job tracking باید از همان database استفاده کند که search history استفاده می‌کند
- Pagination باید backward compatible باشد (اگر page مشخص نشود، صفحه 1 در نظر گرفته شود)
- برای تخمین > 1000، همیشه `has_next_page = True` باشد (مگر اینکه تعداد دقیق نتایج کمتر از page_size باشد)
- Admin panel باید responsive و user-friendly باشد
- تمام feature flags باید در `.env.example` مستند شوند
- تست‌ها باید comprehensive باشند و edge cases را پوشش دهند