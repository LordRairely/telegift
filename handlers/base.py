import logging
import os

from aiogram import Bot, F, Router
from aiogram.filters import Command
from aiogram.types import Message

from database import async_session_factory
from repositories.telegram_users import upsert_telegram_user
from services.parser import parse_telegram_json
from services.yandex_gpt import generate_gift_ideas

router = Router()
logger = logging.getLogger(__name__)


@router.message(Command("start"))
async def cmd_start(message: Message):
    if message.from_user:
        try:
            async with async_session_factory() as session:
                await upsert_telegram_user(session, message.from_user)
        except Exception:
            logger.exception("Failed to upsert Telegram user")

    await message.answer("Привет! Я бот TeleGift. Сделай экспорт чата (в формате JSON), с человеком для которого ищешь подарок, и отправь файл мне. Я почитаю вашу переписку и предложу классные идеи!")


@router.message(F.document)
async def handle_document(message: Message, bot: Bot):
    if not message.document.file_name.endswith('.json'):
        await message.answer("Пожалуйста, отправьте файл в формате JSON.")
        return

    wait_msg = await message.answer("Скачиваю файл, анонимизирую и анализирую переписку... Это может занять около минуты.")

    file_id = message.document.file_id
    file = await bot.get_file(file_id)
    file_path = file.file_path

    # Сохраняем локально временно
    local_path = f"tmp_{message.document.file_name}"
    await bot.download_file(file_path, local_path)

    try:
        dialog_text = parse_telegram_json(local_path)
        if not dialog_text:
            await wait_msg.edit_text("Не удалось найти текстовые сообщения в этом файле.")
            return

        ideas = await generate_gift_ideas(dialog_text)

        # Отправляем ответ по частям, если он слишком длинный
        if len(ideas) > 4000:
            for x in range(0, len(ideas), 4000):
                await message.answer(ideas[x:x+4000])
            await wait_msg.delete()
        else:
            await wait_msg.edit_text(ideas)

    except Exception as e:
        await wait_msg.edit_text(f"Произошла ошибка при обработке: {str(e)}")
    finally:
        if os.path.exists(local_path):
            os.remove(local_path)
