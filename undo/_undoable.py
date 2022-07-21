from __future__ import annotations
from functools import wraps
from typing import Any, Callable, TYPE_CHECKING, Literal, TypeVar
from ._command import Command
from ._const import empty

if TYPE_CHECKING:
    from typing_extensions import ParamSpec
    from ._stack import UndoManager

    _P = ParamSpec("_P")
    _R = TypeVar("_R")
    _Args = TypeVar("_Args", bound=tuple[tuple, dict[str, Any]])


def _dummy_func(*args, **kwargs) -> None:
    return None


class UndoableInterface:
    def __init__(
        self,
        fset: Callable[_P, _R] | None = None,
        fget: Callable[_P, _R] | None = None,
        mgr: UndoManager = None,
    ):
        if fset is None:
            fset = _dummy_func
        else:
            wraps(fset)(self)
        if fget is None:
            fget = _dummy_func
        self.fset = fset
        self.fget = fget
        self.mgr = mgr
        self._cmd = None
        self._instances: dict[int, UndoableInterface] = {}

    def descriptor(self, fget: Callable[_P, _Args]) -> Callable[_P, _Args]:
        return UndoableInterface(fget=fget, fset=self.fset, mgr=self.mgr)

    def setter(self, fset: Callable[_P, _R]) -> Callable[_P, _R]:
        return UndoableInterface(
            fget=self.fget,
            fset=fset,
            mgr=self.mgr,
        )

    @property
    def cmd(self) -> Command:
        if self._cmd is None:
            self._cmd = self._create_command()
        return self._cmd

    def __call__(self, *args: _P.args, **kwargs: _P.kwargs) -> _R:
        _old_state = self.fget(*args, **kwargs)
        out = self.fset(*args, **kwargs)
        self.mgr._append_command(self.cmd, (args, kwargs), _old_state)
        return out

    def __get__(self, obj, objtype=None) -> UndoableInterface:
        if obj is None:
            return self
        _id = id(obj)
        if (out := self._instances.get(_id, None)) is None:
            out = UndoableInterface(
                fset=self.fset.__get__(obj, objtype),
                fget=self.fget.__get__(obj, objtype),
                mgr=self.mgr.__get__(obj, objtype),
            )
            self._instances[_id] = out
        return out

    def __repr__(self) -> str:
        return f"{type(self).__name__}<{self.fset!r}>"

    def _create_command(self) -> Command:
        def fw(new, old):
            args, kwargs = new
            return self.fset(*args, **kwargs)

        def rv(new, old):
            if old is None:
                return empty
            args, kwargs = old
            return self.fset(*args, **kwargs)

        return Command(fw, self.mgr, rv)


class UndoableProperty(property):
    """A property class implemented with undo."""

    def __init__(
        self,
        fget: Callable[[Any], Any] | None = None,
        fset: Callable[[Any], Any] | None = None,
        fdel: Literal[None] = None,
        doc: str | None = None,
        *,
        parent: UndoManager = None,
    ):
        self._cmd_stack = parent
        super().__init__(fget, fset, fdel, doc)

    def getter(self, fget: Callable[[Any], Any], /) -> UndoableProperty:
        return UndoableProperty(
            fget=fget,
            fset=self.fset,
            fdel=self.fdel,
            doc=self.__doc__,
            parent=self._cmd_stack,
        )

    def setter(self, fset: Callable[[Any, Any], None], /) -> UndoableProperty:
        @self._cmd_stack.command
        def fset_cmd(obj, val, old_val):
            fset(obj, val)

        @fset_cmd.undo_def
        def fset_cmd(obj, val, old_val):
            fset(obj, old_val)

        @wraps(fset)
        def nfset(obj, val):
            old_val = self.fget(obj)
            fset_cmd.__get__(obj)(val, old_val)

        return UndoableProperty(
            fget=self.fget,
            fset=nfset,
            fdel=self.fdel,
            doc=self.__doc__,
            parent=self._cmd_stack,
        )

    def deleter(self, fdel: Callable[[Any], None], /) -> UndoableProperty:
        raise TypeError("undoable_property object does not support deleter.")
