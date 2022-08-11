from __future__ import annotations
from typing import Callable, Any


class _Empty:
    def __repr__(self) -> str:
        return "<collections_undo.empty>"

    def __str__(self) -> str:
        return "<empty>"


empty = _Empty()


FormatterType = Callable[[Callable, tuple, dict[str, Any]], str]
