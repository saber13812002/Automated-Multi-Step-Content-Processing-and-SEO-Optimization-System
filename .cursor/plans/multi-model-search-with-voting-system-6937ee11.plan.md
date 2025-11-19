<!-- 6937ee11-283e-42ad-b5c9-629893da7408 8b194d6e-1915-4ae8-81e8-c70be9603f25 -->
# پلن پیاده‌سازی سیستم جستجوی چند مدلی با رای‌دهی

## 1. ساختار دیتابیس

### 1.1. جدول `embedding_models`

- `id`: PRIMARY KEY
- `embedding_provider`: TEXT (مثلاً 'openai')
- `embedding_model`: TEXT (مثلاً 'text-embedding-3-small')
- `collection`: TEXT
- `job_id`: INTEGER (FK به export_jobs - آخرین job موفق)
- `is_active`: BOOLEAN (پیش‌فرض: true)
- `color`: TEXT (hex color، پیش‌فرض: رنگ‌های از پیش تعریف شده)
- `created_at`: DATETIME
- `updated_at`: DATETIME
- `last_completed_job_at`: DATETIME (زمان آخرین job موفق)

### 1.2. جدول `search_votes`

- `id`: PRIMARY KEY
- `guest_user_id`: TEXT (شناسه کاربر مهمان از localStorage)
- `query`: TEXT
- `model_id`: INTEGER (FK به embedding_models، nullable برای رای کلی)
- `result_id`: TEXT (nullable - اگر null باشد یعنی رای برای کل جستجو)
- `vote_type`: TEXT CHECK('like', 'dislike')
- `created_at`: DATETIME

### 1.3. Indexes

- `idx_embedding_models_active` روی `is_active`
- `idx_embedding_models_provider_model` روی `(embedding_provider, embedding_model)`
- `idx_search_votes_query` روی `query`
- `idx_search_votes_guest_user` روی `guest_user_id`

## 2. Backend APIs

### 2.1. مدیریت مدل‌ها (`/admin/models`)

- `GET /admin/models`: لیست تمام مدل‌های کامل شده (حداکثر 10 غیرتکراری)
- `POST /admin/models/{model_id}/toggle`: فعال/غیرفعال کردن مدل
- `PUT /admin/models/{model_id}/color`: تغییر رنگ مدل
- `GET /models/active`: لیست مدل‌های فعال برای کاربر (حداکثر 10)

### 2.2. جستجوی چند مدلی (`/search/multi`)

- `POST /search/multi`: جستجو با چند مدل
- Request: `{query: str, model_ids: List[int], top_k: int}`
- Response: نتایج ترکیبی با تگ مدل و رنگ
- Logic:
- اگر 1 مدل: کوئری عادی
- اگر 2 مدل: کوئری هر دو، cache در Redis، نمایش یکی درمیون
- اگر 3 مدل: نمایش 3+3+1 (حداکثر 7 نتیجه برای 20 نتیجه کل)

### 2.3. سیستم رای‌دهی (`/search/vote`)

- `POST /search/vote`: ثبت لایک/دیسلایک
- Request: `{query: str, model_id?: int, result_id?: str, vote_type: 'like'|'dislike', guest_user_id: str}`
- Response: `{success: bool, message: str}`

### 2.4. آمار رای‌ها (`/admin/search/votes`)

- `GET /admin/search/votes`: لیست رای‌ها با فیلتر
- Query params: `query?: str, model_id?: int, limit?: int`
- Response: لیست رای‌ها با جزئیات

## 3. Frontend - ادمین پنل

### 3.1. بخش مدیریت مدل‌ها

- نمایش لیست مدل‌های کامل شده (حداکثر 10)
- چک‌باکس برای فعال/غیرفعال کردن
- انتخابگر رنگ برای هر مدل
- نمایش آخرین job موفق برای هر مدل

### 3.2. بخش آمار رای‌ها

- جدول رای‌ها با فیلتر بر اساس query و model
- نمایش تعداد لایک/دیسلایک برای هر query/model
- نمایش تاریخچه رای‌ها

## 4. Frontend - صفحه جستجو

### 4.1. انتخاب مدل‌ها

- نمایش مدل‌های فعال (حداکثر 10)
- چک‌باکس برای انتخاب (حداکثر 3)
- پیش‌فرض: همه تیک بخورند (تا 3 تا)
- نمایش رنگ هر مدل

### 4.2. نمایش نتایج

- نمایش نتایج با تگ مدل (رنگ پس‌زمینه)
- اگر 2 مدل: یکی درمیون نمایش
- اگر 3 مدل: 3+3+1 (حداکثر 7)
- دکمه‌های لایک/دیسلایک برای هر نتیجه
- دکمه‌های لایک/دیسلایک برای کل نتایج (در پایین)

## 5. سیستم کاربر مهمان (localStorage)

### 5.1. ایجاد خودکار کاربر

- در اولین بار: ایجاد `guest_user_id` و `guest_token` در localStorage
- `guest_user_id`: UUID v4
- `guest_token`: رشته تصادفی (برای آینده)

### 5.2. ذخیره‌سازی

- کلید: `chroma_search_guest_user`
- مقدار: `{user_id: string, token: string, created_at: string}`

## 6. Redis Cache

### 6.1. ساختار کلید

- Pattern: `search:multi:{query_hash}:{model_ids_sorted}:{top_k}`
- مثال: `search:multi:abc123:1,2,3:20`
- TTL: 24 ساعت

### 6.2. ساختار داده

- JSON شامل نتایج هر مدل با تگ model_id

## 7. رنگ‌های پیش‌فرض

رنگ‌های با تلورانس بالا (HSL):

- Model 1: `#3B82F6` (آبی)
- Model 2: `#10B981` (سبز)
- Model 3: `#F59E0B` (نارنجی)
- Model 4: `#EF4444` (قرمز)
- Model 5: `#8B5CF6` (بنفش)
- Model 6: `#06B6D4` (فیروزه‌ای)
- Model 7: `#F97316` (نارنجی تیره)
- Model 8: `#84CC16` (زرد-سبز)
- Model 9: `#EC4899` (صورتی)
- Model 10: `#6366F1` (نیلی)

## 8. فایل‌های مورد تغییر

### Backend:

- `export-sql-chromadb/web_service/database.py`: اضافه کردن جداول و functions
- `export-sql-chromadb/web_service/schemas.py`: اضافه کردن schemas جدید
- `export-sql-chromadb/web_service/app.py`: اضافه کردن endpoints

### Frontend:

- `export-sql-chromadb/web_service/static/admin.html`: بخش مدیریت مدل‌ها و آمار رای‌ها
- `export-sql-chromadb/web_service/static/index.html`: انتخاب مدل‌ها و نمایش نتایج با رای‌دهی

## 9. تست‌ها

### 9.1. Unit Tests

- تست functions دیتابیس
- تست endpointهای API
- تست منطق ترکیب نتایج

### 9.2. Integration Tests

- تست جریان کامل جستجو با چند مدل
- تست سیستم رای‌دهی
- تست cache در Redis

### 9.3. Frontend Tests

- تست انتخاب مدل‌ها
- تست نمایش نتایج
- تست localStorage برای کاربر مهمان

### To-dos

- [ ] ایجاد جداول embedding_models و search_votes در database.py
- [ ] ایجاد functions برای مدیریت مدل‌ها و رای‌ها در database.py
- [ ] اضافه کردن schemas جدید برای مدل‌ها و رای‌ها در schemas.py
- [ ] ایجاد endpoints مدیریت مدل‌ها در app.py (/admin/models)
- [ ] ایجاد endpoint جستجوی چند مدلی (/search/multi) در app.py
- [ ] ایجاد endpoint رای‌دهی (/search/vote) در app.py
- [ ] اضافه کردن بخش مدیریت مدل‌ها در admin.html
- [ ] اضافه کردن بخش آمار رای‌ها در admin.html
- [ ] اضافه کردن انتخاب مدل‌ها در index.html
- [ ] نمایش نتایج با رنگ‌بندی و تگ مدل در index.html
- [ ] اضافه کردن دکمه‌های لایک/دیسلایک در index.html
- [ ] پیاده‌سازی سیستم کاربر مهمان با localStorage
- [ ] پیاده‌سازی cache در Redis برای نتایج چند مدلی
- [ ] نوشتن تست‌های unit و integration