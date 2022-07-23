from __future__ import annotations
from contextlib import contextmanager
from typing import (
    Any,
    Callable,
    Iterable,
    Literal,
    NamedTuple,
    TYPE_CHECKING,
    TypeVar,
    overload,
)
from dataclasses import dataclass
from functools import wraps

from ._command import ReversibleFunction
from ._undoable import UndoableInterface, UndoableProperty
from ._const import empty

if TYPE_CHECKING:
    from typing_extensions import Self

_F = TypeVar("_F", bound=Callable)


def _fmt_arg(v: Any) -> str:
    v_repr = repr(v)
    if len(v_repr) > 14:
        v_repr = "#" + type(v).__name__ + "#"
    return v_repr


def _deprecated_function(func, name: str):
    @wraps(func)
    def _wrapper(*args, **kwargs):
        import warnings

        warnings.warn(
            f"{name} is deprecated, use {func.__name__} instead",
            DeprecationWarning,
        )
        return func(*args, **kwargs)

    return _wrapper


@dataclass(repr=False)
class Command:
    func: ReversibleFunction
    args: tuple[Any, ...]
    kwargs: dict[str, Any]
    size: float = 0.0

    def __repr__(self) -> str:
        _fn_cls = type(self.func).__name__
        _args = list(map(_fmt_arg, self.args))
        _args += list(f"{k}={_fmt_arg(v)}" for k, v in self.kwargs.items())
        _args = ", ".join(_args)
        _fn = self.func.__name__
        return f"{_fn_cls}<{_fn}({_args})>"

    def _call_with_callback(self):
        return self.func._call_with_callback(*self.args, **self.kwargs)

    def _call_raw(self):
        return self.func._call_raw(*self.args, **self.kwargs)

    def _revert(self):
        return self.func._revert(*self.args, **self.kwargs)

    @classmethod
    def merge(cls, cmds: Iterable[Command]) -> Command:
        """
        Merge multiple commands into one.

        This method is used to reduce command set stack by merging simple operations.
        For instance, if you defined a undoable "append" method and intend to define
        "extend" method by repeating "append" operation, a lot of "append" command
        will be generated. To avoid this, you can use this method to merge "append".

        Parameters
        ----------
        cmds : Iterable[CommandSet]
            List of command sets to merge.

        Returns
        -------
        CommandSet
            Merged command set.
        """
        arguments: list[tuple, dict[str, Any]] = []
        commands: list[ReversibleFunction] = []
        total_size = 0.0

        for cmd in cmds:
            commands.append(cmd.func)
            arguments.append((cmd.args, cmd.kwargs))
            total_size += cmd.size

        cmd_merged = ReversibleFunction.merge(commands)

        return cls(cmd_merged, (arguments,), {}, size=total_size)


class LengthPair(NamedTuple):
    """Pair of stack size."""

    undo: int
    redo: int


def always_zero(*args, **kwargs) -> float:
    return 0.0


class UndoManager:
    def __init__(
        self,
        *,
        measure: Callable[..., float] = always_zero,
        maxsize: float | Literal["inf"] = "inf",
    ):
        self._stack_undo: list[Command] = []
        self._stack_redo: list[Command] = []
        self._instances: dict[int, Self] = {}
        if not callable(measure):
            raise TypeError("measure must be callable")
        self._measure = measure
        self._maxsize = float(maxsize)
        self._stack_undo_size = 0.0
        self._stack_redo_size = 0.0

    def __repr__(self):
        cls_name = type(self).__name__
        n_undo, n_redo = self.stack_lengths
        undo_stack = list(self._stack_undo)
        redo_stack = list(self._stack_redo)

        if n_undo < n_redo:
            undo_stack = [None] * (n_redo - n_undo) + undo_stack
        elif n_undo > n_redo:
            redo_stack = [None] * (n_undo - n_redo) + redo_stack

        s: list[tuple[str, str]] = []
        nchar_max = 0
        _null = " --- "
        for undo, redo in zip(undo_stack, redo_stack):
            _undo = _null if undo is None else repr(undo)
            _redo = _null if redo is None else repr(redo)
            s.append((_undo, _redo))
            nchar_max = max(nchar_max, len(_undo))

        s = "\n".join(f"{s0:>{nchar_max + 2}}, {s1}" for s0, s1 in s)
        return cls_name + f"[\n{s}\n]"

    def __get__(self, obj, objtype=None) -> UndoManager:
        if obj is None:
            return self
        _id = id(obj)
        if (stack := self._instances.get(_id, None)) is None:
            stack = type(self)()
            self._instances[_id] = stack
        return stack

    def undo(self) -> Any:
        """Undo last command and update undo/redo stacks."""
        if len(self._stack_undo) == 0:
            return empty
        cmd = self._stack_undo.pop()
        out = cmd._revert()
        self._stack_redo.append(cmd)

        # update size
        self._stack_undo_size -= cmd.size
        self._stack_redo_size += cmd.size
        return out

    def redo(self) -> Any:
        """Redo last command and update undo/redo stacks."""
        if len(self._stack_redo) == 0:
            return empty
        cmd = self._stack_redo.pop()
        out = cmd._call_raw()
        self._stack_undo.append(cmd)

        # update size
        self._stack_undo_size += cmd.size
        self._stack_redo_size -= cmd.size
        return out

    # def run_all(self) -> Any:
    #     """Run all the command."""
    #     for cmd in self._stack_undo:
    #         out = cmd.func._call_raw(*cmd.args, **cmd.kwargs)
    #     self._stack_redo = self._stack_undo.copy()
    #     self._stack_redo.reverse()
    #     return out

    @property
    def stack_undo(self) -> list[Command]:
        """List of undo stack."""
        return list(self._stack_undo)

    @property
    def stack_redo(self) -> list[Command]:
        """List of redo stack."""
        return list(self._stack_redo)

    @property
    def stack_lengths(self) -> LengthPair:
        """Return length of undo and redo stack"""
        return LengthPair(undo=len(self._stack_undo), redo=len(self._stack_redo))

    @property
    def stack_size(self) -> float:
        """Return size of undo and redo stack"""
        return self._stack_undo_size + self._stack_redo_size

    def append(self, cmd: Command) -> None:
        self._stack_undo.append(cmd)
        self._stack_redo.clear()

        # update size
        self._stack_undo_size += cmd.size
        self._stack_redo_size = 0.0

        # pop items until size is less than maxsize
        while self._stack_undo_size > self._maxsize:
            cmd = self._stack_undo.pop(0)
            self._stack_undo_size -= cmd.size
        return None

    def _append_command(self, cmd, *args, **kwargs):
        cmd = Command(func=cmd, args=args, kwargs=kwargs)
        cmd.size = self._measure(*args, **kwargs)
        return self.append(cmd)

    def clear(self) -> None:
        """Clear the stack."""
        self._stack_undo.clear()
        self._stack_redo.clear()
        self._stack_undo_size = self._stack_redo_size = 0.0

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

    command = _deprecated_function(undoable, "undoable")

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
    def interface(self, f: Callable, name: str | None = None) -> UndoableInterface:
        ...

    @overload
    def interface(
        self,
        f: Literal[None],
        name: str | None = None,
    ) -> Callable[[Callable], UndoableInterface]:
        ...

    def interface(
        self,
        f: Callable | None = None,
        name: str | None = None,
    ) -> UndoableInterface:
        """Decorator for undoable setter function construction."""

        def _wrapper(f):
            itf = UndoableInterface(f, mgr=self)
            if name is not None:
                itf.__name__ = name
            return itf

        return _wrapper if f is None else _wrapper(f)

    def undef(self, undef: _F) -> _F:
        """Mark an function as an undo-undefined function."""

        @wraps(undef)
        def _undef(*args, **kwargs):
            self.clear()
            return undef(*args, **kwargs)

        return _undef

    def merge_commands(self, start: int, stop: int) -> None:
        """Merge a command set into the undo stack."""
        merged = Command.merge(self._stack_undo[start:stop])
        del self._stack_undo[start:stop]
        self._stack_undo.insert(start, merged)
        return None

    @contextmanager
    def merging(self) -> None:
        """Merge all the commands into a single command in this context."""
        len_before = len(self._stack_undo)
        yield None
        len_after = len(self._stack_undo)
        self.merge_commands(len_before, len_after)
        return None
