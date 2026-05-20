"""
events.py — Transport-agnostic event contracts.

LLMSession depends only on this Protocol, not on WebSocket or any other
concrete transport.  Swap the implementation in main.py without touching
the session logic.
"""

from typing import Protocol


class ToolEventEmitter(Protocol):
    """Anything that can receive a tool_result event."""

    async def on_tool_result(self, tool_name: str, result: dict) -> None:
        """Called immediately after a tool finishes executing."""
        ...
