# راهنمای نصب و راه‌اندازی سرویس‌های Systemd

این فایل‌ها برای ایجاد سرویس‌های systemd برای اجرای دائمی سرویس‌های Chroma Search API روی سرور لینوکس استفاده می‌شوند.

## فایل‌های موجود

1. **chroma-search-api.service** - سرویس FastAPI (Python)
2. **chroma-search-api-node.service** - سرویس Express (Node.js) - اختیاری

## پیش‌نیازها

### برای سرویس Python (FastAPI):
- Python 3.11 یا جدیدتر
- Virtual environment در مسیر `export-sql-chromadb/.venv`
- فایل `.env` در مسیر `export-sql-chromadb/.env`
- وابستگی‌های نصب شده در virtual environment

### برای سرویس Node.js:
- Node.js 20+ و npm 9+
- Build شده با `npm run build`
- فایل `.env` در مسیر `apps/chroma_search_api/.env`

## مراحل نصب

### 1. تنظیم مسیرها

قبل از نصب، باید مسیرهای موجود در فایل‌های `.service` را با مسیر واقعی پروژه خود جایگزین کنید:

```bash
# پیدا کردن مسیر کامل پروژه
pwd
# مثال: /home/user/projects/automated-Multi-Step-Content-Processing-and-SEO-Optimization-System
```

سپس در فایل‌های `.service` موارد زیر را تغییر دهید:
- `/path/to/project` → مسیر کامل پروژه شما
- `User=www-data` → نام کاربری مناسب (مثلاً `ubuntu` یا `your-username`)
- `Group=www-data` → گروه کاربری مناسب

### 2. کپی فایل سرویس به systemd

```bash
# برای سرویس Python
sudo cp systemd/chroma-search-api.service /etc/systemd/system/

# برای سرویس Node.js (اگر نیاز دارید)
sudo cp systemd/chroma-search-api-node.service /etc/systemd/system/
```

### 3. بارگذاری مجدد systemd

```bash
sudo systemctl daemon-reload
```

### 4. فعال‌سازی سرویس برای راه‌اندازی خودکار

```bash
# برای سرویس Python
sudo systemctl enable chroma-search-api.service

# برای سرویس Node.js (اگر نیاز دارید)
sudo systemctl enable chroma-search-api-node.service
```

### 5. راه‌اندازی سرویس

```bash
# برای سرویس Python
sudo systemctl start chroma-search-api.service

# برای سرویس Node.js (اگر نیاز دارید)
sudo systemctl start chroma-search-api-node.service
```

## دستورات مدیریتی

### بررسی وضعیت سرویس

```bash
# وضعیت سرویس
sudo systemctl status chroma-search-api.service

# مشاهده لاگ‌های زنده
sudo journalctl -u chroma-search-api.service -f

# مشاهده آخرین لاگ‌ها
sudo journalctl -u chroma-search-api.service -n 100
```

### مدیریت سرویس

```bash
# راه‌اندازی مجدد
sudo systemctl restart chroma-search-api.service

# توقف
sudo systemctl stop chroma-search-api.service

# شروع
sudo systemctl start chroma-search-api.service

# غیرفعال‌سازی راه‌اندازی خودکار
sudo systemctl disable chroma-search-api.service
```

### بررسی پورت

```bash
# بررسی اینکه سرویس روی پورت 8080 در حال اجرا است
sudo netstat -tlnp | grep 8080
# یا
sudo ss -tlnp | grep 8080
```

## عیب‌یابی

### سرویس شروع نمی‌شود

1. **بررسی لاگ‌ها:**
   ```bash
   sudo journalctl -u chroma-search-api.service -n 50
   ```

2. **بررسی مسیرها:**
   - مطمئن شوید مسیرهای در فایل `.service` صحیح هستند
   - بررسی کنید که virtual environment وجود دارد
   - بررسی کنید که فایل `.env` موجود است

3. **بررسی دسترسی‌ها:**
   ```bash
   # بررسی دسترسی کاربر به مسیر پروژه
   sudo -u www-data ls /path/to/project/export-sql-chromadb
   ```

4. **اجرای دستی برای تست:**
   ```bash
   cd /path/to/project/export-sql-chromadb
   source .venv/bin/activate
   uvicorn web_service.app:app --host 0.0.0.0 --port 8080
   ```

### سرویس بعد از ریستارت از بین می‌رود

- مطمئن شوید که سرویس را با `enable` فعال کرده‌اید:
  ```bash
  sudo systemctl enable chroma-search-api.service
  ```

### تغییرات در فایل `.env`

بعد از تغییر فایل `.env`، باید سرویس را راه‌اندازی مجدد کنید:
```bash
sudo systemctl restart chroma-search-api.service
```

## نکات امنیتی

1. **کاربر سرویس:** بهتر است از یک کاربر مخصوص برای اجرای سرویس استفاده کنید (نه root)
2. **فایل `.env`:** مطمئن شوید که فایل `.env` دسترسی مناسب دارد:
   ```bash
   chmod 600 /path/to/project/export-sql-chromadb/.env
   ```
3. **فایروال:** اگر از فایروال استفاده می‌کنید، پورت 8080 را باز کنید:
   ```bash
   sudo ufw allow 8080/tcp
   ```

## تست سرویس

بعد از راه‌اندازی، می‌توانید سرویس را تست کنید:

```bash
# Health check
curl http://localhost:8080/health

# یا از سرور دیگر
curl http://YOUR_SERVER_IP:8080/health
```

## اسکریپت نصب خودکار

می‌توانید یک اسکریپت برای نصب خودکار ایجاد کنید. مثال:

```bash
#!/bin/bash
PROJECT_PATH="/path/to/project"
SERVICE_USER="www-data"

# کپی فایل سرویس
sudo cp systemd/chroma-search-api.service /etc/systemd/system/

# جایگزینی مسیرها
sudo sed -i "s|/path/to/project|$PROJECT_PATH|g" /etc/systemd/system/chroma-search-api.service
sudo sed -i "s|User=www-data|User=$SERVICE_USER|g" /etc/systemd/system/chroma-search-api.service
sudo sed -i "s|Group=www-data|Group=$SERVICE_USER|g" /etc/systemd/system/chroma-search-api.service

# بارگذاری مجدد و فعال‌سازی
sudo systemctl daemon-reload
sudo systemctl enable chroma-search-api.service
sudo systemctl start chroma-search-api.service

echo "سرویس نصب و راه‌اندازی شد!"
```

