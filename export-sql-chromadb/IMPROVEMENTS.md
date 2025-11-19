# پیشنهادات بهبود و بهینه‌سازی

این سند شامل پیشنهادات بهبود عملکرد، کیفیت و قابلیت‌های سیستم export و search است.

> 📖 برای راهنمای کامل نصب و استفاده، به [README.md](README.md) مراجعه کنید.

---

## فهرست مطالب

- [بهینه‌سازی عملکرد](#بهینه‌سازی-عملکرد)
- [بهبود کیفیت Chunking](#بهبود-کیفیت-chunking)
- [تست و اعتبارسنجی](#تست-و-اعتبارسنجی)
- [به‌روزرسانی تدریجی](#به‌روزرسانی-تدریجی)
- [بهبود جستجو](#بهبود-جستجو)
- [مانیتورینگ و آمار](#مانیتورینگ-و-آمار)
- [بهینه‌سازی هزینه](#بهینه‌سازی-هزینه)
- [ابزارهای کمکی](#ابزارهای-کمکی)
- [اولویت‌بندی پیشنهادی](#اولویت‌بندی-پیشنهادی)

---

## بهینه‌سازی عملکرد

### افزایش Batch Size

برای exportهای بزرگ (مثل 247K+ chunk)، می‌توانید batch size را افزایش دهید تا سرعت export بیشتر شود:

```bash
# بجای batch-size پیش‌فرض 48، می‌توانید تا 100-200 افزایش دهید
python3 export-sql-backup-to-chromadb.py \
  --sql-path book_pages.sql \
  --collection book_pages_text-embedding-3-large \
  --embedding-model text-embedding-3-large \
  --batch-size 100  # یا 150-200 برای سرعت بیشتر
```

**نکات:**
- Batch size بالاتر = سرعت بیشتر اما مصرف حافظه بیشتر
- برای `text-embedding-3-large`: پیشنهاد 100-150
- برای `text-embedding-3-small`: می‌توانید تا 200 هم بروید
- اگر خطای memory دریافت کردید، batch size را کاهش دهید

### پردازش موازی Embeddings

**پیشنهاد:** استفاده از چند thread برای تولید embeddings به صورت موازی

**مزایا:**
- کاهش زمان export برای داده‌های بزرگ
- استفاده بهتر از منابع سیستم
- بهینه‌سازی هزینه API calls

**پیاده‌سازی:**
- استفاده از `concurrent.futures.ThreadPoolExecutor`
- تقسیم batchها به چند thread
- مدیریت rate limiting برای OpenAI API

### بهینه‌سازی I/O

- استفاده از async I/O برای خواندن فایل SQL
- Buffering بهتر برای نوشتن در ChromaDB
- Connection pooling برای ChromaDB HTTP client

---

## بهبود کیفیت Chunking

### Chunking هوشمندتر با Sentence Splitting

**مشکل فعلی:** Chunking بر اساس کاراکتر ممکن است جمله‌ها را قطع کند.

**راه‌حل:** استفاده از sentence splitting برای متن فارسی

**مزایا:**
- حفظ مرز جمله‌ها
- بهبود کیفیت embeddings
- نتایج جستجوی بهتر

**پیاده‌سازی:**
```python
# استفاده از کتابخانه‌هایی مثل:
# - hazm (برای فارسی)
# - nltk
# - spacy

def smart_segment_paragraph(paragraph, max_length, context_length):
    # 1. تقسیم به جملات
    sentences = split_sentences(paragraph)
    
    # 2. ترکیب جملات تا رسیدن به max_length
    chunks = []
    current_chunk = []
    current_length = 0
    
    for sentence in sentences:
        if current_length + len(sentence) <= max_length:
            current_chunk.append(sentence)
            current_length += len(sentence)
        else:
            if current_chunk:
                chunks.append(' '.join(current_chunk))
            current_chunk = [sentence]
            current_length = len(sentence)
    
    # 3. اضافه کردن context overlap
    # ...
```

### Deduplication

**پیشنهاد:** حذف chunkهای تکراری قبل از export

**مزایا:**
- کاهش حجم کالکشن
- بهبود کیفیت search
- کاهش هزینه storage

**روش:**
- محاسبه hash برای هر chunk
- مقایسه hashها
- حذف duplicates (یا نگه‌داری فقط یکی)

### بهبود Context Overlap

**پیشنهاد:** Context overlap هوشمندتر بر اساس محتوا

- Context بیشتر برای chunkهای مهم (مثل عنوان‌ها)
- Context کمتر برای chunkهای معمولی
- استفاده از metadata برای تعیین اهمیت

---

## تست و اعتبارسنجی

### اسکریپت تست کیفیت

**پیشنهاد:** ایجاد اسکریپت برای تست کیفیت embeddings و search

**قابلیت‌ها:**
- تست توزیع similarity scores
- تست queryهای نمونه
- مقایسه نتایج با ground truth
- گزارش کیفیت embeddings

**مثال استفاده:**
```bash
python validate_export_quality.py \
  --collection book_pages_text-embedding-3-large \
  --test-queries queries.txt \
  --output report.json
```

### مقایسه مدل‌ها

**پیشنهاد:** مقایسه `text-embedding-3-small` با `text-embedding-3-large`

**روش:**
1. Export با هر دو مدل (در collectionهای جداگانه)
2. تست با queryهای واقعی
3. مقایسه نتایج:
   - دقت (precision)
   - پوشش (recall)
   - زمان پاسخ
   - هزینه

**مثال:**
```bash
# Export با small
python3 export-sql-backup-to-chromadb.py \
  --collection book_pages_small \
  --embedding-model text-embedding-3-small

# Export با large
python3 export-sql-backup-to-chromadb.py \
  --collection book_pages_large \
  --embedding-model text-embedding-3-large

# تست مقایسه
python compare_models.py \
  --collection-small book_pages_small \
  --collection-large book_pages_large \
  --queries test_queries.txt
```

### Validation Script

**پیشنهاد:** اسکریپت برای بررسی صحت export

**بررسی‌ها:**
- تعداد رکوردها با SQL file
- تعداد chunkهای تولید شده
- صحت metadata
- تست sample queries
- بررسی duplicate IDs

---

## به‌روزرسانی تدریجی

### فقط رکوردهای جدید

**پیشنهاد:** قابلیت افزودن فقط رکوردهای جدید به کالکشن موجود

**مزایا:**
- صرفه‌جویی در زمان
- کاهش هزینه API calls
- امکان به‌روزرسانی منظم

**پیاده‌سازی:**
```bash
# شناسایی رکوردهای جدید
python3 export-sql-backup-to-chromadb.py \
  --sql-path book_pages.sql \
  --collection book_pages_text-embedding-3-large \
  --incremental \
  --last-export-id 29848
```

**ویژگی‌ها:**
- ذخیره last_export_id در job record
- مقایسه record_id با last_export_id
- فقط export رکوردهای جدید
- به‌روزرسانی رکوردهای تغییر یافته

### Update Existing Records

**پیشنهاد:** به‌روزرسانی chunkهای موجود در صورت تغییر محتوا

**روش:**
- محاسبه hash محتوا
- مقایسه با hash موجود
- Update در صورت تغییر
- حذف chunkهای قدیمی

---

## بهبود جستجو

### Hybrid Search

**پیشنهاد:** ترکیب semantic search با keyword search

**مزایا:**
- نتایج دقیق‌تر
- پوشش بهتر
- رتبه‌بندی بهتر

**پیاده‌سازی:**
```python
# ترکیب semantic + keyword
semantic_results = chroma_collection.query(
    query_texts=[query],
    n_results=top_k
)

keyword_results = chroma_collection.query(
    query_texts=[query],
    n_results=top_k,
    where={"$or": [
        {"book_title": {"$contains": keyword}},
        {"section_title": {"$contains": keyword}}
    ]}
)

# Merge و re-rank
final_results = merge_and_rerank(
    semantic_results,
    keyword_results
)
```

### فیلتر بر اساس Metadata

**پیشنهاد:** فیلتر پیشرفته بر اساس metadata

**مثال‌ها:**
- جستجو فقط در یک کتاب خاص
- جستجو در یک section خاص
- فیلتر بر اساس تاریخ
- فیلتر بر اساس نوع محتوا

**API:**
```json
{
  "query": "آموزش عقاید",
  "top_k": 10,
  "filters": {
    "book_id": 5,
    "section_id": {"$gte": 10}
  }
}
```

### Query Expansion

**پیشنهاد:** گسترش خودکار query برای نتایج بهتر

**روش:**
- استفاده از synonyms برای فارسی
- استفاده از related terms
- استفاده از context

**مثال:**
```
Query اصلی: "دین چیست"
Query گسترش یافته: "دین چیست | مذهب | اعتقادات | ادیان"
```

### Reranking

**پیشنهاد:** استفاده از reranking model برای بهبود نتایج

**مزایا:**
- نتایج مرتب‌تر
- دقت بالاتر
- تجربه کاربری بهتر

---

## مانیتورینگ و آمار

### Dashboard آمار

**پیشنهاد:** Dashboard برای نمایش آمار و metrics

**آمارها:**
- تعداد queryهای روزانه/هفتگی/ماهانه
- محبوب‌ترین queryها
- زمان پاسخ (latency)
- نرخ موفقیت
- استفاده از collectionها
- هزینه API calls

**پیاده‌سازی:**
- استفاده از Grafana + Prometheus
- یا dashboard ساده با FastAPI + Chart.js
- ذخیره metrics در Redis یا database

### Alerting

**پیشنهاد:** سیستم هشدار برای مشکلات

**هشدارها:**
- خطاهای API
- Latency بالا
- استفاده بیش از حد از API
- Collection size بالا
- خطاهای ChromaDB

**روش:**
- Email notifications
- Slack/Discord webhooks
- SMS (برای موارد critical)

### Performance Monitoring

**پیشنهاد:** مانیتورینگ عملکرد سیستم

**Metrics:**
- Response time
- Throughput
- Error rate
- Resource usage (CPU, Memory)
- Database connection pool

---

## بهینه‌سازی هزینه

### استفاده از مدل کوچکتر برای برخی موارد

**پیشنهاد:** استفاده از `text-embedding-3-small` برای موارد غیر critical

**مثال:**
```bash
# برای تست و توسعه
--embedding-model text-embedding-3-small

# برای production
--embedding-model text-embedding-3-large
```

**مقایسه هزینه:**
- `text-embedding-3-small`: $0.02 per 1M tokens
- `text-embedding-3-large`: $0.13 per 1M tokens

**برای 247K chunk:**
- Small: ~$5-10
- Large: ~$30-50

### Caching

**پیشنهاد:** کش کردن نتایج جستجوهای تکراری

**مزایا:**
- کاهش هزینه API calls
- سرعت بیشتر
- کاهش load روی ChromaDB

**پیاده‌سازی:**
- استفاده از Redis برای cache
- TTL مناسب (مثلاً 1 ساعت)
- Cache key بر اساس query + filters

**مثال:**
```python
# در search endpoint
cache_key = f"search:{hash(query)}:{hash(filters)}"
cached_result = redis.get(cache_key)

if cached_result:
    return cached_result

# جستجو و cache
result = perform_search(query, filters)
redis.setex(cache_key, 3600, result)
```

### Batch Optimization

**پیشنهاد:** بهینه‌سازی batch size بر اساس هزینه و سرعت

**تحلیل:**
- Batch size بالاتر = کمتر API calls = هزینه کمتر
- اما زمان بیشتر برای هر batch
- تعادل بین هزینه و زمان

---

## ابزارهای کمکی

### Export Validation Tool

**پیشنهاد:** ابزار برای بررسی صحت export

**قابلیت‌ها:**
- مقایسه تعداد رکوردها با SQL file
- بررسی صحت metadata
- تست sample queries
- گزارش مشکلات

**مثال:**
```bash
python validate_export.py \
  --sql-path book_pages.sql \
  --collection book_pages_text-embedding-3-large \
  --sample-size 100
```

### Collection Comparison Tool

**پیشنهاد:** ابزار برای مقایسه دو collection

**قابلیت‌ها:**
- شناسایی تفاوت‌ها
- مقایسه تعداد documents
- مقایسه metadata
- تست queryهای یکسان

**مثال:**
```bash
python compare_collections.py \
  --collection1 book_pages_small \
  --collection2 book_pages_large \
  --queries test_queries.txt
```

### Migration Tool

**پیشنهاد:** ابزار برای migration بین collectionها

**قابلیت‌ها:**
- کپی documents از یک collection به دیگری
- تبدیل metadata
- تغییر embedding model
- Backup و restore

### Statistics Tool

**پیشنهاد:** ابزار برای نمایش آمار collection

**آمارها:**
- تعداد documents
- توزیع book_id
- توزیع section_id
- میانگین طول chunk
- توزیع similarity scores

**مثال:**
```bash
python collection_stats.py \
  --collection book_pages_text-embedding-3-large \
  --output stats.json
```

---

## اولویت‌بندی پیشنهادی

### فوری (High Priority)

این موارد را می‌توانید فوراً پیاده‌سازی کنید:

1. **افزایش batch-size به 100-150**
   - ساده و سریع
   - بهبود فوری در سرعت export

2. **اضافه کردن validation script**
   - بررسی صحت export
   - شناسایی مشکلات

3. **تست کیفیت search با queryهای واقعی**
   - ارزیابی کیفیت embeddings
   - شناسایی مشکلات

### کوتاه‌مدت (Medium Priority)

این موارد را در هفته‌های آینده پیاده‌سازی کنید:

1. **بهبود chunking (sentence-aware)**
   - بهبود کیفیت embeddings
   - نتایج جستجوی بهتر

2. **اضافه کردن incremental update**
   - صرفه‌جویی در زمان
   - کاهش هزینه

3. **Hybrid search**
   - نتایج دقیق‌تر
   - تجربه کاربری بهتر

4. **Caching برای search**
   - کاهش هزینه
   - سرعت بیشتر

### بلندمدت (Low Priority)

این موارد را برای آینده در نظر بگیرید:

1. **Dashboard مانیتورینگ**
   - آمار و metrics
   - Alerting

2. **Query expansion**
   - نتایج بهتر
   - پوشش بیشتر

3. **Auto-optimization**
   - بهینه‌سازی خودکار
   - تنظیمات پویا

4. **Reranking**
   - نتایج مرتب‌تر
   - دقت بالاتر

---

## مثال‌های عملی

### مثال 1: Export بهینه با batch size بالا

```bash
python3 export-sql-backup-to-chromadb.py \
  --sql-path book_pages.sql \
  --collection book_pages_text-embedding-3-large \
  --embedding-model text-embedding-3-large \
  --batch-size 150 \
  --max-length 200 \
  --context 100
```

### مثال 2: Export با مدل کوچکتر برای تست

```bash
python3 export-sql-backup-to-chromadb.py \
  --sql-path book_pages.sql \
  --collection book_pages_test \
  --embedding-model text-embedding-3-small \
  --batch-size 200 \
  --reset
```

### مثال 3: Incremental Update

```bash
# اولین export
python3 export-sql-backup-to-chromadb.py \
  --sql-path book_pages.sql \
  --collection book_pages_text-embedding-3-large

# به‌روزرسانی فقط رکوردهای جدید (بعد از پیاده‌سازی)
python3 export-sql-backup-to-chromadb.py \
  --sql-path book_pages_updated.sql \
  --collection book_pages_text-embedding-3-large \
  --incremental \
  --last-export-id 29848
```

---

## منابع و لینک‌ها

- 📖 [README.md](README.md) - راهنمای کامل نصب و استفاده
- 📖 [FEATURES.md](FEATURES.md) - فهرست کامل ویژگی‌ها
- 📖 [API_DOCUMENTATION.md](API_DOCUMENTATION.md) - مستندات API
- 📖 [HUGGINGFACE_MODELS.md](HUGGINGFACE_MODELS.md) - راهنمای مدل‌های HuggingFace

---

**آخرین به‌روزرسانی**: 2025-01-16

