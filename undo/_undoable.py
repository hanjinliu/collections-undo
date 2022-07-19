from __future__ import annotations
from functools import wraps
from typing import Any, Callable, TYPE_CHECKING, Literal, TypeVar
from ._command import Command

if TYPE_CHECKING:
    from typing_extensions import Self, ParamSpec
    from ._stack import UndoStack

    _P = ParamSpec("_P")
    _R = TypeVar("_R")
    _S = TypeVar("_S")


class undoable_function:
    _INSTANCES: dict[int, Self] = {}

    def __init__(
        self,
        func: Callable[_P, _R],
        getter: Callable[[Any], _S] = None,
        setter: Callable[[Any, _S], None] = None,
        parent: UndoStack = None,
    ):
        self._func = func
        self._getter = getter
        if setter is None:
            setter = func
        self._setter = setter
        self._parent = parent
        self._cmd = None
        wraps(func)(self)

    @property
    def cmd(self) -> Command:
        if self._cmd is None:
            self._cmd = self._create_command()
        return self._cmd

    def __get__(self, obj, objtype=None) -> Self:
        if obj is None:
            return self
        _id = id(obj)
        if (out := self._INSTANCES.get(_id, None)) is None:
            if self._getter is None:
                getter = None
            else:
                getter = self._getter.__get__(obj, objtype)
            out = type(self)(
                func=self._func.__get__(obj, objtype),
                getter=getter,
                setter=self._setter.__get__(obj, objtype),
                parent=self._parent.__get__(obj, objtype),
            )
            self._INSTANCES[_id] = out
        return out

    def __call__(self, *args: _P.args, **kwargs: _P.kwargs) -> _R:
        old_state = self._getter()
        out = self._func(*args, **kwargs)
        _new_state = self._getter()
        self._parent._append_command(self.cmd, _new_state, old_state)
        return out

    def __repr__(self) -> str:
        return f"{type(self).__name__}<{self._func!r}>"

    def state_getter(self, f: Callable[[Any], _S]) -> Callable[[Any], _S]:
        """Set the state getter function."""
        self._getter = f
        return f

    def state_setter(self, f: Callable[[_S], None]) -> Callable[[_S], None]:
        """Set the state setter function."""
        self._setter = f
        return f

    def _create_command(self) -> Command:
        def fw(new_state, old_state):
            self._setter(new_state)

        def rv(new_state, old_state):
            self._setter(old_state)

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
