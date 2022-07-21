from __future__ import annotations
from functools import wraps
from typing import Callable, TYPE_CHECKING, TypeVar

if TYPE_CHECKING:
    from typing_extensions import ParamSpec, Self
    from ._stack import UndoManager

    _P = ParamSpec("_P")
    _R = TypeVar("_R")
    _RR = TypeVar("_RR")


class NotReversibleError(RuntimeError):
    """Raised when reversive operation is not defined."""


class Command:
    def __init__(
        self,
        func: Callable[_P, _R],
        mgr: UndoManager,
        inverse_func: Callable[_P, _RR] | None = None,
    ):
        self._func_fw = func
        self._func_rv = inverse_func
        self._mgr = mgr
        wraps(func)(self)
        self._instances: dict[int, Self] = {}

    def __repr__(self) -> str:
        return f"{type(self).__name__}<{self.__name__}>"

    def undo_def(self, undo: Callable[_P, _RR]) -> Self:
        return type(self)(self._func_fw, self._mgr, undo)

    def _call_with_callback(self, *args: _P.args, **kwargs: _P.kwargs) -> _R:
        out = self._call_raw(*args, **kwargs)
        self._mgr._append_command(self, *args, *kwargs)
        return out

    def _call_raw(self, *args: _P.args, **kwargs: _P.kwargs) -> _R:
        return self._func_fw(*args, **kwargs)

    def _revert(self, *args: _P.args, **kwargs: _P.kwargs) -> _RR:
        if self._func_rv is None:
            raise NotReversibleError(f"{self!r} is not reversible.")
        return self._func_rv(*args, **kwargs)

    __call__ = _call_with_callback

    def __get__(self, obj, objtype=None) -> Command:
        """Create a method-like command object."""
        if obj is None:
            return self
        _id = id(obj)
        if (out := self._instances.get(_id, None)) is None:
            if self._func_rv is None:
                inv_func = None
            else:
                inv_func = self._func_rv.__get__(obj, objtype)
            out = type(self)(
                func=self._func_fw.__get__(obj, objtype),
                mgr=self._mgr.__get__(obj, objtype),
                inverse_func=inv_func,
            )
            self._instances[_id] = out
        return out
