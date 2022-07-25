from __future__ import annotations
from abc import ABCMeta
from functools import wraps
from typing import TYPE_CHECKING, Any, cast, Callable
from ._stack import UndoManager
from ._reversible import ReversibleFunction

if TYPE_CHECKING:
    from typing_extensions import TypeGuard


class undoable_function(Callable):
    __undo_def__: Any


_UNDO_DEF = "__undo_def__"


def _is_undoable(func) -> TypeGuard[undoable_function]:
    return hasattr(func, _UNDO_DEF)


def _copy_undoable(func: undoable_function) -> undoable_function:
    @wraps(func)
    def _func(*args, **kwargs):
        return func(*args, **kwargs)

    _func = cast(undoable_function, _func)
    _func.__undo_def__ = func.__undo_def__
    return _func


def undoablemethod(func):
    """A decorator indicating undoable methods."""
    func = cast(undoable_function, func)
    func.__undo_def__ = None
    return func


def undo_def(func_fw: Callable):
    if not _is_undoable(func_fw):
        raise TypeError(f"{func_fw} is not marked as a undoable method.")

    def _undo_def(func_rv):
        _func = _copy_undoable(func_fw)
        _func.__undo_def__ = func_rv
        return _func

    return _undo_def


class UndoableABCMeta(ABCMeta):
    _mgr: UndoManager
    __abstract_undoables__: frozenset[str]

    def __new__(mcls, name, bases, namespace: dict[str, Any], /, **kwargs):

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
        cls = ABCMeta.__new__(mcls, name, bases, namespace, **kwargs)
        cls._mgr = mgr
        cls.__abstract_undoables__ = frozenset(_undo_undefined)

        return cls


class UndoableABC(metaclass=UndoableABCMeta):
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
        return self._mgr.undo()

    def redo(self):
        return self._mgr.redo()

    @property
    def undo_manager(self) -> UndoManager:
        """Return the undo manager of this object."""
        return self._mgr
