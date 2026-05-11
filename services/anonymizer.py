import re
from typing import Optional

EMAIL_PATTERN = re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.IGNORECASE)
URL_PATTERN = re.compile(r"\b(?:https?://|www\.)\S+\b", re.IGNORECASE)
TELEGRAM_USERNAME_PATTERN = re.compile(r"(?<!\w)@[A-Za-z0-9_]{5,32}\b")
IP_PATTERN = re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b")
IBAN_PATTERN = re.compile(r"\b[A-Z]{2}\d{2}[A-Z0-9]{11,30}\b", re.IGNORECASE)
SSN_PATTERN = re.compile(r"\b\d{3}-\d{2}-\d{4}\b")
SNILS_PATTERN = re.compile(r"\b\d{3}[- \t]?\d{3}[- \t]?\d{3}[- \t]?\d{2}\b")
PASSPORT_PATTERN = re.compile(r"\b\d{4}[ \t]?\d{6}\b")
CARD_PATTERN = re.compile(r"(?<!\d)(?:\d[ -]?){12,18}\d(?!\d)")
PHONE_PATTERN = re.compile(
    r"(?<!\w)(?:\+?\d{1,3}[ \t().-]*)?\(?\d{3}\)?[ \t().-]*"
    r"\d{3}[ \t().-]*\d{2}[ \t().-]*\d{2}(?!\w)"
)
LONG_NUMBER_PATTERN = re.compile(r"(?<!\d)\d{10,}(?!\d)")

DOB_PATTERN = re.compile(
    r"\b(?:дата[ \t]+рождения|день[ \t]+рождения|др|родил[а-я]*ся)\b"
    r"[ \t]*[:,-]?[ \t]*"
    r"(?:\d{1,2}[./ -]\d{1,2}[./ -]\d{2,4}|"
    r"\d{1,2}[ \t]+[а-яёa-z]+[ \t]+\d{2,4})",
    re.IGNORECASE,
)
SENSITIVE_FIELD_PATTERN = re.compile(
    r"\b(?:"
    r"паспорт|серия[ \t]+и[ \t]+номер|номер[ \t]+паспорта|"
    r"инн|снилс|омс|полис|номер[ \t]+карты|номер[ \t]+сч[её]та|"
    r"iban|cvv|cvc|код[ \t]+подтверждения|пароль"
    r")\b[ \t]*[:№#-]?[ \t]*[A-ZА-ЯЁ0-9][A-ZА-ЯЁ0-9 \t._/-]{2,40}",
    re.IGNORECASE,
)
ADDRESS_CONTEXT_PATTERN = re.compile(
    r"\b(?:адрес|прописка|доставка[ \t]+по[ \t]+адресу|куда[ \t]+(?:привезти|доставить))"
    r"\b[ \t]*[:,-]?[ \t]*[^\n]+",
    re.IGNORECASE,
)
STREET_PATTERN = re.compile(
    r"\b(?:ул\.?|улица|проспект|пр-кт|переулок|пер\.?|шоссе|"
    r"бульвар|бул\.?|набережная|наб\.?)[ \t]+[^,\n]+"
    r"(?:,[ \t]*(?:д\.?|дом|кв\.?|квартира|корп\.?|корпус|стр\.?)[ \t]*[\w/-]+)*",
    re.IGNORECASE,
)
BUILDING_PATTERN = re.compile(
    r"\b(?:д\.?|дом|кв\.?|квартира|корп\.?|корпус|стр\.?)[ \t]*[\w/-]+"
    r"(?:,[ \t]*(?:д\.?|дом|кв\.?|квартира|корп\.?|корпус|стр\.?)[ \t]*[\w/-]+)*",
    re.IGNORECASE,
)
NAME_FIELD_PATTERN = re.compile(
    r"\b(?:фио|полное[ \t]+имя|имя[ \t]+получателя|меня[ \t]+зовут|"
    r"его[ \t]+зовут|е[её][ \t]+зовут|имя|фамилия|отчество)"
    r"\b[ \t]*[:,-]?[ \t]*[A-ZА-ЯЁ][A-Za-zА-Яа-яЁё'-]+"
    r"(?:[ \t]+[A-ZА-ЯЁ][A-Za-zА-Яа-яЁё'-]+){0,2}",
    re.IGNORECASE,
)
AUTHOR_PATTERN = re.compile(r"^([^:\n]{1,80}):", re.MULTILINE)

ANONYMIZATION_REPLACEMENTS = (
    (SENSITIVE_FIELD_PATTERN, "[SENSITIVE_HIDDEN]"),
    (DOB_PATTERN, "[DOB_HIDDEN]"),
    (ADDRESS_CONTEXT_PATTERN, "[ADDRESS_HIDDEN]"),
    (STREET_PATTERN, "[ADDRESS_HIDDEN]"),
    (BUILDING_PATTERN, "[ADDRESS_HIDDEN]"),
    (NAME_FIELD_PATTERN, "[NAME_HIDDEN]"),
    (EMAIL_PATTERN, "[EMAIL_HIDDEN]"),
    (URL_PATTERN, "[URL_HIDDEN]"),
    (TELEGRAM_USERNAME_PATTERN, "[TELEGRAM_USERNAME_HIDDEN]"),
    (IP_PATTERN, "[IP_HIDDEN]"),
    (IBAN_PATTERN, "[IBAN_HIDDEN]"),
    (SSN_PATTERN, "[DOCUMENT_HIDDEN]"),
    (SNILS_PATTERN, "[SNILS_HIDDEN]"),
    (PASSPORT_PATTERN, "[PASSPORT_HIDDEN]"),
    (CARD_PATTERN, "[CARD_HIDDEN]"),
    (PHONE_PATTERN, "[PHONE_HIDDEN]"),
    (LONG_NUMBER_PATTERN, "[NUMBER_HIDDEN]"),
)


def anonymize_dialog_text(
    dialog_text: str,
    author_aliases: Optional[dict[str, str]] = None,
    sensitive_values: Optional[list[str]] = None,
) -> str:
    """
    Удаляет персональные данные из текста диалога перед внешним анализом.
    Авторов заменяет стабильными псевдонимами внутри одного диалога.
    """
    anonymized = _replace_known_values(dialog_text, author_aliases or {}, sensitive_values or [])
    anonymized = _anonymize_authors(anonymized, author_aliases or {})
    anonymized = _replace_known_values(anonymized, author_aliases or {}, sensitive_values or [])
    return _replace_personal_data_patterns(anonymized)


def anonymize_free_text(text: str, sensitive_values: Optional[list[str]] = None) -> str:
    """
    Маскирует персональные данные в произвольном пользовательском тексте.
    Не заменяет строки вида "Поле: значение" на участников диалога.
    """
    anonymized = _replace_known_values(text, {}, sensitive_values or [])
    return _replace_personal_data_patterns(anonymized)


def _replace_personal_data_patterns(text: str) -> str:
    anonymized = text

    for pattern, placeholder in ANONYMIZATION_REPLACEMENTS:
        anonymized = pattern.sub(placeholder, anonymized)

    return anonymized


def _replace_known_values(dialog_text: str, author_aliases: dict[str, str], sensitive_values: list[str]) -> str:
    anonymized = dialog_text

    for value, alias in sorted(author_aliases.items(), key=lambda item: len(item[0]), reverse=True):
        if len(value.strip()) < 2:
            continue

        anonymized = re.sub(re.escape(value), alias, anonymized, flags=re.IGNORECASE)

    for value in sorted(set(sensitive_values), key=len, reverse=True):
        if len(value.strip()) < 2:
            continue

        anonymized = re.sub(re.escape(value), "[NAME_HIDDEN]", anonymized, flags=re.IGNORECASE)

    return anonymized


def _anonymize_authors(dialog_text: str, known_author_aliases: dict[str, str]) -> str:
    author_aliases: dict[str, str] = {}

    def replace_author(match: re.Match) -> str:
        author = match.group(1).strip()
        if not author:
            return match.group(0)

        if author in known_author_aliases.values():
            return f"{author}:"

        if author in known_author_aliases:
            return f"{known_author_aliases[author]}:"

        if author not in author_aliases:
            author_aliases[author] = f"[Участник {len(author_aliases) + 1}]"

        return f"{author_aliases[author]}:"

    return AUTHOR_PATTERN.sub(replace_author, dialog_text)
