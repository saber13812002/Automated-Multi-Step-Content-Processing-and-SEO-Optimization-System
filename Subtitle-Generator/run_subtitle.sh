#!/bin/bash

LANGUAGE=$1
DIRECTORY=$2
TIMESTAMP=$(date '+%Y-%m-%d %H:%M:%S')
LOG_FILE=~/subtitle_log.txt

# فعال‌سازی محیط مجازی
source ~/automated-multi-step-content-processing-and-seo-optimization-system/Subtitle-Generator/myenv/bin/activate

# اجرای اسکریپت و گرفتن خروجی
OUTPUT=$(python3 ~/automated-multi-step-content-processing-and-seo-optimization-system/Subtitle-Generator/subAlljob.py --language "$LANGUAGE" --directory "$DIRECTORY" 2>&1)
EXIT_CODE=$?

# ذخیره در لاگ
{
  echo "[$TIMESTAMP] LANG=$LANGUAGE DIR=$DIRECTORY"
  echo "$OUTPUT"
  echo "-----------------------------"
} >> "$LOG_FILE"

# ارسال به تلگرام
TOKEN="YOUR_TELEGRAM_BOT_TOKEN"
CHAT_ID="YOUR_TELEGRAM_CHAT_ID"

MESSAGE="🎬 اجرای اسکریپت زیرنویس:
🗂 مسیر: $DIRECTORY
🌐 زبان: $LANGUAGE
⏰ زمان: $TIMESTAMP
🚦 وضعیت: $([ $EXIT_CODE -eq 0 ] && echo موفق یا ✅ || echo خطا یا ❌ )
"

curl -s -X POST "https://api.telegram.org/bot${TOKEN}/sendMessage" \
  -d chat_id="${CHAT_ID}" \
  -d text="${MESSAGE}" \
  -d parse_mode="Markdown"

# 👇👇 نمایش لاگ به n8n (فقط آخرین ۵۰ خط)
echo "========== خروجی لاگ (آخرین ۵۰ خط) =========="
tail -n 50 "$LOG_FILE"
