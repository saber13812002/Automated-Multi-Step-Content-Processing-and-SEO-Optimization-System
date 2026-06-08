# Infrastructure Stack Compatibility Guide

Host reference: `192.168.1.84` (primary server)

This document defines which `docker-compose` stacks can run simultaneously on the same host without port conflicts, and which combinations must never be started together.

## Compose Files (9 total)

| Stack | Compose File | Project Name (default) |
|-------|-------------|------------------------|
| GitLab CE | `tools/gitlab/docker-compose.yml` | `gitlab` |
| RAG infra (main) | `apps/chroma_search_api/docker-compose.yml` | `chroma_search_api` |
| RAG infra (alt) | `apps/chroma_search_api/docker-compose.redis.yml` | `chroma_search_api` |
| Search API | `export-sql-chromadb/docker-compose.yml` | `export-sql-chromadb` |
| Whisper task runner | `whisper-task-runner/docker-compose.yml` | `whisper-task-runner` |
| Whisper cron worker | `whisper-cron-worker/docker-compose.yml` | `whisper-cron-worker` |
| Grafana stack | `tools/grafana/docker-compose.yml` | `grafana` |
| n8n | `tools/n8n/docker-compose.yml` | `n8n` |
| Open WebUI | `tools/open-web-ui/docker-compose.yml` | `open-web-ui` |

## Port Map

| Port | Service | Stack |
|------|---------|-------|
| 81 | GitLab HTTP | GitLab |
| 444 | GitLab HTTPS | GitLab |
| 2222 | GitLab SSH | GitLab |
| 5433 | Postgres | GitLab **or** RAG `redis.yml` (conflict) |
| 5434 | Postgres | RAG main compose |
| 6379 | Redis | GitLab **or** RAG `redis.yml` (conflict) |
| 6380 | Redis | RAG main compose |
| 8000 | ChromaDB | export-sql-chromadb **or** RAG `redis.yml` (conflict) |
| 8001 | ChromaDB | RAG main compose |
| 8080 | FastAPI search API | export-sql-chromadb |
| 8081 | Adminer | whisper-task-runner (resolved) |
| 8108 | Typesense | RAG `redis.yml` only |
| 3000 | Whisper API | whisper-task-runner |
| 3001 | Cron worker API | whisper-cron-worker |
| 3002 | Grafana | Grafana (resolved) |
| 3005 | Open WebUI | Open WebUI |
| 3306 | MySQL | whisper-task-runner |
| 5678 | n8n | n8n |
| 9090 | Prometheus | Grafana |
| 9100 | node-exporter | Grafana |

External (not on this host):

| Endpoint | Service |
|----------|---------|
| `192.168.2.160:11434` | Ollama (Open WebUI backend) |
| `192.168.1.68:8000` | Remote ChromaDB (export-sql-chromadb target) |

## Safe Co-Existence Sets

### Recommended production set (192.168.1.84)

All of these can run together after port conflict resolutions:

```
✅ tools/gitlab/docker-compose.yml
✅ apps/chroma_search_api/docker-compose.yml        ← use MAIN, not redis.yml
✅ export-sql-chromadb/docker-compose.yml           ← Chroma on :8000 only if RAG redis.yml NOT running
✅ whisper-task-runner/docker-compose.yml
✅ whisper-cron-worker/docker-compose.yml
✅ tools/grafana/docker-compose.yml                 ← Grafana on :3002
✅ tools/n8n/docker-compose.yml
✅ tools/open-web-ui/docker-compose.yml
```

### Mutually exclusive pairs (never run both)

| Pair | Conflicting Port(s) | Resolution |
|------|---------------------|------------|
| GitLab + RAG `redis.yml` | 5433, 6379 | Use RAG **main** compose (5434/6380/8001) |
| export-sql-chromadb + RAG `redis.yml` | 8000 | Use RAG **main** compose or remap export Chroma |
| Grafana + whisper-task-runner | 3000 | Grafana moved to 3002 |
| export-sql-chromadb + whisper Adminer | 8080 | Adminer moved to 8081 |

### RAG compose variant rule

**Always use `docker-compose.yml` (main)** on this host, not `docker-compose.redis.yml`:

- Main uses offset ports: Postgres `5434`, Chroma `8001`, Redis `6380`
- `apps/chroma_search_api/.env` is configured for these ports
- `redis.yml` uses standard ports that collide with GitLab and export-sql-chromadb

## Consumer → Provider Wiring

| Consumer | Connects To | How |
|----------|-------------|-----|
| `apps/chroma_search_api` (Node, host :4000) | RAG Chroma `:8001`, Redis `:6380` | Host IP `192.168.1.84` |
| `export-sql-chromadb` FastAPI | Remote Chroma `192.168.1.68:8000` | `.env` `CHROMA_HOST` |
| `export-sql-chromadb` (compose mode) | In-stack `redis`, `chromadb` | Docker DNS |
| `whisper-task-runner` | In-stack `mysql` | Docker DNS `mysql:3306` |
| `whisper-cron-worker` | No database | File-system only |
| `open-webui` | Remote Ollama `192.168.2.160:11434` | HTTP |
| `n8n` | In-stack `postgres` | Docker DNS |

## GPU Coordination

Both `whisper-task-runner` and `whisper-cron-worker` reserve 1× NVIDIA GPU each. On a single-GPU host they will compete. Options:

1. Run only one GPU worker at a time
2. Use `CRON_ENABLED=false` on cron-worker during task-runner active hours
3. Add a GPU lock file or queue coordinator (future)

## Health Check

Run the infrastructure health script after starting stacks:

```bash
./scripts/infra-health-check.sh
./scripts/infra-health-check.sh --since 6h --host 192.168.1.84
```

## Quick Start Commands

```bash
# RAG infra (main variant)
cd apps/chroma_search_api && docker compose up -d

# GitLab
cd tools/gitlab && docker compose up -d

# Whisper workers
cd whisper-task-runner && docker compose up -d
cd whisper-cron-worker && docker compose up -d

# Monitoring (Grafana on :3002)
cd tools/grafana && docker compose up -d
```
