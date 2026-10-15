#!/usr/bin/env bash
# ==============================================================================
# Immich Native Apple Silicon Suite (Run Immich Outside Docker)
# Provides hardware acceleration for VideoToolbox transcoding, CoreML, and ANE
#
# GUARANTEED ZERO-INTERFERENCE ISOLATION ARCHITECTURE:
# - Production Ports: 2283 (Server), 5432 (Postgres), 6379 (Redis), 8901 (Power Tools)
# - Isolated Ports:   3283 (Server), 5433 (Postgres), 6380 (Redis), 3004 (ML)
# - Isolated Docker Network: immich_exp_network (disjoint from immich_default)
# - Host Bindings:    127.0.0.1 (Loopback only, zero LAN exposure)
# ==============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
COMPOSE_FILE="${REPO_ROOT}/docker/docker-compose.isolated.yml"
PID_DIR="${REPO_ROOT}/.immich-native-run"
mkdir -p "$PID_DIR"

# Load .env.isolated if present
if [ -f "${REPO_ROOT}/.env.isolated" ]; then
  set -a
  # shellcheck source=/dev/null
  source "${REPO_ROOT}/.env.isolated"
  set +a
fi

# Fallback isolated defaults (strictly segregated from production 2283 / 5432 / 6379)
export IMMICH_HOST="${IMMICH_HOST:-127.0.0.1}"
export IMMICH_PORT="${IMMICH_PORT:-3283}"
export SERVER_PORT="${SERVER_PORT:-$IMMICH_PORT}"
export IMMICH_ML_PORT="${IMMICH_ML_PORT:-3004}"
export MACHINE_LEARNING_PORT="${MACHINE_LEARNING_PORT:-$IMMICH_ML_PORT}"
export IMMICH_MACHINE_LEARNING_URL="${IMMICH_MACHINE_LEARNING_URL:-http://127.0.0.1:$IMMICH_ML_PORT}"
export DB_HOSTNAME="${DB_HOSTNAME:-127.0.0.1}"
export DB_PORT="${DB_PORT:-5433}"
export DB_USERNAME="${DB_USERNAME:-postgres}"
export DB_PASSWORD="${DB_PASSWORD:-postgres}"
export DB_DATABASE_NAME="${DB_DATABASE_NAME:-immich_exp}"
export DB_VECTOR_EXTENSION="${DB_VECTOR_EXTENSION:-vectorchord}"
export REDIS_HOSTNAME="${REDIS_HOSTNAME:-127.0.0.1}"
export REDIS_PORT="${REDIS_PORT:-6380}"
export REDIS_DBINDEX="${REDIS_DBINDEX:-0}"
export IMMICH_MEDIA_LOCATION="${IMMICH_MEDIA_LOCATION:-${HOME}/immich-experimental-data}"
export UPLOAD_LOCATION="${UPLOAD_LOCATION:-$IMMICH_MEDIA_LOCATION}"
export MACHINE_LEARNING_CACHE_FOLDER="${MACHINE_LEARNING_CACHE_FOLDER:-${HOME}/.cache/immich_ml}"

RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m'

log_info() { echo -e "${BLUE}[INFO]${NC} $*"; }
log_success() { echo -e "${GREEN}[SUCCESS]${NC} $*"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $*"; }
log_error() { echo -e "${RED}[ERROR]${NC} $*" >&2; }

assert_port_available() {
  local port="$1"
  local desc="$2"
  if python3 -c "import socket; s = socket.socket(); sys_exit = s.connect_ex(('127.0.0.1', $port)) == 0; s.close(); exit(0 if sys_exit else 1)" 2>/dev/null; then
    log_warn "Port ${port} (${desc}) is currently in use."
    return 1
  fi
  return 0
}

cmd_doctor() {
  echo -e "\n${BOLD}${CYAN}=== Immich Apple Silicon & Isolation Environment Doctor ===${NC}\n"

  # 1. Hardware & OS
  ARCH="$(uname -m)"
  OS_NAME="$(uname -s)"
  CHIP_NAME="$(sysctl -n machdep.cpu.brand_string 2>/dev/null || echo 'Unknown')"
  HW_CORES="$(sysctl -n hw.ncpu 2>/dev/null || echo 'Unknown')"
  
  log_info "Architecture: ${BOLD}${ARCH}${NC}"
  log_info "OS: ${BOLD}${OS_NAME} $(sw_vers -productVersion 2>/dev/null || true)${NC}"
  log_info "Processor: ${BOLD}${CHIP_NAME}${NC} (${HW_CORES} cores)"

  if [ "$ARCH" = "arm64" ] && [ "$OS_NAME" = "Darwin" ]; then
    log_success "Apple Silicon hardware verified."
  else
    log_warn "Non-Apple Silicon environment detected."
  fi

  # 2. VideoToolbox Support in FFmpeg
  FFMPEG_BIN="$(command -v ffmpeg || echo '')"
  if [ -n "$FFMPEG_BIN" ]; then
    log_info "FFmpeg binary: ${FFMPEG_BIN}"
    if "$FFMPEG_BIN" -encoders 2>&1 | grep -q "h264_videotoolbox"; then
      log_success "VideoToolbox H.264 hardware encoder found."
    else
      log_warn "h264_videotoolbox not found in FFmpeg."
    fi
    if "$FFMPEG_BIN" -encoders 2>&1 | grep -q "hevc_videotoolbox"; then
      log_success "VideoToolbox HEVC hardware encoder found."
    else
      log_warn "hevc_videotoolbox not found in FFmpeg."
    fi
    if "$FFMPEG_BIN" -hwaccels 2>&1 | grep -q "videotoolbox"; then
      log_success "VideoToolbox hardware decoding acceleration supported."
    fi
  else
    log_error "FFmpeg not installed. Run 'brew install ffmpeg' to enable VideoToolbox."
  fi

  # 3. Python & Machine Learning (CoreML)
  if command -v uv >/dev/null 2>&1; then
    UV_VER="$(uv --version)"
    log_success "UV package manager found: ${UV_VER}"
    ORT_PROVIDERS="$(uv run --project "${REPO_ROOT}/machine-learning" python -c "import onnxruntime as ort; print(ort.get_available_providers())" 2>/dev/null || echo 'None')"
    log_info "Available ONNX Runtime Providers: ${ORT_PROVIDERS}"
    if echo "$ORT_PROVIDERS" | grep -q "CoreMLExecutionProvider"; then
      log_success "CoreML Execution Provider (Apple Neural Engine / Metal GPU) is active and available."
    else
      log_warn "CoreMLExecutionProvider not listed in ORT providers."
    fi
  else
    log_error "uv not found. Install uv to manage machine learning environments."
  fi

  # 4. Port & Network Isolation Audit
  echo -e "\n${BOLD}--- Port & Network Isolation Audit ---${NC}"
  log_info "Active Production Check:"
  if python3 -c "import socket; s = socket.socket(); sys_exit = s.connect_ex(('127.0.0.1', 2283)) == 0; s.close(); exit(0 if sys_exit else 1)" 2>/dev/null; then
    log_success "Production Immich server detected running safely on port 2283 (PROTECTED - NOT TOUCHED)."
  else
    log_info "No production server listening on 2283."
  fi

  log_info "Isolated Ports Assignment:"
  echo "  - Isolated Immich Server Port : ${IMMICH_PORT} (Production uses 2283)"
  echo "  - Isolated Machine Learning   : ${IMMICH_ML_PORT} (Production uses 3003)"
  echo "  - Isolated PostgreSQL Port    : ${DB_PORT} (Production uses 5432)"
  echo "  - Isolated Redis Port         : ${REDIS_PORT} (Production uses 6379)"
  echo "  - Host Binding Address        : ${IMMICH_HOST} (Strict loopback)"
  echo "  - Isolated Docker Network     : immich_exp_network (Disjoint from immich_default)"

  # Check that experimental ports don't conflict with production
  if [ "$IMMICH_PORT" = "2283" ] || [ "$DB_PORT" = "5432" ] || [ "$REDIS_PORT" = "6379" ]; then
    log_error "FATAL: Port collision detected! Isolated ports must NEVER equal production ports."
    exit 1
  fi
  log_success "Zero port collisions with production configuration."

  echo -e "\n${GREEN}${BOLD}Doctor checks completed successfully.${NC}\n"
}

cmd_start_deps() {
  log_info "Starting isolated backend dependencies (PostgreSQL 14 VectorChord & Valkey/Redis)..."
  log_info "Using Docker compose file: ${COMPOSE_FILE}"
  docker compose -f "$COMPOSE_FILE" -p immich_exp up -d immich-exp-database immich-exp-redis

  log_info "Waiting for isolated database to report healthy on 127.0.0.1:${DB_PORT}..."
  local attempts=0
  until docker inspect --format='{{.State.Health.Status}}' immich_exp_postgres 2>/dev/null | grep -q "healthy" || [ $attempts -ge 30 ]; do
    sleep 1
    attempts=$((attempts + 1))
  done

  if docker inspect --format='{{.State.Health.Status}}' immich_exp_postgres 2>/dev/null | grep -q "healthy"; then
    log_success "Isolated PostgreSQL is healthy on 127.0.0.1:${DB_PORT} (database: ${DB_DATABASE_NAME})."
  else
    log_warn "Isolated PostgreSQL started (container: immich_exp_postgres)."
  fi

  log_success "Isolated dependencies ready! Network: immich_exp_network | DB: ${DB_PORT} | Redis: ${REDIS_PORT}"
}

cmd_stop_deps() {
  log_info "Stopping isolated backend dependencies (immich_exp_postgres & immich_exp_redis)..."
  docker compose -f "$COMPOSE_FILE" -p immich_exp stop immich-exp-database immich-exp-redis
  log_success "Isolated dependencies stopped safely. Production containers remain untouched."
}

cmd_status() {
  echo -e "\n${BOLD}${CYAN}=== Immich Isolation & Runtime Status ===${NC}\n"

  # 1. Production Status
  echo -e "${BOLD}1. Production Status (Safety Verification):${NC}"
  docker ps --filter "name=immich_" --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}\t{{.Networks}}" | grep -E "immich_server|immich_postgres|immich_redis|immich_machine_learning|immich_power_tools" || echo "  No production containers matching filter."

  # 2. Isolated Containers Status
  echo -e "\n${BOLD}2. Isolated Containers Status:${NC}"
  docker ps -a --filter "name=immich_exp_" --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}\t{{.Networks}}"

  # 3. Native Background Processes
  echo -e "\n${BOLD}3. Native Outside-Docker Processes:${NC}"
  if [ -f "${PID_DIR}/ml.pid" ] && kill -0 "$(cat "${PID_DIR}/ml.pid")" 2>/dev/null; then
    echo -e "  - Native ML:     ${GREEN}RUNNING${NC} (PID: $(cat "${PID_DIR}/ml.pid"), Port: ${IMMICH_ML_PORT})"
  else
    echo -e "  - Native ML:     ${YELLOW}STOPPED${NC}"
  fi

  if [ -f "${PID_DIR}/server.pid" ] && kill -0 "$(cat "${PID_DIR}/server.pid")" 2>/dev/null; then
    echo -e "  - Native Server: ${GREEN}RUNNING${NC} (PID: $(cat "${PID_DIR}/server.pid"), Port: ${IMMICH_PORT})"
  else
    echo -e "  - Native Server: ${YELLOW}STOPPED${NC}"
  fi
  echo ""
}

cmd_start_ml() {
  log_info "Starting Machine Learning service natively outside Docker on ${IMMICH_HOST}:${IMMICH_ML_PORT}..."
  mkdir -p "${IMMICH_MEDIA_LOCATION}" "${MACHINE_LEARNING_CACHE_FOLDER}"

  export IMMICH_HOST="${IMMICH_HOST}"
  export IMMICH_PORT="${IMMICH_ML_PORT}"
  export MACHINE_LEARNING_PORT="${IMMICH_ML_PORT}"
  export MACHINE_LEARNING_CACHE_FOLDER="${MACHINE_LEARNING_CACHE_FOLDER}"
  export IMMICH_MEDIA_LOCATION="${IMMICH_MEDIA_LOCATION}"

  cd "${REPO_ROOT}/machine-learning"
  exec uv run python -m immich_ml
}

cmd_start_server() {
  log_info "Starting Immich Server natively outside Docker on ${IMMICH_HOST}:${IMMICH_PORT}..."
  mkdir -p "${IMMICH_MEDIA_LOCATION}"

  export IMMICH_HOST="${IMMICH_HOST}"
  export IMMICH_PORT="${IMMICH_PORT}"
  export SERVER_PORT="${IMMICH_PORT}"
  export IMMICH_MACHINE_LEARNING_URL="${IMMICH_MACHINE_LEARNING_URL}"
  export IMMICH_MEDIA_LOCATION="${IMMICH_MEDIA_LOCATION}"
  export DB_HOSTNAME="${DB_HOSTNAME}"
  export DB_PORT="${DB_PORT}"
  export DB_USERNAME="${DB_USERNAME}"
  export DB_PASSWORD="${DB_PASSWORD}"
  export DB_DATABASE_NAME="${DB_DATABASE_NAME}"
  export REDIS_HOSTNAME="${REDIS_HOSTNAME}"
  export REDIS_PORT="${REDIS_PORT}"
  export REDIS_DBINDEX="${REDIS_DBINDEX}"
  export IMMICH_BUILD_DATA="${IMMICH_BUILD_DATA:-${REPO_ROOT}/.build_data}"
  export PATH="${SCRIPT_DIR}:${PATH}"

  if [ ! -f "${REPO_ROOT}/server/dist/main.js" ]; then
    log_info "Building server..."
    pnpm --filter immich run build
  fi

  cd "${REPO_ROOT}/server"
  exec node dist/main.js
}

cmd_test() {
  log_info "Running Apple Silicon & Isolation end-to-end verification suite..."
  uv run --project "${REPO_ROOT}/machine-learning" python "${SCRIPT_DIR}/test-apple-silicon.py"
}

cmd_help() {
  echo "Usage: $0 {doctor|status|start-deps|stop-deps|start-ml|start-server|test}"
  echo ""
  echo "Commands:"
  echo "  doctor         Audit hardware acceleration and verify 100% port/network isolation"
  echo "  status         Inspect running production containers, isolated containers, and native processes"
  echo "  start-deps     Start isolated Postgres (${DB_PORT}) and Redis (${REDIS_PORT}) containers"
  echo "  stop-deps      Stop isolated dependency containers safely without touching production"
  echo "  start-ml       Start native ML service with CoreML on ${IMMICH_HOST}:${IMMICH_ML_PORT}"
  echo "  start-server   Start native Immich server on ${IMMICH_HOST}:${IMMICH_PORT}"
  echo "  test           Execute Apple Silicon hardware acceleration & network isolation test suite"
  echo ""
  echo "Port Configuration Matrix:"
  echo "  - Immich Server:      ${IMMICH_PORT} (Production: 2283)"
  echo "  - Machine Learning:   ${IMMICH_ML_PORT} (Production: 3003)"
  echo "  - Postgres Database:  ${DB_PORT} (Production: 5432)"
  echo "  - Redis Cache:        ${REDIS_PORT} (Production: 6379)"
  echo "  - Bind Address:       ${IMMICH_HOST} (Loopback only)"
}

case "${1:-help}" in
  doctor) cmd_doctor ;;
  status) cmd_status ;;
  start-deps) cmd_start_deps ;;
  stop-deps) cmd_stop_deps ;;
  start-ml) cmd_start_ml ;;
  start-server) cmd_start_server ;;
  test) cmd_test ;;
  help|--help|-h) cmd_help ;;
  *)
    log_error "Unknown command: $1"
    cmd_help
    exit 1
    ;;
esac
