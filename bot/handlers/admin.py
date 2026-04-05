"""Admin-only commands (/admin — stats dashboard)."""
import logging

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

from bot.config import settings
from bot.services.analytics import get_stats

logger = logging.getLogger(__name__)
router = Router()


@router.message(Command("admin"))
async def cmd_admin(message: Message) -> None:
    if message.from_user.id not in settings.admin_user_ids:
        await message.answer("⛔ Недостаточно прав.")
        return

    try:
        s = await get_stats()
    except Exception:
        logger.exception("Failed to fetch admin stats")
        await message.answer("⚠️ Ошибка при получении статистики.")
        return

    text = (
        "📊 <b>Статистика бота</b>\n\n"
        f"👥 Всего пользователей: <b>{s['total_users']}</b>\n"
        f"🆕 Новых сегодня: <b>{s['new_today']}</b>\n"
        f"📅 MAU (30 дней): <b>{s['mau']}</b>\n\n"
        f"💎 Платных подписчиков: <b>{s['paid_users']}</b>\n"
        f"📈 Конверсия: <b>{s['conversion_pct']}%</b>\n"
        f"💳 Новых подписок в этом месяце: <b>{s['new_subs_this_month']}</b>\n\n"
        f"📋 Протоколов всего: <b>{s['protocols_total']}</b>\n"
        f"📋 Протоколов в этом месяце: <b>{s['protocols_this_month']}</b>"
    )
    await message.answer(text)
