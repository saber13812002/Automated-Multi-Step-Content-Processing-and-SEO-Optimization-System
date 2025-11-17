#!/bin/bash
# اسکریپت نصب خودکار سرویس systemd برای Chroma Search API (Uvicorn)

set -e

# رنگ‌ها برای خروجی
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}=== نصب سرویس Systemd برای Chroma Search API (Uvicorn) ===${NC}\n"

# مسیر پیش‌فرض پروژه
DEFAULT_PROJECT_PATH="/root/saberprojects/automated-Multi-Step-Content-Processing-and-SEO-Optimization-System/export-sql-chromadb"

# دریافت مسیر پروژه
if [ -z "$1" ]; then
    PROJECT_PATH="$DEFAULT_PROJECT_PATH"
    echo -e "${YELLOW}استفاده از مسیر پیش‌فرض: $PROJECT_PATH${NC}"
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
SERVICE_FILE="systemd/chroma-search-api-uvicorn.service"
if [ ! -f "$SERVICE_FILE" ]; then
    # اگر از داخل پوشه export-sql-chromadb اجرا نشده، مسیر را اصلاح کن
    if [ -f "$PROJECT_PATH/$SERVICE_FILE" ]; then
        SERVICE_FILE="$PROJECT_PATH/$SERVICE_FILE"
    else
        echo -e "${RED}خطا: فایل سرویس موجود نیست: $SERVICE_FILE${NC}"
        exit 1
    fi
fi

# بررسی وجود virtual environment
VENV_PATH="$PROJECT_PATH/.venv"
if [ ! -d "$VENV_PATH" ]; then
    echo -e "${YELLOW}هشدار: Virtual environment موجود نیست: $VENV_PATH${NC}"
    echo -e "${YELLOW}لطفاً ابتدا virtual environment را ایجاد کنید:${NC}"
    echo -e "  cd $PROJECT_PATH"
    echo -e "  python3 -m venv .venv"
    echo -e "  source .venv/bin/activate"
    echo -e "  pip install -r requirements.txt"
    read -p "آیا می‌خواهید ادامه دهید؟ (y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# بررسی وجود uvicorn در venv
UVICORN_PATH="$VENV_PATH/bin/uvicorn"
if [ ! -f "$UVICORN_PATH" ]; then
    echo -e "${RED}خطا: uvicorn در virtual environment موجود نیست${NC}"
    echo -e "${YELLOW}لطفاً uvicorn را نصب کنید:${NC}"
    echo -e "  cd $PROJECT_PATH"
    echo -e "  source .venv/bin/activate"
    echo -e "  pip install uvicorn"
    exit 1
fi

echo -e "\n${GREEN}در حال نصب سرویس...${NC}"

# کپی فایل سرویس
echo -e "کپی فایل سرویس به /etc/systemd/system/..."
sudo cp "$SERVICE_FILE" /etc/systemd/system/chroma-search-api-uvicorn.service

# جایگزینی مسیرها
echo -e "تنظیم مسیرها و کاربر..."
sudo sed -i "s|WorkingDirectory=.*|WorkingDirectory=$PROJECT_PATH|g" /etc/systemd/system/chroma-search-api-uvicorn.service
sudo sed -i "s|ExecStart=.*|ExecStart=$UVICORN_PATH web_service.app:app --host 0.0.0.0 --port 8080 --reload|g" /etc/systemd/system/chroma-search-api-uvicorn.service
sudo sed -i "s|Environment=\"PATH=.*|Environment=\"PATH=$VENV_PATH/bin:/usr/local/bin:/usr/bin:/bin\"|g" /etc/systemd/system/chroma-search-api-uvicorn.service
sudo sed -i "s|User=.*|User=$SERVICE_USER|g" /etc/systemd/system/chroma-search-api-uvicorn.service
sudo sed -i "s|Group=.*|Group=$SERVICE_USER|g" /etc/systemd/system/chroma-search-api-uvicorn.service

# بارگذاری مجدد systemd
echo -e "بارگذاری مجدد systemd..."
sudo systemctl daemon-reload

# فعال‌سازی سرویس
echo -e "فعال‌سازی سرویس برای راه‌اندازی خودکار..."
sudo systemctl enable chroma-search-api-uvicorn.service

# راه‌اندازی سرویس
echo -e "راه‌اندازی سرویس..."
sudo systemctl start chroma-search-api-uvicorn.service

# بررسی وضعیت
echo -e "\n${GREEN}بررسی وضعیت سرویس...${NC}"
sleep 2
sudo systemctl status chroma-search-api-uvicorn.service --no-pager -l

echo -e "\n${GREEN}=== نصب با موفقیت انجام شد! ===${NC}\n"
echo -e "دستورات مفید:"
echo -e "  ${YELLOW}وضعیت سرویس:${NC} sudo systemctl status chroma-search-api-uvicorn.service"
echo -e "  ${YELLOW}مشاهده لاگ‌ها:${NC} sudo journalctl -u chroma-search-api-uvicorn.service -f"
echo -e "  ${YELLOW}راه‌اندازی مجدد:${NC} sudo systemctl restart chroma-search-api-uvicorn.service"
echo -e "  ${YELLOW}توقف:${NC} sudo systemctl stop chroma-search-api-uvicorn.service"
echo -e "\n${GREEN}تست سرویس:${NC} curl http://localhost:8080/health"

