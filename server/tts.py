import io
import logging
import numpy as np
import soundfile as sf
from kokoro import KPipeline

from .config import KOKORO_LANG, KOKORO_VOICE, KOKORO_SPEED, KOKORO_SAMPLE_RATE

logger = logging.getLogger(__name__)

_pipeline: KPipeline | None = None


def load() -> KPipeline:
    global _pipeline
    if _pipeline is None:
        logger.info("Loading Kokoro TTS...")
        _pipeline = KPipeline(lang_code=KOKORO_LANG)
        logger.info("Kokoro ready.")
    return _pipeline


def synthesize(text: str) -> bytes:
    """Convert text to a WAV byte-string (24 kHz, mono, float32).

    Returns raw WAV bytes ready to send over WebSocket or write to a file.
    Runs synchronously — call via asyncio.run_in_executor in async contexts.
    """
    pipeline = load()
    chunks = [audio for _, _, audio in pipeline(text, voice=KOKORO_VOICE, speed=KOKORO_SPEED)]
    audio: np.ndarray = np.concatenate(chunks)

    buf = io.BytesIO()
    sf.write(buf, audio, KOKORO_SAMPLE_RATE, format="WAV", subtype="FLOAT")
    return buf.getvalue()
