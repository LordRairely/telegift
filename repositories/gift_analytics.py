from typing import Optional

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from models import GiftAnalysis, GiftFeedback, TelegramUser
from services.feedback import parse_gift_ratings, strip_rating_fragments


async def create_gift_analysis(
    session: AsyncSession,
    telegram_user_id: int,
    file_format: str,
    file_size_bytes: Optional[int],
) -> int:
    analysis = GiftAnalysis(
        telegram_user_id=telegram_user_id,
        file_format=file_format,
        file_size_bytes=file_size_bytes,
        status="processing",
    )
    session.add(analysis)
    await session.commit()
    return analysis.id


async def count_gift_analyses_for_user(session: AsyncSession, telegram_id: int) -> int:
    statement = (
        select(func.count(GiftAnalysis.id))
        .join(TelegramUser, TelegramUser.id == GiftAnalysis.telegram_user_id)
        .where(TelegramUser.telegram_id == telegram_id)
    )
    result = await session.execute(statement)
    return result.scalar_one()


async def mark_gift_analysis_success(session: AsyncSession, analysis_id: int, telegram_user_id: int) -> None:
    await session.execute(
        update(GiftAnalysis)
        .where(GiftAnalysis.id == analysis_id)
        .values(status="success", error_type=None, finished_at=func.now(), updated_at=func.now())
    )
    await session.execute(
        update(TelegramUser)
        .where(TelegramUser.id == telegram_user_id)
        .values(
            analysis_count=TelegramUser.analysis_count + 1,
            last_analysis_at=func.now(),
            updated_at=func.now(),
        )
    )
    await session.commit()


async def mark_gift_analysis_failed(session: AsyncSession, analysis_id: int, error_type: str) -> None:
    await session.execute(
        update(GiftAnalysis)
        .where(GiftAnalysis.id == analysis_id)
        .values(status="failed", error_type=error_type[:128], finished_at=func.now(), updated_at=func.now())
    )
    await session.commit()


async def save_gift_feedback(session: AsyncSession, analysis_id: int, feedback_text: str) -> int:
    ratings = parse_gift_ratings(feedback_text)
    comment = strip_rating_fragments(feedback_text).strip() or None

    feedback_rows = [
        GiftFeedback(
            analysis_id=analysis_id,
            gift_index=rating.gift_index,
            rating=rating.rating,
            comment=comment,
        )
        for rating in ratings
    ]

    if not feedback_rows:
        feedback_rows = [GiftFeedback(analysis_id=analysis_id, comment=feedback_text.strip() or None)]

    session.add_all(feedback_rows)
    await session.commit()
    return len(feedback_rows)
