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
PRIVACY_POLICY_URL = os.getenv("PRIVACY_POLICY_URL")
ADMIN_USERNAME = os.getenv("ADMIN_USERNAME", "admin").lstrip("@")
ADMIN_DIALOG_URL = os.getenv("ADMIN_DIALOG_URL", f"https://t.me/{ADMIN_USERNAME}")
UNLIMITED_UPLOAD_USERNAMES = {
    username.strip().lower().lstrip("@")
    for username in os.getenv("UNLIMITED_UPLOAD_USERNAMES", ADMIN_USERNAME).split(",")
    if username.strip()
}


def validate_bot_config() -> None:
    if not BOT_TOKEN:
        raise ValueError("BOT_TOKEN не найден в переменных окружения")
