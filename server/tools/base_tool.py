from abc import ABC, abstractmethod
from typing import Any


class BaseTool(ABC):

    @property
    @abstractmethod
    def name(self) -> str:
        """Unique name the LLM uses to call this tool."""
        ...

    @property
    @abstractmethod
    def description(self) -> str:
        """Plain-English description shown to the LLM."""
        ...

    @property
    @abstractmethod
    def parameters(self) -> dict:
        """JSON-Schema-style dict describing the tool's parameters."""
        ...

    @abstractmethod
    def run(self, **kwargs: Any) -> Any:
        """Execute the tool and return a result."""
        ...
