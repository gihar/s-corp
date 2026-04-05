from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession

from bot.database.models import User
from bot.database.session import async_session_factory
from bot.services.analytics import track

router = Router()

START_TEXT = """
👋 <b>Привет! Я бот для составления протоколов встреч.</b>

Провели встречу? Я превращу ваши заметки и голосовые сообщения в готовый официальный протокол с помощью ИИ.

<b>Как начать:</b>
1. /new — создайте встречу (название, участники, повестка)
2. Отправляйте текст или голос во время встречи
3. Нажмите <b>✅ Завершить</b> — получите готовый протокол

<b>Бесплатно:</b> 3 протокола в месяц
<b>Премиум (100 ₽/мес):</b> без ограничений → /subscribe

Введите /help, чтобы увидеть все команды.
""".strip()

HELP_TEXT = """
📋 <b>Команды:</b>

/new — Начать новую встречу
/list — Мои протоколы
/view &lt;номер&gt; — Открыть протокол
/cancel — Отменить текущую встречу
/status — Мой план и остаток протоколов
/subscribe — Оформить Премиум (100 ₽/мес)
/help — Это сообщение

<b>Как это работает:</b>
1. /new → введите название, участников и повестку
2. Отправляйте текстовые заметки или голосовые сообщения
3. Нажмите «✅ Завершить встречу» — ИИ составит протокол

<b>Бесплатный план:</b> 3 протокола в месяц
<b>Премиум:</b> неограниченно — /subscribe
""".strip()


async def _upsert_user(message: Message) -> None:
    async with async_session_factory() as session:
        user = await session.get(User, message.from_user.id)
        is_new = user is None
        if is_new:
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
    if is_new:
        await track(message.from_user.id, "new_user")


@router.message(Command("start"))
async def cmd_start(message: Message) -> None:
    await _upsert_user(message)
    await message.answer(START_TEXT)


@router.message(Command("help"))
async def cmd_help(message: Message) -> None:
    await message.answer(HELP_TEXT, parse_mode="HTML")
