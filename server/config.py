import os
from dotenv import load_dotenv

load_dotenv()

# ── HuggingFace LLM ──────────────────────────────────────────────────────────
API_TOKEN: str = os.getenv("API_TOKEN", "")
AI_MODEL: str = "gemma4:31b-cloud"
# BASE_URL: str = "https://router.huggingface.co/v1"
BASE_URL: str = "http://localhost:11434/v1/"
LLM_MAX_TOKENS: int = 512
MAX_HISTORY_TURNS: int = 20  # user+assistant pairs to keep per session

# ── Shop ──────────────────────────────────────────────────────────────────────
COMPANY_NAME: str = "DataMasterAI"

def _build_system_prompt() -> str:
    # Imported here to avoid a circular import (catalog imports nothing from config)
    return (
        f"You are a helpful voice shopping assistant for {COMPANY_NAME}. "
        "Start by welcoming the customer and asking how you can help. "
        "Respond in plain spoken English only. "
        "Do not use markdown, bullet points, asterisks, hashtags, or any special formatting. "
        "Use the available tools whenever appropriate — they always return the current cart "
        "contents so you can confirm exactly what the customer has. "
        "Keep your replies short and conversational.\n\n"
    )

SYSTEM_PROMPT: str = _build_system_prompt()

# ── Whisper (STT) ────────────────────────────────────────────────────────────
WHISPER_MODEL_SIZE: str = "small"
WHISPER_SAMPLE_RATE: int = 16000  # Hz

# ── Kokoro (TTS) ─────────────────────────────────────────────────────────────
KOKORO_LANG: str = "a"        # American English
KOKORO_VOICE: str = "af_heart"
KOKORO_SPEED: float = 1.0
KOKORO_SAMPLE_RATE: int = 24000  # Hz

# ── Server ───────────────────────────────────────────────────────────────────
HOST: str = os.getenv("HOST", "127.0.0.1")
PORT: int = int(os.getenv("PORT", "8080"))
