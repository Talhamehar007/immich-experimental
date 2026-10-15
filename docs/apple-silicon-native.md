# Immich Native Apple Silicon Hardware Acceleration Guide

This guide explains how to run Immich compute natively outside Docker on Apple Silicon (M1/M2/M3/M4) Macs, unlocking direct access to:
- **Apple Neural Engine (ANE) & Metal GPU** for Machine Learning (CLIP smart search embeddings, face detection/recognition, and OCR) via ONNX Runtime's **CoreML Execution Provider**.
- **Apple VideoToolbox** hardware encoding & decoding for ultra-fast, energy-efficient video transcoding (`h264_videotoolbox` and `hevc_videotoolbox`).
- **High performance native Sharp / Libvips** thumbnail generation.

---

## Architecture Overview

Standard Docker Desktop on macOS runs inside a Linux virtual machine, preventing containers from directly accessing Apple Silicon hardware features (the Neural Engine, Metal GPU, and VideoToolbox hardware encoders).

By running the compute-heavy processes natively on macOS outside Docker:
```
Docker or Native (Storage & DB)          Native macOS (Hardware Accelerated)
+-------------------------------+       +------------------------------------+
|  PostgreSQL                   |       |  scripts/apple-silicon/            |
|  Redis                        |<----->|  +- immich-macos.sh                |
|  (Ports: 5432, 6379)          |       |                                    |
+-------------------------------+       |  +- Immich Server / Microservices  |
                                        |     +- VideoToolbox Transcoding    |
                                        |     +- Native Sharp Thumbnails     |
                                        |                                    |
                                        |  +- Machine Learning Service       |
                                        |     +- CoreML Execution Provider   |
                                        |     +- Apple Neural Engine (ANE)   |
                                        |     +- Metal GPU Acceleration      |
                                        +------------------------------------+
```

---

## 1. Video Transcoding with VideoToolbox

### Server Integration
Immich's video transcoding engine now natively supports `videotoolbox` as an acceleration API alongside `nvenc`, `qsv`, `vaapi`, and `rkmpp`:
- **H.264 Encoder:** `h264_videotoolbox`
- **HEVC / H.265 Encoder:** `hevc_videotoolbox`
- **Apple / Web Compatibility:** Outputs are stamped with `-tag:v hvc1` for seamless playback in Safari, Chrome, and iOS/macOS apps.
- **Hardware Decoding:** Uses `-hwaccel videotoolbox` for zero-copy hardware decode.
- **Quality Mapping:** Automatically maps CRF quality to VideoToolbox `-q:v` (1–100 scale).

### Web UI Configuration
Under **Administration -> System Settings -> Transcoding -> Hardware Acceleration**:
- Select **VideoToolbox (Apple Silicon / Metal / macOS)** in the Acceleration API dropdown.

### Standalone VideoToolbox FFmpeg Wrapper
For setups running standard ffmpeg scripts or custom pipelines:
```bash
./scripts/apple-silicon/ffmpeg-videotoolbox.sh -i input.mov -c:v libx264 -crf 23 output.mp4
```
The wrapper intercepts software encoder requests (`libx264`, `libx265`) and automatically maps them to hardware `h264_videotoolbox` and `hevc_videotoolbox`.

---

## 2. Machine Learning with CoreML & Apple Neural Engine

The machine learning service (`immich_ml`) automatically prioritizes `CoreMLExecutionProvider` on Apple Silicon Macs:
- **Compute Units:** Configured with `MLComputeUnits: ALL`, automatically scheduling layers across the Apple Neural Engine, Metal GPU, and high-performance CPU cores.
- **Precision:** FP16 low-precision accumulation enabled on the GPU.
- **Cache Management:** Models are compiled once into `~/.cache/immich_ml/coreml/<chip_model>/<resolution_pins>/` for instant subsequent loads.
- **Environment Override:** You can force specific execution providers at any time using:
  ```bash
  export MACHINE_LEARNING_EXECUTION_PROVIDERS='["CoreMLExecutionProvider", "CPUExecutionProvider"]'
  ```

---

## 3. Running Immich Outside Docker

The repository includes a dedicated orchestrator script: `scripts/apple-silicon/immich-macos.sh`.

### Environment Inspection (Doctor)
Run the doctor tool to inspect your hardware, encoders, and libraries:
```bash
./scripts/apple-silicon/immich-macos.sh doctor
```

### Running Machine Learning Natively
Start the ML service on port `3004` (isolated from any Docker containers):
```bash
./scripts/apple-silicon/immich-macos.sh start-ml
```

### Running the Server Natively
Start the Immich server on port `3283` (isolated from Docker on 2283):
```bash
./scripts/apple-silicon/immich-macos.sh start-server
```

### Port & Network Isolation Matrix
To avoid any collision with existing production Immich containers:
| Service | Production Port | Native Isolated Port | Loopback Binding |
| :--- | :--- | :--- | :--- |
| Immich Server / Web | `2283` | `3283` | `127.0.0.1:3283` |
| Machine Learning | `3003` (internal) | `3004` | `127.0.0.1:3004` |
| PostgreSQL Database | `5432` (internal) | `5433` | `127.0.0.1:5433` |
| Redis Cache | `6379` | `6380` | `127.0.0.1:6380` |
| Docker Network | `immich_default` | `immich_exp_network` | Disjoint Bridge |

### Starting Isolated Backing Dependencies
To start isolated PostgreSQL (`immich_exp_postgres` on port 5433) and Redis (`immich_exp_redis` on port 6380):
```bash
./scripts/apple-silicon/immich-macos.sh start-deps
```
To stop them:
```bash
./scripts/apple-silicon/immich-macos.sh stop-deps
```

For complete network architecture and security details, see [docs/isolated-environment.md](isolated-environment.md).

---

## 4. Hardware & Isolation Verification Suite

Run the full end-to-end automated test suite at any time:
```bash
./scripts/apple-silicon/immich-macos.sh test
```

This verifies:
1. Apple Silicon CPU and GPU core detection.
2. CoreML Execution Provider registration and tensor calculation accuracy.
3. Live `h264_videotoolbox` and `hevc_videotoolbox` transcoding speed and stream tagging.
4. VideoToolbox FFmpeg wrapper argument rewriting.
5. Isolated FastAPI ML server start/ping/stop lifecycle on port 3042.
6. Port and network isolation guarantees (zero overlap with production).
7. Production container safety validation (confirming production containers remain healthy and untouched).
