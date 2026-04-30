import aiohttp
from config import YANDEX_API_KEY, YANDEX_FOLDER_ID

async def generate_gift_ideas(dialog_text: str) -> str:
    """
    Отправляет переписку в YandexGPT и просит сгенерировать идеи для подарка.
    """
    if not YANDEX_API_KEY or not YANDEX_FOLDER_ID:
        return "Ошибка: Не настроены ключи Yandex Cloud в .env файле."

    url = "https://llm.api.cloud.yandex.net/foundationModels/v1/completion"
    
    headers = {
        "Authorization": f"Api-Key {YANDEX_API_KEY}",
        "x-folder-id": YANDEX_FOLDER_ID,
        "x-data-logging-enabled": "false"
    }
    
    # Чтобы не превышать лимиты токенов, обрежем диалог до последних 10000 символов
    dialog_text = dialog_text[-10000:]
    
    # Формируем промпт
    prompt = f"Проанализируй следующую анонимизированную переписку между людьми и предложи 3-5 креативных идей для подарка одному из них, на основе их интересов, хобби или упоминаний в диалоге. Игнорируй технические маркеры персональных данных вроде [телефон], [адрес], [email]. Обоснуй каждую идею.\n\nПереписка:\n{dialog_text}"
    
    payload = {
        "modelUri": f"gpt://{YANDEX_FOLDER_ID}/yandexgpt",
        "completionOptions": {
            "stream": False,
            "temperature": 0.6,
            "maxTokens": "2000"
        },
        "messages": [
            {
                "role": "system",
                "text": "Ты - креативный помощник по выбору подарков. Твоя задача - анализировать диалоги и предлагать персонализированные идеи для подарка."
            },
            {
                "role": "user",
                "text": prompt
            }
        ]
    }
    
    async with aiohttp.ClientSession() as session:
        async with session.post(url, headers=headers, json=payload) as response:
            if response.status != 200:
                text = await response.text()
                return f"Ошибка API Yandex: {text}"
                
            data = await response.json()
            try:
                result = data['result']['alternatives'][0]['message']['text']
                return result
            except (KeyError, IndexError):
                return "Ошибка: Неожиданный ответ от Yandex API."
