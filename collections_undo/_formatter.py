from __future__ import annotations
from typing import Callable, Literal, TypeVar, overload

_T = TypeVar("_T", bound=type)


class FormatterFactory:
    def __init__(self) -> None:
        self._type_map: dict[type[_T], Callable[[_T], str]] = {}

    def _map_object(self, value: _T) -> Callable[[_T], str]:
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
            _args = list(map(self._map_object, args))
            _args += list(f"{k}={self._map_object(v)}" for k, v in kwargs.items())
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
register_type = DEFAULT_FACTORY.register_type
get_formatter = DEFAULT_FACTORY.get_formatter
