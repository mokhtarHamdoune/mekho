import io
import logging
import numpy as np
import soundfile as sf
from kokoro import KPipeline

from ..config import KOKORO_LANG, KOKORO_VOICE, KOKORO_SPEED, KOKORO_SAMPLE_RATE
from .base import TTSProvider

logger = logging.getLogger(__name__)

class KokoroProvider(TTSProvider):
    def __init__(self):
        self._pipeline = None

    def load(self) -> None:
        if self._pipeline is None:
            logger.info("Loading Kokoro TTS...")
            self._pipeline = KPipeline(lang_code=KOKORO_LANG)
            logger.info("Kokoro ready.")

    def synthesize(self, text: str) -> bytes:
        self.load()
        chunks = [audio for _, _, audio in self._pipeline(text, voice=KOKORO_VOICE, speed=KOKORO_SPEED)]
        audio: np.ndarray = np.concatenate(chunks)
        buf = io.BytesIO()
        sf.write(buf, audio, KOKORO_SAMPLE_RATE, format="WAV", subtype="FLOAT")
        return buf.getvalue()
