from __future__ import annotations

from contextlib import contextmanager
from functools import wraps
from inspect import isgeneratorfunction
from typing import (
    TYPE_CHECKING,
    Any,
    Callable,
    Generator,
    Hashable,
    Literal,
    TypeVar,
    overload,
)

from ._command import Command, _CommandBase
from ._const import empty
from ._reversible import ReversibleFunction
from ._stack_utils import CallbackList, CallType, LengthPair
from ._undoable import UndoableGenerator, UndoableInterface, UndoableProperty

if TYPE_CHECKING:
    from typing_extensions import ParamSpec, Self

    _P = ParamSpec("_P")
    _R = TypeVar("_R")
    _RR = TypeVar("_RR")

_F = TypeVar("_F", bound=Callable)


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
        self.is_merging = False
        self.is_reducing = False
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
        maxsize: float = float("inf"),
    ):
        self._instances: dict[int, Self] = {}
        if not callable(measure):
            raise TypeError("measure must be callable")
        self._state = ManagerState(measure, float(maxsize))

    def set_state(
        self,
        *,
        measure: Callable[..., float] = always_zero,
        maxsize: float = float("inf"),
    ) -> Self:
        """Set manager state."""
        if not self.empty:
            raise RuntimeError("Cannot set state while manager is not empty")
        self._state.measure = measure
        self._state.maxsize = float(maxsize)
        return self

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

    def __get__(self, obj, objtype=None) -> Self:
        if obj is None:
            return self
        return self.instance_for(obj)

    def instance_for(self, obj: Any) -> Self:
        """Get an undo manager instance for an object."""
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

    def link(self, other: Self) -> None:
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
        """Return length of undo and redo stack."""
        return LengthPair(
            undo=len(self._state.stack_undo),
            redo=len(self._state.stack_redo),
        )

    @property
    def stack_size(self) -> float:
        """Return size of undo and redo stack."""
        return self._state.stack_undo_size + self._state.stack_redo_size

    @property
    def empty(self) -> bool:
        """True if stack is empty."""
        return len(self._state.stack_undo) == 0 and len(self._state.stack_redo) == 0

    def append(self, cmd: _CommandBase) -> None:
        """Append new command to the undo stack."""
        if self.is_blocked:
            return None

        if self._state.is_reducing and len(self._state.stack_undo) > 0:
            last_cmd = self._state.stack_undo[-1]
            if isinstance(last_cmd, Command):
                new_cmd = last_cmd.reduce_with(cmd)
                popped_cmd = self._state.stack_undo.pop(-1)
                self._state.stack_undo_size -= popped_cmd.size
            else:
                new_cmd = cmd
            self._state.stack_undo.append(new_cmd)
        else:
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

    def _append_command(
        self,
        fn: ReversibleFunction[_P, Any, Any],
        *args: _P.args,
        **kwargs: _P.kwargs,
    ) -> None:
        _cmd = Command(func=fn, args=args, kwargs=kwargs)
        _cmd.size = self._state.measure(*args, **kwargs)
        return self.append(_cmd)

    def clear(self) -> None:
        """Clear the stack."""
        self._state.stack_undo.clear()
        self._state.stack_redo.clear()
        self._state.stack_undo_size = self._state.stack_redo_size = 0.0
        return None

    @overload
    def undoable(
        self, f: Callable[_P, Generator[_R, None, _RR]], name: str | None = None
    ) -> UndoableGenerator[_P, _R, _RR]:
        ...

    @overload
    def undoable(
        self, f: Callable[_P, _R], name: str | None = None
    ) -> ReversibleFunction[_P, _R, Any]:
        ...

    @overload
    def undoable(self, f: property, name: str | None = None) -> UndoableProperty:
        ...

    @overload
    def undoable(
        self,
        f: Literal[None] = None,
        name: str | None = None,
    ) -> (
        Callable[
            [Callable[_P, Generator[_R, None, _RR]]], UndoableGenerator[_P, _R, _RR]
        ]
        | Callable[[Callable[_P, _R]], ReversibleFunction[_P, _R, Any]]
        | Callable[[property], UndoableProperty]
    ):
        ...

    def undoable(self, f=None, name=None):
        """Decorator for undoable object construction."""

        def _wrapper(f):
            if isinstance(f, property):
                if name is not None:
                    import warnings

                    warnings.warn(
                        "'name' is ignored for property.",
                        UserWarning,
                        stacklevel=2,
                    )
                return UndoableProperty.from_property(f, mgr=self)
            elif isgeneratorfunction(f):
                gen = UndoableGenerator(f, mgr=self)
                if name is not None:
                    gen.__name__ = name
                return gen
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
    def interface(
        self, func: Callable[_P, _R], name: str | None = None
    ) -> UndoableInterface[_P, _R, _R]:
        ...

    @overload
    def interface(
        self,
        func: Literal[None],
        name: str | None = None,
    ) -> Callable[[Callable[_P, _R]], UndoableInterface[_P, _R, _R]]:
        ...

    def interface(self, func=None, name=None) -> UndoableInterface:
        """Decorator for undoable setter function construction."""

        def _wrapper(f):
            itf = UndoableInterface(f, mgr=self)
            if name is not None:
                itf.__name__ = name
            return itf

        return _wrapper if func is None else _wrapper(func)

    @overload
    def undoable_gen(
        self, func: Callable[_P, Generator[_R, None, _RR]], name: str | None = None
    ) -> UndoableGenerator[_P, _R, _RR]:
        ...

    @overload
    def undoable_gen(
        self, func: Literal[None], name: str | None = None
    ) -> Callable[
        [Callable[_P, Generator[_R, None, _RR]]], UndoableGenerator[_P, _R, _RR]
    ]:
        ...

    def undoable_gen(self, func=None, name=None):
        """Decorator for undoable generator construction."""

        def _wrapper(f):
            gen = UndoableGenerator(f, mgr=self)
            if name is not None:
                gen.__name__ = name
            return gen

        return _wrapper if func is None else _wrapper(func)

    def irreversible(self, f: _F) -> _F:
        """
        Mark an function as an irreversible function.

        When marked function is called, undo/redo stack gets cleared.
        """

        @wraps(f)
        def _irreversible(*args, **kwargs):
            self.clear()
            return f(*args, **kwargs)

        return _irreversible

    undef = irreversible  # backward compatible alias

    def merge_commands(
        self,
        start: int,
        stop: int,
        formatter: Callable | None = None,
        invert: bool = False,
    ) -> None:
        """Merge a command set into the undo stack."""
        cmds = self._state.stack_undo[start:stop]
        merged = Command.merge(cmds, formatter=formatter, invert=invert)
        del self._state.stack_undo[start:stop]
        self._state.stack_undo.insert(start, merged)
        return None

    @contextmanager
    def merging(
        self,
        formatter: Callable | None = None,
        invert: bool = False,
    ) -> None:
        """Merge all the commands into a single command in this context."""
        if self._state.is_merging:
            yield None
            return None

        blocked = self._state.is_blocked
        merging = self._state.is_merging
        len_before = len(self._state.stack_undo)
        self._state.is_merging = True
        try:
            yield None
        finally:
            self._state.is_merging = merging
            if not blocked and not merging:
                len_after = len(self._state.stack_undo)
                self.merge_commands(
                    len_before, len_after, formatter=formatter, invert=invert
                )
                self.called.evoke(self._state.stack_undo[-1], CallType.call)
        return None

    def set_merging(self, enabled: bool) -> None:
        """Enable/disable merging."""
        self._state.is_merging = bool(enabled)
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

    @contextmanager
    def reducing(self):
        """Enable command reduction in this context."""
        was_reducing = self._state.is_reducing
        self._state.is_reducing = True
        try:
            yield None
        finally:
            self._state.is_reducing = was_reducing
        return None

    def set_reducing(self, enabled: bool):
        """Enable/disable command reduction."""
        self._state.is_reducing = bool(enabled)
        return None


def _join_stack(stack: list, max: int = 10):
    _splitter = ",\n    "
    if len(stack) > max:
        s = _splitter.join(repr(cmd) for cmd in stack[-max:])
        return _splitter.join(["...", s])
    else:
        return _splitter.join(repr(cmd) for cmd in stack)


_GLOBAL_UNDO_MANAGERS: dict[Hashable, UndoManager] = {}


def get_undo_manager(name: Hashable) -> UndoManager:
    """
    Get a global undo manager for the given name, create if not exists.

    Global undo managers are useful for making classes with undoable
    methods without adding an undo manager as a class attribute. They
    can also be used to share the same undo/redo stack between multiple
    functions defined in different files or modules.

    Examples
    --------
    >>> mgr = get_undo_manager("myapp")
    >>> class A:
    ...     @mgr.undoable
    ...     def f(self): ...
    """
    if mgr := _GLOBAL_UNDO_MANAGERS.get(name):
        return mgr
    mgr = _GLOBAL_UNDO_MANAGERS[name] = UndoManager()
    return mgr
