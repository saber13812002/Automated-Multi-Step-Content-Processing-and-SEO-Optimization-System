# Quick Start Guide

## Prerequisites

- Docker and Docker Compose installed
- NVIDIA GPU with CUDA support
- NVIDIA Container Toolkit installed on host
- (Optional) Telegram bot token and chat ID for notifications

## Setup Steps

### 1. Configure Environment

```bash
cd whisper-cron-worker
cp .env.example .env
```

Edit `.env` and set:
- `CRON_SCHEDULE` (e.g., `0 * * * *` for hourly)
- `TELEGRAM_BOT_TOKEN` and `TELEGRAM_CHAT_ID` (optional)
- Or `REPORT_WEBHOOK_URL` for webhook notifications

### 2. Start Services

```bash
docker compose up -d
```

### 3. Verify Services

```bash
# Check containers
docker compose ps

# Check logs
docker compose logs app

# Check cron status
curl http://localhost:3001/api/cron/status
```

### 4. Add Video Files

Place video files in the input directory:
```bash
cp /path/to/video.mp4 ./media/input/
```

The cron job will automatically process them according to the schedule.

### 5. Control Cron Job

#### Enable/Disable via API
```bash
# Enable
curl -X POST http://localhost:3001/api/cron/enable

# Disable
curl -X POST http://localhost:3001/api/cron/disable

# Check status
curl http://localhost:3001/api/cron/status
```

#### Run Job Manually
```bash
curl -X POST http://localhost:3001/api/job/run
```

#### Using Shell Scripts (inside container)
```bash
docker exec whisper-cron-worker-app bash /app/scripts/toggle-cron.sh enable
docker exec whisper-cron-worker-app bash /app/scripts/run-job.sh
```

## Common Tasks

### Stop Services
```bash
docker compose down
```

### View Logs
```bash
docker compose logs -f app
```

### Update Cron Schedule
```bash
curl -X POST http://localhost:3001/api/cron/schedule \
  -H "Content-Type: application/json" \
  -d '{"schedule": "0 */2 * * *"}'
```

## Telegram Bot Setup

1. Message [@BotFather](https://t.me/botfather) on Telegram
2. Send `/newbot` and follow instructions
3. Copy the bot token
4. Send a message to your bot
5. Visit: `https://api.telegram.org/bot<TOKEN>/getUpdates`
6. Find your chat ID in the response
7. Add to `.env`:
   ```env
   TELEGRAM_BOT_TOKEN=your_token_here
   TELEGRAM_CHAT_ID=your_chat_id_here
   ```

## Troubleshooting

### Cron not running
1. Check if enabled: `curl http://localhost:3001/api/cron/status`
2. Check logs: `docker compose logs app`
3. Verify schedule format

### Notifications not working
1. Verify Telegram credentials or webhook URL
2. Test webhook manually
3. Check logs for errors

### Files not processing
1. Verify input directory is mounted
2. Check file permissions
3. Ensure files don't already have SRT files

