# 📚 مستندات کامل پروژه Fine-tuning Whisper

---

## 🎯 خلاصه پروژه
Fine-tuning مدل Whisper Large V3 برای زبان فارسی با استفاده از 1327 نمونه صوتی (89 دقیقه)

---

## 📋 مراحل انجام شده

### 1️⃣ نصب و راه‌اندازی Docker + NVIDIA

```bash
# نصب Docker
sudo apt update
sudo apt install -y docker-ce docker-ce-cli containerd.io

# نصب NVIDIA Container Toolkit
curl -fsSL https://nvidia.github.io/libnvidia-container/gpgkey | sudo gpg --dearmor -o /usr/share/keyrings/nvidia-container-toolkit-keyring.gpg
echo "deb [signed-by=/usr/share/keyrings/nvidia-container-toolkit-keyring.gpg] https://nvidia.github.io/libnvidia-container/stable/deb/amd64 /" | sudo tee /etc/apt/sources.list.d/nvidia-container-toolkit.list
sudo apt update
sudo apt install -y nvidia-container-toolkit
sudo nvidia-ctk runtime configure --runtime=docker
sudo systemctl restart docker

# تست GPU
docker run --rm --gpus all nvidia/cuda:12.0.0-base-ubuntu22.04 nvidia-smi
```

---

### 2️⃣ ساخت Docker Container

**Dockerfile:**
```dockerfile
FROM nvidia/cuda:11.8.0-cudnn8-runtime-ubuntu22.04

ENV DEBIAN_FRONTEND=noninteractive
ENV TZ=Asia/Tehran

RUN apt-get update && apt-get install -y \
    python3.10 python3-pip ffmpeg git vim wget curl \
    && rm -rf /var/lib/apt/lists/*

RUN pip3 install --upgrade pip

RUN pip3 install --no-cache-dir \
    torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118

RUN pip3 install --no-cache-dir \
    openai-whisper faster-whisper transformers accelerate \
    datasets evaluate jiwer tensorboard gradio pydub \
    numpy pandas python-Levenshtein rapidfuzz python-docx

WORKDIR /workspace
EXPOSE 7860 6006
CMD ["/bin/bash"]
```

**docker-compose.yml:**
```yaml
services:
  whisper-stable:
    build: .
    image: whisper-stable:latest
    container_name: whisper-stable
    restart: unless-stopped
    
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              count: 1
              capabilities: [gpu]
    
    environment:
      - NVIDIA_VISIBLE_DEVICES=all
      - CUDA_VISIBLE_DEVICES=0
      - HF_HOME=/workspace/models
      - TRANSFORMERS_CACHE=/workspace/models
      
    volumes:
      - ./data:/workspace/data
      - ./models:/workspace/models
      - ./output:/workspace/output
      - ./scripts:/workspace/scripts
      - whisper_cache:/root/.cache
      
    working_dir: /workspace
    stdin_open: true
    tty: true
    ports:
      - "7860:7860"
      - "6006:6006"

volumes:
  whisper_cache:
    driver: local
```

**ساخت و اجرا:**
```bash
cd ~/whisper-project
docker compose build
docker compose up -d
docker compose exec whisper-stable bash
```

---

### 3️⃣ Mount کردن Windows Share

```bash
# نصب ابزار
sudo apt install -y cifs-utils

# Mount
sudo mkdir -p /mnt/share
sudo mount -t cifs //172.18.40.150/share /mnt/share \
  -o username=s.tabatabaei,password=Fxxxxxxxxxxx,domain=QABAS.net,vers=3.0,uid=0,gid=0,file_mode=0777,dir_mode=0777

# Mount دائمی
echo "username=s.tabatabaei" | sudo tee /root/.smbcredentials
echo "password=Fxxxxxxxxxx" | sudo tee -a /root/.smbcredentials
echo "domain=QABAS.net" | sudo tee -a /root/.smbcredentials
sudo chmod 600 /root/.smbcredentials

# اضافه به fstab
echo "//172.18.40.150/share /mnt/share cifs credentials=/root/.smbcredentials,vers=3.0,uid=0,gid=0,file_mode=0777,dir_mode=0777,_netdev 0 0" | sudo tee -a /etc/fstab
```

---

### 4️⃣ کپی فایل‌ها

```bash
# ساخت پوشه‌ها
mkdir -p ~/whisper-project/data/raw

# کپی فایل‌ها
cp /mnt/share/471*.txt ~/whisper-project/data/raw/471.txt
cp /mnt/share/471*.srt ~/whisper-project/data/raw/471.srt
cp /mnt/share/471*.wav ~/whisper-project/data/raw/471.wav

cp /mnt/share/*215*.txt ~/whisper-project/data/raw/215.txt
cp /mnt/share/*215*.srt ~/whisper-project/data/raw/215.srt
cp /mnt/share/*215*.wav ~/whisper-project/data/raw/215.wav
```

---

### 5️⃣ پردازش دیتاست

**اسکریپت `/workspace/scripts/process_all.py`:**
- Parse کردن SRT با الگوریتم انعطاف‌پذیر
- تطبیق SRT با متن مرجع (Fuzzy Matching)
- برش فایل‌های صوتی بر اساس SRT تصحیح شده
- فیلتر کردن (1-30 ثانیه)
- حذف موسیقی و متن‌های کوتاه

**نتیجه:**
- ✅ 1327 قطعه صوتی
- ✅ 710 قطعه از فایل 471
- ✅ 617 قطعه از فایل 215
- ✅ میانگین طول: 4 ثانیه
- ✅ مدت کل: 89.2 دقیقه

---

### 6️⃣ تبدیل به HuggingFace Dataset

**اسکریپت `/workspace/scripts/create_hf_dataset.py`:**
```python
# تقسیم به train/validation/test (80/10/10)
# Cast audio به Audio(sampling_rate=16000)
# ذخیره در /workspace/data/hf_dataset
```

**نتیجه:**
- Train: 1061 نمونه (80%)
- Validation: 133 نمونه (10%)
- Test: 133 نمونه (10%)

---

### 7️⃣ Fine-tuning Whisper

**اسکریپت `/workspace/scripts/train.py`:**

**تنظیمات:**
```python
MODEL_NAME = "openai/whisper-large-v3"
LANGUAGE = "persian"
TASK = "transcribe"

# Training Args:
- per_device_train_batch_size: 4
- gradient_accumulation_steps: 2
- learning_rate: 1e-5
- max_steps: 5000
- fp16: True
- evaluation_strategy: steps (هر 500 step)
- metric: WER (Word Error Rate)
```

**اجرا:**
```bash
# داخل container
python3 /workspace/scripts/train.py
```

**زمان تقریبی:** 4-7 ساعت (با RTX 4090)

---

## 📁 ساختار نهایی پروژه

```
~/whisper-project/
├── Dockerfile
├── docker-compose.yml
├── data/
│   ├── raw/                    # فایل‌های اولیه
│   │   ├── 471.txt
│   │   ├── 471.srt
│   │   ├── 471.wav
│   │   ├── 215.txt
│   │   ├── 215.srt
│   │   └── 215.wav
│   ├── processed/              # دیتاست پردازش شده
│   │   ├── dataset_471/
│   │   │   ├── audio/          # 710 فایل WAV
│   │   │   └── transcripts/    # 710 فایل TXT
│   │   ├── dataset_215/
│   │   │   ├── audio/          # 617 فایل WAV
│   │   │   └── transcripts/    # 617 فایل TXT
│   │   ├── 471_corrected.srt
│   │   ├── 215_corrected.srt
│   │   └── all_segments.json
│   └── hf_dataset/             # HuggingFace Dataset
│       ├── train/
│       ├── validation/
│       └── test/
├── scripts/
│   ├── process_all.py          # پردازش SRT و برش صوت
│   ├── create_hf_dataset.py    # تبدیل به HF Dataset
│   └── train.py                # Fine-tuning
├── output/
│   └── whisper-persian/        # مدل Fine-tuned شده
│       ├── pytorch_model.bin
│       ├── config.json
│       ├── preprocessor_config.json
│       └── ...
└── models/                     # Cache مدل‌ها
```

---

## 🚀 دستورات مهم

```bash
# ورود به container
docker compose exec whisper-stable bash

# مانیتور GPU
nvidia-smi

# TensorBoard
tensorboard --logdir /workspace/output/whisper-persian --host 0.0.0.0

# چک کردن پیشرفت
ls -lh /workspace/output/whisper-persian/checkpoint-*
```

---

## 📊 آمار نهایی

| مشخصه | مقدار |
|-------|-------|
| کل دیتاست | 1327 نمونه |
| مدت زمان کل | 89.2 دقیقه |
| میانگین طول | 4 ثانیه |
| Train | 1061 نمونه |
| Validation | 133 نمونه |
| Test | 133 نمونه |
| مدل پایه | Whisper Large V3 |
| GPU | RTX 4090 (24GB) |
| زمان Training | ~5 ساعت |

---

## 🎯 مرحله بعد: Upload به HuggingFace

```bash
# نصب huggingface_hub
pip install huggingface_hub

# Login
huggingface-cli login

# Upload
python3 << EOF
from huggingface_hub import HfApi
api = HfApi()
api.create_repo("whisper-large-v3-persian-finetuned")
api.upload_folder(
    folder_path="/workspace/output/whisper-persian",
    repo_id="YOUR_USERNAME/whisper-large-v3-persian-finetuned",
    repo_type="model"
)
EOF
```

---

**این مستندات کامل پروژه است! ✅**