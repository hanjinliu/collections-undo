from __future__ import annotations
from functools import wraps
from typing import Any, Callable, TYPE_CHECKING, Literal, TypeVar
from ._command import Command
from ._const import empty

if TYPE_CHECKING:
    from typing_extensions import Self, ParamSpec
    from ._stack import UndoStack

    _P = ParamSpec("_P")
    _R = TypeVar("_R")


def _default_getter(*args, **kwargs) -> None:
    return None


class undoable_setitem:
    _INSTANCES: dict[int, Self] = {}

    def __init__(
        self,
        func: Callable[_P, _R],
        getter: Callable[_P, _R] | None = None,
        parent: UndoStack = None,
    ):
        self._func = func
        if getter is None:
            getter = _default_getter
        self._getter = getter
        self._parent = parent
        self._cmd = None
        wraps(func)(self)

    def getter(self, f: Callable[_P, _R]) -> Callable[_P, _R]:
        self._getter = f
        return f

    @property
    def cmd(self) -> Command:
        if self._cmd is None:
            self._cmd = self._create_command()
        return self._cmd

    def __call__(self, *args: _P.args, **kwargs: _P.kwargs) -> _R:
        _old_state = self._getter(*args, **kwargs)
        out = self._func(*args, **kwargs)
        self._parent._append_command(self.cmd, (args, kwargs), _old_state)
        return out

    def __get__(self, obj, objtype=None) -> Self:
        if obj is None:
            return self
        _id = id(obj)
        if (out := self._INSTANCES.get(_id, None)) is None:
            out = type(self)(
                func=self._func.__get__(obj, objtype),
                getter=self._getter.__get__(obj, objtype),
                parent=self._parent.__get__(obj, objtype),
            )
            self._INSTANCES[_id] = out
        return out

    def __repr__(self) -> str:
        return f"{type(self).__name__}<{self._func!r}>"

    def _create_command(self) -> Command:
        def fw(new, old):
            args, kwargs = new
            return self._func(*args, **kwargs)

        def rv(new, old):
            if old is None:
                return empty
            args, kwargs = old
            return self._func(*args, **kwargs)

        return Command(fw, self._parent, rv)


class undoable_property(property):
    """A property class implemented with undo."""

    def __init__(
        self,
        fget: Callable[[Any], Any] | None = None,
        fset: Callable[[Any], Any] | None = None,
        fdel: Literal[None] = None,
        doc: str | None = None,
        *,
        parent: UndoStack = None,
    ):
        self._cmd_stack = parent
        super().__init__(fget, fset, fdel, doc)

    def getter(self, fget: Callable[[Any], Any], /) -> undoable_property:
        return undoable_property(
            fget=fget,
            fset=self.fset,
            fdel=self.fdel,
            doc=self.__doc__,
            parent=self._cmd_stack,
        )

    def setter(self, fset: Callable[[Any, Any], None], /) -> undoable_property:
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

        return undoable_property(
            fget=self.fget,
            fset=nfset,
            fdel=self.fdel,
            doc=self.__doc__,
            parent=self._cmd_stack,
        )

    def deleter(self, fdel: Callable[[Any], None], /) -> undoable_property:
        raise TypeError("undoable_property object does not support deleter.")
