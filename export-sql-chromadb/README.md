# راهنمای راه‌اندازی و استفاده

این پروژه اسکریپتی برای خواندن داده‌های `book_pages.sql` و بارگذاری پاراگراف‌های تمیز‌شده در ChromaDB فراهم می‌کند. همچنین اسکریپت مستقلی برای تست و مشاهده نتایج جستجوی معنایی در مجموعه‌ی ایجاد شده وجود دارد.

## پیش‌نیازها

- Python 3.10 یا جدیدتر
- دسترسی به سرویس ChromaDB (لوکال یا از طریق شبکه)
- کلید API برای OpenAI (در صورت استفاده از بردارهای OpenAI)

## نصب وابستگی‌ها

```bash
python -m venv .venv
.venv\Scripts\activate             # در ویندوز
# یا
sudo apt update
sudo apt install python3.12-venv
python3 -m venv .venv
source .venv/bin/activate          # در لینوکس/مک

pip install -r requirements.txt
```

## پیکربندی متغیرهای محیطی

می‌توانید متغیرها را به صورت دستی یا با استفاده از فایل `.env` تنظیم کنید. مهم‌ترین گزینه‌ها:

- `BOOK_PAGES_SQL`: مسیر فایل SQL (پیش‌فرض `book_pages.sql`)
- `CHROMA_HOST`, `CHROMA_PORT`, `CHROMA_SSL`, `CHROMA_API_KEY`: تنظیمات اتصال به سرور ChromaDB
- `CHROMA_COLLECTION`: نام کالکشن مقصد (پیش‌فرض `book_pages`)
- `OPENAI_API_KEY`: کلید OpenAI برای تولید امبدینگ
- `CHUNK_MAX_LENGTH`: طول هر قطعه متنی (پیش‌فرض ۲۰۰ کاراکتر)
- `CHUNK_CONTEXT_LENGTH`: طول متن زمینه قبل و بعد از هر قطعه (پیش‌فرض ۱۰۰ کاراکتر)
- `CHROMA_BATCH_SIZE`: اندازه دسته برای بارگذاری (پیش‌فرض ۴۸)

## اجرای اسکریپت صادرات

```bash
python export-sql-backup-to-chromadb.py \
  --sql-path book_pages.sql \
  --collection book_pages \
  --host 10.0.0.5 \
  --port 8000 \
  --embedding-provider openai \
  --reset
```


```bash
python3 export-sql-backup-to-chromadb.py   --sql-path book_pages_mini.sql   --collection book_pages_mini   --host 192.168.1.68   --port 8000  --embedding-provider openai   --reset
```


- گزینه `--reset` کالکشن قبلی را حذف و داده‌های جدید را جایگزین می‌کند.
- اگر از ChromaDB توکار (Persist Client) استفاده می‌کنید، گزینه `--persist-directory ./chroma-store` را اضافه کنید.
- در صورت نبود کلید OpenAI می‌توانید `--embedding-provider none` را انتخاب کنید؛ در این حالت فرض می‌شود سمت سرور امبدینگ تولید می‌شود.

### منطق قطعه‌بندی

1. هر رکورد صفحه از SQL خوانده و HTML آن به متن ساده تبدیل می‌شود.
2. متن بر اساس پاراگراف (فاصله‌ی دو خط) جدا می‌شود.
3. هر پاراگراف به قطعات حداکثر ۲۰۰ کاراکتری تقسیم می‌شود.
4. برای هر قطعه ۱۰۰ کاراکتر قبل و بعد به‌عنوان زمینه اضافه می‌شود تا مفهوم حفظ شود.
5. هر قطعه به همراه متادیتا (کتاب، بخش، لینک، شماره پاراگراف و Segment) در ChromaDB ذخیره می‌شود.

## تست و ارزیابی نتایج

پس از پایان بارگذاری می‌توانید از اسکریپت زیر برای ارسال کوئری و بررسی نتایج استفاده کنید:

```bash
python verify_chroma_export.py \
  --collection book_pages \
  --query "دین چیست" \
  --host 10.0.0.5 \
  --port 8000 \
  --top-k 5
```

خروجی شامل شناسه، فاصله، لینک منبع و پیش‌نمایش هر قطعه است تا بتوانید کیفیت داده‌های ذخیره‌شده را ارزیابی کنید.

## نکات تکمیلی

- در متادیتا، لینک اصلی صفحه (`source_link`) ذخیره می‌شود تا ارجاع به منبع حفظ گردد.
- فیلد `error` از فایل SQL نیز منتقل می‌شود تا در صورت وجود خطا یا هشدار در منبع بتوانید آن را ردیابی کنید.
- در صورت نیاز به قطعه‌بندی متفاوت، پارامترهای `--max-length` و `--context` را تغییر دهید.
- **امبدینگ‌ها چگونه ساخته می‌شوند؟**
  - پارامتر `--embedding-provider` تعیین می‌کند که آیا بردارها هنگام وارد کردن داده ساخته شوند یا خیر.
  - مقدار پیش‌فرض `openai` با مدل `text-embedding-3-small` برای هر سگمنت یک بردار ۱۵۳۶ بعدی تولید می‌کند و آن را به کالکشن اضافه می‌نماید؛ این حالت برای وقتی مناسب است که می‌خواهید همه‌چیز سمت اسکریپت انجام شود.
  - اگر گزینه‌ی `--embedding-provider none` را انتخاب کنید، فقط متن و متادیتا ذخیره می‌شوند و باید در مراحل بعدی (مثلاً روی سرور Chroma یا سرویس دیگر) امبدینگ ساخته شود. در غیر این صورت جست‌وجوی برداری نتیجه‌ای نخواهد داشت.
  - هنگام جست‌وجو (چه با `verify_chroma_export.py` و چه با API‌های دیگر) همان مدل باید برای تولید امبدینگ سؤال استفاده شود؛ چون Chroma بردار کوئری را با بردارهای ذخیره‌شده مقایسه می‌کند.

## سرویس وب جستجوی معنایی

یک سرویس FastAPI در مسیر `web_service/` اضافه شده تا کوئری کاربر را گرفته، با همان مدل `text-embedding-3-small` امبدینگ کند و روی ChromaDB جستجو انجام دهد.

### اجرای محلی

```bash
cd export-sql-chromadb
python -m venv .venv
.venv\Scripts\activate  # یا source .venv/bin/activate
pip install -r web_service/requirements.txt
uvicorn web_service.app:app --reload --host 0.0.0.0 --port 8080
```

سرویس از همان `.env` استفاده می‌کند. مسیرها:

- `POST /search` ورودی:

```json
{
  "query": "آموزش عقاید چیست؟",
  "top_k": 5
}
```

خروجی شامل `id`, `distance`, `score`, `document`, `metadata` و اطلاعات مدل است.

- `GET /health` وضعیت ChromaDB، Redis، و آمار کالکشن را بازمی‌گرداند.

### متغیرهای محیطی مرتبط با سرویس وب

- `APP_HOST` و `APP_PORT` برای کنترل آدرس و پورت سرویس (پیش‌فرض: `0.0.0.0:8080`)
- `REDIS_URL` یا ترکیب `REDIS_HOST`, `REDIS_PORT`, `REDIS_DB`, `REDIS_PASSWORD`
- سایر متغیرها همان مقادیر مورد استفاده در اسکریپت‌های صادرات و اعتبارسنجی (`CHROMA_*`, `OPENAI_API_KEY`, `EMBEDDING_MODEL`, ...)

### Docker

```bash
cd export-sql-chromadb
docker build -t chroma-search-api .
docker run --env-file .env -p 8080:8080 chroma-search-api
```

### Docker Compose

```bash
cd export-sql-chromadb
docker compose up --build
```

سرویس با کانتینر Redis بالا می‌آید و تمام متغیرهای محیطی از طریق `.env` یا متغیرهای محیطی سیستم تزریق‌پذیر هستند. Healthcheck داخلی وضعیت `/health` را پایش می‌کند.
در فایل `docker-compose.yml` یک سرویس اختیاری `chromadb` نیز تعریف شده تا در محیط‌های توسعه یا تست بتوانید ChromaDB را به‌صورت کانتینری اجرا کنید. در صورت استفاده از سرور خارجی، می‌توانید این سرویس را حذف یا غیرفعال کنید.