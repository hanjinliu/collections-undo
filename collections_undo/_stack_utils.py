from __future__ import annotations
from enum import Enum
from typing import (
    Callable,
    Iterator,
    MutableSequence,
    NamedTuple,
    TypeVar,
)

_F = TypeVar("_F", bound=Callable)


class CallbackList(MutableSequence[_F]):
    """
    A list of callbacks of UndoManager updates.

    Callbacks are useful for such as logging.
    """

    def __init__(self) -> None:
        self._list = []

    def insert(self, index: int, callback: _F, /):
        self._check_callable(callback)
        self._list.insert(index, callback)

    def __repr__(self) -> str:
        return f"{type(self).__name__}({self._list!r})"

    def __len__(self) -> int:
        return len(self._list)

    def __iter__(self) -> Iterator[_F]:
        return iter(self._list)

    def __getitem__(self, key):
        return self._list[key]

    def __setitem__(self, key, callback):
        self._check_callable(callback)
        self._list[key] = callback

    def __delitem__(self, key):
        del self._list[key]

    def evoke(self, *args, **kwargs) -> None:
        """Evoce all callbacks."""
        for callback in self._list:
            callback(*args, **kwargs)
        return None

    @staticmethod
    def _check_callable(obj):
        if not callable(obj):
            raise TypeError("Can only insert callable object to the callback list.")


class CallType(Enum):
    call = "call"
    undo = "undo"
    redo = "redo"

    def __eq__(self, other):
        if isinstance(other, str):
            return self.value == other
        return super().__eq__(other)


class LengthPair(NamedTuple):
    """Pair of stack size."""

    undo: int
    redo: int
