import io
import logging
import numpy as np
import soundfile as sf
from supertonic import TTS

from .base import TTSProvider
from ..config import LANGUAGE, SUPERTONIC_VOICE, SUPERTONIC_MODEL_SAMPLE_RATE

logger = logging.getLogger(__name__)


class SupertonicProvider(TTSProvider):
    def __init__(self) -> None:
        self._tts: TTS | None = None
        self._voice_style = None

    def load(self) -> None:
        if self._tts is None:
            logger.info("Loading Supertonic TTS...")
            self._tts = TTS(auto_download=True)
            self._voice_style = self._tts.get_voice_style(voice_name=SUPERTONIC_VOICE)
            logger.info("Supertonic ready.")

    def synthesize(self, text: str) -> bytes:
        self.load()
        wav, _ = self._tts.synthesize(text, voice_style=self._voice_style, lang=LANGUAGE, speed=1.05, total_steps=12)
        
        buf = io.BytesIO()
        sf.write(buf, wav.squeeze(), SUPERTONIC_MODEL_SAMPLE_RATE, format="WAV", subtype="FLOAT")
        return buf.getvalue()
