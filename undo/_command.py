from __future__ import annotations
from functools import wraps
from typing import Any, Callable, TYPE_CHECKING, Iterable, TypeVar

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

    def __hash__(self) -> int:
        return id(self)

    def __newlike__(
        self,
        func: Callable[_P, _R],
        mgr: UndoManager,
        inverse_func: Callable[_P, _RR] | None = None,
    ) -> Self:
        return type(self)(func, mgr, inverse_func)

    def __repr__(self) -> str:
        return f"{type(self).__name__}<{self.__name__}>"

    def undo_def(self, undo: Callable[_P, _RR]) -> Self:
        return self.__newlike__(
            func=self._func_fw,
            mgr=self._mgr,
            inverse_func=undo,
        )

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

    def __get__(self, obj, objtype=None) -> Self:
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

    @classmethod
    def merge(cls, cmds: Iterable[Command]) -> Self:
        """Merge multiple commands into a single command."""
        _fws = []
        _rvs = []
        _mgr = None
        for cmd in cmds:
            _fws.append(cmd._func_fw)
            _rvs.append(cmd._func_rv)
            if _mgr is not None:
                if _mgr is not cmd._mgr:
                    raise ValueError("Commands must be from the same manager.")
            else:
                _mgr = cmd._mgr

        def merged(arguments: list[tuple[tuple, dict[str, Any]]]):
            for _fw, (args, kwargs) in zip(_fws, arguments):
                out = _fw(*args, **kwargs)
            return out

        def _func_rv(arguments: list[tuple[tuple, dict[str, Any]]]):
            for _rv, (args, kwargs) in zip(reversed(_rvs), reversed(arguments)):
                out = _rv(*args, **kwargs)
            return out

        return cls(merged, _mgr, _func_rv)

    def inverted(self) -> Self:
        """Create a command with swapped forward and reverse functions."""
        return self.__newlike__(
            func=self._func_rv,
            mgr=self._mgr,
            inverse_func=self._func_fw,
        )
