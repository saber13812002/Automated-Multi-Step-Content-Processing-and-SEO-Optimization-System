#!/bin/bash

# فایل: setup_and_run.sh

set -e

# 1. ساخت محیط مجازی
echo "✅ Creating Python virtual environment..."
python3 -m venv venv

# 2. فعال‌سازی محیط مجازی
echo "✅ Activating virtual environment..."
source venv/bin/activate

# 3. نصب پکیج‌ها
echo "✅ Installing required Python packages..."
pip install --upgrade pip
pip install transformers torch

# 4. اجرای اسکریپت summarize.py
INPUT_FILE=$1
LANG=$2

if [ -z "$INPUT_FILE" ] || [ -z "$LANG" ]; then
  echo "❗ Usage: ./setup_and_run.sh <input_file.txt> <language: fa|en>"
  exit 1
fi

echo "✅ Running summarization on $INPUT_FILE..."
python summarize.py "$INPUT_FILE" "$LANG"
