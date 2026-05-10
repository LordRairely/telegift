from typing import Optional


def parse_start_source(message_text: Optional[str]) -> tuple[str, Optional[str]]:
    if not message_text:
        return "organic", None

    parts = message_text.split(maxsplit=1)
    if len(parts) < 2:
        return "organic", None

    payload = parts[1].strip()[:64]
    if not payload:
        return "organic", None

    if payload.startswith("ref_") or payload.startswith("tg_"):
        return "referral", payload

    return payload, None
