#!/usr/bin/env bash
# VideoToolbox FFmpeg Hardware Acceleration Wrapper for Apple Silicon
# Translates software encoder arguments into Apple VideoToolbox hardware encoders.

set -euo pipefail

REAL_FFMPEG="${IMMICH_REAL_FFMPEG:-$(command -v ffmpeg || echo "/opt/homebrew/bin/ffmpeg")}"

if [ ! -x "$REAL_FFMPEG" ]; then
  echo "Error: ffmpeg binary not found at $REAL_FFMPEG" >&2
  exit 1
fi

# Convert 0-51 CRF scale (lower is better) to VideoToolbox 1-100 quality scale (higher is better)
crf_to_vt_quality() {
  local crf="$1"
  # Clamp crf to 0-51
  if [ "$crf" -lt 0 ]; then crf=0; fi
  if [ "$crf" -gt 51 ]; then crf=51; fi
  local q=$(( ((51 - crf) * 99 + 25) / 51 + 1 ))
  if [ "$q" -lt 1 ]; then q=1; fi
  if [ "$q" -gt 100 ]; then q=100; fi
  echo "$q"
}

USE_HW_ENCODER=false
USE_HEVC=false
ARGS=("$@")
NEW_ARGS=()

# Hardware decode flag (default true on Apple Silicon)
HW_DECODE="${IMMICH_VT_HW_DECODE:-true}"

if [ "$HW_DECODE" = "true" ]; then
  # Inject hardware decoding before input arguments if -i is present and not lavfi
  has_hwaccel=false
  has_input=false
  is_lavfi=false
  for ((idx=0; idx<${#ARGS[@]}; idx++)); do
    arg="${ARGS[$idx]}"
    if [ "$arg" = "-hwaccel" ]; then
      has_hwaccel=true
    elif [ "$arg" = "-i" ]; then
      has_input=true
    elif [ "$arg" = "-f" ] && [ "${ARGS[$((idx+1))]:-}" = "lavfi" ]; then
      is_lavfi=true
    fi
  done
  if [ "$has_hwaccel" = "false" ] && [ "$has_input" = "true" ] && [ "$is_lavfi" = "false" ]; then
    NEW_ARGS+=("-hwaccel" "videotoolbox")
  fi
fi

i=0
while [ $i -lt ${#ARGS[@]} ]; do
  arg="${ARGS[$i]}"

  case "$arg" in
    -c:v|-vcodec)
      next="${ARGS[$((i+1))]:-}"
      case "$next" in
        h264|libx264|libx264rgb)
          NEW_ARGS+=("$arg" "h264_videotoolbox" "-allow_sw" "1")
          USE_HW_ENCODER=true
          i=$((i + 2))
          continue
          ;;
        hevc|libx265)
          NEW_ARGS+=("$arg" "hevc_videotoolbox" "-allow_sw" "1" "-tag:v" "hvc1")
          USE_HW_ENCODER=true
          USE_HEVC=true
          i=$((i + 2))
          continue
          ;;
        h264_videotoolbox|hevc_videotoolbox)
          NEW_ARGS+=("$arg" "$next" "-allow_sw" "1")
          USE_HW_ENCODER=true
          if [ "$next" = "hevc_videotoolbox" ]; then
            USE_HEVC=true
            NEW_ARGS+=("-tag:v" "hvc1")
          fi
          i=$((i + 2))
          continue
          ;;
      esac
      ;;

    # Strip CPU-specific software presets when using VideoToolbox
    -preset|-x264-params|-x265-params|-svtav1-params)
      if [ "$USE_HW_ENCODER" = "true" ]; then
        i=$((i + 2))
        continue
      fi
      ;;

    # Translate -crf into -q:v for VideoToolbox
    -crf)
      if [ "$USE_HW_ENCODER" = "true" ]; then
        crf_val="${ARGS[$((i+1))]:-23}"
        vt_q=$(crf_to_vt_quality "$crf_val")
        NEW_ARGS+=("-q:v" "$vt_q")
        i=$((i + 2))
        continue
      fi
      ;;
  esac

  NEW_ARGS+=("$arg")
  i=$((i + 1))
done

exec "$REAL_FFMPEG" "${NEW_ARGS[@]}"
