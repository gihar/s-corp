"""Analytics event tracking and stats aggregation."""
import logging
from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select, text

from bot.database.models import Meeting, User, UserEvent
from bot.database.session import async_session_factory

logger = logging.getLogger(__name__)


async def track(user_id: int, event: str) -> None:
    """Append an analytics event. Silently absorbs errors so it never breaks the main flow."""
    try:
        async with async_session_factory() as session:
            session.add(UserEvent(user_id=user_id, event=event))
            await session.commit()
    except Exception:
        logger.exception("analytics.track failed for user=%d event=%s", user_id, event)


async def get_stats() -> dict:
    """Return a summary dict for the /admin command."""
    now = datetime.now(timezone.utc)
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    day_30_ago = now - timedelta(days=30)

    async with async_session_factory() as session:
        total_users = (await session.execute(select(func.count()).select_from(User))).scalar_one()

        new_today = (
            await session.execute(
                select(func.count()).select_from(User).where(User.created_at >= today_start)
            )
        ).scalar_one()

        mau = (
            await session.execute(
                select(func.count(func.distinct(UserEvent.user_id)))
                .select_from(UserEvent)
                .where(UserEvent.created_at >= day_30_ago)
            )
        ).scalar_one()

        protocols_total = (
            await session.execute(select(func.count()).select_from(Meeting).where(Meeting.status == "done"))
        ).scalar_one()

        protocols_this_month = (
            await session.execute(
                select(func.count())
                .select_from(Meeting)
                .where(Meeting.status == "done", Meeting.created_at >= month_start)
            )
        ).scalar_one()

        paid_users = (
            await session.execute(
                select(func.count())
                .select_from(User)
                .where(User.is_subscribed == True, User.subscription_expires_at > now)  # noqa: E712
            )
        ).scalar_one()

        new_subs_this_month = (
            await session.execute(
                select(func.count())
                .select_from(UserEvent)
                .where(
                    UserEvent.event.in_(["subscription_started", "subscription_renewed"]),
                    UserEvent.created_at >= month_start,
                )
            )
        ).scalar_one()

    conversion_rate = (paid_users / total_users * 100) if total_users else 0.0

    return {
        "total_users": total_users,
        "new_today": new_today,
        "mau": mau,
        "paid_users": paid_users,
        "conversion_pct": round(conversion_rate, 1),
        "new_subs_this_month": new_subs_this_month,
        "protocols_total": protocols_total,
        "protocols_this_month": protocols_this_month,
    }
