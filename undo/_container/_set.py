from __future__ import annotations
from abc import abstractmethod

from typing import Hashable, Iterable, Iterator, MutableSet, TypeVar, TYPE_CHECKING
from .._stack import UndoManager

if TYPE_CHECKING:
    from typing_extensions import Self

_T = TypeVar("_T", bound=Hashable)


class AbstractUndoableSet(MutableSet[_T]):
    _mgr = UndoManager()

    def __repr__(self) -> str:
        clsname = type(self).__name__
        return f"{clsname}({set(self)!r})"

    @abstractmethod
    def __contains__(self, x: _T) -> bool:
        ...

    @abstractmethod
    def __iter__(self) -> Iterator[_T]:
        ...

    @abstractmethod
    def __len__(self) -> int:
        ...

    @abstractmethod
    def _raw_add(self, value: _T) -> None:
        ...

    @abstractmethod
    def _raw_discard(self, value: _T) -> None:
        ...

    def add(self, value: _T) -> None:
        if value not in self:
            self._add(value)
        return None

    @_mgr.command
    def _add(self, value: _T):
        self._raw_add(value)

    @_add.undo_def
    def _add(self, value: _T):
        self._raw_discard(value)

    def discard(self, value: _T) -> None:
        if value in self:
            self._discard(value)
        return None

    @_mgr.command
    def _discard(self, value: _T) -> None:
        self._raw_discard(value)

    @_discard.undo_def
    def _discard(self, value: _T) -> None:
        self._raw_add(value)

    @_mgr.command
    def _add_or_discard(self, values: Iterable[_T], add: Iterable[bool]) -> None:
        """This method is used for operators."""
        for val, add in zip(values, add):
            if add:
                self._raw_add(val)
            else:
                self._raw_discard(val)
        return None

    @_add_or_discard.undo_def
    def _add_or_discard(self, values: Iterable[_T], add: Iterable[bool]) -> None:
        for val, add in zip(values, add):
            if add:
                self._raw_discard(val)
            else:
                self._raw_add(val)
        return None

    # reimplemented methods

    def clear(self) -> None:
        """Clear the set."""
        # NOTE: Must make a copy of the set because size changes during iteration.
        self._add_or_discard(set(self), [False] * len(self))
        return None

    def __ior__(self, it) -> Self:
        _it = [val for val in it if val not in self]
        self._add_or_discard(_it, [True] * len(_it))
        return self

    def __iand__(self, it) -> Self:
        cmp = self - it
        self._add_or_discard(cmp, [False] * len(cmp))
        return self

    def __ixor__(self, it) -> Self:
        if it is self:
            self.clear()
        else:
            if not isinstance(it, set):
                it = set(it)
            _add = [value not in self for value in it]
            self._add_or_discard(it, _add)
        return self

    def __isub__(self, it) -> Self:
        _it = [val for val in it if val in self]
        self._add_or_discard(_it, [False] * len(_it))
        return self

    def undo(self):
        """Undo the last operation."""
        return self._mgr.undo()

    def redo(self):
        """Redo the last undo operation."""
        return self._mgr.redo()


class UndoableSet(AbstractUndoableSet[_T]):
    def __init__(self, iterable: Iterable[_T] = (), /) -> None:
        self._set = set(iterable)

    def __contains__(self, x: _T) -> bool:
        return x in self._set

    def __iter__(self) -> Iterator[_T]:
        return iter(self._set)

    def __len__(self) -> int:
        return len(self._set)

    def _raw_add(self, value: _T) -> None:
        self._set.add(value)

    def _raw_discard(self, value: _T) -> None:
        self._set.discard(value)
