import asyncio

import aiohttp

from config import YANDEX_API_KEY, YANDEX_FOLDER_ID
from services.anonymizer import anonymize_free_text
from services.prompts import build_dialog_question_prompt, build_gift_prompt

YANDEX_API_URL = "https://llm.api.cloud.yandex.net/foundationModels/v1/completion"
YANDEX_REQUEST_RETRIES = 3
YANDEX_RETRY_DELAY_SECONDS = 2


async def generate_gift_ideas(dialog_text: str, gift_context: str = "") -> str:
    """
    Отправляет переписку в YandexGPT и просит сгенерировать идеи для подарка.
    """
    if not YANDEX_API_KEY or not YANDEX_FOLDER_ID:
        return "Ошибка: Не настроены ключи Yandex Cloud в .env файле."

    headers = {
        "Authorization": f"Api-Key {YANDEX_API_KEY}",
        "x-folder-id": YANDEX_FOLDER_ID,
        "x-data-logging-enabled": "false",
    }

    # Чтобы не превышать лимиты токенов, обрежем диалог до последних 10000 символов
    dialog_text = dialog_text[-10000:]
    gift_context = anonymize_free_text(gift_context)

    # Формируем промпт
    prompt = build_gift_prompt(dialog_text, gift_context=gift_context)

    payload = {
        "modelUri": f"gpt://{YANDEX_FOLDER_ID}/yandexgpt",
        "completionOptions": {
            "stream": False,
            "temperature": 0.6,
            "maxTokens": "2000",
        },
        "messages": [
            {
                "role": "system",
                "text": "Ты - креативный помощник по выбору подарков. Твоя задача - анализировать диалоги и предлагать персонализированные идеи для подарка.",
            },
            {
                "role": "user",
                "text": prompt,
            },
        ],
    }

    timeout = aiohttp.ClientTimeout(total=180, connect=30, sock_connect=30, sock_read=150)

    for attempt in range(1, YANDEX_REQUEST_RETRIES + 1):
        try:
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.post(YANDEX_API_URL, headers=headers, json=payload) as response:
                    if response.status != 200:
                        text = await response.text()
                        return f"Ошибка API Yandex: {text}"

                    data = await response.json()
                    try:
                        return data["result"]["alternatives"][0]["message"]["text"]
                    except (KeyError, IndexError):
                        return "Ошибка: Неожиданный ответ от Yandex API."
        except (aiohttp.ClientError, asyncio.TimeoutError):
            if attempt == YANDEX_REQUEST_RETRIES:
                return (
                    "YandexGPT сейчас не отвечает или отвечает слишком долго. "
                    "Попробуй отправить файл ещё раз через минуту. "
                    "Если ошибка повторится, уменьши файл или экспортируй меньший период переписки."
                )

            await asyncio.sleep(YANDEX_RETRY_DELAY_SECONDS)


async def answer_dialog_question(dialog_text: str, question: str) -> str:
    """
    Отвечает на вопрос строго по анонимизированной переписке.
    """
    if not YANDEX_API_KEY or not YANDEX_FOLDER_ID:
        return "Ошибка: Не настроены ключи Yandex Cloud в .env файле."

    headers = {
        "Authorization": f"Api-Key {YANDEX_API_KEY}",
        "x-folder-id": YANDEX_FOLDER_ID,
        "x-data-logging-enabled": "false",
    }
    prompt = build_dialog_question_prompt(dialog_text[-10000:], anonymize_free_text(question))
    payload = {
        "modelUri": f"gpt://{YANDEX_FOLDER_ID}/yandexgpt",
        "completionOptions": {
            "stream": False,
            "temperature": 0.0,
            "maxTokens": "800",
        },
        "messages": [
            {
                "role": "system",
                "text": "Ты отвечаешь на вопросы только по предоставленной переписке. Если ответа нет, прямо скажи, что ответа нет.",
            },
            {
                "role": "user",
                "text": prompt,
            },
        ],
    }

    timeout = aiohttp.ClientTimeout(total=90, connect=30, sock_connect=30, sock_read=60)

    for attempt in range(1, YANDEX_REQUEST_RETRIES + 1):
        try:
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.post(YANDEX_API_URL, headers=headers, json=payload) as response:
                    if response.status != 200:
                        text = await response.text()
                        return f"Ошибка API Yandex: {text}"

                    data = await response.json()
                    try:
                        return data["result"]["alternatives"][0]["message"]["text"]
                    except (KeyError, IndexError):
                        return "Ошибка: Неожиданный ответ от Yandex API."
        except (aiohttp.ClientError, asyncio.TimeoutError):
            if attempt == YANDEX_REQUEST_RETRIES:
                return (
                    "YandexGPT сейчас не отвечает или отвечает слишком долго. "
                    "Попробуй задать вопрос ещё раз через минуту."
                )

            await asyncio.sleep(YANDEX_RETRY_DELAY_SECONDS)
