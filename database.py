import asyncio
import logging
from collections.abc import AsyncIterator
from typing import Optional

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from config import DATABASE_URL

logger = logging.getLogger(__name__)


class Base(DeclarativeBase):
    pass


engine = create_async_engine(DATABASE_URL, pool_pre_ping=True)
async_session_factory = async_sessionmaker(engine, expire_on_commit=False)


async def get_session() -> AsyncIterator[AsyncSession]:
    async with async_session_factory() as session:
        yield session


async def wait_for_database(retries: int = 30, delay: float = 1.0) -> None:
    last_error: Optional[Exception] = None

    for attempt in range(1, retries + 1):
        try:
            async with engine.connect() as connection:
                await connection.execute(text("SELECT 1"))
            logger.info("Database connection is ready")
            return
        except Exception as error:
            last_error = error
            logger.warning(
                "Database is not ready yet (%s/%s): %s",
                attempt,
                retries,
                error,
            )
            await asyncio.sleep(delay)

    raise RuntimeError("Database did not become ready in time") from last_error


async def close_database() -> None:
    await engine.dispose()
