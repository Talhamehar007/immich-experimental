# Immich Experimental Isolated Network & Port Architecture

This document describes the isolation architecture for running and testing experimental Immich features (including the YouTube video player and Apple Silicon native acceleration) without interfering with or touching any existing production Immich containers, databases, or networks.

---

## 1. Safety Principles & Guarantees

1. **Zero Port Collisions:** Experimental processes and containers bind strictly to dedicated, non-overlapping port numbers.
2. **Network Isolation:** Auxiliary containers run on a separate Docker bridge network (`immich_exp_network`) that is completely isolated and disjoint from the production `immich_default` network.
3. **Loopback Host Binding:** All host-bound services bind strictly to `127.0.0.1` (loopback only), preventing LAN exposure or accidental routing to docker containers.
4. **Volume Segregation:** Dedicated volumes (`immich_exp_pgdata`, `immich_exp_redisdata`, and `${HOME}/immich-experimental-data`) prevent any risk of database or photo library corruption.

---

## 2. Port & Network Allocation Matrix

| Component | Production Environment | Isolated Experimental Environment | Loopback Binding | Purpose |
| :--- | :--- | :--- | :--- | :--- |
| **Immich Server / Web API** | `2283` | `3283` | `127.0.0.1:3283` | Primary Web UI and REST API |
| **Machine Learning Service** | `3003` (internal Docker) | `3004` (test: `3042`) | `127.0.0.1:3004` | CoreML, Face detection, CLIP smart search |
| **PostgreSQL (VectorChord)** | `5432` (internal Docker) | `5433` | `127.0.0.1:5433` | Isolated Postgres database (`immich_exp`) |
| **Redis / Valkey Cache** | `6379` (host/Docker) | `6380` | `127.0.0.1:6380` | Background job queues and cache |
| **Docker Network** | `immich_default` | `immich_exp_network` | Disjoint bridge | Container-to-container routing |
| **Media / Upload Directory** | Production data folder | `${HOME}/immich-experimental-data` | Local filesystem | Uploaded photos, videos, and transcoded assets |

---

## 3. Architecture Topology

```
+-----------------------------------------------------------------------------------+
| USER MACHINE (macOS Apple Silicon)                                                |
|                                                                                   |
|  [ PRODUCTION IMMICH STACK - UNTOUCHED & ISOLATED ]                               |
|  +-----------------------------------------------------------------------------+  |
|  | Network: immich_default                                                      |  |
|  | - immich_server             (Port 0.0.0.0:2283)                             |  |
|  | - immich_machine_learning   (Port 3003 internal)                            |  |
|  | - immich_postgres           (Port 5432 internal)                            |  |
|  | - immich_redis              (Port 6379 internal/host)                       |  |
|  | - immich_power_tools        (Port 0.0.0.0:8901)                             |  |
|  +-----------------------------------------------------------------------------+  |
|                                                                                   |
|  [ EXPERIMENTAL ISOLATED STACK ]                                                  |
|  +-----------------------------------------------------------------------------+  |
|  | 1. Docker Backing Services (Network: immich_exp_network)                     |  |
|  |    - immich_exp_postgres    (Port 127.0.0.1:5433 -> 5432)                   |  |
|  |    - immich_exp_redis       (Port 127.0.0.1:6380 -> 6379)                   |  |
|  |                                                                             |  |
|  | 2. Native Apple Silicon Processes (Outside Docker)                          |  |
|  |    - Native ML Service      (Port 127.0.0.1:3004)                           |  |
|  |         +- CoreMLExecutionProvider -> Apple Neural Engine (ANE) / Metal GPU |  |
|  |    - Native Immich Server   (Port 127.0.0.1:3283)                           |  |
|  |         +- VideoToolbox Transcoding (h264_videotoolbox, hevc_videotoolbox)  |  |
|  |         +- YouTube Video Player Suite (Adaptive HLS, Settings, HUD)         |  |
|  +-----------------------------------------------------------------------------+  |
+-----------------------------------------------------------------------------------+
```

---

## 4. Quick Start & Workflow

### 1. Audit Environment & Verify Production Safety
```bash
./scripts/apple-silicon/immich-macos.sh doctor
```
Checks:
- Apple Silicon hardware & OS version
- VideoToolbox encoders in FFmpeg
- CoreML Execution Provider in ONNX Runtime
- Verifies production containers on port 2283 are untouched
- Confirms zero port collision

### 2. Start Isolated Backing Dependencies
```bash
./scripts/apple-silicon/immich-macos.sh start-deps
```
This boots `immich_exp_postgres` (on `127.0.0.1:5433`) and `immich_exp_redis` (on `127.0.0.1:6380`) inside `immich_exp_network`.

### 3. Check Live Status
```bash
./scripts/apple-silicon/immich-macos.sh status
```
Displays:
1. Production status (verifies `immich_server` is untouched and healthy)
2. Isolated containers (`immich_exp_postgres` on 5433, `immich_exp_redis` on 6380)
3. Native background processes

### 4. Start Native ML Service (Apple Neural Engine / CoreML)
```bash
./scripts/apple-silicon/immich-macos.sh start-ml
```
Runs natively outside Docker on `http://127.0.0.1:3004`.

### 5. Start Native Immich Server (VideoToolbox + YouTube Player)
```bash
./scripts/apple-silicon/immich-macos.sh start-server
```
Runs natively outside Docker on `http://127.0.0.1:3283`.
Access the web application at: [http://127.0.0.1:3283](http://127.0.0.1:3283).

### 6. Run Automated Hardware & Isolation Verification Tests
```bash
./scripts/apple-silicon/immich-macos.sh test
```
Executes all 7 automated test stages:
1. Apple Silicon hardware environment check
2. ONNX Runtime CoreML execution verification
3. FFmpeg VideoToolbox transcoding (H.264 & HEVC)
4. VideoToolbox smart CLI wrapper
5. Native FastAPI ML server on isolated port 3042
6. Port & network isolation verification
7. Production container safety check

### 7. Stop Isolated Dependencies
```bash
./scripts/apple-silicon/immich-macos.sh stop-deps
```
Cleanly tears down `immich_exp_postgres` and `immich_exp_redis` without affecting any other running container on the system.
