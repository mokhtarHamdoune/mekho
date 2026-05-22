"""
Text processing utilities for LLM streaming output.

These helpers are intentionally decoupled from the LLM session so they
can be unit-tested in isolation and reused if a second output channel
(e.g. chat transcript) is added later.
"""

import re


# ── Markdown cleaner ─────────────────────────────────────────────────────────
# Some models ignore the "no markdown" system prompt instruction.
# We strip it here before handing text to TTS so the voice doesn't
# read out asterisks, hash symbols, or URLs.

_MARKDOWN_PATTERNS = [
    (re.compile(r"#+\s*"), ""),                                       # headings
    (re.compile(r"[*_]{1,3}(.*?)[*_]{1,3}"), r"\1"),                 # bold/italic
    (re.compile(r"`{1,3}.*?`{1,3}", re.DOTALL), ""),                  # code
    (re.compile(r"^\s*[-*+]\s+", re.MULTILINE), ""),                  # bullets
    (re.compile(r"\[([^\]]+)\]\([^)]+\)"), r"\1"),                    # links
    (re.compile(r"\n{2,}"), " "),                                      # blank lines
]


def strip_markdown(text: str) -> str:
    """Remove common markdown syntax from *text* and return plain text."""
    for pattern, replacement in _MARKDOWN_PATTERNS:
        text = pattern.sub(replacement, text)
    return text.strip()


# ── Sentence splitter ────────────────────────────────────────────────────────
# The LLM streams tokens, not sentences.  We buffer the raw stream and
# yield one complete sentence at a time so TTS can start speaking as
# early as possible without cutting off mid-sentence.

_SENTENCE_END = re.compile(r"(?<=[.!?])\s+")


def flush_sentences(buffer: str) -> tuple[list[str], str]:
    """Split *buffer* on sentence boundaries.

    Returns a tuple of ``(complete_sentences, remainder)`` where
    *remainder* is everything after the last detected sentence boundary
    and should be carried forward to the next call.
    """
    parts = _SENTENCE_END.split(buffer)
    if len(parts) == 1:
        return [], buffer
    sentences = [s.strip() for s in parts[:-1] if s.strip()]
    return sentences, parts[-1]
