"""
Tool Interface Contracts
========================

This module defines the two abstract base classes that every tool
implementation in this project must extend.  Think of them as
*interfaces* in the classical OOP sense: they describe **what** a
component must do, not **how** it does it.

BaseTool
--------
Represents a single, callable capability exposed to the LLM.
An LLM sees each tool as a JSON function schema (name + description +
parameters).  When the model decides to call one, the runtime invokes
``BaseTool.run(state, **kwargs)`` with the parsed arguments.

Concrete tools are never registered directly; they live inside a
``ToolGroup`` which owns their lifecycle and shared state.

ToolGroup
---------
A logical container for one or more related ``BaseTool`` instances
that share per-session state.

Why groups?  Some tools are stateful within a conversation (e.g. a
shopping cart that accumulates items across multiple LLM turns).
Rather than scattering state management across every tool, each group
owns a single ``new_session_state()`` factory.  The registry calls
that factory once per session and threads the resulting object through
every ``tool.run(state, ...)`` call in the group.

Stateless groups (e.g. read-only catalog lookups) simply leave the
default ``new_session_state`` returning ``None`` — no overhead, same
dispatch path.

Extension guide
---------------
1. Subclass ``BaseTool`` for each individual action.
2. Subclass ``ToolGroup``, declare its ``tools`` list, and optionally
   override ``new_session_state`` to return a typed state object.
3. Register the group once at startup::

       from server.tools.registry import ToolRegistry
       ToolRegistry().register_group(MyGroup())

"""

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
    def run(self, state: Any, **kwargs: Any) -> dict:
        """Execute the tool and return a JSON-serialisable dict result.

        ``state`` is the per-session state object produced by the tool's
        parent ``ToolGroup.new_session_state()``.  It is ``None`` for
        stateless groups.
        """
        ...


class ToolGroup(ABC):
    """
    A cohesive set of related tools that share per-session state.

    Register a concrete subclass with ``registry.register_group(MyGroup())``.
    The registry will:
      - expose every tool in ``tools`` to the LLM via its schema
      - call ``new_session_state()`` once per ``LLMSession`` to create
        isolated, typed state (e.g. a CartState instance)
      - pass that state as the first positional argument to every
        ``tool.run(state, **kwargs)`` call inside the session

    Stateless groups (e.g. catalog search) simply leave ``new_session_state``
    returning ``None`` — no overhead, same dispatch path.
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Unique identifier for this group (used as the state key)."""
        ...

    @property
    @abstractmethod
    def tools(self) -> list[BaseTool]:
        """All tools that belong to this group."""
        ...

    def new_session_state(self) -> Any:
        """
        Return a fresh state object for a new session.
        Override in stateful groups; the default (None) means stateless.
        """
        return None
