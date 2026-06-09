from __future__ import annotations

from typing import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from .config import get_settings
from .storage import AudioMaster, Base

_engine = None
_SessionLocal = None


def _sqlite_connect_args(database_url: str) -> dict:
    if database_url.startswith("sqlite"):
        return {"check_same_thread": False}
    return {}


def get_engine():
    global _engine, _SessionLocal
    if _engine is None:
        settings = get_settings()
        _engine = create_engine(
            settings.database_url,
            connect_args=_sqlite_connect_args(settings.database_url),
        )
        _SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=_engine)
    return _engine


def get_session_factory():
    get_engine()
    return _SessionLocal


def init_db() -> None:
    engine = get_engine()
    Base.metadata.create_all(bind=engine)


def get_db() -> Generator[Session, None, None]:
    session_factory = get_session_factory()
    db = session_factory()
    try:
        yield db
    finally:
        db.close()


def seed_audio_master(
    session: Session,
    audio_guid: str,
    file_name: str,
    approved_text: str,
) -> AudioMaster:
    """Create or update an AudioMaster record."""
    existing = session.get(AudioMaster, audio_guid)
    if existing:
        existing.file_name = file_name
        existing.approved_text = approved_text
        session.commit()
        session.refresh(existing)
        return existing

    record = AudioMaster(
        audio_guid=audio_guid,
        file_name=file_name,
        approved_text=approved_text,
    )
    session.add(record)
    session.commit()
    session.refresh(record)
    return record


def reset_engine() -> None:
    """Reset cached engine — useful for tests."""
    global _engine, _SessionLocal
    if _engine is not None:
        _engine.dispose()
    _engine = None
    _SessionLocal = None
    get_settings.cache_clear()
