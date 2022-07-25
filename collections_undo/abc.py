from __future__ import annotations
from abc import ABCMeta
from functools import wraps
from typing import Any, Callable, TypeVar

from ._stack import UndoManager
from ._reversible import ReversibleFunction

_F = TypeVar("_F", bound=Callable)


__all__ = ["undoablemethod", "undo_def", "UndoableABC"]


def _is_undoable(func) -> bool:
    return hasattr(func, "__undo_def__")


def _copy_undoable(func: _F) -> _F:
    @wraps(func)
    def _func(*args, **kwargs):
        return func(*args, **kwargs)

    _func.__undo_def__ = func.__undo_def__
    return _func  # type: ignore


def undoablemethod(func: _F) -> _F:
    """A decorator indicating undoable methods."""
    if not callable(func):
        raise TypeError("@undoablemethod must be called on a function.")
    func.__undo_def__ = None
    return func


def undo_def(func_fw: _F) -> Callable[[Callable], _F]:
    """Mark a function as the undo function of a already defined function."""
    if not _is_undoable(func_fw):
        raise TypeError(f"{func_fw} is not marked as a undoable method.")

    def _undo_def(func_rv: Callable):
        _func = _copy_undoable(func_fw)
        _func.__undo_def__ = func_rv
        return _func

    return _undo_def


class UndoableABCMeta(ABCMeta):
    """An ABC metaclass that adds a support for undo check."""

    _mgr: UndoManager
    __abstract_undoables__: frozenset[str]

    def __new__(cls, name, bases, namespace: dict[str, Any], /, **kwargs):

        mgr = UndoManager()
        _undoables_ns: dict[str, Any] = {}
        _undo_undefined: set[str] = set()

        for base in bases:
            if type(base) is UndoableABCMeta:
                _undo_undefined.update(base.__abstract_undoables__)

        for name, value in namespace.items():
            if _is_undoable(value):
                _undo_def = value.__undo_def__
                if _undo_def is None:
                    _undo_undefined.add(name)
                else:
                    rfunc = ReversibleFunction(
                        func=value, inverse_func=_undo_def, mgr=mgr
                    )
                    _undoables_ns[name] = rfunc
                    _undo_undefined.discard(name)

        namespace.update(_undoables_ns)
        newcls = ABCMeta.__new__(cls, name, bases, namespace, **kwargs)
        newcls._mgr = mgr
        newcls.__abstract_undoables__ = frozenset(_undo_undefined)

        return newcls


class UndoableABC(metaclass=UndoableABCMeta):
    """
    The base class for undoables.

    Using this base class in combination with ``@undoablemethod`` and ``@undo_def``
    decorators, you can define well defined undoable methods.

    Examples
    --------
    >>> class A(UndoableABC):
    >>>     @undoablemethod
    >>>     def f(self, x):
    >>>         # do something
    >>>     @undo_def(f)
    >>>     def f(self, x):
    >>>         # undo something
    """

    _mgr: UndoManager

    def __new__(cls, *args, **kwargs):
        self = super().__new__(cls)
        if cls.__abstract_undoables__:
            raise TypeError(
                "Undo functions of abstract undoables are not defined: "
                f"{set(cls.__abstract_undoables__)!r}."
            )
        return self

    def undo(self):
        """Undo last operation."""
        return self._mgr.undo()

    def redo(self):
        """Redo last undo operation."""
        return self._mgr.redo()

    @property
    def undo_manager(self) -> UndoManager:
        """Return the undo manager of this object."""
        return self._mgr
