from __future__ import annotations

import os
from pathlib import Path
import shutil
import subprocess

from alembic import command
from alembic.config import Config

from parrot_cloud.database import get_database_url, get_repo_root
from parrot_cloud.repository import VenueRepository


def get_alembic_config() -> Config:
    config = Config(str(get_repo_root() / "alembic.ini"))
    config.set_main_option("script_location", str(get_repo_root() / "parrot_cloud_alembic"))
    config.set_main_option("sqlalchemy.url", get_database_url())
    return config


def run_migrations() -> None:
    command.upgrade(get_alembic_config(), "head")


def get_frontend_dir() -> Path:
    return get_repo_root() / "parrot_cloud" / "frontend"


def get_static_dir() -> Path:
    return get_repo_root() / "parrot_cloud" / "static"


def build_frontend(force: bool = False) -> None:
    if os.environ.get("PARROT_SKIP_FRONTEND_BUILD") == "1":
        return

    frontend_dir = get_frontend_dir()
    static_dir = get_static_dir()
    index_path = static_dir / "index.html"

    if not force and index_path.exists():
        latest_source_mtime = max(
            path.stat().st_mtime
            for path in frontend_dir.rglob("*")
            if path.is_file()
        )
        if index_path.stat().st_mtime >= latest_source_mtime:
            return

    npm_path = shutil.which("npm")
    if npm_path is None:
        raise RuntimeError("npm is required to build the Parrot Cloud React frontend")

    node_modules_dir = frontend_dir / "node_modules"
    if not node_modules_dir.exists():
        install_command = ["npm", "ci"] if (frontend_dir / "package-lock.json").exists() else ["npm", "install"]
        subprocess.run(install_command, cwd=frontend_dir, check=True)
    subprocess.run(["npm", "run", "build"], cwd=frontend_dir, check=True)


def seed_database() -> None:
    VenueRepository().ensure_seed_data()


def initialize_database() -> None:
    run_migrations()
    seed_database()


def database_exists() -> bool:
    db_path = Path(get_database_url().removeprefix("sqlite:///"))
    return db_path.exists()
