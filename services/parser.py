import json

from services.anonymizer import anonymize_dialog_text

def parse_telegram_json(file_path: str) -> str:
    """
    Парсит JSON файл экспорта Telegram и возвращает текст переписки.
    Мы берем только текстовые сообщения.
    """
    with open(file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
        
    messages = data.get("messages", [])
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
                
    return anonymize_dialog_text(dialog_text)
