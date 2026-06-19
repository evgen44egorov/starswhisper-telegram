from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from bot.database.models import Base

_engine: AsyncEngine | None = None
_session_factory: async_sessionmaker[AsyncSession] | None = None


def configure_database(database_url: str) -> None:
    global _engine, _session_factory

    _engine = create_async_engine(database_url)
    _session_factory = async_sessionmaker(_engine, expire_on_commit=False)


async def init_database() -> None:
    if _engine is None:
        raise RuntimeError("База данных не настроена")

    async with _engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)


@asynccontextmanager
async def session_scope() -> AsyncIterator[AsyncSession]:
    if _session_factory is None:
        raise RuntimeError("База данных не настроена")

    async with _session_factory() as session:
        yield session


async def close_database() -> None:
    if _engine is not None:
        await _engine.dispose()

