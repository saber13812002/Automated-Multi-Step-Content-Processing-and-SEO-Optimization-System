#!/bin/bash
# اسکریپت نصب خودکار سرویس systemd برای Chroma Search API

set -e

# رنگ‌ها برای خروجی
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}=== نصب سرویس Systemd برای Chroma Search API ===${NC}\n"

# دریافت مسیر پروژه
if [ -z "$1" ]; then
    # اگر مسیر داده نشده، از مسیر فعلی استفاده کن
    PROJECT_PATH=$(pwd)
    echo -e "${YELLOW}مسیر پروژه: $PROJECT_PATH${NC}"
else
    PROJECT_PATH="$1"
fi

# بررسی وجود مسیر
if [ ! -d "$PROJECT_PATH" ]; then
    echo -e "${RED}خطا: مسیر پروژه موجود نیست: $PROJECT_PATH${NC}"
    exit 1
fi

# دریافت نام کاربری
if [ -z "$2" ]; then
    SERVICE_USER=$(whoami)
    echo -e "${YELLOW}استفاده از کاربر فعلی: $SERVICE_USER${NC}"
else
    SERVICE_USER="$2"
fi

# بررسی وجود کاربر
if ! id "$SERVICE_USER" &>/dev/null; then
    echo -e "${RED}خطا: کاربر موجود نیست: $SERVICE_USER${NC}"
    exit 1
fi

# بررسی وجود فایل سرویس
SERVICE_FILE="systemd/chroma-search-api.service"
if [ ! -f "$SERVICE_FILE" ]; then
    echo -e "${RED}خطا: فایل سرویس موجود نیست: $SERVICE_FILE${NC}"
    exit 1
fi

# بررسی وجود virtual environment
VENV_PATH="$PROJECT_PATH/export-sql-chromadb/.venv"
if [ ! -d "$VENV_PATH" ]; then
    echo -e "${YELLOW}هشدار: Virtual environment موجود نیست: $VENV_PATH${NC}"
    echo -e "${YELLOW}لطفاً ابتدا virtual environment را ایجاد کنید:${NC}"
    echo -e "  cd $PROJECT_PATH/export-sql-chromadb"
    echo -e "  python3 -m venv .venv"
    echo -e "  source .venv/bin/activate"
    echo -e "  pip install -r web_service/requirements.txt"
    read -p "آیا می‌خواهید ادامه دهید؟ (y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# بررسی وجود فایل .env
ENV_FILE="$PROJECT_PATH/export-sql-chromadb/.env"
if [ ! -f "$ENV_FILE" ]; then
    echo -e "${YELLOW}هشدار: فایل .env موجود نیست: $ENV_FILE${NC}"
    echo -e "${YELLOW}لطفاً فایل .env را ایجاد کنید.${NC}"
    read -p "آیا می‌خواهید ادامه دهید؟ (y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

echo -e "\n${GREEN}در حال نصب سرویس...${NC}"

# کپی فایل سرویس
echo -e "کپی فایل سرویس به /etc/systemd/system/..."
sudo cp "$SERVICE_FILE" /etc/systemd/system/chroma-search-api.service

# جایگزینی مسیرها
echo -e "تنظیم مسیرها و کاربر..."
sudo sed -i "s|/path/to/project|$PROJECT_PATH|g" /etc/systemd/system/chroma-search-api.service
sudo sed -i "s|User=www-data|User=$SERVICE_USER|g" /etc/systemd/system/chroma-search-api.service
sudo sed -i "s|Group=www-data|Group=$SERVICE_USER|g" /etc/systemd/system/chroma-search-api.service

# تنظیم دسترسی فایل .env
if [ -f "$ENV_FILE" ]; then
    echo -e "تنظیم دسترسی فایل .env..."
    sudo chmod 600 "$ENV_FILE"
    sudo chown "$SERVICE_USER:$SERVICE_USER" "$ENV_FILE"
fi

# بارگذاری مجدد systemd
echo -e "بارگذاری مجدد systemd..."
sudo systemctl daemon-reload

# فعال‌سازی سرویس
echo -e "فعال‌سازی سرویس برای راه‌اندازی خودکار..."
sudo systemctl enable chroma-search-api.service

# راه‌اندازی سرویس
echo -e "راه‌اندازی سرویس..."
sudo systemctl start chroma-search-api.service

# بررسی وضعیت
echo -e "\n${GREEN}بررسی وضعیت سرویس...${NC}"
sleep 2
sudo systemctl status chroma-search-api.service --no-pager -l

echo -e "\n${GREEN}=== نصب با موفقیت انجام شد! ===${NC}\n"
echo -e "دستورات مفید:"
echo -e "  ${YELLOW}وضعیت سرویس:${NC} sudo systemctl status chroma-search-api.service"
echo -e "  ${YELLOW}مشاهده لاگ‌ها:${NC} sudo journalctl -u chroma-search-api.service -f"
echo -e "  ${YELLOW}راه‌اندازی مجدد:${NC} sudo systemctl restart chroma-search-api.service"
echo -e "  ${YELLOW}توقف:${NC} sudo systemctl stop chroma-search-api.service"
echo -e "\n${GREEN}تست سرویس:${NC} curl http://localhost:8080/health"

