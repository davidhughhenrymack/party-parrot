from __future__ import annotations

import subprocess
import sys
import threading
import time
import webbrowser

import requests


DEFAULT_SERVICE_URL = "http://127.0.0.1:4041"
DEFAULT_WEB_PORT = 4040


def _web_port_and_no_web_flag(argv: list[str]) -> tuple[int, bool]:
    """Infer embedded web UI port and whether the user disabled it (mirrors parrot.main defaults)."""
    port = DEFAULT_WEB_PORT
    no_web = False
    i = 0
    while i < len(argv):
        item = argv[i]
        if item == "--no-web":
            no_web = True
        elif item == "--web-port" and i + 1 < len(argv):
            try:
                port = int(argv[i + 1])
            except ValueError:
                pass
            i += 1
        i += 1
    return port, no_web


def _open_web_client_when_ready(base_url: str) -> None:
    """Wait for the Party Parrot HTTP API, then open the static web UI once."""

    def runner() -> None:
        for _ in range(120):
            try:
                response = requests.get(f"{base_url}/api/config", timeout=0.5)
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
    runtime_args = sys.argv[1:]
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

    web_port, no_web = _web_port_and_no_web_flag(runtime_args)
    if not no_web:
        _open_web_client_when_ready(f"http://127.0.0.1:{web_port}")

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
