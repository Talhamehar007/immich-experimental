#!/usr/bin/env bash
# ==============================================================================
# Immich Native Apple Silicon Suite (Run Immich Outside Docker)
# Provides hardware acceleration for VideoToolbox transcoding, CoreML, and ANE
# ==============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"

# Runtime Ports (configured to NEVER collide with production containers on 2283 / 3003)
DEFAULT_SERVER_PORT=3283
DEFAULT_ML_PORT=3004

IMMICH_PORT="${IMMICH_PORT:-$DEFAULT_SERVER_PORT}"
IMMICH_ML_PORT="${IMMICH_ML_PORT:-$DEFAULT_ML_PORT}"
IMMICH_MEDIA_LOCATION="${IMMICH_MEDIA_LOCATION:-${HOME}/immich-data}"
PID_DIR="${REPO_ROOT}/.immich-native-run"

mkdir -p "$PID_DIR"

RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
BOLD='\033[1m'
NC='\033[0m'

log_info() { echo -e "${BLUE}[INFO]${NC} $*"; }
log_success() { echo -e "${GREEN}[SUCCESS]${NC} $*"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $*"; }
log_error() { echo -e "${RED}[ERROR]${NC} $*" >&2; }

cmd_doctor() {
  echo -e "\n${BOLD}=== Immich Apple Silicon Environment Doctor ===${NC}\n"

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

  # 4. Node.js & Server Build
  if command -v node >/dev/null 2>&1; then
    NODE_VER="$(node --version)"
    log_success "Node.js found: ${NODE_VER}"
  else
    log_error "Node.js not found in PATH."
  fi

  if [ -f "${REPO_ROOT}/server/dist/main.js" ]; then
    log_success "Immich server build artifact exists (server/dist/main.js)."
  else
    log_warn "server/dist/main.js not found. Run 'pnpm --filter immich run build' to generate."
  fi

  # 5. Port Safety
  log_info "Configured Native Server Port: ${BOLD}${IMMICH_PORT}${NC}"
  log_info "Configured Native ML Port: ${BOLD}${IMMICH_ML_PORT}${NC}"
  if lsof -Pi :2283 -sTCP:LISTEN -t >/dev/null 2>&1; then
    log_info "Production Immich detected running safely on port 2283 (isolated, will not be touched)."
  fi

  echo -e "\n${GREEN}${BOLD}Doctor checks completed.${NC}\n"
}

cmd_start_ml() {
  log_info "Starting Machine Learning service natively outside Docker on port ${IMMICH_ML_PORT}..."
  export MACHINE_LEARNING_PORT="${IMMICH_ML_PORT}"
  export IMMICH_PORT="${IMMICH_ML_PORT}"
  export MACHINE_LEARNING_CACHE_FOLDER="${HOME}/.cache/immich_ml"
  export IMMICH_MEDIA_LOCATION="${IMMICH_MEDIA_LOCATION}"

  cd "${REPO_ROOT}/machine-learning"
  exec uv run python -m immich_ml
}

cmd_start_server() {
  log_info "Starting Immich Server natively outside Docker on port ${IMMICH_PORT}..."
  export SERVER_PORT="${IMMICH_PORT}"
  export IMMICH_PORT="${IMMICH_PORT}"
  export IMMICH_MACHINE_LEARNING_URL="http://127.0.0.1:${IMMICH_ML_PORT}"
  export IMMICH_MEDIA_LOCATION="${IMMICH_MEDIA_LOCATION}"
  export PATH="${SCRIPT_DIR}:${PATH}"

  if [ ! -f "${REPO_ROOT}/server/dist/main.js" ]; then
    log_info "Building server..."
    pnpm --filter immich run build
  fi

  cd "${REPO_ROOT}/server"
  exec node dist/main.js
}

cmd_test() {
  log_info "Running Apple Silicon end-to-end verification suite..."
  uv run --project "${REPO_ROOT}/machine-learning" python "${SCRIPT_DIR}/test-apple-silicon.py"
}

cmd_help() {
  echo "Usage: $0 {doctor|start-ml|start-server|test}"
  echo ""
  echo "Commands:"
  echo "  doctor         Inspect hardware acceleration (VideoToolbox, CoreML, ANE, FFmpeg)"
  echo "  start-ml       Start machine learning service natively with CoreML on port ${DEFAULT_ML_PORT}"
  echo "  start-server   Start Immich server & microservices natively with VideoToolbox on port ${DEFAULT_SERVER_PORT}"
  echo "  test           Execute in-depth Apple Silicon hardware acceleration tests"
  echo ""
  echo "Environment Variables:"
  echo "  IMMICH_PORT              Port for native server (default: ${DEFAULT_SERVER_PORT})"
  echo "  IMMICH_ML_PORT           Port for native ML (default: ${DEFAULT_ML_PORT})"
  echo "  IMMICH_MEDIA_LOCATION    Media storage path (default: ${HOME}/immich-data)"
}

case "${1:-help}" in
  doctor) cmd_doctor ;;
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
