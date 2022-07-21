from __future__ import annotations

from typing import Iterable, Iterator, MutableSequence, TypeVar
from .._stack import UndoManager

_T = TypeVar("_T")


class UndoableList(MutableSequence[_T]):
    """A list-like object implemented with undo functionalities."""

    _mgr = UndoManager()

    def __init__(self, iterable=(), /):
        self._list: list[_T] = list(iterable)

    def __repr__(self) -> str:
        clsname = type(self).__name__
        return f"{clsname}({self._list!r})"

    def __len__(self) -> int:
        """Length of list."""
        return len(self._list)

    def __getitem__(self, i):
        return self._list[i]

    def __iter__(self) -> Iterator[_T]:
        return iter(self._list)

    def __setitem__(self, key, val: _T):
        if isinstance(key, slice):
            key = slice(*key.indices(len(self)))
        return self._setitem(key, val)

    @_mgr.interface
    def _setitem(self, key, val):
        self._list[key] = val

    @_setitem.descriptor
    def _setitem(self, key, val):
        _val = self._list[key]
        if isinstance(key, slice):
            _val = list(_val)
        return (key, _val), {}

    def __delitem__(self, key) -> None:
        if isinstance(key, slice):
            key = slice(*key.indices(len(self)))
        return self._delitem_command(key)

    @_mgr.command
    def _delitem_command(self, key, val):
        del self._list[key]

    @_delitem_command.undo_def
    def _delitem_command(self, key, val):
        if isinstance(key, slice):
            s0, s1, step = key.start, key.stop, key.step
            if step == 1:
                self._list[s0:s0] = val
            else:
                # TODO: implement this
                ...
            raise NotImplementedError()
        else:
            self._list.insert(key, val)

    @_mgr.command
    def insert(self, index: int, val: _T):
        self._list.insert(index, val)

    @insert.undo_def
    def insert(self, index: int, val: _T):
        del self._list[index]

    @_mgr.command
    def extend(self, values: Iterable[_T]) -> None:
        return self._list.extend(values)

    @extend.undo_def
    def extend(self, values: Iterable[_T]):
        del self._list[-len(values) :]

    def clear(self) -> None:
        self._clear(self._list)

    @_mgr.command
    def _clear(self, values):
        self._list.clear()

    @_clear.undo_def
    def _clear(self, values: list[_T]):
        if self._list:
            raise RuntimeError("Unexpectedly non-empty list")
        self._list = values.copy()

    def undo(self):
        """Undo the last operation."""
        return self._mgr.undo()

    def redo(self):
        """Redo the last undo operation."""
        return self._mgr.redo()

    def sort(self, *, key=None, reverse=False):
        self[:] = sorted(self._list, key=key, reverse=reverse)

    def reverse(self):
        self[:] = reversed(self._list)
