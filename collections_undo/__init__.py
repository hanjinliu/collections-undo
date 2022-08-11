__version__ = "0.0.4"

from ._stack import UndoManager
from ._const import empty
from . import abc, fmt, containers

__all__ = [
    "UndoManager",
    "empty",
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
