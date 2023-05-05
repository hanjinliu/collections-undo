__version__ = "0.0.8"

from . import abc, containers, fmt
from ._const import empty
from ._stack import UndoManager, get_undo_manager
from ._undoable import is_undoable

__all__ = [
    "UndoManager",
    "get_undo_manager",
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
