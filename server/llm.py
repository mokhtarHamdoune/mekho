import re
import logging
from openai import AsyncOpenAI

from .config import (
    HF_TOKEN,
    HF_MODEL,
    HF_BASE_URL,
    LLM_MAX_TOKENS,
    MAX_HISTORY_TURNS,
    SYSTEM_PROMPT,
)

logger = logging.getLogger(__name__)

_client: AsyncOpenAI | None = None


def _get_client() -> AsyncOpenAI:
    global _client
    if _client is None:
        _client = AsyncOpenAI(base_url=HF_BASE_URL, api_key=HF_TOKEN)
    return _client


# ── Markdown cleaner (models ignore the system prompt sometimes) ─────────────

_MARKDOWN_PATTERNS = [
    (re.compile(r"#+\s*"), ""),                                       # headings
    (re.compile(r"[*_]{1,3}(.*?)[*_]{1,3}"), r"\1"),                # bold/italic
    (re.compile(r"`{1,3}.*?`{1,3}", re.DOTALL), ""),                 # code
    (re.compile(r"^\s*[-*+]\s+", re.MULTILINE), ""),                 # bullets
    (re.compile(r"\[([^\]]+)\]\([^)]+\)"), r"\1"),                   # links
    (re.compile(r"\n{2,}"), " "),                                     # blank lines
]


def _strip_markdown(text: str) -> str:
    for pattern, replacement in _MARKDOWN_PATTERNS:
        text = pattern.sub(replacement, text)
    return text.strip()


# ── Sentence splitter ────────────────────────────────────────────────────────

_SENTENCE_END = re.compile(r"(?<=[.!?])\s+")


def _flush_sentences(buffer: str) -> tuple[list[str], str]:
    """Split buffer on sentence boundaries. Returns (complete sentences, remainder)."""
    parts = _SENTENCE_END.split(buffer)
    if len(parts) == 1:
        return [], buffer
    sentences = [s.strip() for s in parts[:-1] if s.strip()]
    return sentences, parts[-1]


# ── Session ──────────────────────────────────────────────────────────────────

class LLMSession:
    """One instance per WebSocket connection — owns the conversation history."""

    def __init__(self) -> None:
        self.history: list[dict] = []

    def _trim(self) -> None:
        """Evict the oldest turns once the history exceeds MAX_HISTORY_TURNS pairs."""
        max_msgs = MAX_HISTORY_TURNS * 2
        if len(self.history) > max_msgs:
            self.history = self.history[-max_msgs:]

    async def ask_stream(self, user_text: str):
        """Async generator — yields one *complete sentence* at a time as the
        LLM streams its reply.  Each yielded string is markdown-free and
        ready for TTS."""
        self.history.append({"role": "user", "content": user_text})
        self._trim()

        stream = await _get_client().chat.completions.create(
            model=HF_MODEL,
            messages=[{"role": "system", "content": SYSTEM_PROMPT}] + self.history,
            max_tokens=LLM_MAX_TOKENS,
            stream=True,
        )

        buffer = ""
        full_reply = ""

        async for chunk in stream:
            delta = chunk.choices[0].delta.content or ""
            buffer += delta
            full_reply += delta

            sentences, buffer = _flush_sentences(buffer)
            for sentence in sentences:
                yield _strip_markdown(sentence)

        # Yield whatever is left in the buffer (last sentence may lack trailing space)
        if buffer.strip():
            yield _strip_markdown(buffer.strip())

        self.history.append({"role": "assistant", "content": _strip_markdown(full_reply)})
        logger.debug("History length: %d messages", len(self.history))

    def clear(self) -> None:
        """Reset the conversation (e.g. user says 'start over')."""
        self.history.clear()
