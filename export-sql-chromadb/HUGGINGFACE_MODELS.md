# راهنمای استفاده از مدل‌های HuggingFace برای Embedding

این راهنما شامل مثال‌های کامل و پیشنهادات مدل‌های HuggingFace برای استفاده در اسکریپت `export-sql-backup-to-chromadb.py` است.

## 🚀 شروع سریع

### نصب وابستگی‌ها

برای استفاده از مدل‌های HuggingFace، ابتدا کتابخانه‌های مورد نیاز را نصب کنید:

```bash
pip install transformers torch numpy
```

### مثال سریع با ParsBERT

```bash
python export-sql-backup-to-chromadb.py \
  --sql-path book_pages.sql \
  --collection book_pages_parsbert \
  --embedding-provider huggingface \
  --embedding-model "HooshvareLab/bert-base-parsbert-uncased" \
  --batch-size 32
```

این مثال از ParsBERT (بهترین مدل برای متون فارسی) استفاده می‌کند. برای جزئیات بیشتر و مثال‌های دیگر، ادامه مطلب را مطالعه کنید.

---

## 🎯 مدل‌های پیشنهادی برای تست

### مدل‌های فارسی (Persian/Farsi)

#### 1. **ParsBERT** ⭐ (پیشنهاد اول)
- **مدل**: `HooshvareLab/bert-base-parsbert-uncased`
- **مناسب برای**: متون فارسی عمومی و رسمی
- **اندازه**: ~440MB
- **ویژگی**: بهترین عملکرد برای متون فارسی استاندارد

#### 2. **ParsBERT v2**
- **مدل**: `HooshvareLab/bert-base-parsbert-v2`
- **مناسب برای**: متون فارسی عمومی (نسخه بهبود یافته)
- **ویژگی**: بهبود یافته نسبت به نسخه اول

#### 3. **FaBERT**
- **مدل**: `sbunlp/fabert`
- **مناسب برای**: متون وبلاگ و شبکه‌های اجتماعی فارسی
- **ویژگی**: بهینه شده برای متون غیررسمی

### مدل‌های عربی (Arabic)

#### 1. **AraBERT v2** ⭐ (پیشنهاد اول)
- **مدل**: `aubmindlab/bert-base-arabertv2`
- **مناسب برای**: متون عربی مدرن
- **ویژگی**: بهترین عملکرد برای متون عربی معاصر

#### 2. **AraBERT v1**
- **مدل**: `aubmindlab/bert-base-arabert`
- **مناسب برای**: متون عربی عمومی

#### 3. **ArabicBERT**
- **مدل**: `asafaya/bert-base-arabic`
- **مناسب برای**: متون عربی کلاسیک و مدرن

### مدل‌های چندزبانه (Multilingual)

#### 1. **mBERT** (Multilingual BERT)
- **مدل**: `bert-base-multilingual-cased`
- **پشتیبانی**: 104 زبان شامل فارسی و عربی
- **ویژگی**: مناسب برای محتوای ترکیبی چندزبانه

#### 2. **XLM-RoBERTa Base**
- **مدل**: `xlm-roberta-base`
- **پشتیبانی**: 100 زبان
- **ویژگی**: عملکرد بهتر از mBERT در برخی وظایف

---

## 💻 مثال‌های کامل Command Line

### مثال 1: ParsBERT (فارسی) ⭐

```bash
python3 export-sql-backup-to-chromadb.py \
  --sql-path book_pages.sql \
  --collection book_pages_parsbert \
  --embedding-provider huggingface \
  --embedding-model "HooshvareLab/bert-base-parsbert-uncased" \
  --batch-size 32 \
  --max-length 200 \
  --context 100 \
  --device cuda
```

### مثال 2: AraBERT v2 (عربی) ⭐

```bash
python3 export-sql-backup-to-chromadb.py \
  --sql-path book_pages.sql \
  --collection book_pages_arabert \
  --embedding-provider huggingface \
  --embedding-model "aubmindlab/bert-base-arabertv2" \
  --batch-size 32 \
  --max-length 200 \
  --context 100 \
  --device cuda
```

### مثال 3: FaBERT (فارسی - وبلاگ/شبکه‌های اجتماعی)

```bash
python3 export-sql-backup-to-chromadb.py \
  --sql-path book_pages.sql \
  --collection book_pages_fabert \
  --embedding-provider huggingface \
  --embedding-model "sbunlp/fabert" \
  --batch-size 24 \
  --max-length 200 \
  --context 100
```

### مثال 4: mBERT (چندزبانه - برای هر دو زبان)

```bash
python3 export-sql-backup-to-chromadb.py \
  --sql-path book_pages.sql \
  --collection book_pages_mbert \
  --embedding-provider huggingface \
  --embedding-model "bert-base-multilingual-cased" \
  --batch-size 32 \
  --max-length 200 \
  --context 100 \
  --device cuda
```

### مثال 5: XLM-RoBERTa (چندزبانه - عملکرد بهتر)

```bash
python3 export-sql-backup-to-chromadb.py \
  --sql-path book_pages.sql \
  --collection book_pages_xlmr \
  --embedding-provider huggingface \
  --embedding-model "xlm-roberta-base" \
  --batch-size 24 \
  --max-length 200 \
  --context 100 \
  --device cuda
```

### مثال 6: استفاده از CPU (اگر GPU ندارید)

```bash
python3 export-sql-backup-to-chromadb.py \
  --sql-path book_pages.sql \
  --collection book_pages_parsbert_cpu \
  --embedding-provider huggingface \
  --embedding-model "HooshvareLab/bert-base-parsbert-uncased" \
  --batch-size 16 \
  --max-length 200 \
  --context 100 \
  --device cpu
```

### مثال 7: استفاده از Environment Variables

#### در Linux/Mac:

```bash
export EMBEDDING_PROVIDER=huggingface
export EMBEDDING_MODEL="HooshvareLab/bert-base-parsbert-uncased"
export EMBEDDING_DEVICE=cuda
export CHROMA_BATCH_SIZE=32

python export-sql-backup-to-chromadb.py --sql-path book_pages.sql
```

#### در Windows PowerShell:

```powershell
$env:EMBEDDING_PROVIDER="huggingface"
$env:EMBEDDING_MODEL="HooshvareLab/bert-base-parsbert-uncased"
$env:EMBEDDING_DEVICE="cuda"
$env:CHROMA_BATCH_SIZE="32"

python export-sql-backup-to-chromadb.py --sql-path book_pages.sql
```

---

## 🧪 راهنمای تست و مقایسه

### برای شروع تست:

1. **ابتدا با ParsBERT تست کنید** (مدل فارسی محبوب و قابل اعتماد)
2. **از batch-size کوچکتر شروع کنید** (16-24) برای تست سریع‌تر
3. **اگر GPU دارید، از `--device cuda` استفاده کنید** (سرعت بسیار بیشتر)

### تست مقایسه‌ای بین مدل‌ها:

```bash
# تست 1: ParsBERT
python export-sql-backup-to-chromadb.py \
  --sql-path book_pages.sql \
  --collection test_parsbert \
  --embedding-provider huggingface \
  --embedding-model "HooshvareLab/bert-base-parsbert-uncased" \
  --batch-size 16

# تست 2: AraBERT
python export-sql-backup-to-chromadb.py \
  --sql-path book_pages.sql \
  --collection test_arabert \
  --embedding-provider huggingface \
  --embedding-model "aubmindlab/bert-base-arabertv2" \
  --batch-size 16

# تست 3: mBERT (چندزبانه)
python export-sql-backup-to-chromadb.py \
  --sql-path book_pages.sql \
  --collection test_mbert \
  --embedding-provider huggingface \
  --embedding-model "bert-base-multilingual-cased" \
  --batch-size 16
```

---

## ⚙️ نکات مهم و بهینه‌سازی

### تنظیمات Batch Size:

- **با GPU**: `--batch-size 24-32` (پیشنهاد: 32)
- **بدون GPU (CPU)**: `--batch-size 8-16` (پیشنهاد: 16)
- **مدل‌های بزرگتر** (مثل XLM-RoBERTa): batch-size کوچکتر (16-24)

### مدیریت حافظه:

- **مدل‌های بزرگتر** (مثل XLM-RoBERTa) ممکن است به RAM بیشتر نیاز داشته باشند
- اگر خطای Out of Memory دریافت کردید، `--batch-size` را کاهش دهید
- برای CPU، batch-size را به 8 یا کمتر کاهش دهید

### دانلود مدل:

- **اولین بار** که مدل را اجرا می‌کنید، HuggingFace آن را دانلود می‌کند
- دانلود ممکن است **چند دقیقه** طول بکشد (بسته به سرعت اینترنت)
- مدل‌ها در `~/.cache/huggingface/transformers/` ذخیره می‌شوند

### انتخاب Device:

- **`--device cuda`**: اگر GPU دارید (NVIDIA با CUDA)
- **`--device cpu`**: اگر GPU ندارید یا می‌خواهید از CPU استفاده کنید
- **بدون `--device`**: به صورت خودکار CUDA را تشخیص می‌دهد (اگر موجود باشد)

---

## 📊 پیشنهادات بر اساس نوع محتوا

### برای محتوای فارسی:

- **متون عمومی و رسمی**: `HooshvareLab/bert-base-parsbert-uncased` ⭐
- **متون غیررسمی و شبکه‌های اجتماعی**: `sbunlp/fabert`
- **متون ترکیبی (فارسی + عربی)**: `bert-base-multilingual-cased` یا `xlm-roberta-base`

### برای محتوای عربی:

- **متون مدرن عربی**: `aubmindlab/bert-base-arabertv2` ⭐
- **متون کلاسیک و مدرن**: `asafaya/bert-base-arabic`

### برای محتوای ترکیبی (فارسی + عربی):

- **mBERT**: `bert-base-multilingual-cased` (پشتیبانی از 104 زبان)
- **XLM-RoBERTa**: `xlm-roberta-base` (عملکرد بهتر، پشتیبانی از 100 زبان)

---

## 🔗 لینک‌های مفید

- [HuggingFace Models](https://huggingface.co/models)
- [ParsBERT در HuggingFace](https://huggingface.co/HooshvareLab/bert-base-parsbert-uncased)
- [AraBERT v2 در HuggingFace](https://huggingface.co/aubmindlab/bert-base-arabertv2)
- [mBERT در HuggingFace](https://huggingface.co/bert-base-multilingual-cased)

---

## ❓ سوالات متداول

### آیا می‌توانم مدل‌های دیگر HuggingFace را استفاده کنم؟

بله! هر مدل HuggingFace که از `AutoTokenizer` و `AutoModel` پشتیبانی کند، قابل استفاده است. فقط نام مدل را در `--embedding-model` قرار دهید.

### تفاوت بین مدل‌های مختلف چیست؟

- **ParsBERT**: بهینه شده برای فارسی، بهترین برای متون فارسی
- **AraBERT**: بهینه شده برای عربی، بهترین برای متون عربی
- **mBERT/XLM-RoBERTa**: چندزبانه، مناسب برای محتوای ترکیبی

### چرا batch-size مهم است؟

batch-size بزرگتر = سرعت بیشتر اما نیاز به حافظه بیشتر
batch-size کوچکتر = سرعت کمتر اما نیاز به حافظه کمتر

### آیا می‌توانم از چند مدل همزمان استفاده کنم؟

بله، می‌توانید با `--collection` های مختلف، چندین مدل را تست کنید و نتایج را مقایسه کنید.

