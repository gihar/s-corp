from datetime import datetime

from sqlalchemy import BigInteger, DateTime, Index, Integer, String, Text, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)  # Telegram user_id
    username: Mapped[str | None] = mapped_column(String(64), nullable=True)
    full_name: Mapped[str] = mapped_column(String(256))
    language_code: Mapped[str | None] = mapped_column(String(10), nullable=True)
    is_subscribed: Mapped[bool] = mapped_column(default=False)
    subscription_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    # Free tier usage tracking: count and "YYYY-MM" month string
    protocols_used_this_month: Mapped[int] = mapped_column(Integer, default=0)
    protocols_month: Mapped[str | None] = mapped_column(String(7), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class Meeting(Base):
    __tablename__ = "meetings"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(BigInteger)
    title: Mapped[str | None] = mapped_column(String(512), nullable=True)
    # Comma-separated participant names
    participants: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Newline-separated agenda items
    agenda: Mapped[str | None] = mapped_column(Text, nullable=True)
    raw_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    protocol: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(32), default="draft")  # draft, recording, processing, done
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class UserEvent(Base):
    """Append-only analytics event log."""

    __tablename__ = "user_events"
    __table_args__ = (
        Index("ix_user_events_event_at", "event", "created_at"),
        Index("ix_user_events_user_id", "user_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(BigInteger)
    # event kinds: new_user, protocol_created, subscription_started,
    #               subscription_renewed, free_limit_hit, stt_ok, stt_fail, llm_fail
    event: Mapped[str] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True)
