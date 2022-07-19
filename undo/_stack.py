from __future__ import annotations
from functools import wraps
from typing import Any, Callable, Iterator, NamedTuple, TYPE_CHECKING
from dataclasses import dataclass
from ._command import Command
from frozenlist import FrozenList

if TYPE_CHECKING:
    from typing_extensions import Self


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


class LengthPair(NamedTuple):
    undo: int
    redo: int


class _Empty:
    def __repr__(self) -> str:
        return "<undo.CommandStack.empty>"

    def __str__(self) -> str:
        return "<empty>"


class CommandStack:
    empty = _Empty()
    _STACK_MAP: dict[int, Self] = {}

    def __init__(self, max: int | float = float("inf")):
        self._stack_undo: list[CommandSet] = []
        self._stack_redo: list[CommandSet] = []
        self._max = max

    def __repr__(self):
        cls_name = type(self).__name__
        n_undo, n_redo = self.stack_lengths
        undo_stack = self._stack_undo
        redo_stack = self._stack_redo

        if n_undo < n_redo:
            undo_stack = undo_stack + [None] * (n_redo - n_undo)
        elif n_undo > n_redo:
            redo_stack = redo_stack + [None] * (n_undo - n_redo)

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

    def __get__(self, obj, objtype=None) -> CommandStack:
        if obj is None:
            return self
        _id = id(obj)
        if (stack := self._STACK_MAP.get(_id, None)) is None:
            stack = type(self)(max=self._max)
            self._STACK_MAP[_id] = stack
        return stack

    def undo(self) -> Any:
        """Undo last command and update undo/redo stacks."""
        if len(self._stack_undo) == 0:
            return self.empty
        cmdset = self._stack_undo.pop()
        out = cmdset.cmd._revert(*cmdset.args, **cmdset.kwargs)
        self._stack_redo.append(cmdset)
        return out

    def redo(self) -> Any:
        """Redo last command and update undo/redo stacks."""
        if len(self._stack_redo) == 0:
            return self.empty
        cmdset = self._stack_redo.pop()
        out = cmdset.cmd._call_raw(*cmdset.args, **cmdset.kwargs)
        self._stack_undo.append(cmdset)
        return out

    def repeat(self) -> Any:
        """Repeat the last command and update undo/redo stacks."""
        if len(self._stack_undo) == 0:
            return self.empty
        cmdset = self._stack_undo[-1]
        out = cmdset.cmd._call_raw(*cmdset.args, **cmdset.kwargs)
        self._stack_undo.append(cmdset)
        return out

    def run_all(self) -> Any:
        """Run all the command."""
        for cmdset in self._stack_undo:
            out = cmdset.cmd._call_raw(*cmdset.args, **cmdset.kwargs)
        self._stack_redo = list(reversed(self._stack_undo))
        return out

    def subset(self, start: int, stop: int) -> Self:
        """Create a new stack with a subset of undo stack."""
        s = self._stack_undo[start:stop]
        new = type(self)()
        new._stack_undo = s
        return new

    def _check_stack_size(self):
        if len(self._stack_undo) > self._max:
            self._stack_undo = self._stack_undo[1:]
        if len(self._redo_undo) > self._max:
            self._redo_undo = self._stack_redo[1:]

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

    def __getitem__(self, index: int) -> CommandSet:
        return self._stack_undo[index]

    def __iter__(self) -> Iterator[CommandSet]:
        return iter(self._stack_undo)

    def command(self, f: Callable) -> Command:
        """Decorator for command construction."""
        return Command(f, parent=self)

    def property(
        self,
        fget: Callable[[Any], Any] | None = None,
        fset: Callable[[Any, Any], None] | None = None,
        fdel: Callable[[Any], None] | None = None,
        doc: str | None = None,
    ) -> undoable_property:
        """Decorator for undoable property construction."""
        return undoable_property(fget, fset, fdel, doc=doc, parent=self)


class undoable_property(property):
    """A property class implemented with undo."""

    def __init__(
        self, fget=None, fset=None, fdel=None, doc=None, *, parent: CommandStack = None
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
