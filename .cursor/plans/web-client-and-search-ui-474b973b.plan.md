<!-- 474b973b-ab78-42a3-a9c3-41baf5a6ee7f d6a87f2f-88c6-4bf0-86e5-a4a73efb36f3 -->
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
- محاسبه `total_pages` فقط اگر `estimated_total` عدد

### To-dos

- [ ] در export-sql-backup-to-chromadb.py: اضافه کردن نمایش تعداد کل مستندات در کالکشن در خلاصه نهایی
- [ ] در config.py: اضافه کردن ENABLE_TOTAL_DOCUMENTS, ENABLE_ESTIMATED_RESULTS, ESTIMATED_RESULTS_SAMPLE_SIZE
- [ ] در schemas.py: اضافه کردن total_documents و estimated_total_results به SearchResponse
- [ ] در app.py: پیاده‌سازی منطق تخمین نتایج و گرفتن تعداد کل مستندات با توجه به feature flags
- [ ] در index.html: نمایش تعداد کل مستندات و تخمین نتایج در بخش results-meta
- [ ] ایجاد یا به‌روزرسانی .env.example با متغیرهای جدید feature flags