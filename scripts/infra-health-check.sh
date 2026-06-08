#!/usr/bin/env bash
# infra-health-check.sh — Multi-container infrastructure health verification
# Usage: ./scripts/infra-health-check.sh [--since 2h] [--cpu-warn 80] [--mem-warn 85]
set -uo pipefail

# ── Defaults (from repo config) ──────────────────────────────────────────────
HOST_IP="${HOST_IP:-192.168.1.84}"
CHROMA_RAG_PORT=8001
REDIS_RAG_PORT=6380
CHROMA_EXPORT_HOST="${CHROMA_EXPORT_HOST:-192.168.1.68}"
CHROMA_EXPORT_PORT=8000
FASTAPI_PORT=8080
NODE_SEARCH_PORT=4000
WHISPER_API_PORT=3000
WHISPER_CRON_PORT=3001
MYSQL_PORT=3306
OLLAMA_HOST="${OLLAMA_HOST:-192.168.2.160:11434}"
LOG_SINCE="2h"
CPU_WARN=80
MEM_WARN=85
LOCK_TIMEOUT_MINUTES=120
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

# ── Counters ─────────────────────────────────────────────────────────────────
PASS_COUNT=0
WARN_COUNT=0
FAIL_COUNT=0
EXIT_CODE=0

# ── Colors ───────────────────────────────────────────────────────────────────
if [[ -t 1 ]]; then
  C_GREEN='\033[0;32m'; C_YELLOW='\033[1;33m'; C_RED='\033[0;31m'
  C_CYAN='\033[0;36m'; C_BOLD='\033[1m'; C_RESET='\033[0m'
else
  C_GREEN=''; C_YELLOW=''; C_RED=''; C_CYAN=''; C_BOLD=''; C_RESET=''
fi

# ── Argument parsing ─────────────────────────────────────────────────────────
while [[ $# -gt 0 ]]; do
  case "$1" in
    --since)       LOG_SINCE="$2"; shift 2 ;;
    --cpu-warn)    CPU_WARN="$2"; shift 2 ;;
    --mem-warn)    MEM_WARN="$2"; shift 2 ;;
    --host)        HOST_IP="$2"; shift 2 ;;
    -h|--help)
      echo "Usage: $0 [--since 2h] [--cpu-warn 80] [--mem-warn 85] [--host IP]"
      exit 0 ;;
    *) echo "Unknown option: $1"; exit 2 ;;
  esac
done

pass() { echo -e "  ${C_GREEN}PASS${C_RESET}  $*"; ((PASS_COUNT++)) || true; }
warn() { echo -e "  ${C_YELLOW}WARN${C_RESET}  $*"; ((WARN_COUNT++)) || true; EXIT_CODE=1; }
fail() { echo -e "  ${C_RED}FAIL${C_RESET}  $*"; ((FAIL_COUNT++)) || true; EXIT_CODE=2; }

section() {
  echo ""
  echo -e "${C_BOLD}${C_CYAN}━━━ $1 ━━━${C_RESET}"
}

# ── Section 1: Prerequisites & Container Discovery ───────────────────────────
section "1. Prerequisites & Container Discovery"

for cmd in docker curl; do
  if command -v "$cmd" &>/dev/null; then
    pass "$cmd available"
  else
    fail "$cmd not found — required"
  fi
done

HAS_NC=false
if command -v nc &>/dev/null; then HAS_NC=true; pass "nc available"
elif command -v timeout &>/dev/null; then pass "timeout available (TCP probes)"
else warn "nc/timeout not found — TCP probes will use curl only"
fi

HAS_NVIDIA=false
if command -v nvidia-smi &>/dev/null; then
  HAS_NVIDIA=true
  pass "nvidia-smi available"
else
  warn "nvidia-smi not found — GPU checks skipped"
fi

if ! docker info &>/dev/null; then
  fail "Docker daemon not reachable"
  echo -e "\n${C_RED}Cannot continue without Docker.${C_RESET}"
  exit 2
fi
pass "Docker daemon reachable"

# Known container name patterns
KNOWN_PATTERNS=(
  "docusaurus_rag_postgres"
  "docusaurus_rag_chromadb"
  "docusaurus_rag_redis"
  "whisper-task-runner-app"
  "whisper-task-runner-mysql"
  "whisper-task-runner-adminer"
  "whisper-cron-worker-app"
  "gitlab"
  "gitlab-postgres"
  "gitlab-redis"
  "n8n"
  "postgres"
  "prometheus"
  "node-exporter"
  "grafana"
)

# Discover running containers
mapfile -t ALL_CONTAINERS < <(docker ps -a --format '{{.Names}}' 2>/dev/null | sort)
RUNNING_CONTAINERS=()
for c in "${ALL_CONTAINERS[@]}"; do
  state=$(docker inspect --format '{{.State.Status}}' "$c" 2>/dev/null || echo "unknown")
  [[ "$state" == "running" ]] && RUNNING_CONTAINERS+=("$c")
done

echo "  Found ${#ALL_CONTAINERS[@]} containers total, ${#RUNNING_CONTAINERS[@]} running"

FOUND_KNOWN=0
for pattern in "${KNOWN_PATTERNS[@]}"; do
  if docker ps -a --format '{{.Names}}' 2>/dev/null | grep -qx "$pattern"; then
    state=$(docker inspect --format '{{.State.Status}}' "$pattern" 2>/dev/null)
    health=$(docker inspect --format '{{if .State.Health}}{{.State.Health.Status}}{{else}}none{{end}}' "$pattern" 2>/dev/null)
    if [[ "$state" == "running" ]]; then
      pass "$pattern (running, health=$health)"
    elif [[ "$state" == "exited" ]]; then
      warn "$pattern (exited)"
    else
      warn "$pattern ($state)"
    fi
    ((FOUND_KNOWN++)) || true
  fi
done

# Also discover export-sql-chromadb project containers by image/name pattern
for c in "${ALL_CONTAINERS[@]}"; do
  if [[ "$c" == *chroma-search* ]] || [[ "$c" == *export-sql* ]]; then
    state=$(docker inspect --format '{{.State.Status}}' "$c" 2>/dev/null)
    if [[ "$state" == "running" ]]; then pass "$c (export-sql-chromadb stack, running)"
    else warn "$c (export-sql-chromadb stack, $state)"; fi
    ((FOUND_KNOWN++)) || true
  fi
done

if [[ $FOUND_KNOWN -eq 0 ]]; then
  warn "No known containers found — stacks may not be deployed"
fi

# Flag bad states across all containers
for c in "${ALL_CONTAINERS[@]}"; do
  state=$(docker inspect --format '{{.State.Status}}' "$c" 2>/dev/null)
  health=$(docker inspect --format '{{if .State.Health}}{{.State.Health.Status}}{{else}}none{{end}}' "$c" 2>/dev/null)
  case "$state" in
    restarting) fail "$c is restarting" ;;
    exited)
      exit_code=$(docker inspect --format '{{.State.ExitCode}}' "$c" 2>/dev/null)
      [[ "$exit_code" != "0" ]] && warn "$c exited with code $exit_code"
      ;;
  esac
  [[ "$health" == "unhealthy" ]] && fail "$c health=unhealthy"
done

# ── Section 2: Resource Utilization ──────────────────────────────────────────
section "2. Container Resource Utilization (CPU>${CPU_WARN}% MEM>${MEM_WARN}%)"

if [[ ${#RUNNING_CONTAINERS[@]} -gt 0 ]]; then
  while IFS= read -r line; do
    [[ -z "$line" ]] && continue
    name=$(echo "$line" | awk '{print $1}')
    cpu_raw=$(echo "$line" | awk '{print $2}' | tr -d '%')
    mem_raw=$(echo "$line" | awk '{print $3}' | tr -d '%')
    cpu_int=${cpu_raw%%.*}
    mem_int=${mem_raw%%.*}
    cpu_int=${cpu_int:-0}
    mem_int=${mem_int:-0}

    if [[ "$cpu_int" -gt "$CPU_WARN" ]] || [[ "$mem_int" -gt "$MEM_WARN" ]]; then
      warn "$name — CPU=${cpu_raw}% MEM=${mem_raw}%"
    else
      pass "$name — CPU=${cpu_raw}% MEM=${mem_raw}%"
    fi
  done < <(docker stats --no-stream --format '{{.Name}} {{.CPUPerc}} {{.MemPerc}}' 2>/dev/null)
else
  warn "No running containers for stats"
fi

# GPU checks
if $HAS_NVIDIA; then
  echo ""
  echo "  Host GPU:"
  nvidia-smi --query-gpu=name,utilization.gpu,memory.used,memory.total,temperature.gpu --format=csv,noheader 2>/dev/null | while IFS= read -r gpu_line; do
    util=$(echo "$gpu_line" | awk -F',' '{print $2}' | tr -d ' %')
    util=${util:-0}
    if [[ "$util" -gt "$CPU_WARN" ]]; then
      warn "GPU high utilization: $gpu_line"
    else
      pass "GPU: $gpu_line"
    fi
  done || warn "nvidia-smi query failed"

  for gpu_container in whisper-task-runner-app whisper-cron-worker-app; do
    if docker ps --format '{{.Names}}' 2>/dev/null | grep -qx "$gpu_container"; then
      if docker exec "$gpu_container" nvidia-smi --query-gpu=name,utilization.gpu --format=csv,noheader 2>/dev/null | head -1 | grep -q .; then
        gpu_out=$(docker exec "$gpu_container" nvidia-smi --query-gpu=name,utilization.gpu --format=csv,noheader 2>/dev/null | head -1)
        pass "$gpu_container sees GPU: $gpu_out"
      else
        fail "$gpu_container cannot access GPU (nvidia-smi failed inside container)"
      fi
    fi
  done
fi

# ── Section 3: Connectivity Matrix ───────────────────────────────────────────
section "3. Port & Connectivity Matrix"

tcp_probe() {
  local host="$1" port="$2" label="$3"
  if $HAS_NC; then
    if nc -z -w3 "$host" "$port" 2>/dev/null; then pass "$label ($host:$port TCP open)"
    else warn "$label ($host:$port TCP closed/unreachable)"; fi
  elif command -v timeout &>/dev/null; then
    if timeout 3 bash -c "echo >/dev/tcp/$host/$port" 2>/dev/null; then
      pass "$label ($host:$port TCP open)"
    else warn "$label ($host:$port TCP closed/unreachable)"; fi
  else
    warn "$label — cannot TCP probe (no nc/timeout)"
  fi
}

http_probe() {
  local url="$1" label="$2" expect="${3:-200}"
  local code
  code=$(curl -s -o /dev/null -w '%{http_code}' --connect-timeout 5 --max-time 10 "$url" 2>/dev/null || echo "000")
  if [[ "$code" == "$expect" ]] || [[ "$code" =~ ^2 ]]; then
    pass "$label ($url → HTTP $code)"
  elif [[ "$code" == "000" ]]; then
    warn "$label ($url → connection failed)"
  else
    warn "$label ($url → HTTP $code, expected $expect)"
  fi
}

redis_ping() {
  local host="$1" port="$2" label="$3"
  local result
  result=$(redis-cli -h "$host" -p "$port" ping 2>/dev/null || echo "ERR")
  if [[ "$result" == "PONG" ]]; then pass "$label (redis-cli PONG)"
  else
    result=$(curl -s --connect-timeout 3 "redis://$host:$port" 2>/dev/null || true)
    tcp_probe "$host" "$port" "$label (TCP fallback, redis-cli unavailable)"
  fi
}

# Host-level probes
redis_ping "$HOST_IP" "$REDIS_RAG_PORT" "RAG Redis"
http_probe "http://${HOST_IP}:${CHROMA_RAG_PORT}/api/v2/heartbeat" "RAG ChromaDB v2 heartbeat"
http_probe "http://${CHROMA_EXPORT_HOST}:${CHROMA_EXPORT_PORT}/api/v1/heartbeat" "Export ChromaDB v1 heartbeat"
http_probe "http://127.0.0.1:${FASTAPI_PORT}/health" "export-sql-chromadb FastAPI /health"
http_probe "http://127.0.0.1:${NODE_SEARCH_PORT}/health" "chroma_search_api Node /health" || \
  http_probe "http://127.0.0.1:${NODE_SEARCH_PORT}/" "chroma_search_api Node root"
tcp_probe "127.0.0.1" "$MYSQL_PORT" "whisper-task-runner MySQL"
http_probe "http://127.0.0.1:${GRAFANA_PORT:-3002}/" "Grafana :${GRAFANA_PORT:-3002}" || true
http_probe "http://${HOST_IP}:81/" "GitLab :81"
http_probe "http://127.0.0.1:5678/" "n8n :5678"
http_probe "http://127.0.0.1:3005/" "Open WebUI :3005"
http_probe "http://${OLLAMA_HOST}/api/tags" "Ollama remote"
tcp_probe "127.0.0.1" "$WHISPER_API_PORT" "whisper-task-runner API"
tcp_probe "127.0.0.1" "$WHISPER_CRON_PORT" "whisper-cron-worker API"

# In-container probes
echo ""
echo "  In-container connectivity:"

if docker ps --format '{{.Names}}' 2>/dev/null | grep -qx "whisper-task-runner-app"; then
  if docker exec whisper-task-runner-app sh -c 'command -v mysqladmin >/dev/null && mysqladmin ping -h mysql -u whisper -pwhisper123 2>/dev/null | grep -q alive' 2>/dev/null; then
    pass "whisper-task-runner-app → mysql (mysqladmin ping)"
  elif docker exec whisper-task-runner-app sh -c 'nc -z mysql 3306 2>/dev/null || timeout 2 bash -c "echo >/dev/tcp/mysql/3306" 2>/dev/null'; then
    pass "whisper-task-runner-app → mysql:3306 (TCP)"
  else
    fail "whisper-task-runner-app cannot reach mysql"
  fi
fi

# Find export-sql-chromadb API container
EXPORT_API=""
for c in "${RUNNING_CONTAINERS[@]}"; do
  img=$(docker inspect --format '{{.Config.Image}}' "$c" 2>/dev/null || echo "")
  if [[ "$c" == *chroma-search* ]] || [[ "$img" == *export-sql* ]] || [[ "$img" == *chroma_search* ]]; then
    EXPORT_API="$c"
    break
  fi
done
if [[ -n "$EXPORT_API" ]]; then
  if docker exec "$EXPORT_API" sh -c 'command -v redis-cli >/dev/null && redis-cli -h redis ping 2>/dev/null' 2>/dev/null | grep -q PONG; then
    pass "$EXPORT_API → redis (redis-cli PING)"
  else
    warn "$EXPORT_API → redis probe inconclusive"
  fi
  if docker exec "$EXPORT_API" curl -sf http://chromadb:8000/api/v1/heartbeat &>/dev/null 2>&1 || \
     docker exec "$EXPORT_API" curl -sf http://chromadb:8000/api/v2/heartbeat &>/dev/null 2>&1; then
    pass "$EXPORT_API → chromadb heartbeat"
  else
    warn "$EXPORT_API → chromadb heartbeat failed"
  fi
fi

if docker ps --format '{{.Names}}' 2>/dev/null | grep -qx "n8n"; then
  if docker exec n8n sh -c 'command -v pg_isready >/dev/null && pg_isready -h postgres 2>/dev/null' 2>/dev/null | grep -q "accepting"; then
    pass "n8n → postgres (pg_isready)"
  else
    warn "n8n → postgres probe inconclusive"
  fi
fi

# ── Section 4: Log Aggregation ───────────────────────────────────────────────
section "4. Log Error Pattern Detection (since $LOG_SINCE)"

LOG_TARGETS=(
  "whisper-task-runner-app"
  "whisper-cron-worker-app"
)

# Add export-sql-chromadb API container if found
[[ -n "$EXPORT_API" ]] && LOG_TARGETS+=("$EXPORT_API")

declare -A LOG_PATTERNS=(
  ["connectivity"]='ECONNREFUSED|ETIMEDOUT|connection.*timeout|connect EHOSTUNREACH|EHOSTUNREACH|getaddrinfo'
  ["db_lock"]='EBUSY|ERESTART|database is locked|Lock wait timeout|SQLITE_BUSY'
  ["whisper_gpu"]='Error processing with Whisper|whisper.*[Ee]rror|CUDA|out of memory|No such file.*whisper|❌ Error processing'
  ["generic_error"]='level=error|\bERROR\b|\bFATAL\b|Traceback \(most recent'
)

for container in "${LOG_TARGETS[@]}"; do
  if ! docker ps -a --format '{{.Names}}' 2>/dev/null | grep -qx "$container"; then
    warn "Log target $container not found — skipping"
    continue
  fi

  echo ""
  echo "  Logs: $container"
  logs=$(docker logs --since "$LOG_SINCE" "$container" 2>&1 || true)
  if [[ -z "$logs" ]]; then
    warn "$container — no logs in window"
    continue
  fi

  for pattern_name in connectivity db_lock whisper_gpu generic_error; do
    pattern="${LOG_PATTERNS[$pattern_name]}"
    count=$(echo "$logs" | grep -ciE "$pattern" 2>/dev/null || echo "0")
    count=$(echo "$count" | tr -d '[:space:]')
    count=${count:-0}

    if [[ "$count" -gt 0 ]]; then
      warn "$container [$pattern_name]: $count matches"
      echo "$logs" | grep -iE "$pattern" | tail -3 | while IFS= read -r line; do
        echo "      | ${line:0:120}"
      done
    else
      pass "$container [$pattern_name]: 0 matches"
    fi
  done
done

# ── Section 5: Stale Lock Files ──────────────────────────────────────────────
section "5. Stale Lock File Check (whisper-task-runner)"

LOCK_DIR="$REPO_ROOT/whisper-task-runner/media/input"
if [[ -d "$LOCK_DIR" ]]; then
  stale_count=0
  while IFS= read -r lockfile; do
    age_min=$(( ( $(date +%s) - $(stat -c %Y "$lockfile" 2>/dev/null || echo 0) ) / 60 ))
    if [[ "$age_min" -gt "$LOCK_TIMEOUT_MINUTES" ]]; then
      warn "Stale lock (${age_min}m): $lockfile"
      ((stale_count++)) || true
    fi
  done < <(find "$LOCK_DIR" -name '*.lock' -type f 2>/dev/null)

  total_locks=$(find "$LOCK_DIR" -name '*.lock' -type f 2>/dev/null | wc -l)
  if [[ "$stale_count" -eq 0 ]]; then
    pass "Lock files: $total_locks total, 0 stale (>${LOCK_TIMEOUT_MINUTES}m)"
  fi
else
  warn "Lock directory not found: $LOCK_DIR"
fi

# ── Section 6: Summary ───────────────────────────────────────────────────────
section "6. Summary"

echo -e "  ${C_GREEN}PASS: $PASS_COUNT${C_RESET}  ${C_YELLOW}WARN: $WARN_COUNT${C_RESET}  ${C_RED}FAIL: $FAIL_COUNT${C_RESET}"

if [[ $FAIL_COUNT -gt 0 ]]; then
  echo -e "\n  ${C_RED}Result: CRITICAL — $FAIL_COUNT failure(s) detected${C_RESET}"
  exit 2
elif [[ $WARN_COUNT -gt 0 ]]; then
  echo -e "\n  ${C_YELLOW}Result: WARNINGS — $WARN_COUNT warning(s)${C_RESET}"
  exit 1
else
  echo -e "\n  ${C_GREEN}Result: ALL CHECKS PASSED${C_RESET}"
  exit 0
fi
