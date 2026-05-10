import logging
import os
import tempfile
from pathlib import Path

from aiogram import Bot, F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message

from database import async_session_factory
from repositories.gift_analytics import (
    create_gift_analysis,
    mark_gift_analysis_failed,
    mark_gift_analysis_success,
    save_gift_feedback,
)
from repositories.telegram_users import upsert_telegram_user
from services.parser import parse_dialog_file
from services.referrals import parse_start_source
from services.yandex_gpt import answer_dialog_question, generate_gift_ideas

router = Router()
logger = logging.getLogger(__name__)
AVAILABLE_COMMANDS = (
    "/start — начать работу и посмотреть инструкцию",
    "/help — показать доступные команды",
    "/cancel — отменить текущий анализ",
    "/feedback — оценить идеи после анализа",
)
SUPPORTED_EXTENSIONS = {".json", ".txt"}
MAX_DOWNLOAD_SIZE_MB = 20
MAX_DOWNLOAD_SIZE_BYTES = MAX_DOWNLOAD_SIZE_MB * 1024 * 1024
MAX_SPLIT_HINT_SIZE_MB = 35
MAX_SPLIT_HINT_SIZE_BYTES = MAX_SPLIT_HINT_SIZE_MB * 1024 * 1024
CONTEXT_QUESTIONS_TEXT = (
    "Перед анализом ответь, пожалуйста, на 5 коротких вопросов одним сообщением:\n\n"
    "1. Повод: день рождения, годовщина, Новый год или другое?\n"
    "2. Бюджет: примерная сумма или диапазон.\n"
    "3. Город/страна: где подарок нужно купить или доставить?\n"
    "4. Кто этот человек тебе: партнёр, друг, родственник, коллега?\n"
    "5. Что точно не дарить: аллергии, табу, уже есть, не любит?\n\n"
    "Можно коротко, например: «ДР, до 5000, Москва, партнёр, не дарить косметику». "
    "После этого я анонимизирую переписку и отправлю её во внешний AI-сервис для анализа."
)
FEEDBACK_REQUEST_TEXT = (
    "Теперь можешь задавать вопросы по этой переписке, например: «Какой любимый цвет у Подаркополучателя?» "
    "Я отвечу только если это есть в тексте.\n\n"
    "А чтобы помочь улучшить рекомендации, отправь оценку командой:\n"
    "/feedback 1: 5, 2: 3, 3: 4. Вторая слишком банальная, первая попала точно"
)


class GiftFlow(StatesGroup):
    waiting_for_context = State()
    qa = State()


def get_help_text() -> str:
    commands = "\n".join(AVAILABLE_COMMANDS)
    return (
        "Я умею анализировать переписку и предлагать идеи подарков.\n\n"
        "Отправь мне экспорт чата в формате JSON или TXT.\n\n"
        f"Доступные команды:\n{commands}"
    )


@router.message(Command("start"))
async def cmd_start(message: Message):
    if message.from_user:
        try:
            acquisition_source, referred_by_code = parse_start_source(message.text)
            async with async_session_factory() as session:
                await upsert_telegram_user(
                    session,
                    message.from_user,
                    acquisition_source=acquisition_source,
                    referred_by_code=referred_by_code,
                )
        except Exception:
            logger.exception("Failed to upsert Telegram user")

    await message.answer(
        "Привет! Я бот TeleGift. Сделай экспорт чата с человеком, для которого ищешь подарок, "
        "и отправь файл мне в формате JSON или TXT. Я почитаю переписку и предложу классные идеи!\n\n"
        "Команды:\n"
        + "\n".join(AVAILABLE_COMMANDS)
    )


@router.message(Command("help"))
async def cmd_help(message: Message):
    await message.answer(get_help_text())


@router.message(Command("cancel"))
async def cmd_cancel(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("Ок, текущий анализ отменён. Можешь отправить новый файл, когда будешь готова.")


@router.message(F.document)
async def handle_document(message: Message, state: FSMContext):
    file_name = message.document.file_name or ""
    file_extension = Path(file_name).suffix.lower()

    if file_extension not in SUPPORTED_EXTENSIONS:
        await message.answer("Пожалуйста, отправьте файл в формате JSON или TXT.")
        return

    if message.document.file_size and message.document.file_size > MAX_DOWNLOAD_SIZE_BYTES:
        if message.document.file_size <= MAX_SPLIT_HINT_SIZE_BYTES:
            await message.answer(
                f"Файл больше {MAX_DOWNLOAD_SIZE_MB} МБ, поэтому Telegram не даёт мне его скачать. "
                "Раздели экспорт на 2 JSON-файла, чтобы каждый был меньше 20 МБ, и отправь их по очереди."
            )
            return

        await message.answer(
            f"Файл слишком большой: {MAX_SPLIT_HINT_SIZE_MB} МБ или больше. "
            "Попробуй экспортировать чат за меньший период, без медиа, или разделить переписку на несколько JSON-файлов."
        )
        return

    await state.set_state(GiftFlow.waiting_for_context)
    await state.update_data(
        file_id=message.document.file_id,
        file_name=file_name,
        file_extension=file_extension,
        file_size=message.document.file_size,
    )
    await message.answer(CONTEXT_QUESTIONS_TEXT)


@router.message(GiftFlow.waiting_for_context, F.text)
async def handle_gift_context(message: Message, bot: Bot, state: FSMContext):
    data = await state.get_data()
    file_id = data.get("file_id")
    file_extension = data.get("file_extension") or ".json"
    file_size = data.get("file_size")
    analysis_id = None
    telegram_user_id = None

    if not file_id:
        await state.clear()
        await message.answer("Я потерял файл для анализа. Отправь его ещё раз, пожалуйста.")
        return

    wait_msg = await message.answer("Скачиваю файл, анонимизирую и анализирую переписку... Это может занять около минуты.")

    file = await bot.get_file(file_id)
    file_path = file.file_path

    tmp_file = tempfile.NamedTemporaryFile(delete=False, prefix="telegift_", suffix=file_extension)
    local_path = tmp_file.name
    tmp_file.close()
    await bot.download_file(file_path, local_path)

    try:
        if message.from_user:
            try:
                async with async_session_factory() as session:
                    telegram_user_id = await upsert_telegram_user(session, message.from_user)
                    analysis_id = await create_gift_analysis(
                        session,
                        telegram_user_id=telegram_user_id,
                        file_format=file_extension.lstrip("."),
                        file_size_bytes=file_size,
                    )
            except Exception:
                logger.exception("Failed to create gift analysis analytics row")

        dialog_text = parse_dialog_file(local_path, sender_user=message.from_user)
        if not dialog_text:
            if analysis_id:
                async with async_session_factory() as session:
                    await mark_gift_analysis_failed(session, analysis_id, "empty_dialog")
            await wait_msg.edit_text("Не удалось найти текстовые сообщения в этом файле.")
            return

        ideas = await generate_gift_ideas(dialog_text, gift_context=message.text)

        # Отправляем ответ по частям, если он слишком длинный
        if len(ideas) > 4000:
            for x in range(0, len(ideas), 4000):
                await message.answer(ideas[x:x+4000])
            await wait_msg.delete()
        else:
            await wait_msg.edit_text(ideas)

        if analysis_id and telegram_user_id:
            async with async_session_factory() as session:
                await mark_gift_analysis_success(session, analysis_id, telegram_user_id)

        await state.set_state(GiftFlow.qa)
        await state.update_data(analysis_id=analysis_id, dialog_text=dialog_text)
        await message.answer(FEEDBACK_REQUEST_TEXT)

    except Exception as e:
        if analysis_id:
            try:
                async with async_session_factory() as session:
                    await mark_gift_analysis_failed(session, analysis_id, type(e).__name__)
            except Exception:
                logger.exception("Failed to mark gift analysis as failed")

        await wait_msg.edit_text(f"Произошла ошибка при обработке: {str(e)}")
        await state.clear()
    finally:
        if os.path.exists(local_path):
            os.remove(local_path)


@router.message(Command("feedback"))
async def handle_feedback(message: Message, state: FSMContext):
    data = await state.get_data()
    analysis_id = data.get("analysis_id")
    feedback_text = (message.text or "").replace("/feedback", "", 1).strip()

    if not feedback_text:
        await message.answer("Пришли оценку после команды, например: /feedback 1: 5, 2: 3. Первая идея попала лучше.")
        return

    if analysis_id:
        try:
            async with async_session_factory() as session:
                await save_gift_feedback(session, analysis_id, feedback_text)
        except Exception:
            logger.exception("Failed to save gift feedback")

    await message.answer(
        "Спасибо! Оценку сохранила: по ней будет видно, какие сценарии реально попадают в человека."
    )


@router.message(GiftFlow.qa, F.text)
async def handle_dialog_question(message: Message, state: FSMContext):
    data = await state.get_data()
    dialog_text = data.get("dialog_text")

    if not dialog_text:
        await state.clear()
        await message.answer("Я уже очистил переписку из текущей сессии. Отправь файл заново, чтобы задать вопрос.")
        return

    wait_msg = await message.answer("Проверяю по переписке без догадок...")
    answer = await answer_dialog_question(dialog_text, message.text or "")
    await wait_msg.edit_text(answer)


@router.message(F.text.startswith("/"))
async def handle_unknown_command(message: Message):
    await message.answer("У меня нет такой команды.\n\n" + get_help_text())


@router.message(F.text)
async def handle_plain_text(message: Message):
    await message.answer(
        "Я пока не анализирую обычные сообщения прямо из чата. "
        "Отправь мне файл переписки в формате JSON или TXT, а команды можно посмотреть через /help."
    )
