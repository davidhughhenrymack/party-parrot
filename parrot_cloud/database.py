from __future__ import annotations

import os
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker


def get_repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def get_default_database_path() -> Path:
    return get_repo_root() / "parrot_cloud.db"


def get_database_url() -> str:
    configured_path = os.environ.get("PARROT_CLOUD_DB_PATH") or os.environ.get(
        "PARROT_VENUE_DB_PATH"
    )
    if configured_path:
        db_path = Path(configured_path).expanduser().resolve()
    else:
        db_path = get_default_database_path()
    return f"sqlite:///{db_path}"


class Base(DeclarativeBase):
    pass


_engine = None
_session_factory: sessionmaker[Session] | None = None


def get_engine():
    global _engine
    if _engine is None:
        _engine = create_engine(
            get_database_url(),
            connect_args={"check_same_thread": False},
            future=True,
        )
    return _engine


def get_session_factory() -> sessionmaker[Session]:
    global _session_factory
    if _session_factory is None:
        _session_factory = sessionmaker(
            bind=get_engine(),
            expire_on_commit=False,
            future=True,
        )
    return _session_factory


def create_session() -> Session:
    return get_session_factory()()


def reset_database_state() -> None:
    global _engine, _session_factory
    if _engine is not None:
        _engine.dispose()
    _engine = None
    _session_factory = None
