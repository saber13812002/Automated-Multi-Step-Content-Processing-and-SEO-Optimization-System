# Shared base image for whisper-task-runner and whisper-cron-worker.
# Build: docker build -t whisper-base:latest -f docker/whisper-base/Dockerfile docker/whisper-base
FROM nvidia/cuda:12.1.0-runtime-ubuntu22.04

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    python3 \
    python3-pip \
    ffmpeg \
    && curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y --no-install-recommends nodejs \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt /tmp/requirements.txt
RUN pip3 install --no-cache-dir -r /tmp/requirements.txt && rm /tmp/requirements.txt

RUN useradd -m -u 1000 -s /bin/bash whisper \
    && mkdir -p /home/whisper/.cache/whisper /media/input /media/output /app \
    && chown -R whisper:whisper /home/whisper /media /app

ENV HOME=/home/whisper
ENV XDG_CACHE_HOME=/home/whisper/.cache

USER whisper
WORKDIR /app
