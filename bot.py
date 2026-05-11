import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.exceptions import TelegramNetworkError

from config import BOT_TOKEN, PRIVACY_POLICY_URL, validate_bot_config
from database import close_database, wait_for_database
from handlers import routers

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

POLLING_RETRY_DELAY_SECONDS = 5


async def main():
    validate_bot_config()
    await wait_for_database()

    bot = Bot(token=BOT_TOKEN)
    dp = Dispatcher()

    try:
        if PRIVACY_POLICY_URL:
            try:
                await bot.set_my_description(
                    description=(
                        "TeleGift анализирует экспорт переписки для подбора подарков. "
                        f"Политика обработки персональных данных: {PRIVACY_POLICY_URL}"
                    )
                )
            except Exception:
                logger.exception("Failed to set bot privacy policy description")

        # Регистрация хэндлеров
        for router in routers:
            dp.include_router(router)

        while True:
            try:
                await dp.start_polling(bot)
                break
            except TelegramNetworkError:
                logger.exception(
                    "Telegram network error while polling. Retrying in %s seconds",
                    POLLING_RETRY_DELAY_SECONDS,
                )
                await asyncio.sleep(POLLING_RETRY_DELAY_SECONDS)
            except OSError:
                logger.exception(
                    "Network error while polling. Retrying in %s seconds",
                    POLLING_RETRY_DELAY_SECONDS,
                )
                await asyncio.sleep(POLLING_RETRY_DELAY_SECONDS)
    finally:
        await bot.session.close()
        await close_database()


if __name__ == "__main__":
    asyncio.run(main())
