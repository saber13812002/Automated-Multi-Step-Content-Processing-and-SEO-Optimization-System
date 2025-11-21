# مستندات API - Chroma Search Service

این سند شامل لیست کامل endpoint‌های API و نحوه استفاده از آن‌ها است.

## Base URL

```
http://localhost:8080
```

یا در محیط production:

```
https://your-domain.com
```

## Authentication

API از سیستم Bearer Token authentication پشتیبانی می‌کند. برای فعال کردن authentication، متغیر `ENABLE_API_AUTH=true` را در `.env` تنظیم کنید.

**نکته:** Authentication به صورت پیش‌فرض غیرفعال است (`ENABLE_API_AUTH=false`).

### استفاده از Token

برای استفاده از API با authentication، header زیر را به درخواست‌ها اضافه کنید:

```
Authorization: Bearer <your-token>
```

### ایجاد Token

برای ایجاد token، از endpoint `/admin/auth/tokens` استفاده کنید (نیاز به دسترسی admin دارد).

### Rate Limiting

هر token دارای یک حد مجاز روزانه است (پیش‌فرض: 1000 درخواست در روز). در صورت تجاوز از این حد، پاسخ `429 Too Many Requests` برگردانده می‌شود.

Headers مربوط به rate limiting:
- `X-RateLimit-Limit`: حد مجاز
- `X-RateLimit-Remaining`: تعداد باقی‌مانده
- `X-RateLimit-Reset`: زمان ریست (Unix timestamp)

## Endpoints

### 1. جستجوی معنایی

#### `POST /search`

انجام جستجوی معنایی در ChromaDB.

**Request Body:**

```json
{
  "query": "آموزش عقاید چیست؟",
  "top_k": 10,
  "save": false,
  "page": 1,
  "page_size": 20
}
```

**Parameters:**

- `query` (required, string): متن جستجو
- `top_k` (optional, int, default: 10): حداکثر تعداد نتایج (1-50)
- `save` (optional, bool, default: false): ذخیره نتایج در دیتابیس
- `page` (optional, int, default: 1): شماره صفحه (شروع از 1)
- `page_size` (optional, int, default: 20): تعداد نتایج در هر صفحه (1-100)

**Response:**

```json
{
  "query": "آموزش عقاید چیست؟",
  "top_k": 10,
  "returned": 10,
  "provider": "openai",
  "model": "text-embedding-3-small",
  "collection": "book_pages",
  "took_ms": 245.67,
  "timestamp": "2025-01-13T12:24:39.123456",
  "total_documents": 5678,
  "pagination": {
    "page": 1,
    "page_size": 20,
    "total_pages": 1,
    "has_next_page": false,
    "has_previous_page": false,
    "estimated_total_results": "10"
  },
  "results": [
    {
      "id": "1001-113-0-10-c6662ea8",
      "distance": 1.1791,
      "score": -0.1791,
      "document": "متن کامل سند...",
      "metadata": {
        "book_id": 1001,
        "book_title": "آموزش عقاید",
        "section_id": 1016,
        "page_id": 113,
        "source_link": "https://example.com/node/1016#p113"
      }
    }
  ]
}
```

**Example with curl:**

```bash
curl -X POST http://localhost:8080/search \
  -H "Content-Type: application/json; charset=utf-8" \
  -d '{
    "query": "آموزش عقاید چیست؟",
    "top_k": 10,
    "save": true
  }'
```

---

### 2. Health Check

#### `GET /health`

بررسی وضعیت ChromaDB، Redis و کالکشن.

**Response:**

```json
{
  "status": "ok",
  "chroma": {
    "status": "ok",
    "latency_ms": 12.5,
    "extras": {
      "heartbeat": 1763216609
    }
  },
  "collection": {
    "status": "ok",
    "latency_ms": 8.3,
    "extras": {
      "collection": "book_pages",
      "documents": 5678
    }
  },
  "redis": {
    "status": "ok",
    "latency_ms": 0.8,
    "extras": {
      "ping": true,
      "url": "redis://localhost:6379/0"
    }
  },
  "timestamp": "2025-01-13T12:24:39.123456"
}
```

---

### 3. تاریخچه جستجو

#### `GET /history`

دریافت تاریخچه جستجوهای اخیر.

**Query Parameters:**

- `limit` (optional, int, default: 20): تعداد نتایج
- `offset` (optional, int, default: 0): offset برای pagination

**Response:**

```json
{
  "searches": [
    {
      "id": 1,
      "query": "آموزش عقاید چیست؟",
      "result_count": 10,
      "took_ms": 245.67,
      "timestamp": "2025-01-13T12:24:39.123456",
      "collection": "book_pages",
      "provider": "openai",
      "model": "text-embedding-3-small"
    }
  ],
  "total": 100,
  "limit": 20,
  "offset": 0
}
```

#### `GET /history/{search_id}`

دریافت جزئیات کامل یک جستجوی خاص.

**Response:**

```json
{
  "id": 1,
  "query": "آموزش عقاید چیست؟",
  "result_count": 10,
  "took_ms": 245.67,
  "timestamp": "2025-01-13T12:24:39.123456",
  "collection": "book_pages",
  "provider": "openai",
  "model": "text-embedding-3-small",
  "results": [...]
}
```

---

### 4. Admin Endpoints

#### `GET /admin/chroma/collections`

لیست تمام کالکشن‌های موجود در ChromaDB.

**Response:**

```json
{
  "collections": [
    {
      "name": "book_pages",
      "count": 5678,
      "metadata": {}
    }
  ]
}
```

#### `POST /admin/chroma/test-connection`

تست اتصال به ChromaDB.

**Response:**

```json
{
  "success": true,
  "message": "Successfully connected to ChromaDB. Found 1 collection(s).",
  "heartbeat": 1763216609,
  "collections": ["book_pages"]
}
```

#### `POST /admin/chroma/generate-export-command`

تولید دستور export با پارامترهای قابل تنظیم.

**Request Body:**

```json
{
  "sql_path": "book_pages.sql",
  "collection": "book_pages",
  "embedding_provider": "openai",
  "embedding_model": "text-embedding-3-small",
  "reset": false,
  "batch_size": 64,
  "max_length": 500,
  "context_length": 100
}
```

**Response:**

```json
{
  "command": "python3 export-sql-backup-to-chromadb.py   --sql-path book_pages.sql   --collection book_pages   --embedding-provider openai   --embedding-model text-embedding-3-small",
  "description": "Export command for collection 'book_pages' using openai/text-embedding-3-small"
}
```

#### `POST /admin/chroma/generate-uvicorn-command`

تولید دستور uvicorn با override collection.

**Request Body:**

```json
{
  "host": "0.0.0.0",
  "port": 8080,
  "reload": true,
  "collection": "book_pages_new"
}
```

**Response:**

```json
{
  "command": "uvicorn web_service.app:app --host 0.0.0.0 --port 8080 --reload",
  "description": "Start web service on 0.0.0.0:8080 with collection override: book_pages_new",
  "env_vars": {
    "CHROMA_COLLECTION": "book_pages_new"
  }
}
```

#### `GET /admin/queries`

لیست query approvals با فیلتر.

**Query Parameters:**

- `min_count` (optional, int, default: 0): حداقل تعداد تکرار
- `status` (optional, string): فیلتر بر اساس وضعیت (approved/rejected/pending)
- `limit` (optional, int, default: 50): تعداد نتایج

**Response:**

```json
{
  "queries": [
    {
      "id": 1,
      "query": "آموزش عقاید چیست؟",
      "status": "approved",
      "approved_at": "2025-01-13T12:24:39.123456",
      "rejected_at": null,
      "notes": null,
      "search_count": 5,
      "last_searched_at": "2025-01-13T12:24:39.123456"
    }
  ],
  "stats": {
    "total": 100,
    "approved": 80,
    "rejected": 10,
    "pending": 10,
    "total_searches": 500
  }
}
```

#### `POST /admin/queries/{query}/approve`

تایید یک query.

**Response:**

```json
{
  "success": true,
  "message": "Query 'آموزش عقاید چیست؟' approved"
}
```

#### `POST /admin/queries/{query}/reject`

رد یک query.

**Response:**

```json
{
  "success": true,
  "message": "Query 'آموزش عقاید چیست؟' rejected"
}
```

#### `DELETE /admin/queries/{query}`

حذف یک query از approvals.

**Response:**

```json
{
  "success": true,
  "message": "Query 'آموزش عقاید چیست؟' deleted"
}
```

#### `GET /admin/queries/stats`

آمار query approvals.

**Response:**

```json
{
  "total": 100,
  "approved": 80,
  "rejected": 10,
  "pending": 10,
  "total_searches": 500
}
```

#### `GET /admin/jobs`

لیست 50 job اخیر.

**Response:**

```json
{
  "jobs": [
    {
      "id": 1,
      "status": "completed",
      "started_at": "2025-01-13T12:24:39.123456",
      "completed_at": "2025-01-13T12:30:45.123456",
      "duration_seconds": 366.0,
      "collection": "book_pages",
      "total_records": 1000,
      "total_books": 10,
      "total_segments": 5000,
      "total_documents_in_collection": 5000,
      "error_message": null
    }
  ]
}
```

#### `GET /admin/jobs/{job_id}`

جزئیات کامل یک job.

**Response:**

```json
{
  "id": 1,
  "status": "completed",
  "started_at": "2025-01-13T12:24:39.123456",
  "completed_at": "2025-01-13T12:30:45.123456",
  "duration_seconds": 366.0,
  "sql_path": "book_pages.sql",
  "collection": "book_pages",
  "batch_size": 64,
  "max_length": 500,
  "context_length": 100,
  "host": "localhost",
  "port": 8000,
  "ssl": false,
  "embedding_provider": "openai",
  "embedding_model": "text-embedding-3-small",
  "reset": false,
  "total_records": 1000,
  "total_books": 10,
  "total_segments": 5000,
  "total_documents_in_collection": 5000,
  "error_message": null,
  "command_line_args": "{...}"
}
```

#### `GET /approved-queries`

دریافت query‌های تایید شده برای نمایش در صفحه اصلی.

**Response:**

```json
{
  "queries": [
    {
      "id": 1,
      "query": "آموزش عقاید چیست؟",
      "status": "approved",
      "search_count": 5,
      "last_searched_at": "2025-01-13T12:24:39.123456"
    }
  ],
  "stats": {...}
}
```

#### `POST /admin/auth/users`

ایجاد کاربر جدید.

**Request Body:**

```json
{
  "username": "user1",
  "email": "user1@example.com"
}
```

**Response:**

```json
{
  "success": true,
  "user_id": 1,
  "message": "User 'user1' created"
}
```

#### `GET /admin/auth/users`

لیست تمام کاربران.

**Response:**

```json
{
  "users": [
    {
      "id": 1,
      "username": "user1",
      "email": "user1@example.com",
      "created_at": "2025-01-13T12:24:39.123456",
      "is_active": true,
      "token_count": 2
    }
  ]
}
```

#### `POST /admin/auth/tokens`

ایجاد توکن جدید.

**Request Body:**

```json
{
  "user_id": 1,
  "name": "Production API",
  "rate_limit_per_day": 1000,
  "expires_at": "2026-01-13T12:24:39.123456"
}
```

**Response:**

```json
{
  "id": 1,
  "user_id": 1,
  "token": "abc123...",
  "name": "Production API",
  "rate_limit_per_day": 1000,
  "created_at": "2025-01-13T12:24:39.123456",
  "expires_at": "2026-01-13T12:24:39.123456",
  "username": "user1",
  "email": "user1@example.com"
}
```

**نکته:** توکن فقط یک بار در پاسخ نمایش داده می‌شود. لطفاً آن را ذخیره کنید.

#### `GET /admin/auth/tokens`

لیست تمام توکن‌ها.

**Query Parameters:**

- `user_id` (optional, int): فیلتر بر اساس user ID

**Response:**

```json
{
  "tokens": [
    {
      "id": 1,
      "user_id": 1,
      "name": "Production API",
      "rate_limit_per_day": 1000,
      "created_at": "2025-01-13T12:24:39.123456",
      "expires_at": "2026-01-13T12:24:39.123456",
      "is_active": true,
      "last_used_at": "2025-01-13T15:30:00.123456",
      "username": "user1",
      "email": "user1@example.com",
      "usage_today": 150
    }
  ]
}
```

#### `DELETE /admin/auth/tokens/{token_id}`

غیرفعال کردن یک توکن.

**Response:**

```json
{
  "success": true,
  "message": "Token #1 revoked"
}
```

#### `GET /admin/auth/tokens/{token_id}/usage`

آمار استفاده یک توکن.

**Response:**

```json
{
  "token_id": 1,
  "usage_today": 150,
  "rate_limit": 1000,
  "remaining": 850,
  "reset_at": "2025-01-14T00:00:00.000000"
}
```

---

## Error Responses

تمام endpoints در صورت خطا، response با status code مناسب برمی‌گردانند:

```json
{
  "detail": "Error message here"
}
```

**Status Codes:**

- `200 OK`: موفقیت
- `400 Bad Request`: درخواست نامعتبر
- `404 Not Found`: منبع یافت نشد
- `429 Too Many Requests`: تعداد درخواست بیش از حد (در نسخه‌های آینده با rate limiting)
- `500 Internal Server Error`: خطای سرور
- `502 Bad Gateway`: خطا در اتصال به ChromaDB

---

## Environment Variables

برای تنظیمات، از فایل `.env` استفاده کنید. لیست کامل متغیرها در `.env.example` موجود است.

---

## مستندات تعاملی

- **Swagger UI**: `http://localhost:8080/docs`
- **ReDoc**: `http://localhost:8080/redoc`

---

## مثال‌های استفاده

### Python

```python
import requests

# جستجو
response = requests.post(
    "http://localhost:8080/search",
    json={
        "query": "آموزش عقاید چیست؟",
        "top_k": 10,
        "save": True
    },
    headers={"Content-Type": "application/json; charset=utf-8"}
)
data = response.json()
print(data["results"])
```

### JavaScript (Fetch API)

```javascript
// جستجو
fetch('http://localhost:8080/search', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json; charset=utf-8',
    'Accept': 'application/json; charset=utf-8'
  },
  body: JSON.stringify({
    query: 'آموزش عقاید چیست؟',
    top_k: 10,
    save: true
  })
})
.then(response => response.json())
.then(data => console.log(data.results));
```

---

## نکات مهم

1. تمام endpoint‌ها از UTF-8 encoding استفاده می‌کنند
2. برای جستجو، مدل embedding باید همان مدلی باشد که برای export استفاده شده است
3. Pagination برای نتایج جستجو قابل فعال/غیرفعال‌سازی است
4. Query approvals به صورت خودکار هنگام ذخیره جستجو به‌روزرسانی می‌شوند

---

## ⚠️ قوانین به‌روزرسانی مستندات API

### قانون طلایی: همگام‌سازی تغییرات

**هر تغییری که در API اعمال می‌شود، باید در این مستندات به‌روز شود.**

این قانون برای اطمینان از این است که:
- برنامه‌نویسان استفاده‌کننده از API همیشه اطلاعات دقیق و به‌روز داشته باشند
- مثال‌های کد قابل اجرا و صحیح باشند
- تغییرات breaking به درستی مستند شوند

### چک‌لیست به‌روزرسانی مستندات:

هنگام اعمال تغییرات در API، حتماً موارد زیر را بررسی کنید:

#### 1. تغییرات در Endpoint‌ها
- [ ] **اضافه کردن endpoint جدید:** 
  - بخش جدید در "Endpoints" اضافه شده است
  - Request/Response examples اضافه شده است
  - Parameters و validation rules توضیح داده شده است
  
- [ ] **تغییر در endpoint موجود:**
  - Request/Response schema به‌روز شده است
  - مثال‌های کد به‌روز شده است
  - تغییرات breaking در بخش "Migration Guide" (در صورت نیاز) توضیح داده شده است

#### 2. تغییرات در Request/Response Models
- [ ] **اضافه کردن فیلد جدید:**
  - فیلد در schema توضیح داده شده است
  - مثال‌های JSON به‌روز شده است
  - Default values و validation rules مشخص شده است

- [ ] **تغییر در فیلد موجود:**
  - تغییرات در توضیحات منعکس شده است
  - مثال‌ها به‌روز شده است
  - Breaking changes مشخص شده است

#### 3. تغییرات در Pagination
- [ ] منطق pagination در مستندات توضیح داده شده است
- [ ] مثال‌های pagination به‌روز شده است
- [ ] نحوه محاسبه `has_next_page` و `estimated_total_results` توضیح داده شده است

#### 4. تغییرات در Error Handling
- [ ] کدهای خطای جدید در بخش "Error Responses" اضافه شده است
- [ ] مثال‌های error response به‌روز شده است

#### 5. مثال‌های کد
- [ ] مثال‌های curl به‌روز شده و قابل اجرا هستند
- [ ] مثال‌های Python/JavaScript به‌روز شده و کار می‌کنند
- [ ] مثال‌ها با آخرین تغییرات API هماهنگ هستند

### مثال‌های تغییراتی که نیاز به به‌روزرسانی دارند:

#### ✅ مثال صحیح:
```markdown
**تغییر:** اضافه شدن فیلد `page_size` به request
**اقدامات:**
1. در بخش `/search` endpoint، فیلد `page_size` اضافه شد
2. مثال JSON request به‌روز شد
3. توضیحات validation rules اضافه شد
4. مثال‌های curl/Python به‌روز شد
```

#### ❌ مثال نادرست:
```markdown
**تغییر:** اضافه شدن فیلد `page_size` به request
**اقدامات:**
- فقط کد backend به‌روز شد
- مستندات فراموش شد ❌
```

### نکات مهم برای توسعه‌دهندگان:

1. **همیشه قبل از commit:** مستندات را بررسی کنید
2. **برای تغییرات breaking:** یک بخش "Migration Guide" یا "Breaking Changes" اضافه کنید
3. **برای تغییرات جدید:** مثال‌های کامل و قابل اجرا اضافه کنید
4. **برای تغییرات در pagination:** منطق را به صورت واضح توضیح دهید (مثلاً چرا `estimated_total_results` ممکن است "75+" باشد به جای "76")

### فرآیند پیشنهادی:

1. **تغییر در کد:** ابتدا تغییرات را در backend اعمال کنید
2. **به‌روزرسانی Schema:** `schemas.py` را به‌روز کنید
3. **به‌روزرسانی مستندات:** این فایل را به‌روز کنید
4. **تست مثال‌ها:** مطمئن شوید مثال‌های کد کار می‌کنند
5. **Review:** قبل از merge، مستندات را review کنید

---

**یادآوری:** این مستندات تنها منبع رسمی برای استفاده از API است. هر تغییری که در API اعمال می‌شود، باید در اینجا منعکس شود تا برنامه‌نویسان استفاده‌کننده بتوانند به درستی از API استفاده کنند.

