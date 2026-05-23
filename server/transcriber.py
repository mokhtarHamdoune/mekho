import os
import tempfile
import logging
import numpy as np
import whisper

from .config import WHISPER_MODEL_SIZE

logger = logging.getLogger(__name__)

_model: whisper.Whisper | None = None


def load() -> whisper.Whisper:
    global _model
    if _model is None:
        logger.info("Loading Whisper (%s)...", WHISPER_MODEL_SIZE)
        _model = whisper.load_model(WHISPER_MODEL_SIZE)
        logger.info("Whisper ready.")
    return _model


def transcribe_bytes(audio_bytes: bytes, suffix: str = ".wav") -> str:
    """Transcribe raw audio bytes (any format ffmpeg supports) to text.

    Writes to a temp file so Whisper's internal ffmpeg pipeline can decode it.
    Supports WebM/Opus from the browser's MediaRecorder, WAV, MP4, etc.
    """
    model = load()
    tmp_path: str | None = None
    try:
        with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
            tmp.write(audio_bytes)
            tmp_path = tmp.name
        result = model.transcribe(tmp_path, fp16=False)
    finally:
        if tmp_path and os.path.exists(tmp_path):
            os.unlink(tmp_path)
    return result["text"].strip()
