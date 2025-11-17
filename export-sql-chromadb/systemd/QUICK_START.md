# راهنمای سریع نصب سرویس Systemd

## نصب خودکار (پیشنهادی)

```bash
# در مسیر ریشه پروژه
cd /path/to/automated-Multi-Step-Content-Processing-and-SEO-Optimization-System

# اجرای اسکریپت نصب
bash systemd/install-service.sh [مسیر_پروژه] [نام_کاربر]
```

مثال:
```bash
bash systemd/install-service.sh /home/user/projects/automated-Multi-Step-Content-Processing-and-SEO-Optimization-System ubuntu
```

## نصب دستی

### 1. ویرایش فایل سرویس

فایل `systemd/chroma-search-api.service` را باز کنید و موارد زیر را تغییر دهید:

- `/path/to/project` → مسیر کامل پروژه شما
- `User=www-data` → نام کاربری شما (مثلاً `ubuntu`)
- `Group=www-data` → گروه کاربری شما

### 2. کپی و فعال‌سازی

```bash
# کپی فایل
sudo cp systemd/chroma-search-api.service /etc/systemd/system/

# بارگذاری مجدد
sudo systemctl daemon-reload

# فعال‌سازی برای راه‌اندازی خودکار
sudo systemctl enable chroma-search-api.service

# راه‌اندازی
sudo systemctl start chroma-search-api.service

# بررسی وضعیت
sudo systemctl status chroma-search-api.service
```

## بررسی سرویس

```bash
# وضعیت
sudo systemctl status chroma-search-api.service

# لاگ‌ها
sudo journalctl -u chroma-search-api.service -f

# تست
curl http://localhost:8080/health
```

## دستورات مفید

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

## نکات مهم

1. **قبل از نصب:**
   - Virtual environment باید ایجاد شده باشد: `python3 -m venv .venv`
   - وابستگی‌ها نصب شده باشند: `pip install -r web_service/requirements.txt`
   - فایل `.env` در `export-sql-chromadb/.env` موجود باشد

2. **بعد از تغییر `.env`:**
   ```bash
   sudo systemctl restart chroma-search-api.service
   ```

3. **برای مشاهده خطاها:**
   ```bash
   sudo journalctl -u chroma-search-api.service -n 50
   ```

