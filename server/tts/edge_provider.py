import asyncio
import io
import logging
import soundfile as sf
import numpy as np
from edge_tts import Communicate, SubMaker
from .base import TTSProvider
from ..config import EDGE_TTS_VOICE, EDGE_TTS_RATE, EDGE_TTS_SAMPLE_RATE

logger = logging.getLogger(__name__)

class EdgeProvider(TTSProvider):
    def __init__(self):
        self.voice = EDGE_TTS_VOICE
        self.rate = EDGE_TTS_RATE
        self.sample_rate = EDGE_TTS_SAMPLE_RATE

    def load(self) -> None:
        pass  # No-op for edge-tts

    def synthesize(self, text: str) -> bytes:
        """Synthesize text to WAV bytes using edge-tts (async wrapper)."""
        return asyncio.run(self._synthesize_async(text))

    async def _synthesize_async(self, text: str) -> bytes:
        communicate = Communicate(text, self.voice, rate=self.rate)
        wav_bytes = b""
        async for chunk in communicate.stream():
            if chunk["type"] == "audio":
                wav_bytes += chunk["data"]
        # Optionally resample to float32/24kHz if needed
        data, sr = sf.read(io.BytesIO(wav_bytes))
        if sr != self.sample_rate:
            import librosa
            data = librosa.resample(data, orig_sr=sr, target_sr=self.sample_rate)
        buf = io.BytesIO()
        sf.write(buf, data.astype(np.float32), self.sample_rate, format="WAV", subtype="FLOAT")
        return buf.getvalue()
