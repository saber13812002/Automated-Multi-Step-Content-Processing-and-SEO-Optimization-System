<!-- f6dd9505-4a8d-4abc-ba1b-1e57b750dd17 cfa8b030-345d-4d8f-9eb2-8b3483467c7a -->
# طرح پیشنهادی برای اصلاح کویری‌ها

## گام‌ها

1. **بازنویسی منبع داده کویری‌ها (`web_service/database.py`)**  

- پیاده‌سازی کوئری جدیدی که `search_history` را بر اساس `query` گروه‌بندی می‌کند، ستون‌های `search_count` و `last_searched_at` را می‌سازد و در صورت وجود به `query_approvals` جوین می‌زند.  
- فیلتر `status` و `min_count` را روی دادهٔ ترکیبی اعمال کنید و در صورت نداشتن رکورد تأیید، وضعیت پیش‌فرض `pending` بدهید.  
- تابع `get_query_stats` را بر اساس همین مجموعه‌داده بازنویسی کنید تا اعداد واقعی (total/approved/rejected/pending/total_searches) را برگرداند.  
- تابع جدیدی مثل `get_top_search_queries(limit, min_count)` برای «بیشترین جستجوهای یونیک» اضافه کنید.

2. **به‌روزرسانی API (`web_service/app.py` + `schemas.py`)**  

- مدل `QueryApprovalItem` را طوری تنظیم کنید که در صورت نبود شناسه از جدول approvals همچنان معتبر باشد (مثلاً `id: Optional[int]`).  
- endpointهای `/admin/queries`, `/admin/queries/stats`, `/approved-queries` را با خروجی جدید سازگار کنید و در صورت نیاز شناسهٔ جایگزین بسازید.  
- endpoint تازه‌ای (مثلاً `GET /history/top`) پیاده‌سازی کنید که خروجی `get_top_search_queries` را با یک مدل پاسخ جدید (مثلاً `TopQueryItem/TopQueriesResponse`) ارائه دهد.

3. **اصلاح رابط ادمین (`web_service/static/admin.html`)**  

- منطق `loadQueries` و نمایش لیست را بررسی کنید تا با فیلدهای جدید (و پیش‌فرض pending) هماهنگ باشد و در صورت نیاز پیام‌های خطا/آمار تازه را نمایش دهد.  
- بخش آمار را تست کنید تا اعداد جدید را درست نشان دهد.

4. **تقویت صفحهٔ اصلی (`web_service/static/index.html`)**  

- در تابع‌های تاریخچه (مثل `loadHistory`/`displayHistory`) چیدمان دو ستونه بسازید: ستون اول ۱۰ جستجوی اخیر، ستون دوم «پربسامدترین جستجوهای یونیک».  
- فراخوانی endpoint جدید را اضافه کنید و نتایج را با تعداد تکرار و آخرین زمان نمایش دهید؛ هندلینگ خطا و متن جایگزین اضافه شود.

## TODOهای پیاده‌سازی

- db-queries: بازنویسی لایهٔ دیتابیس برای ترکیب search_history و approvals
- api-endpoints: سازگارکردن endpointهای ادمین و افزودن `/history/top`
- admin-ui: همراستا کردن UI مدیریت با دادهٔ جدید
- public-ui-top: افزودن ستون «بیشترین جستجوها» به صفحهٔ اصلی