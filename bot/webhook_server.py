"""Aiohttp server for receiving YooKassa payment webhook notifications."""
import json
import logging

from aiohttp import web

from bot.config import settings
from bot.services.payment import activate_subscription

logger = logging.getLogger(__name__)


async def _yookassa_webhook(request: web.Request) -> web.Response:
    try:
        raw = await request.read()
        data = json.loads(raw)
    except Exception:
        logger.warning("Invalid webhook payload")
        return web.Response(status=400)

    event = data.get("event")
    payment_obj = data.get("object", {})

    if event == "payment.succeeded":
        metadata = payment_obj.get("metadata", {})
        user_id_str = metadata.get("user_id")
        if user_id_str:
            try:
                await activate_subscription(int(user_id_str))
            except Exception as e:
                logger.exception("Failed to activate subscription for user %s: %s", user_id_str, e)

    return web.Response(status=200)


async def run_webhook_server() -> None:
    app = web.Application()
    app.router.add_post("/webhook/yookassa", _yookassa_webhook)

    runner = web.AppRunner(app)
    await runner.setup()
    # Use Railway's injected PORT if available, otherwise fall back to WEBHOOK_PORT.
    listen_port = settings.port if settings.port != 8080 else settings.webhook_port
    site = web.TCPSite(runner, "0.0.0.0", listen_port)
    await site.start()
    logger.info("YooKassa webhook server listening on port %d", listen_port)

    # Keep running indefinitely alongside the bot
    import asyncio
    await asyncio.Event().wait()
