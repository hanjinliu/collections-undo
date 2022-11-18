from __future__ import annotations
from typing import Callable, Any, Tuple, Dict


class _Empty:
    def __repr__(self) -> str:
        return "<collections_undo.empty>"

    def __str__(self) -> str:
        return "<empty>"


empty = _Empty()


FormatterType = Callable[[Callable, tuple, Dict[str, Any]], str]
Args = Tuple[Tuple[Any], Dict[str, Any]]
ReduceRuleType = Callable[[Dict[str, Any], Dict[str, Any]], Args]
