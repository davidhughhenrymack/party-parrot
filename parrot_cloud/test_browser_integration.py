from __future__ import annotations

import os
from pathlib import Path
import shutil
import socket
import subprocess
import sys
import time

import pytest
import requests
from playwright.sync_api import sync_playwright


def _find_free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def _find_browser_executable() -> str | None:
    candidates = [
        os.environ.get("PLAYWRIGHT_BROWSER_EXECUTABLE"),
        shutil.which("google-chrome"),
        shutil.which("chromium"),
        shutil.which("chromium-browser"),
        "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
        "/Applications/Chromium.app/Contents/MacOS/Chromium",
        "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge",
    ]

    for candidate in candidates:
        if candidate and Path(candidate).exists():
            return candidate
    return None


@pytest.fixture
def parrot_cloud_server(tmp_path):
    browser_path = _find_browser_executable()
    if browser_path is None:
        pytest.skip("No Chrome/Chromium browser executable available for Playwright")

    port = _find_free_port()
    db_path = tmp_path / "browser_integration.sqlite3"
    log_path = tmp_path / "parrot_cloud_server.log"

    env = os.environ.copy()
    env["PARROT_CLOUD_DB_PATH"] = str(db_path)

    with log_path.open("w") as log_file:
        process = subprocess.Popen(
            [
                sys.executable,
                "-m",
                "parrot_cloud.main",
                "--host",
                "127.0.0.1",
                "--port",
                str(port),
            ],
            stdout=log_file,
            stderr=subprocess.STDOUT,
            env=env,
        )

    base_url = f"http://127.0.0.1:{port}"
    deadline = time.time() + 60
    while time.time() < deadline:
        try:
            response = requests.get(f"{base_url}/api/health", timeout=1)
            if response.ok:
                yield {
                    "base_url": base_url,
                    "browser_path": browser_path,
                    "log_path": log_path,
                }
                break
        except Exception:
            time.sleep(0.25)
    else:
        process.terminate()
        process.wait(timeout=5)
        raise AssertionError(log_path.read_text())

    process.terminate()
    try:
        process.wait(timeout=5)
    except subprocess.TimeoutExpired:
        process.kill()


def test_headless_browser_basic_editor_flow(parrot_cloud_server):
    base_url = parrot_cloud_server["base_url"]
    browser_path = parrot_cloud_server["browser_path"]

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(
            headless=True,
            executable_path=browser_path,
            args=["--disable-gpu", "--no-sandbox"],
        )
        page = browser.new_page()
        page.goto(base_url, wait_until="networkidle")
        page.wait_for_selector("#enter-editor-button")
        page.goto(f"{base_url}/venues?test_mode=1", wait_until="networkidle")
        page.wait_for_selector("#add-venue-tile")
        assert "Mountain Lotus Demo" in page.locator("#venue-grid").text_content()

        page.once("dialog", lambda dialog: dialog.accept("Browser Test Venue"))
        page.click("#add-venue-tile")
        page.wait_for_url(lambda url: "/venues/" in url and "test_mode=1" in url)
        page.wait_for_function("document.body.dataset.appReady === 'true'")

        page.wait_for_selector("#venue-name-input")
        assert page.input_value("#venue-name-input") == "Browser Test Venue"
        assert "No lights yet" in page.locator("#fixture-list").text_content()
        assert page.get_attribute("#floor-width", "step") == "10"
        assert page.get_attribute("#floor-height", "step") == "10"

        venue_id = page.url.rsplit("/", 1)[-1].split("?", 1)[0]

        page.fill("#floor-width", "40")
        page.fill("#floor-height", "20")
        page.wait_for_function(
            f"""async () => {{
                const response = await fetch('/api/venues/{venue_id}');
                const data = await response.json();
                return Math.abs(data.floor_width - 12.192) < 0.02 && Math.abs(data.floor_depth - 6.096) < 0.02;
            }}"""
        )

        page.click("#open-add-light-modal-button")
        page.wait_for_selector("#fixture-type-select")
        assert page.locator(".modal-header button", has_text="Close").count() == 0
        page.select_option("#fixture-type-select", "par_rgb")
        page.fill("#fixture-address-input", "321")
        page.select_option("#fixture-universe-input", "art1")
        page.click("#add-fixture-button")
        page.wait_for_function(
            "() => document.querySelector('#fixture-list').textContent.includes('art1:321')"
        )

        fixture_data = page.evaluate(
            f"""async () => {{
                const response = await fetch('/api/venues/{venue_id}');
                const data = await response.json();
                return data.fixtures.map((fixture) => ({{
                    address: fixture.address,
                    universe: fixture.universe,
                }}));
            }}"""
        )
        assert {"address": 321, "universe": "art1"} in fixture_data

        page.locator("#fixture-list button", has_text="art1:321").click()
        page.get_by_role("button", name="art1:321", exact=True).click()
        page.fill("#selected-fixture-address-input", "322")
        page.click("#save-selected-fixture-addressing-button")
        page.wait_for_function(
            f"""async () => {{
                const response = await fetch('/api/venues/{venue_id}');
                const data = await response.json();
                return data.fixtures.some((fixture) => fixture.address === 322 && fixture.universe === 'art1');
            }}"""
        )

        browser.close()


def test_headless_browser_real_editor_loads_without_runtime_errors(parrot_cloud_server):
    base_url = parrot_cloud_server["base_url"]
    browser_path = parrot_cloud_server["browser_path"]
    page_errors: list[str] = []
    console_errors: list[str] = []

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(
            headless=True,
            executable_path=browser_path,
            args=["--disable-gpu", "--no-sandbox"],
        )
        page = browser.new_page()
        page.on("pageerror", lambda error: page_errors.append(str(error)))
        page.on(
            "console",
            lambda message: (
                console_errors.append(message.text)
                if message.type == "error"
                else None
            ),
        )

        bootstrap = requests.get(f"{base_url}/api/bootstrap", timeout=5).json()
        venue_id = bootstrap["active_venue"]["summary"]["id"]

        page.goto(f"{base_url}/venues/{venue_id}", wait_until="networkidle")
        page.wait_for_function("document.body.dataset.appReady === 'true'")
        page.wait_for_selector("#venue-name-input")
        page.wait_for_selector("#viewport canvas")

        assert page_errors == []
        assert console_errors == []
        assert page.locator("#viewport canvas").is_visible()

        browser.close()
