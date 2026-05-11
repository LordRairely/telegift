from typing import Optional

from aiogram.types import User
from sqlalchemy import func, select, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from models import TelegramUser


async def upsert_telegram_user(
    session: AsyncSession,
    user: User,
    acquisition_source: str = "organic",
    referred_by_code: Optional[str] = None,
) -> int:
    statement = (
        insert(TelegramUser)
        .values(
            telegram_id=user.id,
            username=user.username,
            first_name=user.first_name,
            last_name=user.last_name,
            acquisition_source=acquisition_source,
            referral_code=f"tg_{user.id}",
            referred_by_code=referred_by_code,
        )
        .on_conflict_do_update(
            constraint="uq_telegram_users_telegram_id",
            set_={
                "username": user.username,
                "first_name": user.first_name,
                "last_name": user.last_name,
                "updated_at": func.now(),
            },
        )
        .returning(TelegramUser.id)
    )

    result = await session.execute(statement)
    await session.commit()
    return result.scalar_one()


async def accept_terms(
    session: AsyncSession,
    user: User,
    acquisition_source: str = "organic",
    referred_by_code: Optional[str] = None,
) -> int:
    user_id = await upsert_telegram_user(
        session,
        user,
        acquisition_source=acquisition_source,
        referred_by_code=referred_by_code,
    )
    statement = (
        update(TelegramUser)
        .where(TelegramUser.id == user_id)
        .values(terms_accepted_at=func.now(), updated_at=func.now())
    )
    await session.execute(statement)
    await session.commit()
    return user_id


async def has_accepted_terms(session: AsyncSession, telegram_id: int) -> bool:
    statement = select(TelegramUser.terms_accepted_at).where(TelegramUser.telegram_id == telegram_id)
    result = await session.execute(statement)
    return result.scalar_one_or_none() is not None
