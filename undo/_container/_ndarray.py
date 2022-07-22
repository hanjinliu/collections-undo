from __future__ import annotations
from abc import abstractmethod, abstractproperty, ABC
from operator import mul
from functools import reduce
from typing import Iterable, SupportsIndex, TYPE_CHECKING
from .._stack import UndoManager

if TYPE_CHECKING:
    _Shape = tuple[int, ...]


class AbstractUndoableNDArray(ABC):

    _mgr = UndoManager()

    def __repr__(self) -> str:
        clsname = type(self).__name__
        return f"{clsname}({list(self)!r})"

    @abstractproperty
    def shape(self) -> tuple[int, ...]:
        ...

    @property
    def ndim(self) -> int:
        return len(self.shape)

    @abstractmethod
    def __getitem__(self, key: SupportsIndex):
        ...

    @abstractmethod
    def __len__(self) -> int:
        ...

    def __iter__(self):
        n = len(self)
        for i in range(n):
            yield self[i]

    @abstractmethod
    def _raw_setitem(self, key: SupportsIndex, val) -> None:
        ...

    @abstractmethod
    def _raw_reshape(self, shape: _Shape) -> None:
        ...

    def reshape(self, *shape):
        if len(shape) == 1 and hasattr(shape, "__iter__"):
            shape = tuple(shape)

        # normalize shape
        if -1 in shape:
            _shape = list(shape)
            missing = prod(self.shape) / prod(s for s in _shape if s > 0)
            _shape[_shape.index(-1)] = missing
            shape = tuple(_shape)
        elif prod(shape) != prod(self.shape):
            raise ValueError(
                f"Cannot reshape array of shape {self.shape} into shape {shape}."
            )
        return self._reshape(shape)

    @_mgr.command
    def _reshape(self, shape: _Shape, old_shape: _Shape):
        self._raw_reshape(shape)

    @_reshape.undo_def
    def _reshape(self, shape: _Shape, old_shape: _Shape):
        self._raw_reshape(old_shape)

    @abstractmethod
    def _raw_concatenate(self, other) -> None:
        ...

    def __setitem__(self, key: SupportsIndex | tuple[SupportsIndex], val):
        if isinstance(key, tuple):
            key = tuple(
                _normalize_key(k, n) for k, n in zip(key, self.shape)
            )  # TODO: ellipse
        else:
            key = _normalize_key(key, self.shape[0])
        return self._setitem(key, val)

    @_mgr.interface
    def _setitem(self, key, val):
        self._raw_setitem(key, val)

    @_setitem.descriptor
    def _setitem(self, key, val):
        _val = self[key]
        return (key, _val), {}


def _normalize_key(key, n):
    if isinstance(key, slice):
        key = slice(*key.indices(n))
    elif key < 0:
        key += len(n)
    return key


def prod(x: Iterable[int]) -> int:
    return reduce(mul, x, initial=1)
