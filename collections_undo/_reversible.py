from __future__ import annotations
from functools import wraps
from typing import Any, Callable, TYPE_CHECKING, Iterable, TypeVar

if TYPE_CHECKING:
    from typing_extensions import ParamSpec, Self
    from ._stack import UndoManager

    _P = ParamSpec("_P")
    _R = TypeVar("_R")
    _RR = TypeVar("_RR")
    _F = TypeVar("_F", bound=Callable)


class NotReversibleError(RuntimeError):
    """Raised when reversive operation is not defined."""


class Undefined:
    """Used when inverse function is not defined."""

    def __init__(self, name: str):
        self.__name__ = name

    def __call__(self, *args: Any, **kwargs: Any) -> Any:
        raise NotReversibleError(f"Function {self.__name__} is not reversible.")


def _fmt_arg(v: Any) -> str:
    v_repr = repr(v)
    if len(v_repr) > 18:
        v_repr = "#" + type(v).__name__ + "#"
    return v_repr


class ReversibleFunction:
    """Reversible function for undoable operations."""

    def __init__(
        self,
        func: Callable[_P, _R],
        inverse_func: Callable[_P, _RR] | None = None,
        *,
        mgr: UndoManager | None = None,
    ):
        if mgr is None:
            raise ValueError("UndoManager must be specified.")
        self._func_fw = func
        if inverse_func is None:
            inverse_func = Undefined(name=getattr(func, "__name__", str(func)))
        self._func_rv = inverse_func
        self._mgr = mgr
        self._formatter = self._default_formatter
        wraps(func)(self)
        self._instances: dict[int, Self] = {}

    def __hash__(self) -> int:
        """ReversibleFunction is immutable in public level so use id for hashing."""
        return id(self)

    def __newlike__(
        self,
        func: Callable[_P, _R],
        inverse_func: Callable[_P, _RR] | None = None,
        mgr: UndoManager | None = None,
    ) -> Self:
        """Constructor."""
        return type(self)(func=func, mgr=mgr, inverse_func=inverse_func)

    def __repr__(self) -> str:
        return f"{type(self).__name__}<{self.__name__}>"

    def undo_def(self, undo: Callable[_P, _RR]) -> Self:
        """Define inverse function and return a new object."""
        return self.__newlike__(
            func=self._func_fw,
            inverse_func=undo,
            mgr=self._mgr,
        )

    def set_formatter(self, formatter: _F) -> _F:
        """Set a custom formatter function."""
        if not callable(formatter):
            raise TypeError("Can only set a callable as a formatter.")
        self._formatter = formatter

    def format_forward_call(self, *args, **kwargs):
        return self._formatter(self._func_fw, *args, **kwargs)

    def format_reverse_call(self, *args, **kwargs):
        return self._formatter(self._func_rv, *args, **kwargs)

    def _call_with_callback(self, *args: _P.args, **kwargs: _P.kwargs) -> _R:
        out = self._call_raw(*args, **kwargs)
        self._mgr._append_command(self, *args, *kwargs)
        return out

    def _call_raw(self, *args: _P.args, **kwargs: _P.kwargs) -> _R:
        with self._mgr.blocked(), self._mgr.catch_errors():
            return self._func_fw(*args, **kwargs)

    def _revert(self, *args: _P.args, **kwargs: _P.kwargs) -> _RR:
        with self._mgr.blocked(), self._mgr.catch_errors():
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
            self._instances[_id] = out = type(self)(
                func=self._func_fw.__get__(obj, objtype),
                mgr=self._mgr.__get__(obj, objtype),
                inverse_func=inv_func,
            )
        return out

    @classmethod
    def merge(cls, cmds: Iterable[ReversibleFunction]) -> Self:
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

        return cls(merged, _func_rv, mgr=_mgr)

    def inverted(self) -> Self:
        """Create a command with swapped forward and reverse functions."""
        return self.__newlike__(
            func=self._func_rv,
            inverse_func=self._func_fw,
            mgr=self._mgr,
        )

    @staticmethod
    def _default_formatter(func: Callable, *args, **kwargs) -> str:
        _args = list(map(_fmt_arg, args))
        _args += list(f"{k}={_fmt_arg(v)}" for k, v in kwargs.items())
        _args = ", ".join(_args)
        _fn = getattr(func, "__name__", str(func))
        return f"{_fn}({_args})"
