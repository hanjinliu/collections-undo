__version__ = "0.0.7"

from ._stack import UndoManager
from ._const import empty
from . import abc, fmt, containers

__all__ = [
    "UndoManager",
    "empty",
    "arguments",
    "AbstractUndoableDict",
    "AbstractUndoableList",
    "AbstractUndoableSet",
    "UndoableDict",
    "UndoableList",
    "UndoableSet",
    "abc",
    "containers",
    "fmt",
]


def __getattr__(name):
    cls = getattr(containers, name, None)
    if cls is None:
        raise AttributeError(f"module 'collections_undo' has no attribute '{name}'")
    import warnings

    warnings.warn(
        f"Importing {name} from 'collections_undo' is deprecated. Import it from "
        "'collections_undo.containers' instead.",
        DeprecationWarning,
    )
    return cls


def arguments(*args, **kwargs):
    """
    Function that makes returning arguments from a function easier.

    Examples
    --------
    >>> arguments(1, 2)  # returns (1, 2), {}
    >>> arguments(1, 2, a=3)  # returns (1, 2), {'a': 3}
    """
    return args, kwargs
