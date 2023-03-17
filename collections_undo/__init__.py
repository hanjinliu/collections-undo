__version__ = "0.0.8"

from ._stack import UndoManager
from ._const import empty
from ._undoable import is_undoable
from . import abc, fmt, containers

__all__ = [
    "UndoManager",
    "is_undoable",
    "empty",
    "arguments",
    "abc",
    "containers",
    "fmt",
]


def arguments(*args, **kwargs):
    """
    Function that makes returning arguments from a function easier.

    Examples
    --------
    >>> arguments(1, 2)  # returns (1, 2), {}
    >>> arguments(1, 2, a=3)  # returns (1, 2), {'a': 3}
    """
    return args, kwargs
