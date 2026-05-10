import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.exceptions import TelegramNetworkError

from config import BOT_TOKEN, validate_bot_config
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
