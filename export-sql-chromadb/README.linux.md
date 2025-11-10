## Linux Quickstart Guide

This guide walks through running `export-sql-backup-to-chromadb.py` on Linux, using the lightweight `books_pages_mini.sql` sample to populate a ChromaDB instance running in Docker, and then verifying the results.

---

### 1. Prerequisites
- Install **Python 3.10+** (`sudo apt install python3 python3-venv` on Debian/Ubuntu).
- Install **Docker Engine** and ensure your user belongs to the `docker` group (`sudo usermod -aG docker $USER`).
- Optional: obtain an **OpenAI API key** if you want to generate embeddings client-side.

Log out and back in if you just added your user to the `docker` group.
**Check:** `python3 --version` و `docker --version` را اجرا کنید تا از نصب صحیح ابزارها مطمئن شوید؛ همچنین `docker info` باید بدون خطا اجرا شود.

---

### 2. Create and Activate a Virtual Environment
```bash
cd export-sql-chromadb
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```
**Check:** اجرای `python -m pip list | grep chromadb` باید نسخه‌ی chromadb نصب‌شده را نمایش دهد و هیچ خطای dependency در کنسول نباشد.

---

### 3. Configure Environment Variables
1. Review the provided `.env.dev` file and copy it if you prefer to keep settings in a `.env` file:
   ```bash
   cp .env.dev .env
   ```
2. Key values to set (either in `.env` or your shell):
   - `CHROMA_HOST`, `CHROMA_PORT`: defaults for the Docker stack are `localhost` and `8000`.
   - `CHROMA_COLLECTION`: target collection name; both the exporter and downstream services should agree on this (defaults to `book_pages`).
   - `CHROMA_API_KEY`: only if your Chroma instance requires authentication.
   - `OPENAI_API_KEY`: required when `--embedding-provider openai`.
   - `CHUNK_MAX_LENGTH`, `CHUNK_CONTEXT_LENGTH`, `CHROMA_BATCH_SIZE`: tweak to adjust segment size and batching.

To export the variables for the current shell without a `.env`, run e.g.:
```bash
export CHROMA_HOST=localhost
export CHROMA_PORT=8000
export CHROMA_COLLECTION=book_pages_mini
```
**Check:** `env | grep CHROMA_` را اجرا کنید یا محتوای `.env` را بررسی کنید تا مطمئن شوید مقادیر دلخواه تنظیم شده‌اند.

---

### 4. Launch ChromaDB via Docker
```bash
cd export-sql-chromadb
docker compose up -d          # uses docker-compose.yml in this directory
curl http://localhost:8000/api/v2/heartbeat
```
Adjust the URL if you customised host or port. The heartbeat endpoint should return a JSON payload confirming the service is healthy.
**Check:** دستور `docker ps --filter "name=chroma"` باید کانتینر در حال اجرا را نشان دهد و خروجی heartbeat نباید خطا یا زمان‌انتظار طولانی داشته باشد (پاسخ JSON با کلیدهایی مثل `nanosecond heartbeat` نشان می‌دهد API نسخه‌ی ۲ در دسترس است).

---

### 5. Run the Export Script with the Sample Data
Use the smaller `books_pages_mini.sql` dump to keep runtime and token usage low while testing:
```bash
python export-sql-backup-to-chromadb.py \
  --sql-path books_pages_mini.sql \
  --collection book_pages_mini \
  --embedding-provider none \
  --reset
```
or this
```bash
python3 export-sql-backup-to-chromadb.py   --sql-path books_pages_mini.sql   --collection book_pages_mini   --embedding-provider none   --reset
```
- Switch to OpenAI embeddings by adding `--embedding-provider openai --openai-api-key "$OPENAI_API_KEY"` (model defaults to `text-embedding-3-small` for lower cost).
- `--embedding-provider none` avoids client-side embedding generation, resulting in zero token spend; ensure your server workflow handles embeddings if you choose this mode.
- `--reset` drops the existing collection before inserting; omit it when you want to append to an existing dataset.
**Check:** در خروجی کنسول باید پیغام `✅ Export completed. Segments added: ...` مشاهده شود و اگر خطایی رخ دهد، پیام آن ثبت می‌شود؛ در صورت نیاز می‌توانید با `docker logs <container>` جزئیات بیشتر را ببینید. اسکریپت برای نسخه‌های جدید Chroma که استثناء `InvalidCollectionException` را حذف کرده‌اند به‌روزرسانی شده است، پس نباید خطای Import ببینید؛ اگر بسته‌ی قدیمی‌تری نصب شد، با `pip install --upgrade chromadb` آن را به‌روزرسانی کنید. توجه داشته باشید که در اولین اجرا، Chroma ممکن است مدل‌های ONNX (مثلاً `all-MiniLM-L6-v2`) را از اینترنت دانلود و در مسیر `~/.cache/chroma/onnx_models/` ذخیره کند؛ این روند طبیعی است و پس از تکمیل، اجراهای بعدی سریع‌تر خواهند بود.
نمونه‌ی خروجی معمولاً شبیه زیر است:
```
/root/.cache/chroma/onnx_models/all-MiniLM-L6-v2/onnx.tar.gz: 100%|████████████████████████████████| 79.3M/79.3M [07:10<00:00, 193kiB/s]
✅ Export completed. Segments added: 1130
```

---

### 6. Monitor Token Usage
- Token consumption scales with the size of each segment and the number of segments exported.
- With `books_pages_mini.sql`, segment sizes are small (default max length 200 characters plus context), so costs remain low.
- If you need tighter control, consider lowering `--max-length` or batching exports, and track usage in the OpenAI dashboard when embeddings are enabled.
**Check:** در صورت استفاده از OpenAI، داشبورد Usage باید تعداد درخواست‌ها و هزینه‌ی تقریبی را نشان دهد؛ برای بررسی محلی می‌توانید خروجی اسکریپت را از نظر تعداد سگمنت‌ها نیز پایش کنید.

---

### 7. Verify the Export
```bash
python verify_chroma_export.py \
  --collection book_pages_mini \
  --query "دین چیست" \
  --host localhost \
  --port 8000 \
  --top-k 5
```
- Successful responses include the document ID, distance score, `metadata.source_link`, and a text preview for each match.
- If you exported without embeddings, vector searches may return empty results unless embeddings are generated server-side.
> **Example sanity check:** برای اطمینان از ذخیره شدن لینک‌های خاص، می‌توانید کوئری هدفمند بزنید:
```bash
python verify_chroma_export.py \
  --collection book_pages_mini \
  --query "اعتقاد به آفریننده" \
  --host localhost \
  --port 8000 \
  --top-k 10
```
یا
```bash
python3 verify_chroma_export.py   --collection book_pages_mini   --query "اعتقاد به آفریننده"   --host localhost   --port 8000   --top-k 10
```
در خروجی، به دنبال `metadata.source_link` با مقدار `https://mesbahyazdi.ir/node/1003#p11` بگردید؛ وجود آن نشان می‌دهد رکورد مربوطه به‌درستی بارگذاری شده است.
اگر API جست‌وجوی Node.js را بالا آورده‌اید، می‌توانید همان عبارت را با `curl "http://localhost:4000/search?phrase=اعتقاد%20به%20آفریننده"` امتحان کنید و در نتایج به همان لینک توجه نمایید.
**Check:** در خروجی اسکریپت باید آرایه‌ی `items` با حداقل یک نتیجه (یا توضیح قابل انتظار) نمایش داده شود؛ در صورت نبود نتیجه، لاگ‌ها و تنظیمات کالکشن را بازبینی کنید.

---

### 8. Shutdown and Cleanup
```bash
docker compose down
deactivate
```
Re-run `docker compose up -d` and `source .venv/bin/activate` whenever you return to the project.
**Check:** `docker ps` پس از `down` نباید کانتینر Chroma را نشان دهد و `which python` باید به سیستم‌پایتون برگردد (نه محیط مجازی).

---

These steps provide a Linux-friendly workflow that mirrors the Windows guide, using the small SQL sample as a low-cost way to validate the pipeline before processing large backups.

