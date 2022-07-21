__version__ = "0.0.1"

from ._stack import UndoManager
from ._const import empty
from ._container import UndoableList, UndoableSet

__all__ = ["UndoManager", "empty", "UndoableList", "UndoableSet"]
