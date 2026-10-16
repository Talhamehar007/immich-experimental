<p align="center"> 
  <br/>
  <a href="https://opensource.org/license/agpl-v3"><img src="https://img.shields.io/badge/License-AGPL_v3-blue.svg?color=3F51B5&style=for-the-badge&label=License&logoColor=000000&labelColor=ececec" alt="License: AGPLv3"></a>
  <a href="https://discord.immich.app">
    <img src="https://img.shields.io/discord/979116623879368755.svg?label=Discord&logo=Discord&style=for-the-badge&logoColor=000000&labelColor=ececec" alt="Discord"/>
  </a>
  <br/>
  <br/>
</p>

<p align="center">
<img src="design/immich-logo-stacked-light.svg" width="300" title="Login With Custom URL">
</p>
<h3 align="center">High performance self-hosted photo and video management solution — Experimental Apple Silicon & Advanced Video Edition</h3>
<br/>
<a href="https://immich.app">
<img src="design/immich-screenshots.png" title="Main Screenshot">
</a>
<br/>

## 🚀 About `immich-experimental` (What's Different from Upstream Immich?)

**`immich-experimental`** is an enhanced fork of [Immich](https://github.com/immich-app/immich) (synced with upstream `v3.3.3` / `main`) focused on **full-video AI understanding**, **native Apple Silicon hardware acceleration (M-series Metal / CoreML / VideoToolbox)**, **advanced adaptive video playback**, and **isolated side-by-side deployment**.

### Key Differences vs. Upstream Immich

| Capability | Upstream Immich (`immich-app/immich`) | `immich-experimental` (This Fork) |
| :--- | :--- | :--- |
| **Video Semantic Search (CLIP)** | Encodes only a single static thumbnail frame (`previewPath`) per video, missing actions/scenes later in the video. | **Multi-Frame Temporal CLIP Pooling:** Uniformly samples up to **30 frames** across the entire video duration, encodes each frame with CLIP, and stores an **L2-normalized mean-pooled embedding vector** representing the whole video in `smart_search`. |
| **Video Facial Recognition** | Detects faces only on a single static video preview image, missing anyone not visible in that exact frame. | **Multi-Frame Video Face Recognition & Clustering:** Samples up to **30 frames** across the video, detects faces in every frame, and **clusters/deduplicates faces across frames** via cosine similarity (`>= 0.45`). Each distinct person appearing anywhere in the video gets a consolidated face entry with their highest-scoring bounding box and an L2-normalized combined face embedding. |
| **Apple Silicon ML Inference** | Runs inside Linux Docker containers on macOS, restricting ONNX Runtime to CPU emulation without Apple Neural Engine (ANE) or Metal GPU access. | **Native Outside-Docker macOS ML Execution:** Runs `immich_ml` natively on macOS using `CoreMLExecutionProvider` + `MPS`/`Metal` (ANE + Apple GPU) with in-process Uvicorn execution (avoiding macOS Objective-C `fork()` crashes). |
| **Apple Silicon Video Transcoding & Thumbnails** | Linux `/dev/dri` checks in `VideotoolboxConfig` prevent hardware acceleration on macOS; Homebrew `ffmpeg` 9.x lacks `libwebp` for `.webp` video thumbnails. | **Native VideoToolbox (`h264_videotoolbox` / `hevc_videotoolbox`) & WebP/RAW Fallbacks:** Fixes macOS VideoToolbox device detection, maps software CRF to hardware `-q:v`, transparently generates `.webp` video thumbnails via `cwebp`/`sharp`, and falls back to `exiftool` embedded previews for Canon `.CR2`/RAW files. |
| **Web Video Player Experience** | Basic HTML5 video tag with standard controls. | **Immich-Themed Custom Video Player Suite:** Adaptive HLS (`hls.js`) + direct playback with quality selector, custom playback speed slider (`0.25x`–`4x`), buffered range scrubber, double-tap/gesture feedback overlays, Picture-in-Picture, **Stats for Nerds** live telemetry HUD, and non-conflicting `Shift+` keyboard shortcuts (`Shift+K/J/L/F/M/I/C/< / >`) styled in Immich's sky-blue/primary palette. |
| **Side-by-Side Production Isolation** | Default ports (`2283`, `5432`, `6379`, `3003`) collide with an existing local Immich instance. | **Zero-Interference Isolated Stack (`immich-macos.sh`):** Runs on isolated ports (`3283` Server, `3004` Native ML, `5433` VectorChord Postgres, `6380` Valkey/Redis) and an isolated Docker network (`immich_exp_network`) so it can run alongside a live production Immich server with zero interference. |

### Quick Start (macOS Apple Silicon Isolated Stack)

```bash
# 1. Verify hardware acceleration (Metal, MPS, CoreML, VideoToolbox) & port isolation
./scripts/apple-silicon/immich-macos.sh doctor

# 2. Start isolated Postgres/Redis containers + native CoreML ML (port 3004) + Server (port 3283)
./scripts/apple-silicon/immich-macos.sh start

# 3. Check live runtime & isolation status
./scripts/apple-silicon/immich-macos.sh status
```

Once started, open **`http://127.0.0.1:3283/`** (or **`http://localhost:3283/`**).

---

<p align="center">
  <a href="readme_i18n/README_ca_ES.md">Català</a>
  <a href="readme_i18n/README_es_ES.md">Español</a>
  <a href="readme_i18n/README_fr_FR.md">Français</a>
  <a href="readme_i18n/README_it_IT.md">Italiano</a>
  <a href="readme_i18n/README_ja_JP.md">日本語</a>
  <a href="readme_i18n/README_ko_KR.md">한국어</a>
  <a href="readme_i18n/README_de_DE.md">Deutsch</a>
  <a href="readme_i18n/README_nl_NL.md">Nederlands</a>
  <a href="readme_i18n/README_tr_TR.md">Türkçe</a>
  <a href="readme_i18n/README_zh_CN.md">简体中文</a>
  <a href="readme_i18n/README_zh_TW.md">正體中文</a>
  <a href="readme_i18n/README_uk_UA.md">Українська</a>
  <a href="readme_i18n/README_ru_RU.md">Русский</a>
  <a href="readme_i18n/README_bg_BG.md">Български</a>
  <a href="readme_i18n/README_pt_BR.md">Português Brasileiro</a>
  <a href="readme_i18n/README_sv_SE.md">Svenska</a>
  <a href="readme_i18n/README_ar_JO.md">العربية</a>
  <a href="readme_i18n/README_vi_VN.md">Tiếng Việt</a>
  <a href="readme_i18n/README_th_TH.md">ภาษาไทย</a>
  <a href="readme_i18n/README_ml_IN.md">മലയാളം</a>
</p>


> [!WARNING]
> ⚠️ Always follow [3-2-1](https://www.backblaze.com/blog/the-3-2-1-backup-strategy/) backup plan for your precious photos and videos!
> 
 

> [!NOTE]
> You can find the main documentation, including installation guides, at https://immich.app/.

## Links

- [Documentation](https://docs.immich.app/)
- [About](https://docs.immich.app/overview/introduction)
- [Installation](https://docs.immich.app/install/requirements)
- [Roadmap](https://immich.app/roadmap)
- [Demo](#demo)
- [Features](#features)
- [Translations](https://docs.immich.app/developer/translations)
- [Contributing](https://docs.immich.app/overview/support-the-project)


## Demo

Access the demo [here](https://demo.immich.app). For the mobile app, you can use `https://demo.immich.app` for the `Server Endpoint URL`.

### Login credentials

| Email           | Password |
| --------------- | -------- |
| demo@immich.app | demo     |

## Features

| Features                                     | Mobile | Web |
| :------------------------------------------- | ------ | --- |
| Upload and view videos and photos            | Yes    | Yes |
| Auto backup when the app is opened           | Yes    | N/A |
| Prevent duplication of assets                | Yes    | Yes |
| Selective album(s) for backup                | Yes    | N/A |
| Download photos and videos to local device   | Yes    | Yes |
| Multi-user support                           | Yes    | Yes |
| Album and Shared albums                      | Yes    | Yes |
| Scrubbable/draggable scrollbar               | Yes    | Yes |
| Support raw formats                          | Yes    | Yes |
| Metadata view (EXIF, map)                    | Yes    | Yes |
| Search by metadata, objects, faces, and CLIP | Yes    | Yes |
| Administrative functions (user management)   | No     | Yes |
| Background backup                            | Yes    | N/A |
| Virtual scroll                               | Yes    | Yes |
| OAuth support                                | Yes    | Yes |
| API Keys                                     | N/A    | Yes |
| LivePhoto/MotionPhoto backup and playback    | Yes    | Yes |
| Support 360 degree image display             | No     | Yes |
| User-defined storage structure               | Yes    | Yes |
| Public Sharing                               | Yes    | Yes |
| Archive and Favorites                        | Yes    | Yes |
| Global Map                                   | Yes    | Yes |
| Partner Sharing                              | Yes    | Yes |
| Facial recognition and clustering            | Yes    | Yes |
| Memories (x years ago)                       | Yes    | Yes |
| Offline support                              | Yes    | No  |
| Read-only gallery                            | Yes    | Yes |
| Stacked Photos                               | Yes    | Yes |
| Tags                                         | No     | Yes |
| Folder View                                  | Yes    | Yes |

## Translations

Read more about translations [here](https://docs.immich.app/developer/translations).

<a href="https://hosted.weblate.org/engage/immich/">
<img src="https://hosted.weblate.org/widget/immich/immich/multi-auto.svg" alt="Translation status" />
</a>

## Repository activity

![Activities](https://repobeats.axiom.co/api/embed/9e86d9dc3ddd137161f2f6d2e758d7863b1789cb.svg "Repobeats analytics image")

## Contributors

<a href="https://github.com/immich-app/immich/graphs/contributors">
  <img src="https://contrib.rocks/image?repo=immich-app/immich" width="100%"/>
</a>
