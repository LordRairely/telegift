import json
from pathlib import Path
from typing import Any, Optional

from services.anonymizer import anonymize_dialog_text


def parse_dialog_file(file_path: str, sender_user: Any = None) -> str:
    suffix = Path(file_path).suffix.lower()

    if suffix == ".json":
        return parse_telegram_json(file_path, sender_user=sender_user)

    if suffix == ".txt":
        return parse_text_file(file_path, sender_user=sender_user)

    raise ValueError("Поддерживаются только файлы JSON и TXT.")


def parse_telegram_json(file_path: str, sender_user: Any = None) -> str:
    """
    Парсит JSON файл экспорта Telegram и возвращает текст переписки.
    Мы берем только текстовые сообщения.
    """
    with open(file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    messages = data.get("messages", [])
    sender_identity = _get_sender_identity(sender_user)
    author_aliases = _build_telegram_author_aliases(data, messages, sender_identity)
    sensitive_values = _collect_sensitive_names(data, messages, sender_identity)
    dialog_text = ""

    for msg in messages:
        if msg.get("type") == "message" and "text" in msg:
            text = msg["text"]
            # В Telegram text может быть массивом строк и объектов (ссылок, форматирования)
            if isinstance(text, list):
                text_parts = []
                for part in text:
                    if isinstance(part, str):
                        text_parts.append(part)
                    elif isinstance(part, dict) and "text" in part:
                        text_parts.append(part["text"])
                text = "".join(text_parts)

            if text.strip():
                author = msg.get("from", "Unknown")
                dialog_text += f"{author}: {text}\n"

    return anonymize_dialog_text(
        dialog_text,
        author_aliases=author_aliases,
        sensitive_values=sensitive_values,
    )


def parse_text_file(file_path: str, sender_user: Any = None) -> str:
    """
    Читает обычный TXT-файл с перепиской и анонимизирует его.
    """
    sender_identity = _get_sender_identity(sender_user)

    with open(file_path, encoding="utf-8") as f:
        dialog_text = f.read()

    author_aliases = _build_text_author_aliases(dialog_text, sender_identity)
    sensitive_values = _collect_text_sensitive_names(dialog_text, sender_identity)

    return anonymize_dialog_text(
        dialog_text,
        author_aliases=author_aliases,
        sensitive_values=sensitive_values,
    )


def _build_telegram_author_aliases(
    data: dict[str, Any],
    messages: list[dict[str, Any]],
    sender_identity: dict[str, Any],
) -> dict[str, str]:
    own_names = _get_telegram_owner_names(data)
    own_user_id = _get_telegram_owner_user_id(data)
    authors = _get_message_authors(messages)
    gift_giver_author = _find_sender_author(messages, sender_identity)

    aliases: dict[str, str] = {}
    gift_giver_found = False
    gift_recipient_found = False

    for msg in messages:
        author = msg.get("from")
        if not author or author in aliases:
            continue

        from_id = str(msg.get("from_id", ""))
        is_sender = author == gift_giver_author
        is_owner = author in own_names or (own_user_id and from_id == f"user{own_user_id}")

        if is_sender or (not gift_giver_author and is_owner):
            aliases[author] = "Подаркодаритель"
            gift_giver_found = True
        elif not gift_recipient_found:
            aliases[author] = "Подаркополучатель"
            gift_recipient_found = True
        else:
            aliases[author] = "Другой участник"

    if not gift_giver_found and authors:
        aliases[authors[0]] = "Подаркодаритель"

    if not gift_recipient_found:
        for author in authors:
            if aliases.get(author) != "Подаркодаритель":
                aliases[author] = "Подаркополучатель"
                break

    return aliases


def _build_text_author_aliases(dialog_text: str, sender_identity: dict[str, Any]) -> dict[str, str]:
    authors = _get_text_authors(dialog_text)
    sender_author = _find_sender_text_author(authors, sender_identity)

    aliases: dict[str, str] = {}
    gift_recipient_found = False

    for author in authors:
        if author == sender_author:
            aliases[author] = "Подаркодаритель"
        elif not gift_recipient_found:
            aliases[author] = "Подаркополучатель"
            gift_recipient_found = True
        else:
            aliases[author] = "Другой участник"

    if not sender_author and authors:
        aliases[authors[0]] = "Подаркодаритель"
        for author in authors[1:]:
            aliases[author] = "Подаркополучатель"
            break

    return aliases


def _get_sender_identity(sender_user: Any) -> dict[str, Any]:
    if not sender_user:
        return {"id": "", "names": set()}

    sender_id = str(_get_attr_or_item(sender_user, "id") or "").strip()
    first_name = str(_get_attr_or_item(sender_user, "first_name") or "").strip()
    last_name = str(_get_attr_or_item(sender_user, "last_name") or "").strip()
    username = str(_get_attr_or_item(sender_user, "username") or "").strip()
    full_name = " ".join(name for name in (first_name, last_name) if name).strip()

    names = {first_name, last_name, username, full_name}
    return {"id": sender_id, "names": {name for name in names if name}}


def _get_attr_or_item(value: Any, key: str) -> Any:
    if isinstance(value, dict):
        return value.get(key)

    return getattr(value, key, None)


def _find_sender_author(messages: list[dict[str, Any]], sender_identity: dict[str, Any]) -> Optional[str]:
    sender_id = sender_identity.get("id")
    sender_names = sender_identity.get("names") or set()

    if sender_id:
        for msg in messages:
            author = msg.get("from")
            from_id = str(msg.get("from_id", ""))
            if author and from_id == f"user{sender_id}":
                return author

    for msg in messages:
        author = msg.get("from")
        if author and author in sender_names:
            return author

    return None


def _find_sender_text_author(authors: list[str], sender_identity: dict[str, Any]) -> Optional[str]:
    sender_names = sender_identity.get("names") or set()

    for author in authors:
        author_parts = {part for part in author.split() if len(part) > 2}
        if author in sender_names or author_parts.intersection(sender_names):
            return author

    return None


def _get_telegram_owner_names(data: dict[str, Any]) -> set[str]:
    personal_info = data.get("personal_information") or {}
    names = {
        str(personal_info.get("first_name") or "").strip(),
        str(personal_info.get("last_name") or "").strip(),
        str(personal_info.get("username") or "").strip(),
    }

    full_name = " ".join(name for name in (personal_info.get("first_name"), personal_info.get("last_name")) if name)
    names.add(full_name.strip())

    return {name for name in names if name}


def _get_telegram_owner_user_id(data: dict[str, Any]) -> str:
    personal_info = data.get("personal_information") or {}
    return str(personal_info.get("user_id") or "").strip()


def _get_message_authors(messages: list[dict[str, Any]]) -> list[str]:
    authors = []

    for msg in messages:
        author = msg.get("from")
        if author and author not in authors:
            authors.append(author)

    return authors


def _get_text_authors(dialog_text: str) -> list[str]:
    authors = []

    for line in dialog_text.splitlines():
        if ":" not in line:
            continue

        author, _ = line.split(":", 1)
        author = author.strip()

        if 1 < len(author) <= 80 and author not in authors:
            authors.append(author)

    return authors


def _collect_sensitive_names(
    data: dict[str, Any],
    messages: list[dict[str, Any]],
    sender_identity: dict[str, Any],
) -> list[str]:
    values = list(_get_telegram_owner_names(data))
    values.extend(sender_identity.get("names") or [])

    for author in _get_message_authors(messages):
        values.append(author)
        values.extend(part for part in author.split() if len(part) > 2)

    return values


def _collect_text_sensitive_names(dialog_text: str, sender_identity: dict[str, Any]) -> list[str]:
    values = list(sender_identity.get("names") or [])

    for author in _get_text_authors(dialog_text):
        values.append(author)
        values.extend(part for part in author.split() if len(part) > 2)

    return values
