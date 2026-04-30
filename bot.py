import asyncio
import logging

from aiogram import Bot, Dispatcher

from config import BOT_TOKEN, validate_bot_config
from database import close_database, wait_for_database
from handlers import routers

logging.basicConfig(level=logging.INFO)


async def main():
    validate_bot_config()
    await wait_for_database()

    bot = Bot(token=BOT_TOKEN)
    dp = Dispatcher()

    try:
        # Регистрация хэндлеров
        for router in routers:
            dp.include_router(router)

        await dp.start_polling(bot)
    finally:
        await close_database()

if __name__ == "__main__":
    asyncio.run(main())
