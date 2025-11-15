# راهنمای اجرای سرویس وب جستجوی Chroma

## خلاصه

سرویس وب FastAPI برای جستجوی معنایی در ChromaDB که:
- کوئری متنی کاربر را با مدل `text-embedding-3-small` امبدینگ می‌کند
- نتایج را از ChromaDB با فیلدهای `id`, `distance`, `score`, `document`, `metadata` برمی‌گرداند
- مسیر `/health` وضعیت ChromaDB، Redis و کالکشن را نمایش می‌دهد
- از فایل `.env` برای تنظیمات استفاده می‌کند

**مسیرهای API:**
- `POST /search` — جستجوی معنایی
- `GET /health` — بررسی وضعیت سرویس‌ها

---

این فایل مراحل گام‌به‌گام راه‌اندازی و اجرای سرویس را توضیح می‌دهد. فرض بر این است که فایل `.env` در ریشه‌ی پوشه `export-sql-chromadb` قرار دارد و شامل کلیدهای اتصال به ChromaDB، Redis و سرویس امبدینگ است.

---

## ۱. پیش‌نیازها

- Python 3.11 یا جدیدتر
- دسترسی شبکه به سرور ChromaDB (یا استفاده از سرویس کانتینری موجود در `docker-compose.yml`)
- کلید معتبر OpenAI برای مدل `text-embedding-3-small`
- دسترسی به Redis (محلی، ریموت یا کانتینری)


## ۲. تنظیم متغیرهای محیطی

فایل `.env` باید حداقل شامل متغیرهای زیر باشد:

```
CHROMA_HOST=192.168.1.68
CHROMA_PORT=8000
CHROMA_SSL=false
CHROMA_API_KEY=
CHROMA_COLLECTION=book_pages_allame
CHROMA_ANONYMIZED_TELEMETRY=False

EMBEDDING_PROVIDER=openai
EMBEDDING_MODEL=text-embedding-3-small
OPENAI_API_KEY=sk-...

REDIS_URL=redis://username:password@host:port/db     # یا REDIS_HOST/REDIS_PORT/...

APP_HOST=0.0.0.0
APP_PORT=8080
APP_LOG_LEVEL=INFO
```

> اگر `REDIS_URL` را تعریف نکنید، مقادیر `REDIS_HOST`, `REDIS_PORT`, `REDIS_DB`, `REDIS_PASSWORD` استفاده می‌شود.


## ۳. اجرای محلی (Virtualenv)

### ۳.۱. ایجاد محیط مجزا

```bash
cd export-sql-chromadb

# در سیستم‌عامل‌های Unix (Linux/macOS)
python3 -m venv .venv
source .venv/bin/activate

# در ویندوز
python -m venv .venv
.venv\Scripts\activate
```

### ۳.۲. نصب وابستگی‌ها

```bash
pip install --upgrade pip
pip install -r web_service/requirements.txt
```

> **نکته:** اگر `pip` نصب نیست:
> - در Ubuntu/Debian: `sudo apt install python3-pip`
> - در سایر توزیع‌های Linux: دستورالعمل مربوط به توزیع را دنبال کنید

### ۳.۳. اجرای سرویس

```bash
uvicorn web_service.app:app --host 0.0.0.0 --port 8080 --reload
```

پس از مشاهده پیام `Uvicorn running on http://0.0.0.0:8080`، سرویس آماده است.

### ۳.۴. تست سرویس

**بررسی Health Check:**
```bash
curl http://localhost:8080/health
```

**جستجوی معنایی:**
```bash
curl -X POST http://localhost:8080/search \
  -H "Content-Type: application/json" \
  -d '{"query": "آموزش عقاید چیست؟", "top_k": 5}'
```

**مثال با `httpie` (اگر نصب است):**
```bash
http POST http://localhost:8080/search query="آموزش عقاید چیست؟" top_k:=5
```


## ۴. اجرای Docker

```bash
cd export-sql-chromadb
docker build -t chroma-search-api .
docker run --env-file .env -p 8080:8080 chroma-search-api
```

در صورت نیاز به غیرفعال‌کردن Redis داخلی یا تغییر پورت‌ها، متغیرهای محیطی را در زمان `docker run` override کنید:

```bash
docker run --env-file .env -e APP_PORT=9090 -p 9090:9090 chroma-search-api
```


## ۵. اجرای Docker Compose

فایل `docker-compose.yml` شامل سه سرویس است: `chroma-search-api`، `redis` و `chromadb`. اگر ChromaDB یا Redis جداگانه دارید می‌توانید سرویس‌های اضافی را حذف کنید.

```bash
cd export-sql-chromadb
docker compose up --build
```

- سرویس API روی پورت `APP_PORT` (پیش‌فرض 8080) منتشر می‌شود.
- health check داخلی وضعیت `/health` را نظارت می‌کند.
- لاگ‌ها به صورت JSON در خروجی استاندارد قابل مشاهده‌اند.


## ۶. عیب‌یابی و رفع خطاها

### خطای `BaseSettings has been moved to pydantic-settings`

**مشکل:**
```
PydanticImportError: `BaseSettings` has been moved to the `pydantic-settings` package.
```

**راه‌حل:**
```bash
pip install pydantic-settings>=2.6.0
```

یا دوباره نصب کنید:
```bash
pip install -r web_service/requirements.txt
```

### خطای `TypeError: unhashable type: 'Settings'`

**مشکل:**
```
TypeError: unhashable type: 'Settings'
  File ".../web_service/app.py", line 43, in lifespan
    chroma_client = get_chroma_client(settings)
```

**راه‌حل:**
این خطا به‌خاطر استفاده از `Settings` در `@lru_cache` است که در نسخه‌های جدید Pydantic `Settings` unhashable است. این مشکل در کد رفع شده است.

اگر هنوز این خطا را می‌بینید:
1. مطمئن شوید که آخرین نسخه کد را دارید
2. کد را از repository جدید pull کنید
3. یا به‌صورت دستی `@lru_cache` را از توابع در `web_service/clients.py` حذف کنید

### خطای `pip not found`

**مشکل:**
```
Command 'pip' not found, but can be installed with: apt install python3-pip
```

**راه‌حل:**
```bash
sudo apt update
sudo apt install python3-pip python3-venv
```

### خطای اتصال به ChromaDB

**مشکل:** سرویس نمی‌تواند به ChromaDB متصل شود.

**راه‌حل:**
1. بررسی کنید که ChromaDB در حال اجرا باشد:
   ```bash
   curl http://CHROMA_HOST:CHROMA_PORT/api/v1/heartbeat
   ```

2. مقادیر `CHROMA_HOST`, `CHROMA_PORT`, `CHROMA_API_KEY` را در `.env` بررسی کنید.

3. در صورت استفاده از SSL، `CHROMA_SSL=true` را تنظیم کنید.

### خطای اتصال به Redis

**مشکل:** health check برای Redis خطا می‌دهد.

**راه‌حل:**
- اگر Redis نیاز نیست، می‌توانید سرویس را بدون Redis اجرا کنید (سرویس همچنان کار می‌کند، فقط health check خطا خواهد داد).
- اگر Redis نیاز است، `REDIS_URL` یا `REDIS_HOST`/`REDIS_PORT` را در `.env` تنظیم کنید.

### خطای `Collection not found`

**مشکل:**
```
Collection 'book_pages_allame' not found.
```

**راه‌حل:**
- مطمئن شوید که کالکشن با نام صحیح در ChromaDB وجود دارد.
- نام کالکشن را در `.env` با مقدار `CHROMA_COLLECTION` بررسی کنید.
- از اسکریپت `export-sql-backup-to-chromadb.py` برای ایجاد کالکشن استفاده کنید.

### بررسی لاگ‌ها

لاگ‌ها به صورت JSON چاپ می‌شوند. برای خواندن بهتر:
```bash
# با jq
uvicorn web_service.app:app --host 0.0.0.0 --port 8080 | jq

# یا فیلتر کردن خطاها
uvicorn web_service.app:app --host 0.0.0.0 --port 8080 2>&1 | grep -i error
```


## ۷. نکات عملیاتی

- اطمینان حاصل کنید که مدل امبدینگ در سرور ChromaDB همان مدل مورد استفاده در کوئری (`text-embedding-3-small`) باشد.
- لاگ‌ها به صورت JSON چاپ می‌شوند؛ برای خواندن ساده‌تر می‌توانید از ابزارهایی مثل `jq` استفاده کنید.
- در صورتی که ChromaDB توکن می‌خواهد، مقدار `CHROMA_API_KEY` را در `.env` تنظیم کنید.
- برای تغییر تعداد نتایج بازگشتی به صورت پیش‌فرض، مقدار `top_k` را در درخواست POST مشخص کنید.
- مسیر `/health` شامل خلاصه وضعیت Redis، ضربان ChromaDB و تعداد اسناد کالکشن است.
- در محیط توسعه، می‌توانید از فلگ `--reload` در uvicorn استفاده کنید تا تغییرات کد به صورت خودکار اعمال شود.

---

با انجام مراحل بالا، سرویس آماده پذیرش کوئری‌های معنایی و ارسال نتایج به صورت JSON خواهد بود. در صورت نیاز به سفارشی‌سازی بیشتر (مثلاً اضافه کردن مبدأ CORS، احراز هویت یا کش نتایج)، می‌توانید فایل‌های موجود در `web_service/` را توسعه دهید.



