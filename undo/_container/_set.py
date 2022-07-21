from __future__ import annotations

from typing import Hashable, Iterable, Iterator, MutableSet, TypeVar
from .._stack import UndoManager

_T = TypeVar("_T", bound=Hashable)


class UndoableSet(MutableSet[_T]):
    _mgr = UndoManager()

    def __init__(self, iterable: Iterable[_T] = (), /) -> None:
        self._set = set(iterable)

    def __repr__(self) -> str:
        clsname = type(self).__name__
        return f"{clsname}({self._set!r})"

    def __contains__(self, x: _T) -> bool:
        return x in self._set

    def __iter__(self) -> Iterator[_T]:
        return iter(self._set)

    def __len__(self) -> int:
        return len(self._set)

    def add(self, value: _T) -> None:
        if value not in self:
            self._add(value)
        return None

    @_mgr.command
    def _add(self, value: _T):
        self._set.add(value)

    @_add.undo_def
    def _add(self, value: _T):
        self._set.remove(value)

    def discard(self, value: _T) -> None:
        if value in self:
            self._discard(value)
        return None

    @_mgr.command
    def _discard(self, value: _T) -> None:
        self._set.discard(value)

    @_discard.undo_def
    def _discard(self, value: _T) -> None:
        self._set.add(value)

    def undo(self):
        """Undo the last operation."""
        return self._mgr.undo()

    def redo(self):
        """Redo the last undo operation."""
        return self._mgr.redo()
