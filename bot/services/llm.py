"""Claude API integration for protocol generation."""
import asyncio
import logging
from typing import List

import anthropic

from bot.config import settings

logger = logging.getLogger(__name__)

_client: anthropic.AsyncAnthropic | None = None

_RETRY_ATTEMPTS = 3
_RETRY_BACKOFF = 2.0  # seconds, doubled each retry


def _get_client() -> anthropic.AsyncAnthropic:
    global _client
    if _client is None:
        _client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)
    return _client


PROTOCOL_SYSTEM_PROMPT = """Ты — помощник для составления протоколов встреч на русском языке.
Составляй структурированные, чёткие протоколы в деловом стиле.
Используй Markdown для форматирования: заголовки, списки, жирный текст.
Всегда пиши на русском языке."""

PROTOCOL_USER_TEMPLATE = """Составь официальный протокол встречи на основе следующей информации:

**Название встречи:** {title}
**Дата:** {date}
**Участники:** {participants}

**Повестка дня:**
{agenda}

**Заметки и записи в ходе встречи:**
{notes}

---
Протокол должен содержать:
1. Заголовок с названием, датой и участниками
2. Повестку дня (пронумерованные пункты)
3. Ход обсуждения — кратко по каждому пункту повестки
4. Принятые решения (если есть)
5. Поручения (кому, что, срок — если указаны)
6. Подпись «Протокол составлен автоматически»

Пиши лаконично и по делу."""


async def generate_protocol(
    title: str,
    date: str,
    participants: List[str],
    agenda: List[str],
    notes: List[str],
) -> str:
    """Generate a structured meeting protocol using Claude.

    Retries up to _RETRY_ATTEMPTS times on transient API errors (overload / rate limit).
    Raises on permanent errors or if all retries are exhausted.
    """
    if not settings.anthropic_api_key:
        raise ValueError("ANTHROPIC_API_KEY не настроен")

    participants_str = ", ".join(participants) if participants else "не указаны"
    agenda_str = (
        "\n".join(f"{i+1}. {item}" for i, item in enumerate(agenda))
        if agenda
        else "повестка не задана"
    )
    notes_str = "\n\n".join(notes)

    user_message = PROTOCOL_USER_TEMPLATE.format(
        title=title,
        date=date,
        participants=participants_str,
        agenda=agenda_str,
        notes=notes_str,
    )

    client = _get_client()
    last_exc: Exception | None = None
    backoff = _RETRY_BACKOFF

    for attempt in range(1, _RETRY_ATTEMPTS + 1):
        try:
            response = await client.messages.create(
                model="claude-sonnet-4-6",
                max_tokens=2048,
                system=PROTOCOL_SYSTEM_PROMPT,
                messages=[{"role": "user", "content": user_message}],
            )
            return response.content[0].text
        except (anthropic.RateLimitError, anthropic.APIStatusError) as exc:
            # Retry on overload / rate-limit; surface other status errors immediately
            if isinstance(exc, anthropic.APIStatusError) and exc.status_code not in (429, 529):
                raise
            last_exc = exc
            if attempt < _RETRY_ATTEMPTS:
                logger.warning(
                    "Claude API transient error (attempt %d/%d): %s — retrying in %.0fs",
                    attempt,
                    _RETRY_ATTEMPTS,
                    exc,
                    backoff,
                )
                await asyncio.sleep(backoff)
                backoff *= 2
        except anthropic.APIConnectionError as exc:
            last_exc = exc
            if attempt < _RETRY_ATTEMPTS:
                logger.warning(
                    "Claude API connection error (attempt %d/%d): %s — retrying in %.0fs",
                    attempt,
                    _RETRY_ATTEMPTS,
                    exc,
                    backoff,
                )
                await asyncio.sleep(backoff)
                backoff *= 2

    raise RuntimeError(f"Claude API failed after {_RETRY_ATTEMPTS} attempts") from last_exc
