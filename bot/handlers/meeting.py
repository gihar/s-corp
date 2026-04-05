"""Meeting creation flow using aiogram FSM."""
import logging
from datetime import datetime, timezone

from aiogram import Bot, F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
from sqlalchemy.ext.asyncio import AsyncSession

from bot.database.models import Meeting, User
from bot.database.session import async_session_factory
from bot.services.llm import generate_protocol
from bot.services.stt import transcribe_voice
from bot.services.subscription import can_create_protocol, increment_protocol_count

logger = logging.getLogger(__name__)
router = Router()


class MeetingStates(StatesGroup):
    waiting_title = State()
    waiting_participants = State()
    waiting_agenda = State()
    recording = State()
    processing = State()


def done_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="✅ Завершить встречу")]],
        resize_keyboard=True,
        one_time_keyboard=False,
    )


def agenda_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="✅ Повестка готова")]],
        resize_keyboard=True,
        one_time_keyboard=False,
    )


async def _upsert_user(session: AsyncSession, message: Message) -> None:
    user = await session.get(User, message.from_user.id)
    if user is None:
        user = User(
            id=message.from_user.id,
            username=message.from_user.username,
            full_name=message.from_user.full_name,
            language_code=message.from_user.language_code,
        )
        session.add(user)
    else:
        user.username = message.from_user.username
        user.full_name = message.from_user.full_name
    await session.commit()


@router.message(Command("new"))
async def cmd_new(message: Message, state: FSMContext) -> None:
    allowed, remaining = await can_create_protocol(message.from_user.id)
    if not allowed:
        await message.answer(
            "🚫 <b>Лимит бесплатных протоколов исчерпан</b>\n\n"
            "В бесплатном плане доступно 3 протокола в месяц.\n"
            "Перейдите на Премиум, чтобы создавать неограниченное количество протоколов.\n\n"
            "💎 /subscribe — оформить подписку за 100 ₽/месяц"
        )
        return

    await state.clear()
    await state.set_state(MeetingStates.waiting_title)
    hint = f" (осталось бесплатных: {remaining})" if remaining is not None else ""
    await message.answer(
        f"📋 <b>Новая встреча</b>{hint}\n\nВведите название встречи:",
        reply_markup=ReplyKeyboardRemove(),
    )


@router.message(MeetingStates.waiting_title)
async def process_title(message: Message, state: FSMContext) -> None:
    if not message.text:
        await message.answer("Пожалуйста, введите текстовое название встречи.")
        return

    await state.update_data(title=message.text.strip(), participants=[], agenda=[], notes=[])
    await state.set_state(MeetingStates.waiting_participants)
    await message.answer(
        "👥 <b>Участники</b>\n\n"
        "Введите имена участников — по одному на сообщение.\n"
        "Когда закончите, нажмите <b>✅ Повестка готова</b> или напишите <code>/skip</code>.",
        reply_markup=agenda_keyboard(),
    )


@router.message(MeetingStates.waiting_participants, F.text == "✅ Повестка готова")
@router.message(MeetingStates.waiting_participants, Command("skip"))
async def participants_done(message: Message, state: FSMContext) -> None:
    await state.set_state(MeetingStates.waiting_agenda)
    await message.answer(
        "📌 <b>Повестка дня</b>\n\n"
        "Введите пункты повестки — по одному на сообщение.\n"
        "Когда закончите, нажмите <b>✅ Повестка готова</b> или напишите <code>/skip</code>.",
        reply_markup=agenda_keyboard(),
    )


@router.message(MeetingStates.waiting_participants)
async def add_participant(message: Message, state: FSMContext) -> None:
    if not message.text:
        return
    data = await state.get_data()
    participants: list = data.get("participants", [])
    participants.append(message.text.strip())
    await state.update_data(participants=participants)
    await message.answer(f"✔️ Добавлен: <b>{message.text.strip()}</b>\nЕщё участники или нажмите ✅.")


@router.message(MeetingStates.waiting_agenda, F.text == "✅ Повестка готова")
@router.message(MeetingStates.waiting_agenda, Command("skip"))
async def agenda_done(message: Message, state: FSMContext) -> None:
    await state.set_state(MeetingStates.recording)
    await message.answer(
        "🎙 <b>Запись встречи</b>\n\n"
        "Отправляйте текстовые заметки или голосовые сообщения.\n"
        "Когда встреча закончится, нажмите <b>✅ Завершить встречу</b>.",
        reply_markup=done_keyboard(),
    )


@router.message(MeetingStates.waiting_agenda)
async def add_agenda_item(message: Message, state: FSMContext) -> None:
    if not message.text:
        return
    data = await state.get_data()
    agenda: list = data.get("agenda", [])
    agenda.append(message.text.strip())
    await state.update_data(agenda=agenda)
    await message.answer(f"✔️ Пункт добавлен: <b>{message.text.strip()}</b>\nЕщё пункты или нажмите ✅.")


@router.message(MeetingStates.recording, F.text == "✅ Завершить встречу")
async def finish_recording(message: Message, state: FSMContext, bot: Bot) -> None:
    data = await state.get_data()
    await state.set_state(MeetingStates.processing)

    title = data.get("title", "Встреча")
    participants: list = data.get("participants", [])
    agenda: list = data.get("agenda", [])
    notes: list = data.get("notes", [])

    if not notes:
        await message.answer(
            "⚠️ Нет заметок для обработки. Добавьте хотя бы одну заметку перед завершением.",
            reply_markup=done_keyboard(),
        )
        await state.set_state(MeetingStates.recording)
        return

    await message.answer("⏳ Генерирую протокол, подождите...", reply_markup=ReplyKeyboardRemove())

    async with async_session_factory() as session:
        await _upsert_user(session, message)

        meeting = Meeting(
            user_id=message.from_user.id,
            title=title,
            participants=", ".join(participants) if participants else None,
            agenda="\n".join(f"{i+1}. {item}" for i, item in enumerate(agenda)) if agenda else None,
            raw_notes="\n\n".join(notes),
            status="processing",
        )
        session.add(meeting)
        await session.commit()
        meeting_id = meeting.id

    try:
        protocol_text = await generate_protocol(
            title=title,
            date=datetime.now(timezone.utc).strftime("%d.%m.%Y"),
            participants=participants,
            agenda=agenda,
            notes=notes,
        )
    except Exception as e:
        logger.exception("Protocol generation failed: %s", e)
        protocol_text = None

    async with async_session_factory() as session:
        meeting = await session.get(Meeting, meeting_id)
        if meeting:
            meeting.protocol = protocol_text
            meeting.status = "done" if protocol_text else "draft"
            await session.commit()

    if protocol_text:
        await increment_protocol_count(message.from_user.id)

    await state.clear()

    if protocol_text:
        # Telegram message limit is 4096 chars; split if needed
        header = f"✅ <b>Протокол сформирован</b> (ID: {meeting_id})\n\n"
        full_text = header + protocol_text
        if len(full_text) <= 4096:
            await message.answer(full_text)
        else:
            await message.answer(header)
            # send in 4000-char chunks
            for i in range(0, len(protocol_text), 4000):
                await message.answer(protocol_text[i:i + 4000])
    else:
        await message.answer(
            f"⚠️ Не удалось сгенерировать протокол. Заметки сохранены (ID: {meeting_id}).\n"
            "Попробуйте позже командой /retry или проверьте настройки API."
        )


@router.message(MeetingStates.recording, F.voice)
async def handle_voice_note(message: Message, state: FSMContext, bot: Bot) -> None:
    status_msg = await message.answer("🔄 Расшифровываю голосовое сообщение...")

    try:
        file = await bot.get_file(message.voice.file_id)
        file_bytes = await bot.download_file(file.file_path)
        transcript = await transcribe_voice(file_bytes.read(), filename="voice.ogg")
    except Exception as e:
        logger.exception("Voice transcription failed: %s", e)
        transcript = None

    await bot.delete_message(message.chat.id, status_msg.message_id)

    if transcript:
        data = await state.get_data()
        notes: list = data.get("notes", [])
        notes.append(f"[Голосовая заметка]: {transcript}")
        await state.update_data(notes=notes)
        await message.answer(f"🎤 Расшифровано: <i>{transcript}</i>")
    else:
        await message.answer(
            "⚠️ Не удалось расшифровать голосовое сообщение. "
            "Проверьте настройку OPENAI_API_KEY или отправьте текстовую заметку."
        )


@router.message(MeetingStates.recording, F.text)
async def handle_text_note(message: Message, state: FSMContext) -> None:
    data = await state.get_data()
    notes: list = data.get("notes", [])
    notes.append(message.text.strip())
    await state.update_data(notes=notes)
    await message.answer(f"📝 Заметка #{len(notes)} сохранена.")


@router.message(Command("cancel"))
async def cmd_cancel(message: Message, state: FSMContext) -> None:
    current = await state.get_state()
    if current is None:
        await message.answer("Нет активной встречи.", reply_markup=ReplyKeyboardRemove())
        return
    await state.clear()
    await message.answer("❌ Встреча отменена.", reply_markup=ReplyKeyboardRemove())
