from __future__ import annotations
from functools import wraps, partial
from typing import Any, Callable, TYPE_CHECKING, Iterable, TypeVar, Generic
from collections_undo._formatter import get_formatter
from collections_undo._const import FormatterType, ReduceRuleType, Args
from typing_extensions import ParamSpec

if TYPE_CHECKING:
    from collections_undo._stack import UndoManager
    from typing_extensions import Self

_P = ParamSpec("_P")
_R = TypeVar("_R")
_RR = TypeVar("_RR")

_Fmt = TypeVar("_Fmt", bound=FormatterType)


class NotReversibleError(RuntimeError):
    """Raised when reversive operation is not defined."""


class Undefined:
    """Used when inverse function is not defined."""

    def __init__(self, name: str):
        self.__name__ = name

    def __call__(self, *args: Any, **kwargs: Any) -> Any:
        raise NotReversibleError(f"Function {self.__name__} is not reversible.")

    def __get__(self, obj, objtype=None):
        return self


def _as_method(func, obj):
    if hasattr(func, "__get__"):
        return func.__get__(obj)
    return partial(func, obj)


class ReversibleFunction(Generic[_P, _R, _RR]):
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
        self._function_id = id(func)
        wraps(func)(self)
        self._instances: dict[int, Self] = {}

        # Default argument mapping.
        self._formatter_fw: FormatterType = get_formatter(func)
        self._formatter_rv: FormatterType = self._formatter_fw

        self._map_args: Callable[[tuple, dict], Args] = _default_map_args
        self._reduce_rule: Callable[[dict, dict], tuple[tuple, dict]] | None = None

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

    def __set_name__(self, owner: type, name: str) -> None:
        self.__name__ = name

    @property
    def function_id(self) -> int:
        """Return the function ID."""
        return self._function_id

    def undo_def(self, undo: Callable[_P, _RR]) -> Self[_P, _R]:
        """Define inverse function and return a new object."""
        return self.__newlike__(
            func=self._func_fw,
            inverse_func=undo,
            mgr=self._mgr,
        )

    def set_formatter(
        self,
        formatter: _Fmt,
        /,
    ) -> _Fmt:
        """Set a formatter for the forward function."""
        if not callable(formatter):
            raise TypeError(f"{formatter!r} is not callable")
        self._formatter_fw = formatter
        return formatter

    def set_formatter_inv(
        self,
        formatter: _Fmt,
        /,
    ) -> _Fmt:
        """Set a formatter for the reverse function."""
        if not callable(formatter):
            raise TypeError(f"{formatter!r} is not callable")
        self._formatter_rv = formatter
        return formatter

    def format_forward_call(self, *args, **kwargs):
        args, kwargs = self._map_args(*args, **kwargs)
        return self._formatter_fw(*args, **kwargs)

    def format_reverse_call(self, *args, **kwargs):
        args, kwargs = self._map_args(*args, **kwargs)
        return self._formatter_rv(*args, **kwargs)

    def _call_with_callback(self, *args: _P.args, **kwargs: _P.kwargs) -> _R:
        out = self._call_raw(*args, **kwargs)
        self._mgr._append_command(self, *args, **kwargs)
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
            # get inverse function
            if self._func_rv is None:
                inv_func = None
            else:
                inv_func = self._func_rv.__get__(obj, objtype)

            # register instance
            self._instances[_id] = out = type(self)(
                func=self._func_fw.__get__(obj, objtype),
                mgr=self._mgr.__get__(obj, objtype),
                inverse_func=inv_func,
            )

            # copy name
            out.__name__ = self.__name__

            # get formatters
            if self._formatter_fw is self._formatter_rv:
                out._formatter_fw = out._formatter_rv = _as_method(
                    self._formatter_fw, obj
                )
            else:
                out._formatter_fw = _as_method(self._formatter_fw, obj)
                out._formatter_rv = _as_method(self._formatter_rv, obj)

            # copy argument mapping
            out._map_args = self._map_args

            # get reduce rule
            if self._reduce_rule is not None:
                out._reduce_rule = _as_method(self._reduce_rule, obj)
            else:
                out._reduce_rule = None
        return out

    @classmethod
    def merge(cls, rfuncs: Iterable[ReversibleFunction]) -> Self:
        """Merge multiple reversible functions into a single command."""
        _fws = []
        _rvs = []
        _mgr = None
        for rf in rfuncs:
            _fws.append(rf._func_fw)
            _rvs.append(rf._func_rv)
            if _mgr is not None:
                if _mgr is not rf._mgr:
                    raise ValueError("Commands must be from the same manager.")
            else:
                _mgr = rf._mgr

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

    def reduce_rule(self, rule: ReduceRuleType):
        self._reduce_rule = rule
        return rule


def _default_map_args(*args, **kwargs):
    """The default argument mapping."""
    return args, kwargs
