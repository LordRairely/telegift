from typing import Optional

from config import ADMIN_DIALOG_URL, ADMIN_USERNAME, UNLIMITED_UPLOAD_USERNAMES

MAX_UPLOAD_ATTEMPTS = 3


def is_unlimited_upload_user(username: Optional[str]) -> bool:
    if not username:
        return False

    return username.lower().lstrip("@") in UNLIMITED_UPLOAD_USERNAMES


def can_upload_more(username: Optional[str], upload_attempt_count: int) -> bool:
    return is_unlimited_upload_user(username) or upload_attempt_count < MAX_UPLOAD_ATTEMPTS


def build_upload_limit_message(upload_attempt_count: int) -> str:
    return (
        f"Лимит бесплатных анализов исчерпан: доступно {MAX_UPLOAD_ATTEMPTS}, "
        f"у тебя уже использовано {upload_attempt_count}. "
        f"Если нужно больше анализов, напиши администратору @{ADMIN_USERNAME}."
    )
