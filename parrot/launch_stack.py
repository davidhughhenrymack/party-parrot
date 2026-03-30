from __future__ import annotations

import subprocess
import sys
import time

import requests


DEFAULT_SERVICE_URL = "http://127.0.0.1:4041"


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
