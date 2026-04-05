"""YooKassa payment integration."""
import asyncio
import logging
import uuid
from datetime import datetime, timedelta, timezone

from bot.config import settings
from bot.database.models import User
from bot.database.session import async_session_factory

logger = logging.getLogger(__name__)

SUBSCRIPTION_PRICE = "100.00"
SUBSCRIPTION_DAYS = 30


def _create_yookassa_payment_sync(user_id: int, return_url: str) -> dict:
    """Synchronous YooKassa payment creation (SDK is sync-only)."""
    from yookassa import Configuration, Payment  # type: ignore[import]

    Configuration.configure(settings.yookassa_shop_id, settings.yookassa_secret_key)
    payment = Payment.create(
        {
            "amount": {"value": SUBSCRIPTION_PRICE, "currency": "RUB"},
            "confirmation": {"type": "redirect", "return_url": return_url},
            "capture": True,
            "description": "Подписка на протокол-бота на 30 дней",
            "metadata": {"user_id": str(user_id)},
        },
        idempotency_key=str(uuid.uuid4()),
    )
    return {
        "id": payment.id,
        "confirmation_url": payment.confirmation.confirmation_url,
    }


async def create_payment(user_id: int, return_url: str) -> dict:
    """Create a YooKassa payment link for the user."""
    return await asyncio.to_thread(_create_yookassa_payment_sync, user_id, return_url)


async def activate_subscription(user_id: int) -> None:
    """Extend user subscription by SUBSCRIPTION_DAYS from today (or from current expiry)."""
    from bot.services.analytics import track  # local import to avoid circular

    is_renewal = False
    async with async_session_factory() as session:
        user = await session.get(User, user_id)
        if user is None:
            logger.warning("activate_subscription: user %d not found", user_id)
            return
        now = datetime.now(timezone.utc)
        current_expiry = user.subscription_expires_at
        if current_expiry and current_expiry > now:
            user.subscription_expires_at = current_expiry + timedelta(days=SUBSCRIPTION_DAYS)
            is_renewal = True
        else:
            user.subscription_expires_at = now + timedelta(days=SUBSCRIPTION_DAYS)
        user.is_subscribed = True
        await session.commit()
        logger.info(
            "Subscription activated for user %d until %s",
            user_id,
            user.subscription_expires_at,
        )
    event = "subscription_renewed" if is_renewal else "subscription_started"
    await track(user_id, event)
