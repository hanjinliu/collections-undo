from __future__ import annotations
from typing import TYPE_CHECKING, Callable, Type, TypeVar

if TYPE_CHECKING:
    from ._command import Command

_T = TypeVar("_T", bound=type)

_TYPE_MAPS: dict[Type[_T], Callable[[_T], str]] = {}


def generate(cmd: Command, ns: str | None = None) -> str:
    _args = [_TYPE_MAPS.get(type(arg), repr)(arg) for arg in cmd.args]
    _kwargs = [f"{k}={_TYPE_MAPS.get(type(v), repr)(v)}" for k, v in cmd.kwargs.items()]
    fname = cmd.func.__name__
    a = ", ".join(_args + _kwargs)
    expr = f"{fname}({a})"
    if ns is None:
        return expr
    return f"{ns}.{expr}"


def register_repr(cls: Type[_T], func: Callable[[_T], str]):
    def _wrapper(func) -> str:
        _TYPE_MAPS[cls] = func
        return func

    return _wrapper if func is None else _wrapper(func)
