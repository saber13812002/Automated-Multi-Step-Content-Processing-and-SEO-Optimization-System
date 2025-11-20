# گزارش پایش امبدینگ و کیفیت (نوامبر 2025)

این سند مراحل پیشنهادی برای پایش کیفیت سگمنت‌سازی و صحت کالکشن آزمایشی را خلاصه می‌کند. ابزارهای جدید:

1. `dataset_stats.py` – استخراج آمار رکورد/پاراگراف/سگمنت و تخمین زمان.
2. `tests/test_paragraph_glue.py` – مقایسه رفتار Glue با مدل لوکال (ParsBERT).
3. `tools/benchmark_embeddings.py` – اجرای مجموعه پرسش‌های آزمایشی روی کالکشن Chroma و محاسبه hit rate.
4. APIهای ادمین – حذف Jobهای خراب و پاکسازی کالکشن‌های تستی.

## روش توصیه‌شده

### ۱. آمار دیتاست
```bash
cd export-sql-chromadb
python dataset_stats.py \
  --sql-path export-sql-chromadb/books_pages_mini.sql \
  --max-length 500 \
  --context 100 \
  --min-paragraph-lines 3 \
  --segments-per-second 45 \
  --json-out stats/books_pages_mini.json
```
- نرخ `segments-per-second` را با ارسال حداقل ۱۰ سند آزمایشی به مدل/کالکشن اندازه‌گیری کنید (زمان کل / تعداد سگمنت‌های batch).

گزارش JSON شامل:
- توزیع خطوط قبل/بعد از ادغام
- تعداد پاراگراف‌های کوتاه و تیتر
- تعداد سند کامل صفحه افزوده‌شده
- تخمین زمان اجرای کامل بر اساس نرخ واقعی (۱۰ سند آزمایشی)

### ۲. تست Glue با مدل لوکال
```bash
pytest export-sql-chromadb/tests/test_paragraph_glue.py -k glue
```
الزام: نصب `transformers`, `torch`, `numpy`. تست بررسی می‌کند که با ادغام پاراگراف‌های کوتاه، تعداد سگمنت کمتر و شباهت کوئری بهبود پیدا کند یا افت نکند.

### ۳. بنچمارک کالکشن آزمایشی
ورودی فایل JSON از نمونه پرسش‌ها:
```json
[
  {
    "query": "شرط انسان زیستن چیست؟",
    "expected_ids": ["1001-15-0-0"],
    "expected_keywords": ["انسان کمال جو"]
  }
]
```
اجرای بنچمارک:
```bash
python tools/benchmark_embeddings.py \
  --collection book_pages_test \
  --queries benchmark/queries.json \
  --json-out benchmark/results.json
```
خروجی شامل latency میانگین، P95 و hit-rate براساس شناسه و کلیدواژه است. این اعداد را قبل و بعد از تغییرات ثبت کنید.

### ۴. پاکسازی
- حذف job خراب:
  ```
  DELETE /admin/jobs/{job_id}
  ```
- حذف کالکشن تستی:
  ```
  DELETE /admin/chroma/collections/{collection_name}
  ```
هر دو از طریق Admin UI قابل مصرف هستند و پاسخ موفق شامل پیام تأیید است.

