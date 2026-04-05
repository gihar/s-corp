"""Subscription management handlers: /subscribe and /status."""
import logging

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, Message

from bot.config import settings
from bot.database.session import async_session_factory
from bot.database.models import User
from bot.services.payment import create_payment
from bot.services.subscription import FREE_TIER_LIMIT, get_current_month, is_subscribed

logger = logging.getLogger(__name__)
router = Router()


@router.message(Command("subscribe"))
async def cmd_subscribe(message: Message) -> None:
    if not settings.yookassa_shop_id or not settings.yookassa_secret_key:
        await message.answer("⚠️ Оплата временно недоступна. Попробуйте позже.")
        return

    async with async_session_factory() as session:
        user = await session.get(User, message.from_user.id)

    already_subscribed = user and is_subscribed(user)
    if already_subscribed:
        expires = user.subscription_expires_at.strftime("%d.%m.%Y")
        intro = (
            f"✅ <b>Подписка активна до {expires}</b>\n\n"
            "Оплатив снова, продлите её ещё на 30 дней.\n\n"
        )
    else:
        intro = ""

    try:
        bot_me = await message.bot.get_me()
        return_url = f"https://t.me/{bot_me.username}"
        payment = await create_payment(message.from_user.id, return_url)
    except Exception as e:
        logger.exception("Payment creation failed: %s", e)
        await message.answer("⚠️ Не удалось создать платёж. Попробуйте позже.")
        return

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text="💳 Оплатить 100 ₽", url=payment["confirmation_url"])]]
    )
    await message.answer(
        intro
        + "💎 <b>Подписка Премиум — 100 ₽/месяц</b>\n\n"
        "Что входит:\n"
        "• Неограниченное количество протоколов\n"
        "• Голосовые заметки без ограничений\n"
        "• Поддержка проекта ❤️\n\n"
        "Нажмите кнопку ниже, чтобы оплатить:",
        reply_markup=keyboard,
    )


@router.message(Command("status"))
async def cmd_status(message: Message) -> None:
    async with async_session_factory() as session:
        user = await session.get(User, message.from_user.id)

    if user is None:
        await message.answer("Вы ещё не зарегистрированы. Отправьте /start.")
        return

    current_month = get_current_month()
    used = user.protocols_used_this_month if user.protocols_month == current_month else 0

    if is_subscribed(user):
        expires = user.subscription_expires_at.strftime("%d.%m.%Y")
        await message.answer(
            f"✨ <b>Статус: Премиум</b>\n\n"
            f"Подписка активна до: <b>{expires}</b>\n"
            f"Протоколов в этом месяце: <b>{used}</b> (без ограничений)\n\n"
            "Продлить: /subscribe"
        )
    else:
        remaining = max(0, FREE_TIER_LIMIT - used)
        await message.answer(
            f"👤 <b>Статус: Бесплатный план</b>\n\n"
            f"Протоколов в этом месяце: <b>{used} / {FREE_TIER_LIMIT}</b>\n"
            f"Осталось бесплатных: <b>{remaining}</b>\n\n"
            "Перейти на Премиум: /subscribe"
        )
