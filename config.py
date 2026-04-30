import os

from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
YANDEX_API_KEY = os.getenv("YANDEX_API_KEY")
YANDEX_FOLDER_ID = os.getenv("YANDEX_FOLDER_ID")
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+asyncpg://telegift:telegift@localhost:5432/telegift",
)


def validate_bot_config() -> None:
    if not BOT_TOKEN:
        raise ValueError("BOT_TOKEN не найден в переменных окружения")
