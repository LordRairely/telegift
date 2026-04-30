from aiogram.types import User
from sqlalchemy import func
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from models import TelegramUser


async def upsert_telegram_user(session: AsyncSession, user: User) -> int:
    statement = (
        insert(TelegramUser)
        .values(
            telegram_id=user.id,
            username=user.username,
            first_name=user.first_name,
            last_name=user.last_name,
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
