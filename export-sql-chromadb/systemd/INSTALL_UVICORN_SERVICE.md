# نصب سرویس Uvicorn برای Chroma Search API

این فایل سرویس systemd برای اجرای خودکار سرویس uvicorn با قابلیت reload است.

## پیش‌نیازها

1. سرویس باید از کاربر `root` اجرا شود (طبق دستور شما)
2. مسیر پروژه: `/root/saberprojects/automated-Multi-Step-Content-Processing-and-SEO-Optimization-System/export-sql-chromadb`
3. Virtual environment باید در `.venv` موجود باشد
4. تمام dependencies باید نصب شده باشند

## مراحل نصب

### 1. کپی فایل سرویس

```bash
sudo cp systemd/chroma-search-api-uvicorn.service /etc/systemd/system/
```

### 2. بررسی و ویرایش مسیرها (در صورت نیاز)

اگر مسیر پروژه شما متفاوت است، فایل را ویرایش کنید:

```bash
sudo nano /etc/systemd/system/chroma-search-api-uvicorn.service
```

مهم‌ترین بخش‌ها:
- `WorkingDirectory`: مسیر پروژه
- `ExecStart`: مسیر کامل به uvicorn در venv
- `User` و `Group`: کاربر و گروه (فعلاً root)

### 3. بارگذاری مجدد systemd

```bash
sudo systemctl daemon-reload
```

### 4. فعال‌سازی سرویس (برای راه‌اندازی خودکار)

```bash
sudo systemctl enable chroma-search-api-uvicorn.service
```

### 5. راه‌اندازی سرویس

```bash
sudo systemctl start chroma-search-api-uvicorn.service
```

### 6. بررسی وضعیت

```bash
sudo systemctl status chroma-search-api-uvicorn.service
```

## دستورات مفید

### مشاهده لاگ‌ها
```bash
sudo journalctl -u chroma-search-api-uvicorn.service -f
```

### توقف سرویس
```bash
sudo systemctl stop chroma-search-api-uvicorn.service
```

### راه‌اندازی مجدد
```bash
sudo systemctl restart chroma-search-api-uvicorn.service
```

### غیرفعال کردن راه‌اندازی خودکار
```bash
sudo systemctl disable chroma-search-api-uvicorn.service
```

### تست سرویس
```bash
curl http://localhost:8080/health
# یا
curl http://localhost:8080/docs
```

## نکات مهم

1. **--reload flag**: این سرویس با `--reload` اجرا می‌شود که برای development مناسب است. برای production بهتر است `--reload` را حذف کنید.

2. **User/Group**: فعلاً روی `root` تنظیم شده. برای امنیت بیشتر می‌توانید کاربر دیگری ایجاد کنید.

3. **Environment Variables**: اگر نیاز به متغیرهای محیطی دارید، می‌توانید `EnvironmentFile` را اضافه کنید:
   ```
   EnvironmentFile=/root/saberprojects/automated-Multi-Step-Content-Processing-and-SEO-Optimization-System/export-sql-chromadb/.env
   ```

## عیب‌یابی

اگر سرویس شروع نمی‌شود:

1. بررسی لاگ‌ها:
   ```bash
   sudo journalctl -u chroma-search-api-uvicorn.service -n 50
   ```

2. بررسی مسیرها:
   ```bash
   ls -la /root/saberprojects/automated-Multi-Step-Content-Processing-and-SEO-Optimization-System/export-sql-chromadb/.venv/bin/uvicorn
   ```

3. تست دستی:
   ```bash
   cd /root/saberprojects/automated-Multi-Step-Content-Processing-and-SEO-Optimization-System/export-sql-chromadb
   source .venv/bin/activate
   uvicorn web_service.app:app --host 0.0.0.0 --port 8080 --reload
   ```

