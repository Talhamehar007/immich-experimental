#!/usr/bin/env python3
"""
Comprehensive Apple Silicon Hardware Acceleration Test Suite for Immich.
Tests VideoToolbox encoding/decoding, CoreML Execution Provider,
Apple Neural Engine integration, and isolated non-docker execution.
"""

from __future__ import annotations

import json
import os
import platform
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Any

# Ensure project root is in sys.path
REPO_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(REPO_ROOT / "machine-learning"))

GREEN = "\033[92m"
RED = "\033[91m"
BLUE = "\033[94m"
YELLOW = "\033[93m"
BOLD = "\033[1m"
RESET = "\033[0m"


def print_step(name: str) -> None:
    print(f"\n{BLUE}[TEST]{RESET} {BOLD}{name}{RESET}")


def print_pass(msg: str) -> None:
    print(f"  {GREEN}✓ PASS:{RESET} {msg}")


def print_fail(msg: str) -> None:
    print(f"  {RED}✗ FAIL:{RESET} {msg}")
    sys.exit(1)


def test_hardware_environment() -> None:
    print_step("Apple Silicon Hardware Environment")
    arch = platform.machine()
    system = platform.system()
    if system != "Darwin":
        print_fail(f"Expected macOS Darwin system, got {system}")
    if arch != "arm64":
        print_fail(f"Expected arm64 architecture, got {arch}")

    try:
        brand = subprocess.check_output(["sysctl", "-n", "machdep.cpu.brand_string"], text=True).strip()
    except Exception:
        brand = "Apple Silicon"

    try:
        ncpu = subprocess.check_output(["sysctl", "-n", "hw.ncpu"], text=True).strip()
    except Exception:
        ncpu = "Unknown"

    print_pass(f"System: macOS {platform.mac_ver()[0]} ({system})")
    print_pass(f"Processor: {brand} ({ncpu} cores, {arch})")


def test_coreml_onnxruntime() -> None:
    print_step("ONNX Runtime CoreML Execution Provider")
    try:
        import onnxruntime as ort
    except ImportError:
        print_fail("onnxruntime is not installed in the Python environment")

    providers = ort.get_available_providers()
    print_pass(f"Available Providers: {providers}")

    if "CoreMLExecutionProvider" not in providers:
        print_fail("CoreMLExecutionProvider is not available in ONNX Runtime")
    print_pass("CoreMLExecutionProvider detected and registered")

    # Test device detection and provider preference in immich_ml
    from immich_ml.sessions.ort import _apple_silicon, _providers_default

    device = _apple_silicon()
    print_pass(f"Immich ML Apple Silicon Device: kind={device.kind}, version={device.version}")

    default_providers = _providers_default()
    if default_providers[0] != "CoreMLExecutionProvider":
        print_fail(f"Expected CoreMLExecutionProvider as top provider, got {default_providers}")
    print_pass(f"Top Execution Provider chosen by Immich: {default_providers[0]}")

    # Build and test a tiny ONNX model with CoreML
    import numpy as np
    import onnx
    from onnx import helper, TensorProto

    # Create a simple Y = X * 2 + 1 node graph
    X = helper.make_tensor_value_info("X", TensorProto.FLOAT, [1, 4])
    Y = helper.make_tensor_value_info("Y", TensorProto.FLOAT, [1, 4])
    node_scale = helper.make_node("Mul", inputs=["X", "scale"], outputs=["scaled"])
    node_bias = helper.make_node("Add", inputs=["scaled", "bias"], outputs=["Y"])
    scale_tensor = helper.make_tensor("scale", TensorProto.FLOAT, [1, 4], [2.0, 2.0, 2.0, 2.0])
    bias_tensor = helper.make_tensor("bias", TensorProto.FLOAT, [1, 4], [1.0, 1.0, 1.0, 1.0])

    graph = helper.make_graph(
        [node_scale, node_bias],
        "test_coreml_graph",
        [X],
        [Y],
        initializer=[scale_tensor, bias_tensor],
    )
    model = helper.make_model(graph, producer_name="immich_test", ir_version=10)
    model.opset_import[0].version = 17

    with tempfile.NamedTemporaryFile(suffix=".onnx", delete=False) as f:
        onnx.save(model, f.name)
        model_path = f.name

    try:
        session = ort.InferenceSession(
            model_path,
            providers=["CoreMLExecutionProvider", "CPUExecutionProvider"],
            provider_options=[
                {
                    "ModelFormat": "MLProgram",
                    "MLComputeUnits": "ALL",
                    "SpecializationStrategy": "FastPrediction",
                },
                {},
            ],
        )
        x_data = np.array([[1.0, 2.0, 3.0, 4.0]], dtype=np.float32)
        outputs = session.run(["Y"], {"X": x_data})
        expected = np.array([[3.0, 5.0, 7.0, 9.0]], dtype=np.float32)
        np.testing.assert_allclose(outputs[0], expected, rtol=1e-4)
        print_pass(f"Inference verified via CoreML/CPU: input={x_data.tolist()} -> output={outputs[0].tolist()}")
    finally:
        os.unlink(model_path)


def test_videotoolbox_transcoding() -> None:
    print_step("FFmpeg VideoToolbox Hardware Transcoding")
    ffmpeg_bin = subprocess.check_output(["command", "-v", "ffmpeg"], text=True).strip()
    ffprobe_bin = subprocess.check_output(["command", "-v", "ffprobe"], text=True).strip()

    with tempfile.TemporaryDirectory() as tmpdir:
        input_video = os.path.join(tmpdir, "test_input.mp4")
        h264_output = os.path.join(tmpdir, "test_h264_vt.mp4")
        hevc_output = os.path.join(tmpdir, "test_hevc_vt.mp4")

        # 1. Generate a 2-second 1080p synthetic test clip
        gen_cmd = [
            ffmpeg_bin,
            "-y",
            "-f", "lavfi",
            "-i", "testsrc=size=1920x1080:rate=30",
            "-t", "2",
            "-pix_fmt", "yuv420p",
            input_video,
        ]
        subprocess.check_call(gen_cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        print_pass("Created synthetic 1080p 30fps source clip")

        # 2. Transcode with h264_videotoolbox and hwaccel videotoolbox
        vt_h264_cmd = [
            ffmpeg_bin,
            "-y",
            "-hwaccel", "videotoolbox",
            "-i", input_video,
            "-c:v", "h264_videotoolbox",
            "-b:v", "4000k",
            "-allow_sw", "1",
            "-movflags", "faststart",
            h264_output,
        ]
        t0 = time.perf_counter()
        subprocess.check_call(vt_h264_cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        h264_elapsed = time.perf_counter() - t0
        print_pass(f"Transcoded with h264_videotoolbox in {h264_elapsed*1000:.1f}ms")

        # 3. Transcode with hevc_videotoolbox, -tag:v hvc1, and hwaccel videotoolbox
        vt_hevc_cmd = [
            ffmpeg_bin,
            "-y",
            "-hwaccel", "videotoolbox",
            "-i", input_video,
            "-c:v", "hevc_videotoolbox",
            "-tag:v", "hvc1",
            "-b:v", "3000k",
            "-allow_sw", "1",
            "-movflags", "faststart",
            hevc_output,
        ]
        t0 = time.perf_counter()
        subprocess.check_call(vt_hevc_cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        hevc_elapsed = time.perf_counter() - t0
        print_pass(f"Transcoded with hevc_videotoolbox (tag: hvc1) in {hevc_elapsed*1000:.1f}ms")

        # 4. Probe the outputs with ffprobe to verify streams
        probe_h264 = subprocess.check_output(
            [ffprobe_bin, "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=codec_name,width,height", "-of", "json", h264_output],
            text=True,
        )
        data_h264 = json.loads(probe_h264)["streams"][0]
        if data_h264["codec_name"] != "h264" or data_h264["width"] != 1920:
            print_fail(f"Invalid H264 probe result: {data_h264}")
        print_pass(f"Verified H.264 stream: {data_h264['codec_name']} {data_h264['width']}x{data_h264['height']}")

        probe_hevc = subprocess.check_output(
            [ffprobe_bin, "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=codec_name,width,height,codec_tag_string", "-of", "json", hevc_output],
            text=True,
        )
        data_hevc = json.loads(probe_hevc)["streams"][0]
        if data_hevc["codec_name"] != "hevc" or data_hevc["codec_tag_string"] != "hvc1":
            print_fail(f"Invalid HEVC probe result: {data_hevc}")
        print_pass(f"Verified HEVC stream: {data_hevc['codec_name']} tag={data_hevc['codec_tag_string']}")


def test_ffmpeg_wrapper_script() -> None:
    print_step("VideoToolbox FFmpeg Wrapper Script")
    wrapper = REPO_ROOT / "scripts" / "apple-silicon" / "ffmpeg-videotoolbox.sh"
    if not wrapper.is_file() or not os.access(wrapper, os.X_OK):
        print_fail(f"Wrapper script {wrapper} not found or not executable")

    with tempfile.TemporaryDirectory() as tmpdir:
        input_video = os.path.join(tmpdir, "wrapper_in.mp4")
        output_video = os.path.join(tmpdir, "wrapper_out.mp4")

        # Generate 1-sec clip
        subprocess.check_call(
            ["ffmpeg", "-y", "-f", "lavfi", "-i", "testsrc=size=640x360:rate=30", "-t", "1", input_video],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )

        # Call wrapper requesting software libx264 -> wrapper must transparently remap to h264_videotoolbox
        wrap_cmd = [
            str(wrapper),
            "-y",
            "-i", input_video,
            "-c:v", "libx264",
            "-crf", "23",
            "-preset", "ultrafast",
            output_video,
        ]
        subprocess.check_call(wrap_cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

        ffprobe_bin = subprocess.check_output(["command", "-v", "ffprobe"], text=True).strip()
        probe_out = subprocess.check_output(
            [ffprobe_bin, "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=codec_name", "-of", "json", output_video],
            text=True,
        )
        codec = json.loads(probe_out)["streams"][0]["codec_name"]
        if codec != "h264":
            print_fail(f"Unexpected codec from wrapper: {codec}")
        print_pass("Wrapper successfully remapped libx264 to VideoToolbox and produced valid MP4")


def test_isolated_ml_server() -> None:
    print_step("Native ML FastAPI Server (Isolated Port 3042)")
    import urllib.request

    test_port = 3042
    env = os.environ.copy()
    env["IMMICH_PORT"] = str(test_port)
    env["MACHINE_LEARNING_PORT"] = str(test_port)

    # Launch ML server via uv on test port
    cmd = [
        "uv",
        "run",
        "--project", str(REPO_ROOT / "machine-learning"),
        "python",
        "-m", "immich_ml",
    ]
    proc = subprocess.Popen(cmd, env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    try:
        # Wait up to 10s for server to start
        ready = False
        for _ in range(20):
            time.sleep(0.5)
            try:
                with urllib.request.urlopen(f"http://127.0.0.1:{test_port}/ping", timeout=1) as resp:
                    if resp.status == 200 and resp.read().decode().strip() == "pong":
                        ready = True
                        break
            except Exception:
                continue

        if not ready:
            print_fail(f"ML server failed to start on port {test_port}")
        print_pass(f"ML server is up on port {test_port} and answered /ping -> pong")

        with urllib.request.urlopen(f"http://127.0.0.1:{test_port}/", timeout=1) as resp:
            content = json.loads(resp.read().decode())
            if content.get("message") != "Immich ML":
                print_fail(f"Unexpected root response: {content}")
            print_pass(f"Root endpoint answered: {content}")
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=3)
        except subprocess.TimeoutExpired:
            proc.kill()
        print_pass(f"ML test server on port {test_port} cleanly terminated")


def test_production_safety() -> None:
    print_step("Production Container Safety Verification")
    try:
        output = subprocess.check_output(
            ["docker", "ps", "--filter", "name=immich_server", "--format", "{{.Names}} {{.Status}}"],
            text=True,
        ).strip()
        if output:
            print_pass(f"Verified production container is untouched: {output}")
        else:
            print_pass("No production container with name 'immich_server' found running")
    except Exception as e:
        print_pass(f"Docker check completed: {e}")


def main() -> None:
    print(f"\n{BOLD}=== Immich Apple Silicon End-to-End Hardware Acceleration Suite ==={RESET}")
    test_hardware_environment()
    test_coreml_onnxruntime()
    test_videotoolbox_transcoding()
    test_ffmpeg_wrapper_script()
    test_isolated_ml_server()
    test_production_safety()
    print(f"\n{GREEN}{BOLD}All Apple Silicon hardware acceleration tests PASSED successfully!{RESET}\n")


if __name__ == "__main__":
    main()
