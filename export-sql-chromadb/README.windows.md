## راهنمای اجرای پروژه در ویندوز

این راهنما مراحل کامل کار با اسکریپت `export-sql-backup-to-chromadb.py` را در ویندوز توضیح می‌دهد؛ فرض بر این است که می‌خواهید داده‌های نمونه‌ی `books_pages_mini.sql` را به یک ChromaDB که داخل Docker اجرا می‌شود منتقل کنید و سپس نتیجه را تست کنید.

---

### ۱. آماده‌سازی پیش‌نیازها
- **Python 3.10+** نصب کنید و مسیر آن را در `Path` قرار دهید.
- **Docker Desktop** را اجرا کنید تا سرویس‌های کانتینری در دسترس باشند.
- اگر قصد دارید از امبدینگ OpenAI استفاده کنید، از قبل کلید `OPENAI_API_KEY` را داشته باشید؛ در غیر این صورت می‌توانید گزینه‌ی بدون امبدینگ را انتخاب کنید.

---

### ۲. ساخت و فعال‌سازی محیط مجازی
```powershell
cd export-sql-chromadb
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

---

### ۳. تنظیم متغیرهای محیطی
1. فایل نمونه‌ی تنظیمات (مثلاً `.env.dev`) را بررسی کنید و در صورت نیاز کپی‌ای با نام `.env` بسازید:
   ```powershell
   Copy-Item .env.dev .env
   ```
2. مقدارهای مهم را در `.env` (یا مستقیماً در محیط پاورشل) ست کنید:
   - `CHROMA_HOST`, `CHROMA_PORT`: آدرس Chroma داخل Docker (برای حالت لوکال معمولاً `localhost` و `8000`).
   - `CHROMA_COLLECTION`: نام کالکشن مقصد؛ پیش‌فرض `book_pages` است، اما می‌توانید نام دیگری انتخاب کنید. دقت کنید همان مقدار در اسکریپت اکسپورت و هر سرویس مصرف‌کننده استفاده شود.
   - `CHROMA_API_KEY`: در صورت نیاز به احراز هویت Chroma.
   - `OPENAI_API_KEY`: فقط اگر می‌خواهید امبدینگ سمت کلاینت تولید شود.
   - `CHUNK_MAX_LENGTH`, `CHUNK_CONTEXT_LENGTH`, `CHROMA_BATCH_SIZE`: در صورت تمایل برای تغییر اندازه‌ی قطعه‌ها یا دسته‌ها.

---

### ۴. راه‌اندازی Docker ChromaDB
```powershell
cd export-sql-chromadb
docker compose up -d         # از docker-compose.yml این پوشه استفاده می‌کند
curl http://localhost:8000/api/v1/heartbeat
```
اگر از پورت یا هاست دیگری استفاده می‌کنید، مقادیر را مطابق `.env` تغییر دهید.

---

### ۵. اجرای اسکریپت با داده‌ی نمونه
در این سناریو به جای فایل بزرگ، از `books_pages_mini.sql` استفاده می‌کنیم تا مصرف توکن و زمان پردازش پایین بماند. این فایل حدود چند ده رکورد دارد و برای تست اولیه کافی است.

```powershell
python export-sql-backup-to-chromadb.py `
  --sql-path books_pages_mini.sql `
  --collection book_pages_mini `
  --embedding-provider none `
  --reset
```

```powershell
python export-sql-backup-to-chromadb.py   --sql-path books_pages_mini.sql   --collection book_pages_mini --embedding-provider none   --reset
```


- اگر می‌خواهید امبدینگ کلاینتی بسازید و هزینه‌ی توکن قابل قبول است، گزینه‌ی `--embedding-provider openai --openai-api-key "..."` را جایگزین کنید. مدل پیش‌فرض `text-embedding-3-small` است که نسبت به مدل‌های بزرگ هزینه‌ی کمتری دارد.
- با انتخاب `--embedding-provider none`، داده بدون بردار ذخیره می‌شود و می‌توانید تولید امبدینگ را به سرور یا مرحله‌ی دیگری بسپارید؛ این روش مصرف توکن را به صفر می‌رساند.
- `--reset` باعث حذف کالکشن قبلی با همان نام می‌شود؛ اگر داده‌ی قبلی برایتان مهم است، این گزینه را بردارید.

---

### ۶. پایش مصرف توکن
- حجم توکن به طور مستقیم به طول متن هر قطعه و تعداد قطعه‌ها بستگی دارد؛ `books_pages_mini.sql` تعداد محدودی صفحه دارد و به صورت پیش‌فرض هر قطعه حدود ۳۰۰ کاراکتر (متن + متن زمینه) است. برای اطمینان از پایین ماندن هزینه:
  - طول قطعه را با `--max-length` پایین‌تر نگه دارید.
  - فقط در صورت نیاز هربار `--reset` را فعال کنید تا از ارسال مجدد داده جلوگیری شود.
  - از گزارش‌های داشبورد OpenAI برای مشاهده‌ی دقیق مصرف استفاده کنید.

---

### ۷. تست نتایج پس از بارگذاری
```powershell
python verify_chroma_export.py `
  --collection book_pages_mini `
  --query "دین چیست" `
  --host localhost `
  --port 8000 `
  --top-k 5
```
- خروجی شامل `id`, `distance`, `metadata.source_link` و بخش‌هایی از متن است تا کیفیت داده‌ها را ارزیابی کنید.
- اگر اسکريپت در حالت `--embedding-provider none` اجرا شده باشد، جست‌وجوی برداری ممکن است نتیجه‌ای ندهد مگر آن‌که سمت سرور امبدینگ تولید شود.

---

### ۸. جمع‌بندی و توقف سرویس‌ها
```powershell
docker compose down
deactivate
```
- اگر قصد دارید Docker و محیط مجازی فعال بمانند، می‌توانید این مرحله را به پایان کار موکول کنید.

این مراحل برای سناریوی ویندوز طراحی شده‌اند و با داده‌ی کوچک `books_pages_mini.sql`، مصرف زمان و توکن به حداقل می‌رسد. در صورت مهاجرت به فایل‌های بزرگ‌تر، فقط کافی است مقدار `--sql-path` و تنظیمات کالکشن را به‌روز کنید.

