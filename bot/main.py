import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

from bot.config import settings
from bot.database.session import create_tables
from bot.handlers.admin import router as admin_router
from bot.handlers.common import router as common_router
from bot.handlers.meeting import router as meeting_router
from bot.handlers.protocol import router as protocol_router
from bot.handlers.subscription import router as subscription_router
from bot.webhook_server import run_webhook_server

logging.basicConfig(
    level=logging.DEBUG if settings.debug else logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
    datefmt="%Y-%m-%dT%H:%M:%S",
)
logger = logging.getLogger(__name__)


async def main() -> None:
    await create_tables()

    bot = Bot(
        token=settings.bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    dp = Dispatcher()
    # Order matters: meeting FSM router first to catch state-based messages
    dp.include_router(meeting_router)
    dp.include_router(subscription_router)
    dp.include_router(protocol_router)
    dp.include_router(admin_router)
    dp.include_router(common_router)

    logger.info("Starting bot...")

    if settings.yookassa_shop_id:
        await asyncio.gather(
            dp.start_polling(bot),
            run_webhook_server(),
        )
    else:
        logger.info("YooKassa not configured — webhook server disabled")
        await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
