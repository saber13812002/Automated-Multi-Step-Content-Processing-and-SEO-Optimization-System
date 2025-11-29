#!/bin/bash
# اسکریپت نصب وابستگی‌های لازم برای Subtitle-Generator

set -e

echo "🔧 شروع نصب وابستگی‌ها..."

# بررسی اینکه در محیط venv هستیم
if [ -z "$VIRTUAL_ENV" ]; then
    echo "⚠️  هشدار: به نظر می‌رسد در محیط venv نیستید."
    echo "لطفاً ابتدا محیط را فعال کنید: source venv/bin/activate"
    read -p "آیا می‌خواهید ادامه دهید؟ (y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# نصب numpy (پیش‌نیاز whisper)
echo "📦 نصب numpy..."
pip install numpy>=1.21.0

# نصب pydub
echo "📦 نصب pydub..."
pip install pydub>=0.25.1

# نصب torch و torchaudio (برای GPU/CPU support)
echo "📦 نصب PyTorch..."
pip install torch torchaudio

# حذف نسخه‌های قدیمی whisper
echo "🗑️  حذف نسخه‌های قدیمی whisper..."
pip uninstall whisper openai-whisper -y || true

# نصب whisper از GitHub
echo "📦 نصب whisper از GitHub..."
pip install --upgrade --force-reinstall git+https://github.com/openai/whisper.git

# نصب سایر وابستگی‌ها از requirements.txt
echo "📦 نصب سایر وابستگی‌ها..."
pip install -r requirements.txt

# بررسی نصب
echo ""
echo "✅ بررسی نصب..."
python3 -c "import numpy; print(f'✅ numpy: {numpy.__version__}')" || echo "❌ numpy نصب نشد"
python3 -c "import whisper; print(f'✅ whisper: {whisper.__version__}')" || echo "❌ whisper نصب نشد"
python3 -c "import pydub; print(f'✅ pydub: {pydub.__version__}')" || echo "❌ pydub نصب نشد"
python3 -c "import torch; print(f'✅ torch: {torch.__version__}')" || echo "❌ torch نصب نشد"

echo ""
echo "🎉 نصب کامل شد!"
echo ""
echo "برای تست، دستور زیر را اجرا کنید:"
echo "python3 -c \"import whisper; model = whisper.load_model('tiny'); print('✅ whisper کار می‌کند!')\""

