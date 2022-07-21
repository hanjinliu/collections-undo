from __future__ import annotations
from collections import deque
from typing import Any, Callable, NamedTuple, TYPE_CHECKING, TypeVar
from dataclasses import dataclass
from functools import wraps
from frozenlist import FrozenList

from ._command import Command
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


@dataclass(repr=False)
class CommandSet:
    cmd: Command
    args: tuple[Any]
    kwargs: dict[str, Any]

    def __repr__(self) -> str:
        _cmd = type(self.cmd).__name__
        _args = list(map(_fmt_arg, self.args))
        _args += list(f"{k}={_fmt_arg(v)}" for k, v in self.kwargs.items())
        args_str = ", ".join(_args)
        fstr = self.cmd._func_fw.__name__
        return f"{_cmd}<{fstr}({args_str})>"

    def copy(self) -> Self:
        return type(self)(self.cmd, self.args, self.kwargs)

    def _call_with_callback(self):
        return self.cmd._call_with_callback(*self.args, **self.kwargs)

    def _call_raw(self):
        return self.cmd._call_raw(*self.args, **self.kwargs)


class LengthPair(NamedTuple):
    """Pair of stack size."""

    undo: int
    redo: int


class UndoManager:
    def __init__(self, max: int | None = None):
        self._stack_undo: deque[CommandSet] = deque(maxlen=max)
        self._stack_redo: deque[CommandSet] = deque(maxlen=max)
        self._max = max
        self._instances: dict[int, Self] = {}

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
            stack = type(self)(max=self._max)
            self._instances[_id] = stack
        return stack

    def undo(self) -> Any:
        """Undo last command and update undo/redo stacks."""
        if len(self._stack_undo) == 0:
            return empty
        cmdset = self._stack_undo.pop()
        out = cmdset.cmd._revert(*cmdset.args, **cmdset.kwargs)
        self._stack_redo.append(cmdset)
        return out

    def redo(self) -> Any:
        """Redo last command and update undo/redo stacks."""
        if len(self._stack_redo) == 0:
            return empty
        cmdset = self._stack_redo.pop()
        out = cmdset.cmd._call_raw(*cmdset.args, **cmdset.kwargs)
        self._stack_undo.append(cmdset)
        return out

    def repeat(self) -> Any:
        """Repeat the last command and update undo/redo stacks."""
        # BUG: incompatible with undoable interface
        if len(self._stack_undo) == 0:
            return empty
        cmdset = self._stack_undo[-1]
        return cmdset._call_with_callback()

    def run_all(self) -> Any:
        """Run all the command."""
        for cmdset in self._stack_undo:
            out = cmdset.cmd._call_raw(*cmdset.args, **cmdset.kwargs)
        self._stack_redo = self._stack_undo.copy()
        self._stack_redo.reverse()
        return out

    def subset(self, start: int, stop: int) -> Self:
        """Create a new stack with a subset of undo stack."""
        s = self._stack_undo[start:stop]
        new = type(self)()
        new._stack_undo = s
        return new

    @property
    def stack_undo(self) -> FrozenList[CommandSet]:
        """Frozen list of undo stack."""
        stack = FrozenList(self._stack_undo)
        stack.freeze()
        return stack

    @property
    def stack_redo(self) -> FrozenList[CommandSet]:
        """Frozen list of redo stack."""
        stack = FrozenList(self._stack_redo)
        stack.freeze()
        return stack

    @property
    def stack_lengths(self) -> LengthPair:
        """Return length of undo and redo stack"""
        return LengthPair(undo=len(self._stack_undo), redo=len(self._stack_redo))

    def append(self, cmdset: CommandSet) -> None:
        self._stack_undo.append(cmdset)
        self._stack_redo.clear()
        return None

    def _append_command(self, cmd, *args, **kwargs):
        cmdset = CommandSet(cmd=cmd, args=args, kwargs=kwargs)
        return self.append(cmdset)

    def clear(self) -> None:
        """Clear the stack."""
        self._stack_undo.clear()
        self._stack_redo.clear()

    def command(self, f: Callable) -> Command:
        """Decorator for command construction."""
        return Command(f, mgr=self)

    def property(
        self,
        fget: Callable[[Any], Any] | None = None,
        fset: Callable[[Any, Any], None] | None = None,
        fdel: Callable[[Any], None] | None = None,
        doc: str | None = None,
    ) -> UndoableProperty:
        """Decorator for undoable property construction."""
        return UndoableProperty(fget, fset, fdel, doc=doc, parent=self)

    def interface(self, f: Callable) -> UndoableInterface:
        """Decorator for undoable setter function construction."""
        return UndoableInterface(f, mgr=self)

    def undef(self, undef: _F) -> _F:
        """Mark an function as an undo-undefined function."""

        @wraps(undef)
        def _undef(*args, **kwargs):
            self.clear()
            return undef(*args, **kwargs)

        return _undef
