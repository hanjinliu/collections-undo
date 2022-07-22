from __future__ import annotations
from abc import abstractmethod

from typing import Hashable, Iterator, Mapping, MutableMapping, TypeVar
from .._stack import UndoManager
from .._const import empty

_K = TypeVar("_K", bound=Hashable)
_V = TypeVar("_V")


class AbstractUndoableDict(MutableMapping[_K, _V]):
    _mgr = UndoManager()

    def __repr__(self) -> str:
        clsname = type(self).__name__
        s = ", ".join(f"{k}={v!r}" for k, v in self.items())
        return f"{clsname}({s})"

    @abstractmethod
    def __iter__(self) -> Iterator[_K]:
        ...

    @abstractmethod
    def __len__(self) -> int:
        ...

    @abstractmethod
    def __getitem__(self, key: _K) -> _V:
        ...

    @abstractmethod
    def _raw_setitem(self, key: _K, value: _V) -> None:
        ...

    @abstractmethod
    def _raw_delitem(self, key: _K) -> None:
        ...

    def __setitem__(self, key: _K, value: _V) -> None:
        self._setitem(key, value, self.get(key, empty))

    @_mgr.command
    def _setitem(self, key: _K, value: _V, old_value: _V):
        return self._raw_setitem(key, value)

    @_setitem.undo_def
    def _setitem(self, key: _K, value: _V, old_value: _V):
        if old_value is empty:
            self._raw_delitem(key)
        else:
            self._raw_setitem(key, old_value)
        return None

    def __delitem__(self, key: _K) -> None:
        self._delitem(key, self[key])

    @_mgr.command
    def _delitem(self, key: _K, value: _V) -> None:
        self._raw_delitem(key)

    @_delitem.undo_def
    def _delitem(self, key: _K, value: _V) -> None:
        return self._raw_setitem(key, value)

    # reimplemented methods

    def clear(self) -> None:
        return self._clear(dict(self))

    @_mgr.command
    def _clear(self, values: dict[_K, _V]) -> None:
        while True:
            try:
                key = next(iter(self))
                self._raw_delitem(key)
            except StopIteration:
                break
        return None

    @_clear.undo_def
    def _clear(self, value: dict[_K, _V]):
        self._update._call_raw(value, {})
        return None

    def update(self, other=(), /, **kwargs):
        """Update the dictionary with the given arguments."""
        values = {}
        if isinstance(other, Mapping):
            for key in other:
                values[key] = other[key]
        elif hasattr(other, "keys"):
            for key in other.keys():
                values[key] = other[key]
        else:
            for key, value in other:
                values[key] = value

        for key, value in kwargs.items():
            values[key] = value

        old_values = {k: self.get(k, empty) for k in values.keys()}
        return self._update(values, old_values)

    @_mgr.command
    def _update(self, values: dict[_K, _V], old_values: dict[_K, _V]):
        for key, value in values.items():
            self._raw_setitem(key, value)
        return None

    @_update.undo_def
    def _update(self, values: dict[_K, _V], old_values: dict[_K, _V]):
        for key, value in old_values.items():
            if value is empty:
                self._raw_delitem(key)
            else:
                self._raw_setitem(key, value)
        return None

    def undo(self):
        """Undo the last operation."""
        return self._mgr.undo()

    def redo(self):
        """Redo the last undo operation."""
        return self._mgr.redo()


class UndoableDict(AbstractUndoableDict[_K, _V]):
    def __init__(self, *args, **kwargs) -> None:
        self._dict = dict(*args, **kwargs)

    def __iter__(self) -> Iterator[_K]:
        return iter(self._dict)

    def __len__(self) -> int:
        return len(self._dict)

    def __getitem__(self, key: _K) -> _V:
        return self._dict[key]

    def _raw_setitem(self, key: _K, value: _V) -> None:
        self._dict[key] = value

    def _raw_delitem(self, key: _K) -> None:
        del self._dict[key]
