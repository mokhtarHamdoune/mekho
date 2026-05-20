from __future__ import annotations

from typing import Dict
from .base_tool import BaseTool


class ToolRegistry:
    _instance: ToolRegistry | None = None
    _tools: Dict[str, BaseTool]

    def __new__(cls) -> ToolRegistry:
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._tools = {}
        return cls._instance

    def register(self, tool: BaseTool) -> None:
        self._tools[tool.name] = tool

    def get(self, name: str) -> BaseTool:
        return self._tools[name]

    def all_tools(self) -> list[BaseTool]:
        return list(self._tools.values())

    def as_llm_schema(self) -> list[dict]:
        """Return the tool list in the format LLM APIs expect."""
        return [
            {
                "type": "function",
                "function": {
                    "name": tool.name,
                    "description": tool.description,
                    "parameters": tool.parameters,
                },
            }
            for tool in self._tools.values()
        ]


registry = ToolRegistry()
