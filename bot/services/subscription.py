"""Subscription status checks and free tier enforcement."""
from datetime import datetime, timezone

from bot.database.models import User
from bot.database.session import async_session_factory

FREE_TIER_LIMIT = 3  # protocols per month


def get_current_month() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m")


def is_subscribed(user: User) -> bool:
    if user.subscription_expires_at is None:
        return False
    return user.subscription_expires_at > datetime.now(timezone.utc)


async def can_create_protocol(user_id: int) -> tuple[bool, int | None]:
    """Return (allowed, remaining_free) — remaining is None for paid users."""
    async with async_session_factory() as session:
        user = await session.get(User, user_id)
        if user is None:
            return True, FREE_TIER_LIMIT

        if is_subscribed(user):
            return True, None  # unlimited

        current_month = get_current_month()
        used = user.protocols_used_this_month if user.protocols_month == current_month else 0
        remaining = FREE_TIER_LIMIT - used
        return remaining > 0, max(0, remaining)


async def increment_protocol_count(user_id: int) -> None:
    """Increment monthly protocol counter for a user."""
    async with async_session_factory() as session:
        user = await session.get(User, user_id)
        if user is None:
            return
        current_month = get_current_month()
        if user.protocols_month != current_month:
            user.protocols_month = current_month
            user.protocols_used_this_month = 1
        else:
            user.protocols_used_this_month += 1
        await session.commit()
