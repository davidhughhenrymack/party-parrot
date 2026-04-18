from __future__ import annotations

import os
from pathlib import Path

from sqlalchemy import create_engine, event
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker


def get_repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def get_default_database_path() -> Path:
    return get_repo_root() / "parrot_cloud.db"


def _resolve_db_path() -> Path:
    configured_path = os.environ.get("PARROT_CLOUD_DB_PATH") or os.environ.get(
        "PARROT_VENUE_DB_PATH"
    )
    if configured_path:
        return Path(configured_path).expanduser().resolve()
    return get_default_database_path()


def get_database_url() -> str:
    return f"sqlite:///{_resolve_db_path()}"


class Base(DeclarativeBase):
    pass


_engine = None
_session_factory: sessionmaker[Session] | None = None


def _ensure_writable(db_path: Path) -> None:
    """Guard against the long-running server entering a permanent 'readonly
    database' state.

    This has bitten us when git operations replace the checked-in
    ``parrot_cloud.db`` while the server holds it open, or when the file was
    dropped on disk with read-only perms. Fail loudly instead of limping on
    with mysterious 500s out of SQLAlchemy.
    """
    if not db_path.exists():
        return
    if not os.access(db_path, os.W_OK):
        try:
            db_path.chmod(0o644)
        except OSError as exc:
            raise RuntimeError(
                f"parrot_cloud database is not writable: {db_path} ({exc})"
            ) from exc
    parent = db_path.parent
    if not os.access(parent, os.W_OK):
        raise RuntimeError(
            f"parrot_cloud database directory is not writable: {parent}"
        )


def _configure_sqlite_connection(dbapi_connection, _connection_record) -> None:
    """Per-connection pragmas applied when SQLAlchemy opens a raw connection.

    * WAL journaling survives the server having the db file open while another
      process rewrites it (git checkout, editor save, etc.) much better than
      the default rollback journal, which is what produced the "attempt to
      write a readonly database" 500s we were seeing from PATCH
      /api/control-state.
    * ``busy_timeout`` lets transient locks resolve instead of immediately
      erroring.
    * ``foreign_keys`` enforces the relationships defined in models.py.
    """
    cursor = dbapi_connection.cursor()
    try:
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA synchronous=NORMAL")
        cursor.execute("PRAGMA busy_timeout=5000")
        cursor.execute("PRAGMA foreign_keys=ON")
    finally:
        cursor.close()


def get_engine():
    global _engine
    if _engine is None:
        db_path = _resolve_db_path()
        _ensure_writable(db_path)
        _engine = create_engine(
            f"sqlite:///{db_path}",
            connect_args={"check_same_thread": False, "timeout": 5.0},
            future=True,
        )
        event.listen(_engine, "connect", _configure_sqlite_connection)
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
