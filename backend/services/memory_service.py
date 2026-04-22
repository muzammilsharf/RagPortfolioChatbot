from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from typing import Deque


@dataclass(frozen=True)
class Turn:
    role: str  # "user" | "assistant"
    content: str


class MemoryService:
    """
    Sliding-window, in-memory session memory.
    Browser session => UI should generate/store a session_id in sessionStorage.
    """

    def __init__(self, *, max_turns: int) -> None:
        self._max_turns = max_turns
        self._store: dict[str, Deque[Turn]] = {}

    def get_history(self, session_id: str) -> list[Turn]:
        return list(self._store.get(session_id, deque()))

    def append(self, session_id: str, turn: Turn) -> None:
        if session_id not in self._store:
            self._store[session_id] = deque(maxlen=self._max_turns * 2)
        self._store[session_id].append(turn)

    def clear(self, session_id: str) -> None:
        self._store.pop(session_id, None)
