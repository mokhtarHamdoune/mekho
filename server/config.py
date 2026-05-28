import os
from dotenv import load_dotenv
import json

load_dotenv()

# ── HuggingFace LLM ──────────────────────────────────────────────────────────
API_TOKEN: str = os.getenv("API_TOKEN", "")
AI_MODEL: str = "gemma4:31b-cloud"
# BASE_URL: str = "https://router.huggingface.co/v1"
BASE_URL: str = "http://localhost:11434/v1/"
LLM_MAX_TOKENS: int = 512
MAX_HISTORY_TURNS: int = 20  # user+assistant pairs to keep per session

# ── Shop ─────────────────────────────────────────────────────────────────-----

COMPANY_NAME: str = "DataMasterAI"

# ── Language & TTS ────────────────────────────────────────────────────────────
LANGUAGE: str = os.getenv("AGENT_LANGUAGE", "en")  # "en" or "ar"
print(f"Configured agent language: {LANGUAGE}")
TTS_PROVIDER: str = os.getenv("TTS_PROVIDER", "auto")  # "auto" | "kokoro" | "edge" | "supertonic"

# ── Prompt loading ─────────────────────────────────────────────────────────---
PROMPT_PATH = os.path.join(os.path.dirname(__file__), f"../prompts/{LANGUAGE}.json")
with open(PROMPT_PATH, encoding="utf-8") as f:
    _PROMPTS = json.load(f)
print(f"Loaded prompts for language '{LANGUAGE}' from {PROMPT_PATH}")
print("System prompt:", _PROMPTS["system"])
SYSTEM_PROMPT: str = _PROMPTS["system"].replace("{company}", COMPANY_NAME)
WELCOME_PROMPT: str = _PROMPTS.get("welcome", "")

# ── Whisper (STT) ────────────────────────────────────────────────────────────
WHISPER_MODEL_SIZE: str = "small"
WHISPER_SAMPLE_RATE: int = 16000  # Hz
WHISPER_LANGUAGE: str = LANGUAGE

# ── Kokoro (TTS) ─────────────────────────────────────────────────────────────
KOKORO_LANG: str = "a"        # American English
KOKORO_VOICE: str = "af_heart"
KOKORO_SPEED: float = 1.0
KOKORO_SAMPLE_RATE: int = 24000  # Hz

# ── Edge TTS (Arabic, etc) ─────────────────────────────────────────────────--
EDGE_TTS_VOICE: str = os.getenv("EDGE_TTS_VOICE", "ar-EG-SalmaNeural")
EDGE_TTS_RATE: str = os.getenv("EDGE_TTS_RATE", "+0%")
EDGE_TTS_SAMPLE_RATE: int = 24000

# ── Supertonic TTS (local, multilingual) ───────────────────────────────────-
SUPERTONIC_VOICE: str = os.getenv("SUPERTONIC_VOICE", "M1")
SUPERTONIC_MODEL_SAMPLE_RATE: int = int(os.getenv("SUPERTONIC_MODEL_SAMPLE_RATE", "44100"))

# ── Server ───────────────────────────────────────────────────────────────────
HOST: str = os.getenv("HOST", "127.0.0.1")
PORT: int = int(os.getenv("PORT", "8080"))
