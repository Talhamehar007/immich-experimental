import os
import signal
import subprocess
import sys
from ipaddress import ip_address
from pathlib import Path

from .config import log, non_prefixed_settings, settings

if source_ref := os.getenv("IMMICH_SOURCE_REF"):
    log.info(f"Initializing Immich ML [{source_ref}]")
else:
    log.info("Initializing Immich ML")

module_dir = Path(__file__).parent

# on i915, Intel's runtime submits every allocation in the process with each run it gives OpenVINO's GPU plugin
if any(driver.resolve().name == "i915" for driver in Path("/sys/class/drm").glob("renderD*/device/driver")):
    os.environ.setdefault("NEOReadDebugKeys", "1")
    os.environ.setdefault("EnableDirectSubmission", "0")


def is_ipv6(host: str) -> bool:
    try:
        return ip_address(host).version == 6
    except ValueError:
        return False


bind_host = non_prefixed_settings.immich_host
if is_ipv6(bind_host):
    bind_host = f"[{bind_host}]"
bind_address = f"{bind_host}:{non_prefixed_settings.immich_port}"

if sys.platform == "darwin":
    # On macOS, UNIX fork() without exec() invalidates Mach bootstrap ports to Apple Metal (MTLCompilerService)
    # and CoreML MPSKernelDAG. Run uvicorn directly in-process so Metal / Neural Engine kernels compile cleanly.
    import asyncio
    import uvicorn
    from .config import CustomUvicornServer

    clean_host = bind_host.strip("[]")
    config = uvicorn.Config(
        "immich_ml.main:app",
        host=clean_host,
        port=non_prefixed_settings.immich_port,
        timeout_keep_alive=settings.http_keepalive_timeout_s,
        log_config=None,
    )
    server = CustomUvicornServer(config=config)
    asyncio.run(server.serve())
    exit(0)

try:
    with subprocess.Popen(
        [
            "python",
            "-m",
            "gunicorn",
            "immich_ml.main:app",
            "-k",
            "immich_ml.config.CustomUvicornWorker",
            "-c",
            module_dir / "gunicorn_conf.py",
            "-b",
            bind_address,
            "-w",
            str(settings.workers),
            "-t",
            str(settings.worker_timeout),
            "--keep-alive",
            str(settings.http_keepalive_timeout_s),
            "--graceful-timeout",
            "10",
            "--no-control-socket",
        ],
    ) as cmd:
        cmd.wait()
except KeyboardInterrupt:
    cmd.send_signal(signal.SIGINT)
exit(cmd.returncode)
