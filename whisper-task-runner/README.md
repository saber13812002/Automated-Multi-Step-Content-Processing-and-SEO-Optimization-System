# Whisper Task Runner

GPU-based Whisper subtitle processing worker with MySQL task queue and time window control.

## Features

- 🎯 **Time Window Control**: Only uses GPU during specified hours (e.g., 11 PM - 5 AM)
- 📁 **File Queue Management**: Processes video files from input directory or MySQL database
- 🔒 **Lock File System**: Prevents duplicate processing with lock files
- 🗄️ **MySQL Integration**: Centralized task queue with timeout handling
- 🌐 **REST API**: Full API for task management and monitoring
- 📊 **Admin Panel**: Adminer included for database management
- 🐳 **Docker Ready**: Full Docker Compose setup with GPU support

## Quick Start

### 1. Clone and Setup

```bash
cd whisper-task-runner
cp .env.example .env
# Edit .env with your settings
```

### 2. Configure Environment Variables

Edit `.env` file:

```env
ACTIVE_START_HOUR=23    # Start hour (24-hour format)
ACTIVE_END_HOUR=5       # End hour
INPUT_DIR=/media/input  # Input directory path
OUTPUT_DIR=/media/output # Output directory path
```

### 3. Start with Docker Compose

```bash
docker compose up -d
```

### 4. Access Services

- **API**: http://localhost:3000
- **Adminer (DB Admin)**: http://localhost:8080
  - Server: `mysql`
  - Username: `whisper` (or `root`)
  - Password: (from `.env`)

## API Endpoints

### Task Management

- `POST /api/tasks` - Create a new task
- `POST /api/tasks/bulk` - Bulk create tasks
- `POST /api/tasks/claim` - Claim pending tasks
- `GET /api/tasks` - List all tasks (with filters)
- `GET /api/tasks/:id` - Get task by ID
- `POST /api/tasks/:id/complete` - Mark task as completed
- `POST /api/tasks/:id/fail` - Mark task as failed

### File Management

- `GET /api/files/scan` - Scan input directory for files

### Health

- `GET /health` - Health check

## Usage Examples

### Create Task via API

```bash
curl -X POST http://localhost:3000/api/tasks \
  -H "Content-Type: application/json" \
  -d '{
    "inputPath": "/media/input/video.mp4",
    "outputPath": "/media/output/video.srt"
  }'
```

### Bulk Import Tasks

```bash
curl -X POST http://localhost:3000/api/tasks/bulk \
  -H "Content-Type: application/json" \
  -d '{
    "tasks": [
      {"inputPath": "/media/input/video1.mp4"},
      {"inputPath": "/media/input/video2.mp4"}
    ]
  }'
```

### Claim Tasks

```bash
curl -X POST http://localhost:3000/api/tasks/claim \
  -H "Content-Type: application/json" \
  -d '{"limit": 5}'
```

## How It Works

1. **File Scanning**: Worker scans `INPUT_DIR` for video files
2. **SRT Check**: Skips files that already have `.srt` files
3. **Lock Files**: Creates `.lock` files to prevent duplicate processing
4. **Time Window**: Only processes during `ACTIVE_START_HOUR` to `ACTIVE_END_HOUR`
5. **Database Fallback**: If directory is empty, fetches tasks from MySQL
6. **Timeout Handling**: Tasks older than `TASK_TIMEOUT_MINUTES` can be reassigned
7. **Graceful Shutdown**: Stops when no work is available

## Database Schema

The `tasks` table includes:

- `id` - Primary key
- `input_path` - Path to input video file
- `output_path` - Path to output SRT file
- `status` - `pending`, `processing`, `done`, `failed`
- `assigned_to` - Machine ID that claimed the task
- `picked_at` - When task was claimed
- `finished_at` - When task completed
- `timeout_minutes` - Timeout duration
- `error_message` - Error details if failed

## Environment Variables

See `.env.example` for all available configuration options.

## GPU Requirements

- NVIDIA GPU with CUDA support
- Docker with NVIDIA Container Toolkit installed
- Sufficient GPU memory for Whisper model (recommended: 8GB+ for `large` model)

## Troubleshooting

### Worker Not Processing Files

1. Check if within active time window
2. Verify GPU is accessible: `docker exec whisper-task-runner-app nvidia-smi`
3. Check logs: `docker compose logs app`

### Database Connection Issues

1. Verify MySQL is healthy: `docker compose ps mysql`
2. Check MySQL logs: `docker compose logs mysql`
3. Verify credentials in `.env`

### Lock Files Not Removed

Lock files are automatically removed after processing. If stuck, manually remove:
```bash
find /media/input -name "*.lock" -delete
```

## Development

### Local Development (without Docker)

```bash
npm install
# Setup MySQL separately
cp .env.example .env
# Edit .env
npm start
```

## License

MIT

