from __future__ import annotations
from typing import Callable, NamedTuple, TYPE_CHECKING, TypeVar

if TYPE_CHECKING:
    from typing_extensions import ParamSpec

    _P = ParamSpec("_P")
    _R = TypeVar("_R")
    _RR = TypeVar("_RR")


class TwoWayFunction(NamedTuple):
    fw: Callable
    rv: Callable


class ForwardCommand:
    def __init__(
        self,
        func: Callable[_P, _R],
        callback: Callable,
    ):
        self._fw = func
        self._callback = callback

    def undo_def(self, undo: Callable[_P, _RR]) -> Command:
        return Command(self._fw, undo, self._callback)


class Command:
    def __init__(
        self,
        func: Callable[_P, _R],
        inverse_func: Callable[_P, _RR],
        callback: Callable,
    ):
        self._func = TwoWayFunction(fw=func, rv=inverse_func)
        self._callback = callback

    def __repr__(self) -> str:
        return f"{type(self).__name__}<{self._func.fw.__name__}>"

    def call_with_callback(self, *args: _P.args, **kwargs: _P.kwargs) -> _R:
        out = self.call_raw(*args, **kwargs)
        self._callback(self, *args, *kwargs)
        return out

    def call_raw(self, *args: _P.args, **kwargs: _P.kwargs) -> _R:
        return self._func.fw(*args, **kwargs)

    def revert(self, *args: _P.args, **kwargs: _P.kwargs) -> _RR:
        return self._func.rv(*args, **kwargs)

    __call__ = call_with_callback
