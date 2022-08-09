from __future__ import annotations
from contextlib import contextmanager
from enum import Enum
from typing import (
    Any,
    Callable,
    Iterator,
    Literal,
    MutableSequence,
    NamedTuple,
    TYPE_CHECKING,
    TypeVar,
    overload,
)
from functools import wraps

from ._reversible import ReversibleFunction
from ._undoable import UndoableInterface, UndoableProperty
from ._command import Command, _CommandBase
from ._const import empty

if TYPE_CHECKING:
    from typing_extensions import Self

_F = TypeVar("_F", bound=Callable)


class CallbackList(MutableSequence[_F]):
    """
    A list of callbacks of UndoManager updates.

    Callbacks are useful for such as logging.
    """

    def __init__(self) -> None:
        self._list = []

    def insert(self, index: int, callback: _F, /):
        self._check_callable(callback)
        self._list.insert(index, callback)

    def __repr__(self) -> str:
        return f"{type(self).__name__}({self._list!r})"

    def __len__(self) -> int:
        return len(self._list)

    def __iter__(self) -> Iterator[_F]:
        return iter(self._list)

    def __getitem__(self, key):
        return self._list[key]

    def __setitem__(self, key, callback):
        self._check_callable(callback)
        self._list[key] = callback

    def __delitem__(self, key):
        del self._list[key]

    def evoke(self, *args, **kwargs) -> None:
        """Evoce all callbacks."""
        for callback in self._list:
            callback(*args, **kwargs)
        return None

    @staticmethod
    def _check_callable(obj):
        if not callable(obj):
            raise TypeError("Can only insert callable object to the callback list.")


class CallType(Enum):
    call = "call"
    undo = "undo"
    redo = "redo"

    def __eq__(self, other):
        if isinstance(other, str):
            return self.value == other
        return super().__eq__(other)


class LengthPair(NamedTuple):
    """Pair of stack size."""

    undo: int
    redo: int


def always_zero(*args, **kwargs) -> float:
    """Default command size counter."""
    return 0.0


class ManagerState:
    def __init__(
        self,
        measure: Callable[..., float],
        maxsize: float,
    ) -> None:
        self.measure = measure
        self.maxsize = maxsize
        self.is_blocked = False
        self.stack_undo: list[_CommandBase] = []
        self.stack_redo: list[_CommandBase] = []
        self.stack_undo_size = 0.0
        self.stack_redo_size = 0.0
        self.called_callbacks: CallbackList[
            Callable[[_CommandBase, CallType], Any]
        ] = CallbackList()
        self.errored_callbacks: CallbackList[
            Callable[[_CommandBase, Exception], Any]
        ] = CallbackList()


class UndoManager:
    def __init__(
        self,
        *,
        measure: Callable[..., float] = always_zero,
        maxsize: float | Literal["inf"] = "inf",
    ):
        self._instances: dict[int, Self] = {}
        if not callable(measure):
            raise TypeError("measure must be callable")
        self._state = ManagerState(measure, float(maxsize))

    def __repr__(self) -> str:
        cls_name = type(self).__name__
        s_undo = _join_stack(self._state.stack_undo)
        s_redo = _join_stack(self._state.stack_redo)
        if s_undo:
            s_undo = f"[\n    {s_undo}\n  ]"
        else:
            s_undo = "[]"
        if s_redo:
            s_redo = f"[\n    {s_redo}\n  ]"
        else:
            s_redo = "[]"
        return f"{cls_name}(\n  undo={s_undo},\n  redo={s_redo}\n)"

    def __get__(self, obj, objtype=None) -> UndoManager:
        if obj is None:
            return self
        _id = id(obj)
        if (stack := self._instances.get(_id, None)) is None:
            self._instances[_id] = stack = type(self)()
        return stack

    @property
    def is_blocked(self) -> bool:
        """True if manager is blocked."""
        return self._state.is_blocked

    @property
    def called(self) -> CallbackList[Callable[[_CommandBase, CallType], Any]]:
        """Callback list for called events."""
        return self._state.called_callbacks

    @property
    def errored(self) -> CallbackList[Callable[[_CommandBase, Exception], Any]]:
        """Callback list for errored events."""
        return self._state.errored_callbacks

    def undo(self) -> Any:
        """Undo last command and update undo/redo stacks."""
        if len(self._state.stack_undo) == 0:
            return empty
        cmd = self._state.stack_undo.pop()
        out = cmd._revert()
        self._state.stack_redo.append(cmd)

        # update size
        self._state.stack_undo_size -= cmd.size
        self._state.stack_redo_size += cmd.size
        self.called.evoke(cmd, CallType.undo)
        return out

    def redo(self) -> Any:
        """Redo last command and update undo/redo stacks."""
        if len(self._state.stack_redo) == 0:
            return empty
        cmd = self._state.stack_redo.pop()
        out = cmd._call_raw()
        self._state.stack_undo.append(cmd)

        # update size
        self._state.stack_undo_size += cmd.size
        self._state.stack_redo_size -= cmd.size
        self.called.evoke(cmd, CallType.redo)
        return out

    def link(self, other: UndoManager) -> None:
        if not isinstance(other, UndoManager):
            raise TypeError(f"Cannot link {other!r}.")
        if self.empty:
            self._state = other._state
        elif other.empty:
            other.link(self)
        else:
            raise ValueError("Either UndoManager must be empty.")
        return None

    # def run_all(self) -> Any:
    #     """Run all the command."""
    #     for cmd in self._state.stack_undo:
    #         out = cmd.func._call_raw(*cmd.args, **cmd.kwargs)
    #     self._state.stack_redo = self._state.stack_undo.copy()
    #     self._state.stack_redo.reverse()
    #     return out

    @property
    def stack_undo(self) -> list[_CommandBase]:
        """List of undo stack."""
        return list(self._state.stack_undo)

    @property
    def stack_redo(self) -> list[_CommandBase]:
        """List of redo stack."""
        return list(self._state.stack_redo)

    @property
    def stack_lengths(self) -> LengthPair:
        """Return length of undo and redo stack"""
        return LengthPair(
            undo=len(self._state.stack_undo),
            redo=len(self._state.stack_redo),
        )

    @property
    def stack_size(self) -> float:
        """Return size of undo and redo stack"""
        return self._state.stack_undo_size + self._state.stack_redo_size

    @property
    def empty(self) -> bool:
        """True if stack is empty."""
        return len(self._state.stack_undo) == 0 and len(self._state.stack_redo) == 0

    def append(self, cmd: _CommandBase) -> None:
        """Append new command to the undo stack."""
        if self.is_blocked:
            return None

        self._state.stack_undo.append(cmd)
        self._state.stack_redo.clear()
        self.called.evoke(cmd, CallType.call)

        # update size
        self._state.stack_undo_size += cmd.size
        self._state.stack_redo_size = 0.0

        # pop items until size is less than maxsize
        while self._state.stack_undo_size > self._state.maxsize:
            cmd = self._state.stack_undo.pop(0)
            self._state.stack_undo_size -= cmd.size
        return None

    def _append_command(self, cmd, *args, **kwargs):
        cmd = Command(func=cmd, args=args, kwargs=kwargs)
        cmd.size = self._state.measure(*args, **kwargs)
        return self.append(cmd)

    def clear(self) -> None:
        """Clear the stack."""
        self._state.stack_undo.clear()
        self._state.stack_redo.clear()
        self._state.stack_undo_size = self._state.stack_redo_size = 0.0
        return None

    @overload
    def undoable(self, f: Callable, name: str | None = None) -> ReversibleFunction:
        ...

    @overload
    def undoable(self, f: property, name: str | None = None) -> UndoableProperty:
        ...

    @overload
    def undoable(
        self,
        f: Literal[None],
        name: str | None = None,
    ) -> Callable[[Callable], ReversibleFunction] | Callable[
        [property], UndoableProperty
    ]:
        ...

    def undoable(self, f=None, name=None):
        """Decorator for undoable object construction."""

        def _wrapper(f):
            if isinstance(f, property):
                return UndoableProperty.from_property(f, mgr=self)
            fn = ReversibleFunction(f, mgr=self)
            if name is not None:
                fn.__name__ = name
            return fn

        return _wrapper if f is None else _wrapper(f)

    def property(
        self,
        fget: Callable[[Any], Any] | None = None,
        fset: Callable[[Any, Any], None] | None = None,
        fdel: Callable[[Any], None] | None = None,
        doc: str | None = None,
    ) -> UndoableProperty:
        """Decorator for undoable property construction."""
        return UndoableProperty(fget, fset, fdel, doc=doc, mgr=self)

    @overload
    def interface(self, func: Callable, name: str | None = None) -> UndoableInterface:
        ...

    @overload
    def interface(
        self,
        func: Literal[None],
        name: str | None = None,
    ) -> Callable[[Callable], UndoableInterface]:
        ...

    def interface(
        self,
        func: Callable | None = None,
        name: str | None = None,
    ) -> UndoableInterface:
        """Decorator for undoable setter function construction."""

        def _wrapper(f):
            itf = UndoableInterface(f, mgr=self)
            if name is not None:
                itf.__name__ = name
            return itf

        return _wrapper if func is None else _wrapper(func)

    def undef(self, undef: _F) -> _F:
        """
        Mark an function as an undo-undefined function.

        When marked function is called, undo/redo stack get cleared.
        """

        @wraps(undef)
        def _undef(*args, **kwargs):
            self.clear()
            return undef(*args, **kwargs)

        return _undef

    def merge_commands(
        self, start: int, stop: int, formatter: Callable | None = None
    ) -> None:
        """Merge a command set into the undo stack."""
        merged = Command.merge(self._state.stack_undo[start:stop], formatter=formatter)
        del self._state.stack_undo[start:stop]
        self._state.stack_undo.insert(start, merged)
        return None

    @contextmanager
    def merging(self, formatter: Callable | None = None) -> None:
        """Merge all the commands into a single command in this context."""
        len_before = len(self._state.stack_undo)
        yield None
        len_after = len(self._state.stack_undo)
        self.merge_commands(len_before, len_after, formatter=formatter)
        return None

    @contextmanager
    def blocked(self):
        """Block new command from being appended to the stack."""
        blocked = self._state.is_blocked
        self._state.is_blocked = True
        try:
            yield None
        finally:
            self._state.is_blocked = blocked
        return None

    @contextmanager
    def catch_errors(self):
        """Catch all the errors in this context and evoke callbacks."""
        try:
            yield None
        except Exception as e:
            self.errored.evoke(e)
            raise e


def _join_stack(stack: list, max: int = 10):
    _splitter = ",\n    "
    if len(stack) > max:
        s = _splitter.join(repr(cmd) for cmd in stack[-max:])
        return _splitter.join(["...", s])
    else:
        return _splitter.join(repr(cmd) for cmd in stack)
