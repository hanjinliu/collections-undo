from __future__ import annotations
from typing import Callable, TYPE_CHECKING, TypeVar

if TYPE_CHECKING:
    from typing_extensions import ParamSpec, Self
    from ._stack import CommandStack

    _P = ParamSpec("_P")
    _R = TypeVar("_R")
    _RR = TypeVar("_RR")


class ForwardCommand:
    def __init__(
        self,
        func: Callable[_P, _R],
        parent: CommandStack,
    ):
        self._fw = func
        self._parent = parent

    def undo_def(self, undo: Callable[_P, _RR]) -> Command:
        return Command(self._fw, undo, self._parent)


class Command:
    _INSTANCES: dict[int, Self] = {}

    def __init__(
        self,
        func: Callable[_P, _R],
        inverse_func: Callable[_P, _RR],
        parent: CommandStack,
    ):
        self._func_fw = func
        self._func_rv = inverse_func
        self._parent = parent

    def __repr__(self) -> str:
        return f"{type(self).__name__}<{self._func_fw.__name__}>"

    def call_with_callback(self, *args: _P.args, **kwargs: _P.kwargs) -> _R:
        out = self.call_raw(*args, **kwargs)
        self._parent._append_command(self, *args, *kwargs)
        return out

    def call_raw(self, *args: _P.args, **kwargs: _P.kwargs) -> _R:
        return self._func_fw(*args, **kwargs)

    def revert(self, *args: _P.args, **kwargs: _P.kwargs) -> _RR:
        return self._func_rv(*args, **kwargs)

    __call__ = call_with_callback

    def __get__(self, obj, objtype=None) -> Command:
        if obj is None:
            return self
        _id = id(obj)
        if (out := self._INSTANCES.get(_id, None)) is None:
            out = type(self)(
                func=self._func_fw.__get__(obj),
                inverse_func=self._func_rv.__get__(obj),
                parent=self._parent.__get__(obj),
            )
            self._INSTANCES[_id] = out
        return out
