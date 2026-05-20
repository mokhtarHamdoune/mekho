import re
import json
import asyncio
import functools
import logging
from openai import AsyncOpenAI

from .config import (
    API_TOKEN,
    AI_MODEL,
    BASE_URL,
    LLM_MAX_TOKENS,
    MAX_HISTORY_TURNS,
    SYSTEM_PROMPT,
)
# TODO: we should get rid of this self-registration
from . import tools as _tools  # noqa: F401 — triggers self-registration of all tools
from .tools.registry import registry
from .events import ToolEventEmitter

logger = logging.getLogger(__name__)

_client: AsyncOpenAI | None = None


def _get_client() -> AsyncOpenAI:
    global _client
    if _client is None:
        _client = AsyncOpenAI(base_url=BASE_URL, api_key=API_TOKEN)
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

    def __init__(self, emitter: ToolEventEmitter | None = None) -> None:
        self.history: list[dict] = []
        self._emitter = emitter

    def _trim(self) -> None:
        """Evict the oldest turns once the history exceeds MAX_HISTORY_TURNS pairs."""
        max_msgs = MAX_HISTORY_TURNS * 2
        if len(self.history) > max_msgs:
            self.history = self.history[-max_msgs:]

    async def ask_stream(self, user_text: str):
        """Async generator — yields one *complete sentence* at a time as the
        LLM streams its reply.  Each yielded string is markdown-free and
        ready for TTS.  Tool calls are executed transparently and the loop
        continues until the LLM returns a plain text response."""
        self.history.append({"role": "user", "content": user_text})
        self._trim()


        # LOOP because:
        # When the LLM decides to call a tool, it won't stream text 
        # — it returns a tool call block. 
        # You execute it, inject the result into history, 
        # then re-call to get the spoken confirmation (which we stream). 
        # This is a two-step round trip but it's the standard pattern.
        while True:
            logger.debug("Sending conversation to LLM with %d messages", len(self.history))
            stream = await _get_client().chat.completions.create(
                model=AI_MODEL,
                messages=[{"role": "system", "content": SYSTEM_PROMPT}] + self.history,
                max_tokens=LLM_MAX_TOKENS,
                stream=True,
                tools=registry.as_llm_schema(),
                tool_choice="auto",
            )

            # index -> {id, name, arguments}
            tool_calls_acc: dict[int, dict] = {}
            buffer = ""
            full_reply = ""
            finish_reason = None

            async for chunk in stream:
                if not chunk.choices:
                    continue
                choice = chunk.choices[0]
                finish_reason = choice.finish_reason or finish_reason
                delta = choice.delta

                # Accumulate streamed tool-call fragments
                if delta.tool_calls:
                    for tc in delta.tool_calls:
                        entry = tool_calls_acc.setdefault(
                            tc.index, {"id": "", "name": "", "arguments": ""}
                        )
                        if tc.id:
                            entry["id"] = tc.id
                        if tc.function:
                            if tc.function.name:
                                entry["name"] += tc.function.name
                            if tc.function.arguments:
                                entry["arguments"] += tc.function.arguments

                # Stream text as sentences
                content = delta.content or ""
                buffer += content
                full_reply += content

                sentences, buffer = _flush_sentences(buffer)
                for sentence in sentences:
                    yield _strip_markdown(sentence)

            if buffer.strip():
                yield _strip_markdown(buffer.strip())

            # No tool calls — conversation turn is complete
            if finish_reason != "tool_calls" or not tool_calls_acc:
                self.history.append({"role": "assistant", "content": _strip_markdown(full_reply)})
                logger.debug("History length: %d messages", len(self.history))
                break

            # Append the assistant's tool-call message
            self.history.append({
                "role": "assistant",
                "content": None,
                "tool_calls": [
                    {
                        "id": tc["id"],
                        "type": "function",
                        "function": {"name": tc["name"], "arguments": tc["arguments"]},
                    }
                    for tc in tool_calls_acc.values()
                ],
            })

            # Execute each tool and append the results
            for tc in tool_calls_acc.values():
                try:
                    args = json.loads(tc["arguments"])
                    # Run in a thread so blocking tools never freeze the event loop
                    result: dict = await asyncio.to_thread(
                        functools.partial(registry.get(tc["name"]).run, **args)
                    )
                except Exception as exc:
                    result = {"error": str(exc)}

                if self._emitter is not None:
                    await self._emitter.on_tool_result(tc["name"], result)

                self.history.append({
                    "role": "tool",
                    "tool_call_id": tc["id"],
                    "content": json.dumps(result),
                })

            logger.debug("Tool calls executed, looping back to LLM.")

    def clear(self) -> None:
        """Reset the conversation (e.g. user says 'start over')."""
        self.history.clear()
