from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession

from bot.database.models import User
from bot.database.session import async_session_factory

router = Router()

START_TEXT = """
👋 Привет! Я бот для составления протоколов встреч.

Я помогу вам:
• Записать ход встречи (текст или голос)
• Сформировать структурированный протокол с помощью ИИ
• Сохранить и найти протоколы прошлых встреч

Введите /help, чтобы узнать о доступных командах.
""".strip()

HELP_TEXT = """
📋 <b>Доступные команды:</b>

/new — Начать новую встречу
/list — Список протоколов
/view &lt;номер&gt; — Просмотр протокола
/cancel — Отменить текущую встречу
/help — Это сообщение

<b>Как это работает:</b>
1. /new — введите название, участников и повестку
2. Отправляйте текстовые заметки или голосовые сообщения
3. Нажмите «✅ Завершить встречу» — ИИ сформирует протокол
""".strip()


async def _upsert_user(message: Message) -> None:
    async with async_session_factory() as session:
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


@router.message(Command("start"))
async def cmd_start(message: Message) -> None:
    await _upsert_user(message)
    await message.answer(START_TEXT)


@router.message(Command("help"))
async def cmd_help(message: Message) -> None:
    await message.answer(HELP_TEXT, parse_mode="HTML")
