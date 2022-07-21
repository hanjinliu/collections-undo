from __future__ import annotations

from typing import Hashable, Iterator, MutableMapping, TypeVar
from .._stack import UndoManager
from .._const import empty

_K = TypeVar("_K", bound=Hashable)
_V = TypeVar("_V")


class UndoableDict(MutableMapping[_K, _V]):
    _mgr = UndoManager()

    def __init__(self, *args, **kwargs) -> None:
        self._dict = dict(*args, **kwargs)

    def __repr__(self) -> str:
        clsname = type(self).__name__
        return f"{clsname}({self._dict!r})"

    def __iter__(self) -> Iterator[_K]:
        return iter(self._dict)

    def __len__(self) -> int:
        return len(self._dict)

    def __getitem__(self, key: _K) -> _V:
        return self._dict[key]

    def __setitem__(self, key: _K, value: _V) -> None:
        self._setitem(key, value, self.get(key, empty))

    @_mgr.command
    def _setitem(self, key: _K, value: _V, old_value: _V):
        self._dict[key] = value
        return None

    @_setitem.undo_def
    def _setitem(self, key: _K, value: _V, old_value: _V):
        if old_value is empty:
            del self._dict[key]
        else:
            self._dict[key] = old_value
        return None

    def __delitem__(self, key: _K) -> None:
        self._delitem(key, self[key])

    @_mgr.command
    def _delitem(self, key: _K, value: _V) -> None:
        del self._dict[key]

    @_delitem.undo_def
    def _delitem(self, key: _K, value: _V) -> None:
        self._dict[key] = value
        return None

    def undo(self):
        """Undo the last operation."""
        return self._mgr.undo()

    def redo(self):
        """Redo the last undo operation."""
        return self._mgr.redo()
