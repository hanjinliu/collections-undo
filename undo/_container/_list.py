from __future__ import annotations
from abc import abstractmethod

from typing import Iterable, Iterator, MutableSequence, TypeVar, SupportsIndex
from .._stack import UndoManager

_T = TypeVar("_T")


class AbstractUndoableList(MutableSequence[_T]):
    """
    An undoable mutable sequence.

    Abstract Methods
    ----------------
    __getitem__, _raw_setitem, _raw_delitem, _raw_insert, __len__, __iter__

    """

    _mgr = UndoManager()

    def __repr__(self) -> str:
        clsname = type(self).__name__
        return f"{clsname}({list(self)!r})"

    @abstractmethod
    def __getitem__(self, key: SupportsIndex) -> _T:
        ...

    @abstractmethod
    def __len__(self) -> int:
        ...

    @abstractmethod
    def __iter__(self) -> Iterator[_T]:
        ...

    @abstractmethod
    def _raw_setitem(self, key: SupportsIndex, val: _T) -> None:
        ...

    @abstractmethod
    def _raw_delitem(self, key: SupportsIndex) -> None:
        ...

    @abstractmethod
    def _raw_insert(self, index: int, val: _T) -> None:
        ...

    def __setitem__(self, key: SupportsIndex, val: _T):
        if isinstance(key, slice):
            key = slice(*key.indices(len(self)))
        elif key < 0:
            key += len(self)
        return self._setitem(key, val)

    @_mgr.interface
    def _setitem(self, key, val):
        self._raw_setitem(key, val)

    @_setitem.descriptor
    def _setitem(self, key, val):
        _val = self[key]
        if isinstance(key, slice):
            _val = list(_val)
        return (key, _val), {}

    def __delitem__(self, key) -> None:
        if isinstance(key, slice):
            key = slice(*key.indices(len(self)))
        elif key < 0:
            key += len(self)
        return self._delitem_command(key, self[key])

    @_mgr.command
    def _delitem_command(self, key, val):
        self._raw_delitem(key)

    @_delitem_command.undo_def
    def _delitem_command(self, key, val):
        if isinstance(key, slice):
            for i, idx in enumerate(range(key.start, key.stop, key.step)):
                self._raw_insert(idx, val[i])
        else:
            self._raw_insert(key, val)

    @_mgr.command
    def insert(self, index: int, val: _T):
        self._raw_insert(index, val)

    @insert.undo_def
    def insert(self, index: int, val: _T):
        self._raw_delitem(index)

    def extend(self, values: Iterable[_T]) -> None:
        with self._mgr.merging(same_command=True):
            for val in values:
                self.append(val)

    def clear(self) -> None:
        with self._mgr.merging(same_command=True):
            [self._raw_delitem(-1) for _ in range(len(self))]

    def undo(self):
        """Undo the last operation."""
        return self._mgr.undo()

    def redo(self):
        """Redo the last undo operation."""
        return self._mgr.redo()


class UndoableList(AbstractUndoableList[_T]):
    def __init__(self, iterable=(), /):
        self._list: list[_T] = list(iterable)

    def __len__(self) -> int:
        """Length of list."""
        return len(self._list)

    def __getitem__(self, i):
        return self._list[i]

    def _raw_setitem(self, key, val: _T) -> None:
        self._list[key] = val

    def _raw_delitem(self, key) -> None:
        del self._list[key]

    def __iter__(self) -> Iterator[_T]:
        return iter(self._list)

    def _raw_insert(self, index: int, val: _T):
        self._list.insert(index, val)

    def sort(self, *, key=None, reverse=False):
        self[:] = sorted(self._list, key=key, reverse=reverse)

    def reverse(self):
        self[:] = reversed(self._list)