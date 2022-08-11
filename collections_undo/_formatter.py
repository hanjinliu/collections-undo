from __future__ import annotations
from typing import Callable, Literal, TypeVar, overload
from types import FunctionType, BuiltinFunctionType, MethodType

_T = TypeVar("_T", bound=type)


class FormatterFactory:
    def __init__(self) -> None:
        self._type_map: dict[type[_T], Callable[[_T], str]] = {}

    def map_object(self, value: _T) -> str:
        val_type = type(value)
        f = self._type_map.get(val_type, None)
        if f is not None:
            return f(value)
        for tp, tmap in self._type_map.items():
            if isinstance(value, tp):
                self._type_map[val_type] = tmap
                return tmap
        return repr(value)

    def get_formatter(self, func: Callable):
        def _fmt(*args, **kwargs) -> str:
            _args = list(map(self.map_object, args))
            _args += list(f"{k}={self.map_object(v)}" for k, v in kwargs.items())
            _args = ", ".join(_args)
            _fn = getattr(func, "__name__", str(func))
            return f"{_fn}({_args})"

        return _fmt

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
    if _s0 is None or _s0 == 0:
        s0 = ""
    else:
        s0 = DEFAULT_FACTORY.map_object(_s0)
    if _s1 is None:
        s1 = ""
    else:
        s1 = DEFAULT_FACTORY.map_object(_s1)
    if _ss is None:
        ss = ""
    else:
        ss = DEFAULT_FACTORY.map_object(_ss)
    out = f"{s0}:{s1}:{ss}"
    if out.endswith("::"):
        return out[:-1]
    return out


def _list_str(lst: list) -> str:
    return "[" + ", ".join(map(DEFAULT_FACTORY.map_object, lst)) + "]"


def _dict_str(dct: dict) -> str:
    _keys = map(DEFAULT_FACTORY.map_object, dct.keys())
    _vals = map(DEFAULT_FACTORY.map_object, dct.values())
    return "{" + ", ".join(f"{k}: {v}" for k, v in zip(_keys, _vals)) + "}"


def _set_str(set: set) -> str:
    if len(set) == 0:
        return "set()"
    return "{" + ", ".join(map(DEFAULT_FACTORY.map_object, set)) + "}"


def _tuple_str(tpl: tuple) -> str:
    if len(tpl) == 1:
        return f"({DEFAULT_FACTORY.map_object(tpl[0])},)"
    return "(" + ", ".join(map(DEFAULT_FACTORY.map_object, tpl)) + ")"


def _frozenset_str(fset: frozenset) -> str:
    return f"frozenset({_list_str(fset)})"


DEFAULT_FACTORY.register_type(_get_name, type)
DEFAULT_FACTORY.register_type(_get_name, FunctionType)
DEFAULT_FACTORY.register_type(_get_name, BuiltinFunctionType)
DEFAULT_FACTORY.register_type(_get_name, MethodType)
DEFAULT_FACTORY.register_type(lambda e: "None", type(None))
DEFAULT_FACTORY.register_type(repr, str)
DEFAULT_FACTORY.register_type(repr, bytes)
DEFAULT_FACTORY.register_type(repr, bytearray)
DEFAULT_FACTORY.register_type(_slice_str, slice)
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
