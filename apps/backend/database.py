from collections.abc import AsyncIterator
from functools import lru_cache
from pathlib import Path

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from apps.backend.config import Settings, get_settings


class Base(DeclarativeBase):
    pass


def build_sqlite_url(db_path: Path) -> str:
    resolved_path = db_path.expanduser()
    if not resolved_path.is_absolute():
        resolved_path = Path.cwd() / resolved_path

    resolved_path.parent.mkdir(parents=True, exist_ok=True)
    return f"sqlite+aiosqlite:///{resolved_path.as_posix()}"


@lru_cache
def get_engine(database_url: str) -> AsyncEngine:
    return create_async_engine(database_url, future=True)


@lru_cache
def get_sessionmaker(database_url: str) -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(
        bind=get_engine(database_url),
        expire_on_commit=False,
        autoflush=False,
    )


async def get_db_session(settings: Settings = Depends(get_settings)) -> AsyncIterator[AsyncSession]:
    sessionmaker = get_sessionmaker(build_sqlite_url(settings.db_path))
    async with sessionmaker() as db_session:
        yield db_session


async def create_database(settings: Settings) -> None:
    import apps.backend.models  # noqa: F401

    engine = get_engine(build_sqlite_url(settings.db_path))
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)

