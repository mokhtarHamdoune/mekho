from __future__ import annotations

from typing import Dict

from .interfaces import BaseTool, ToolGroup


class ToolRegistry:
    _instance: ToolRegistry | None = None
    _groups: list[ToolGroup]
    _tools: Dict[str, BaseTool]
    _tool_to_group: Dict[str, ToolGroup]

    def __new__(cls) -> ToolRegistry:
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._groups = []
            cls._instance._tools = {}
            cls._instance._tool_to_group = {}
        return cls._instance

    def register_group(self, group: ToolGroup) -> None:
        """Register a ToolGroup and index every tool it contains."""
        self._groups.append(group)
        for tool in group.tools:
            self._tools[tool.name] = tool
            self._tool_to_group[tool.name] = group

    def get(self, name: str) -> BaseTool:
        return self._tools[name]

    def get_group(self, tool_name: str) -> ToolGroup:
        """Return the group that owns the named tool."""
        return self._tool_to_group[tool_name]

    def all_groups(self) -> list[ToolGroup]:
        return list(self._groups)

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
