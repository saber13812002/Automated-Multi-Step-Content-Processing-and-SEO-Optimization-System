<!-- 474b973b-ab78-42a3-a9c3-41baf5a6ee7f 0a41e8d3-77a4-4e18-9a5e-48645078e80f -->
# رفع مشکل Encoding فارسی

## مشکل

متن‌های فارسی به صورت mojibake (مثل Ø¨ÛŒÙ†ÛŒ) نمایش داده می‌شوند به جای فارسی صحیح. این مشکل در چند نقطه می‌تواند باشد:

## نقاط احتمالی مشکل

1. **SQLite Connection Encoding**: اتصال SQLite باید UTF-8 باشد
2. **FastAPI JSON Response**: باید charset=UTF-8 header داشته باشد
3. **Fetch Response Encoding**: JavaScript باید encoding را درست بخواند
4. **HTML charset**: باید UTF-8 باشد (قبلاً تنظیم شده ✅)

## راه‌حل‌ها

### 1. SQLite Connection Encoding

- اتصال SQLite را با `encoding='utf-8'` یا `detect_types=sqlite3.PARSE_DECLTYPES` تنظیم کنیم
- یا از `conn.execute("PRAGMA encoding='UTF-8'")` استفاده کنیم

### 2. FastAPI Response Encoding  

- اضافه کردن `charset=utf-8` به Content-Type header در JSONResponse
- یا استفاده از `response.media_type` با charset

### 3. JavaScript Fetch Encoding

- اضافه کردن `.then(response => response.text().then(text => JSON.parse(text)))` برای اطمینان از UTF-8
- یا استفاده از `response.json()` که خودش encoding را مدیریت می‌کند

### 4. Database Text Storage

- اطمینان از اینکه SQLite TEXT columns با UTF-8 ذخیره می‌شوند
- بررسی اینکه `json.dumps` با `ensure_ascii=False` استفاده می‌شود (قبلاً تنظیم شده ✅)

## فایل‌های مورد تغییر

- `export-sql-chromadb/web_service/database.py` - تنظیم encoding در SQLite connection
- `export-sql-chromadb/web_service/app.py` - اضافه کردن charset به JSON responses
- `export-sql-chromadb/web_service/static/index.html` - بررسی encoding در JavaScript fetch (اختیاری)