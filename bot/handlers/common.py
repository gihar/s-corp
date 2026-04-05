from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

router = Router()

START_TEXT = """
👋 Привет! Я бот для составления протоколов встреч.

Я помогу вам:
• Записать ход встречи
• Сформировать структурированный протокол
• Сохранить и найти протоколы прошлых встреч

Введите /help, чтобы узнать о доступных командах.
""".strip()

HELP_TEXT = """
📋 <b>Доступные команды:</b>

/start — Главное меню
/help — Это сообщение
/new — Начать новую встречу
/list — Список протоколов
/subscribe — Подписка (100 ₽/мес)

<i>Бот находится в разработке. Скоро будет больше функций!</i>
""".strip()


@router.message(Command("start"))
async def cmd_start(message: Message) -> None:
    await message.answer(START_TEXT)


@router.message(Command("help"))
async def cmd_help(message: Message) -> None:
    await message.answer(HELP_TEXT, parse_mode="HTML")
