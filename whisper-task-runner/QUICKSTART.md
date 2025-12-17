# Quick Start Guide

## Prerequisites

- Docker and Docker Compose installed
- NVIDIA GPU with CUDA support
- NVIDIA Container Toolkit installed on host

## Setup Steps

### 1. Configure Environment

```bash
cd whisper-task-runner
cp .env.example .env
```

Edit `.env` and set:
- `ACTIVE_START_HOUR` and `ACTIVE_END_HOUR` (e.g., 23 and 5 for 11 PM to 5 AM)
- `INPUT_DIR` and `OUTPUT_DIR` paths
- MySQL credentials

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

# Check GPU access
docker exec whisper-task-runner-app nvidia-smi
```

### 4. Add Tasks

#### Option A: Place files in input directory
```bash
cp /path/to/video.mp4 ./media/input/
```

#### Option B: Use API to create task
```bash
curl -X POST http://localhost:3000/api/tasks \
  -H "Content-Type: application/json" \
  -d '{"inputPath": "/media/input/video.mp4"}'
```

### 5. Monitor Progress

```bash
# View API logs
docker compose logs -f app

# Check task status
curl http://localhost:3000/api/tasks

# Access Adminer (DB UI)
# Open http://localhost:8080 in browser
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

### Restart Worker
```bash
docker compose restart app
```

### Access Database
```bash
docker exec -it whisper-task-runner-mysql mysql -u whisper -p whisper_tasks
```

## Troubleshooting

### Worker not processing
1. Check if within time window: `curl http://localhost:3000/health`
2. Check GPU: `docker exec whisper-task-runner-app nvidia-smi`
3. Check logs: `docker compose logs app`

### Database connection errors
1. Wait for MySQL to be ready: `docker compose ps mysql`
2. Check MySQL logs: `docker compose logs mysql`
3. Verify credentials in `.env`

