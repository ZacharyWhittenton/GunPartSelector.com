import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from site_api.db.database import Database, DatabaseNotConfiguredError


@pytest.mark.asyncio
async def test_unconfigured_database_rejects_sessions() -> None:
    database = Database(None)

    with pytest.raises(DatabaseNotConfiguredError):
        async with database.session():
            pass

    await database.dispose()


@pytest.mark.asyncio
async def test_configured_database_manages_session_without_eager_connection() -> None:
    database = Database("postgresql+psycopg://user:password@localhost/example")

    async with database.session() as session:
        assert isinstance(session, AsyncSession)

    await database.dispose()


@pytest.mark.asyncio
async def test_database_rolls_back_when_work_fails() -> None:
    database = Database("postgresql+psycopg://user:password@localhost/example")

    with pytest.raises(RuntimeError, match="work failed"):
        async with database.session():
            raise RuntimeError("work failed")

    await database.dispose()
