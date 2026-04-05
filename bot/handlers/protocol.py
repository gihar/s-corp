"""Protocol listing and retrieval handlers."""
import logging

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message
from sqlalchemy import select, desc

from bot.database.models import Meeting
from bot.database.session import async_session_factory

logger = logging.getLogger(__name__)
router = Router()

PAGE_SIZE = 5


@router.message(Command("list"))
async def cmd_list(message: Message) -> None:
    async with async_session_factory() as session:
        result = await session.execute(
            select(Meeting)
            .where(Meeting.user_id == message.from_user.id)
            .where(Meeting.status != "cancelled")
            .order_by(desc(Meeting.created_at))
            .limit(PAGE_SIZE)
        )
        meetings = result.scalars().all()

    if not meetings:
        await message.answer(
            "📭 У вас пока нет протоколов.\n"
            "Начните встречу командой /new."
        )
        return

    lines = ["📋 <b>Ваши последние протоколы:</b>\n"]
    for m in meetings:
        status_icon = {"done": "✅", "recording": "🎙", "processing": "⏳", "draft": "📝"}.get(
            m.status, "❓"
        )
        date_str = m.created_at.strftime("%d.%m.%Y")
        title = m.title or "Без названия"
        lines.append(f"{status_icon} <b>#{m.id}</b> — {title} <i>({date_str})</i>")

    lines.append("\nДля просмотра протокола: /view &lt;номер&gt;")
    await message.answer("\n".join(lines))


@router.message(Command("view"))
async def cmd_view(message: Message) -> None:
    parts = message.text.split(maxsplit=1)
    if len(parts) < 2 or not parts[1].strip().isdigit():
        await message.answer("Использование: /view &lt;номер&gt;\nПример: /view 3")
        return

    meeting_id = int(parts[1].strip())

    async with async_session_factory() as session:
        meeting = await session.get(Meeting, meeting_id)

    if meeting is None or meeting.user_id != message.from_user.id:
        await message.answer("❌ Протокол не найден.")
        return

    if meeting.status == "recording":
        await message.answer("⏺ Встреча ещё идёт. Завершите её, чтобы получить протокол.")
        return

    if meeting.status == "processing":
        await message.answer("⏳ Протокол в процессе генерации, попробуйте позже.")
        return

    if not meeting.protocol:
        # Show raw notes if no protocol yet
        raw = meeting.raw_notes or "(нет заметок)"
        header = f"📝 <b>#{meeting.id} — {meeting.title or 'Без названия'}</b>\n<i>(протокол не сгенерирован)</i>\n\n"
        await message.answer(header + raw[:3800])
        return

    header = f"📋 <b>Протокол #{meeting.id}</b>\n\n"
    full = header + meeting.protocol
    if len(full) <= 4096:
        await message.answer(full)
    else:
        await message.answer(header)
        for i in range(0, len(meeting.protocol), 4000):
            await message.answer(meeting.protocol[i:i + 4000])
