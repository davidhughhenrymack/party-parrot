from __future__ import annotations

import subprocess
import sys
import threading
import time
import webbrowser

import requests


DEFAULT_SERVICE_URL = "http://127.0.0.1:4041"


def _open_venue_service_when_ready(base_url: str) -> None:
    """Wait for the venue editor HTTP service, then open it once."""

    def runner() -> None:
        for _ in range(120):
            try:
                response = requests.get(f"{base_url}/api/health", timeout=0.5)
                if response.ok:
                    webbrowser.open(base_url)
                    return
            except Exception:
                pass
            time.sleep(0.25)

    threading.Thread(target=runner, daemon=True).start()


def service_is_healthy(base_url: str) -> bool:
    try:
        response = requests.get(f"{base_url}/api/health", timeout=1)
        return response.ok
    except Exception:
        return False


def main() -> int:
    runtime_args = list(sys.argv[1:])
    user_disabled_web = "--no-web" in runtime_args
    if "--no-web" not in runtime_args:
        runtime_args.insert(0, "--no-web")

    service_url = DEFAULT_SERVICE_URL
    service_process = None

    if not service_is_healthy(service_url):
        service_process = subprocess.Popen(
            [
                sys.executable,
                "-m",
                "parrot_cloud.main",
                "--port",
                "4041",
            ]
        )
        for _ in range(30):
            if service_is_healthy(service_url):
                break
            time.sleep(0.5)
        else:
            raise RuntimeError("Venue editor service failed to start")

    runtime_command = [
        sys.executable,
        "-m",
        "parrot.main",
        "--venue-service-url",
        service_url,
        *runtime_args,
    ]

    if not user_disabled_web:
        _open_venue_service_when_ready(service_url)

    try:
        completed = subprocess.call(runtime_command)
        return int(completed)
    finally:
        if service_process is not None:
            service_process.terminate()
            try:
                service_process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                service_process.kill()


if __name__ == "__main__":
    raise SystemExit(main())
