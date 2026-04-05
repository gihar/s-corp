"""Speech-to-text service using OpenAI Whisper API."""
import io
import logging

from bot.config import settings

logger = logging.getLogger(__name__)


async def transcribe_voice(audio_bytes: bytes, filename: str = "voice.ogg") -> str | None:
    """Transcribe voice message bytes to text using OpenAI Whisper.

    Returns the transcription string, or None if unavailable/failed.
    Requires OPENAI_API_KEY to be set in settings.
    """
    if not settings.openai_api_key:
        logger.warning("OPENAI_API_KEY not configured, skipping STT")
        return None

    try:
        # Import here so the bot starts even without openai installed
        from openai import AsyncOpenAI  # type: ignore

        client = AsyncOpenAI(api_key=settings.openai_api_key)
        audio_file = io.BytesIO(audio_bytes)
        audio_file.name = filename

        transcript = await client.audio.transcriptions.create(
            model="whisper-1",
            file=audio_file,
            language="ru",
        )
        return transcript.text
    except ImportError:
        logger.warning("openai package not installed, STT unavailable. Run: pip install openai")
        return None
    except Exception as e:
        logger.exception("STT transcription failed: %s", e)
        return None
