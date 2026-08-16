from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import NullPool


class DatabaseNotConfiguredError(RuntimeError):
    """Raised when a request needs PostgreSQL before a URL is configured."""


class Database:
    def __init__(self, database_url: str | None) -> None:
        self._engine: AsyncEngine | None = None
        self._sessions: async_sessionmaker[AsyncSession] | None = None

        if database_url is not None:
            self._engine = create_async_engine(
                database_url,
                pool_pre_ping=True,
                poolclass=NullPool,
            )
            self._sessions = async_sessionmaker(
                bind=self._engine,
                expire_on_commit=False,
            )

    @asynccontextmanager
    async def session(self) -> AsyncIterator[AsyncSession]:
        if self._sessions is None:
            raise DatabaseNotConfiguredError

        async with self._sessions() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise

    async def dispose(self) -> None:
        if self._engine is not None:
            await self._engine.dispose()
