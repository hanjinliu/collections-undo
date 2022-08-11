from __future__ import annotations
from typing import Callable, Literal, TypeVar, overload
from types import FunctionType, BuiltinFunctionType, MethodType
import weakref

_T = TypeVar("_T", bound=type)


class DefaultFormatter:
    def __init__(self, func, factory: FormatterFactory):
        self._func = func
        self._factory = weakref.ref(factory)

    def __get__(self, obj, objtype=None):
        if obj is None:
            return self
        return self.__class__(self._func.__get__(obj), self._factory())

    def __call__(self, *args, **kwargs) -> str:
        _map = self._factory().map_object
        _args = list(map(_map, args))
        _args += list(f"{k}={_map(v)}" for k, v in kwargs.items())
        _args = ", ".join(_args)
        _fn = getattr(self._func, "__name__", str(self._func))
        return f"{_fn}({_args})"


class FormatterFactory:
    def __init__(self) -> None:
        self._type_map: dict[type[_T], Callable[[_T], str]] = {}

    def map_object(self, value: _T) -> str:
        """Map object to string."""
        val_type = type(value)
        f = self._type_map.get(val_type, None)
        if f is not None:
            return f(value)
        for tp, tmap in self._type_map.items():
            if isinstance(value, tp):
                self._type_map[val_type] = tmap
                return tmap(value)
        return repr(value)

    def get_formatter(self, func: Callable):
        return DefaultFormatter(func, self)

    @overload
    def register_type(
        self,
        formatter: Callable[[_T], str],
        type: type[_T],
        *,
        overwrite: bool = False,
    ) -> Callable[[_T], str]:
        ...

    @overload
    def register_type(
        self,
        formatter: Callable[[_T], str],
        type: Literal[None],
        *,
        overwrite: bool = False,
    ) -> Callable[[type[_T]], Callable[[_T], str]]:
        ...

    def register_type(
        self,
        formatter,
        type=None,
        *,
        overwrite: bool = False,
    ) -> Callable[[_T], str]:
        def _register(tp: type[_T]) -> Callable[[_T], str]:
            if type in self._type_map and not overwrite:
                raise ValueError(f"Type {type} is already registered.")
            elif not callable(formatter):
                raise ValueError(f"Formatter {formatter} is not callable.")
            self._type_map[type] = formatter
            return formatter

        return _register if type is None else _register(type)


DEFAULT_FACTORY = FormatterFactory()

# default type map
def _get_name(e):
    return e.__name__


def _slice_str(sl: slice) -> str:
    _s0, _s1, _ss = sl.start, sl.stop, sl.step
    tpname = type(sl).__name__
    if _ss is None:
        if _s0 is None:
            return f"{tpname}({map_object(_s1)})"
        return f"{tpname}({map_object(_s0)}, {map_object(_s1)})"
    return f"{tpname}({map_object(_s0)}, {map_object(_s1)}, {map_object(_ss)})"


def _range_str(sl: range) -> str:
    _s0, _s1, _ss = sl.start, sl.stop, sl.step
    tpname = type(sl).__name__
    if _ss == 1:
        if _s0 == 0:
            return f"{tpname}({map_object(_s1)})"
        return f"{tpname}({map_object(_s0)}, {map_object(_s1)})"
    return f"{tpname}({map_object(_s0)}, {map_object(_s1)}, {map_object(_ss)})"


def _list_str(lst: list) -> str:
    tp = type(lst)
    if tp is list:
        return "[" + ", ".join(map(map_object, lst)) + "]"
    return f"{tp.__name__}([" + ", ".join(map(map_object, lst)) + "])"


def _dict_str(dct: dict) -> str:
    _keys = map(map_object, dct.keys())
    _vals = map(map_object, dct.values())
    tp = type(dct)
    if tp is dict:
        return "{" + ", ".join(f"{k}: {v}" for k, v in zip(_keys, _vals)) + "}"
    return (
        f"{tp.__name__}({{"
        + ", ".join(f"{k}: {v}" for k, v in zip(_keys, _vals))
        + "})"
    )


def _set_str(s: set) -> str:
    tp = type(s)
    if len(s) == 0:
        return f"{tp.__name__}()"
    if tp is set:
        return "{" + ", ".join(map(map_object, s)) + "}"
    return f"{tp.__name__}([" + ", ".join(map(map_object, s)) + "])"


def _tuple_str(tpl: tuple) -> str:
    tp = type(tpl)
    if tp is tuple:
        if len(tpl) == 1:
            return f"({map_object(tpl[0])},)"
        return "(" + ", ".join(map(map_object, tpl)) + ")"
    return f"{tp.__name__}([" + ", ".join(map(map_object, tpl)) + "])"


def _frozenset_str(fset: frozenset) -> str:
    s = "[" + ", ".join(map(map_object, fset)) + "]"
    return f"frozenset({s})"


DEFAULT_FACTORY.register_type(_get_name, type)
DEFAULT_FACTORY.register_type(_get_name, FunctionType)
DEFAULT_FACTORY.register_type(_get_name, BuiltinFunctionType)
DEFAULT_FACTORY.register_type(_get_name, MethodType)
DEFAULT_FACTORY.register_type(lambda e: "None", type(None))
DEFAULT_FACTORY.register_type(repr, str)
DEFAULT_FACTORY.register_type(repr, bytes)
DEFAULT_FACTORY.register_type(repr, bytearray)
DEFAULT_FACTORY.register_type(_slice_str, slice)
DEFAULT_FACTORY.register_type(_range_str, range)
DEFAULT_FACTORY.register_type(str, int)
DEFAULT_FACTORY.register_type(str, float)
DEFAULT_FACTORY.register_type(str, complex)
DEFAULT_FACTORY.register_type(str, bool)
DEFAULT_FACTORY.register_type(_list_str, list)
DEFAULT_FACTORY.register_type(_set_str, set)
DEFAULT_FACTORY.register_type(_dict_str, dict)
DEFAULT_FACTORY.register_type(_tuple_str, tuple)
DEFAULT_FACTORY.register_type(_frozenset_str, frozenset)


register_type = DEFAULT_FACTORY.register_type
get_formatter = DEFAULT_FACTORY.get_formatter
map_object = DEFAULT_FACTORY.map_object
