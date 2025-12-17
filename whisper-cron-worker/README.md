# Whisper Cron Worker

Cron-based Whisper worker that processes video files hourly and sends reports to Telegram/webhook.

## Features

- ⏰ **Scheduled Processing**: Runs on configurable cron schedule (default: hourly)
- 🔔 **Notifications**: Sends reports to Telegram bot or webhook
- 🎛️ **Runtime Control**: Enable/disable cron via API or shell script
- 🐳 **Docker Ready**: Full Docker Compose setup with GPU support
- 📊 **Job Reports**: Detailed reports with success/failure statistics

## Quick Start

### 1. Clone and Setup

```bash
cd whisper-cron-worker
cp .env.example .env
# Edit .env with your settings
```

### 2. Configure Environment Variables

Edit `.env` file:

```env
CRON_ENABLED=true
CRON_SCHEDULE=0 * * * *  # Every hour
TELEGRAM_BOT_TOKEN=your_bot_token
TELEGRAM_CHAT_ID=your_chat_id
```

### 3. Start with Docker Compose

```bash
docker compose up -d
```

### 4. Access API

- **API**: http://localhost:3001

## API Endpoints

### Cron Control

- `GET /api/cron/status` - Get cron status
- `POST /api/cron/enable` - Enable cron job
- `POST /api/cron/disable` - Disable cron job
- `POST /api/cron/schedule` - Update cron schedule

### Job Execution

- `POST /api/job/run` - Manually trigger job execution

### Health

- `GET /health` - Health check

## Usage Examples

### Enable/Disable Cron via API

```bash
# Enable
curl -X POST http://localhost:3001/api/cron/enable

# Disable
curl -X POST http://localhost:3001/api/cron/disable

# Check status
curl http://localhost:3001/api/cron/status
```

### Run Job Manually

```bash
curl -X POST http://localhost:3001/api/job/run
```

### Update Cron Schedule

```bash
curl -X POST http://localhost:3001/api/cron/schedule \
  -H "Content-Type: application/json" \
  -d '{"schedule": "0 */2 * * *"}'  # Every 2 hours
```

## Shell Scripts

Scripts are available inside the container at `/app/scripts/`:

### Toggle Cron

```bash
docker exec whisper-cron-worker-app bash /app/scripts/toggle-cron.sh enable
docker exec whisper-cron-worker-app bash /app/scripts/toggle-cron.sh disable
docker exec whisper-cron-worker-app bash /app/scripts/toggle-cron.sh status
```

### Run Job Manually

```bash
docker exec whisper-cron-worker-app bash /app/scripts/run-job.sh
```

## Cron Schedule Format

The cron schedule uses standard cron syntax:

```
* * * * *
│ │ │ │ │
│ │ │ │ └─── Day of week (0-7, Sunday = 0 or 7)
│ │ │ └───── Month (1-12)
│ │ └─────── Day of month (1-31)
│ └───────── Hour (0-23)
└─────────── Minute (0-59)
```

Examples:

- `0 * * * *` - Every hour at minute 0
- `0 */2 * * *` - Every 2 hours
- `0 9,17 * * *` - At 9 AM and 5 PM daily
- `*/30 * * * *` - Every 30 minutes
- `0 0 * * *` - Daily at midnight

## Notification Setup

### Telegram Bot Setup

1. Create a bot with [@BotFather](https://t.me/botfather)
2. Get your bot token
3. Get your chat ID (send a message to your bot, then visit `https://api.telegram.org/bot<TOKEN>/getUpdates`)
4. Add to `.env`:
   ```env
   TELEGRAM_BOT_TOKEN=your_bot_token
   TELEGRAM_CHAT_ID=your_chat_id
   ```

### Webhook Setup

1. Set up a webhook endpoint that accepts POST requests
2. Add to `.env`:
   ```env
   REPORT_WEBHOOK_URL=https://your-webhook-url.com/report
   ```

## Job Report Format

Reports include:

```json
{
  "startTime": "2024-01-01T12:00:00.000Z",
  "endTime": "2024-01-01T12:05:00.000Z",
  "successful": 5,
  "failed": 1,
  "totalDuration": 300,
  "processed": [
    {
      "file": "video1.mp4",
      "success": true,
      "outputPath": "/media/output/video1.srt",
      "duration": 60
    },
    {
      "file": "video2.mp4",
      "success": false,
      "error": "Error message",
      "duration": 30
    }
  ]
}
```

## How It Works

1. **Cron Scheduler**: Runs job at configured schedule
2. **File Scanning**: Scans `INPUT_DIR` for video files without SRT
3. **Processing**: Processes each file with Whisper
4. **Report Generation**: Creates detailed report
5. **Notification**: Sends report to configured channels (Telegram/webhook)

## Environment Variables

See `.env.example` for all available configuration options.

## GPU Requirements

- NVIDIA GPU with CUDA support
- Docker with NVIDIA Container Toolkit installed
- Sufficient GPU memory for Whisper model (recommended: 8GB+ for `large` model)

## Troubleshooting

### Cron Not Running

1. Check if enabled: `curl http://localhost:3001/api/cron/status`
2. Check logs: `docker compose logs app`
3. Verify schedule format is correct

### Notifications Not Sending

1. Verify Telegram credentials or webhook URL
2. Check logs for errors
3. Test webhook manually: `curl -X POST <webhook_url>`

### Files Not Processing

1. Verify input directory is mounted correctly
2. Check file permissions
3. Ensure files don't already have SRT files

## Integration with n8n

You can integrate with n8n workflows:

1. **Enable/Disable Cron**: Use HTTP Request node to call `/api/cron/enable` or `/api/cron/disable`
2. **Manual Job Trigger**: Use HTTP Request node to call `/api/job/run`
3. **Webhook Reports**: Set up webhook endpoint in n8n and configure `REPORT_WEBHOOK_URL`

Example n8n workflow:

```json
{
  "nodes": [
    {
      "name": "Enable Cron",
      "type": "n8n-nodes-base.httpRequest",
      "parameters": {
        "url": "http://whisper-cron-worker-app:3001/api/cron/enable",
        "method": "POST"
      }
    }
  ]
}
```

## Development

### Local Development (without Docker)

```bash
npm install
cp .env.example .env
# Edit .env
npm start
```

## License

MIT

