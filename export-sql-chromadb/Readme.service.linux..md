عالی! این یک طرح بسیار خوب برای DevOps کردن یک سرویس پایتون است. بیایید مرحله به مرحله پیش برویم:

## 🚀 گام اول: راه اندازی سرویس با Systemd (همیشه بالا)

### 1. ایجاد فایل سرویس systemd
```bash
sudo nano /etc/systemd/system/export-sql-chromadb.service
```

### 2. محتوای فایل سرویس
```ini
[Unit]
Description=Export SQL ChromaDB Service
After=network.target
Wants=network.target

[Service]
Type=simple
User=root
Group=root
WorkingDirectory=/root/saberprojects/automated-Multi-Step-Content-Processing-and-SEO-Optimization-System/export-sql-chromadb
Environment=PATH=/root/saberprojects/automated-Multi-Step-Content-Processing-and-SEO-Optimization-System/export-sql-chromadb/.venv/bin
ExecStart=/root/saberprojects/automated-Multi-Step-Content-Processing-and-SEO-Optimization-System/export-sql-chromadb/.venv/bin/uvicorn web_service.app:app --host 0.0.0.0 --port 8080
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
```

### 3. فعال کردن و شروع سرویس
```bash
sudo systemctl daemon-reload
sudo systemctl enable export-sql-chromadb.service
sudo systemctl start export-sql-chromadb.service
```

### 4. بررسی وضعیت سرویس
```bash
sudo systemctl status export-sql-chromadb.service
journalctl -u export-sql-chromadb.service -f
```

## 🔄 گام دوم: اتوماسیون بروزرسانی با Git

### اسکریپت بروزرسانی خودکار
```bash
nano /root/update_service.sh
```

```bash
#!/bin/bash

SERVICE_NAME="export-sql-chromadb"
PROJECT_DIR="/root/saberprojects/automated-Multi-Step-Content-Processing-and-SEO-Optimization-System"
VENV_PATH="$PROJECT_DIR/export-sql-chromadb/.venv"
REQUIREMENTS_FILE="$PROJECT_DIR/export-sql-chromadb/requirements.txt"

echo "$(date): Starting update process..."

# Pull latest changes
cd $PROJECT_DIR
git fetch origin
LOCAL_COMMIT=$(git rev-parse HEAD)
REMOTE_COMMIT=$(git rev-parse origin/main)

if [ "$LOCAL_COMMIT" != "$REMOTE_COMMIT" ]; then
    echo "New changes detected. Pulling updates..."
    git pull origin main
    
    # Update Python dependencies if requirements changed
    if [ -f "$REQUIREMENTS_FILE" ]; then
        echo "Updating Python dependencies..."
        source $VENV_PATH/bin/activate
        pip install -r $REQUIREMENTS_FILE
    fi
    
    # Restart service
    echo "Restarting service..."
    sudo systemctl restart $SERVICE_NAME
    echo "Service updated and restarted successfully"
else
    echo "No changes detected"
fi
```

### قابل اجرا کردن اسکریپت و اضافه کردن به cron
```bash
chmod +x /root/update_service.sh
# هر 5 دقیقه چک کند
crontab -e
*/5 * * * * /root/update_service.sh >> /var/log/service_update.log 2>&1
```

## 🩺 گام سوم: راه حل ساده برای مانیتورینگ و آلرت

### راه حل 1: اسکریپت ساده با cron + mail

#### نصب mailutils
```bash
sudo apt update
sudo apt install mailutils postfix
```

#### اسکریپت سلامت چک
```bash
nano /root/health_check.sh
```

```bash
#!/bin/bash

SERVICE_URL="http://localhost:8080/health"
SERVICE_NAME="export-sql-chromadb"
ALERT_EMAIL="your-email@example.com"

# Check service health
response=$(curl -s -w "%{http_code}" -o /tmp/health_response.json $SERVICE_URL)
http_code=$(echo "$response" | tail -n1)

if [ "$http_code" -ne 200 ]; then
    echo "$(date): Service $SERVICE_NAME is DOWN! HTTP Code: $http_code" >> /var/log/health_check.log
    echo "Service $SERVICE_NAME is DOWN! HTTP Code: $http_code" | mail -s "ALERT: Service Down" $ALERT_EMAIL
    # Try to restart service
    sudo systemctl restart $SERVICE_NAME
else
    echo "$(date): Service $SERVICE_NAME is healthy" >> /var/log/health_check.log
fi
```

#### اضافه کردن به cron
```bash
chmod +x /root/health_check.sh
# هر 2 دقیقه چک کند
crontab -e
*/2 * * * * /root/health_check.sh
```

### راه حل 2: استفاده از Uptime Kuma (راه حل مستقل و پایدار)

#### نصب با Docker
```bash
docker run -d \
  --name uptime-kuma \
  -p 3001:3001 \
  -v /root/uptime-kuma:/app/data \
  louislam/uptime-kuma:1
```

#### دسترسی به Uptime Kuma
```
http://192.168.1.68:3001
```

در Uptime Kuma:
1. اضافه کردن مونیتور جدید برای سرویس شما
2. تنظیم آلرت از طریق: Email, Telegram, Discord, Slack, etc.
3. Uptime Kuma خودش مانیتورینگ مستقل دارد

## 🛠️ راه حل ترکیبی پیشنهادی (توصیه شده)

### 1. Systemd Service (همیشه بالا)
```bash
# لاگ سرویس
sudo journalctl -u export-sql-chromadb.service -n 50 -f
```

### 2. اسکریپت بروزرسانی بهبود یافته
```bash
nano /root/deploy_service.sh
```

```bash
#!/bin/bash

set -e

SERVICE_NAME="export-sql-chromadb"
PROJECT_DIR="/root/saberprojects/automated-Multi-Step-Content-Processing-and-SEO-Optimization-System"
SERVICE_DIR="$PROJECT_DIR/export-sql-chromadb"
BACKUP_DIR="/root/backups"

echo "$(date): Starting deployment..."

# Backup current version
mkdir -p $BACKUP_DIR
cp -r $SERVICE_DIR $BACKUP_DIR/service_backup_$(date +%Y%m%d_%H%M%S)

# Stop service
echo "Stopping service..."
sudo systemctl stop $SERVICE_NAME

# Update code
cd $PROJECT_DIR
git pull origin main

# Update dependencies
cd $SERVICE_DIR
source .venv/bin/activate
if [ -f "requirements.txt" ]; then
    pip install -r requirements.txt
fi

# Start service
echo "Starting service..."
sudo systemctl start $SERVICE_NAME

# Wait and check health
sleep 10
if curl -f http://localhost:8080/health > /dev/null 2>&1; then
    echo "Deployment successful!"
else
    echo "Deployment failed! Rolling back..."
    sudo systemctl stop $SERVICE_NAME
    # Add rollback logic here
    exit 1
fi
```

### 3. مانیتورینگ ساده اما موثر
```bash
# نصب htop برای مانیتورینگ منابع
sudo apt install htop

# چک کردن پورت
netstat -tlnp | grep 8080

# چک کردن لاگ
tail -f /var/log/syslog | grep export-sql-chromadb
```

این راه حل‌ها:
- ✅ سرویس شما را همیشه بالا نگه می‌دارد
- ✅ بروزرسانی خودکار دارد
- ✅ مانیتورینگ ساده اما موثر
- ✅ در صورت مشکل، آلرت می‌فرستد
- ✅ بسیار پایدار و کم هزینه است

کدام بخش را اول می‌خواهید اجرا کنید؟