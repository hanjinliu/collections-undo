from __future__ import annotations
from typing import Any, Iterator, NamedTuple
from dataclasses import dataclass
from ._command import ForwardCommand, Command
from frozenlist import FrozenList


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
        fstr = self.cmd._func.fw.__name__
        return f"{_cmd}<{fstr}({args_str})>"


class LengthPair(NamedTuple):
    undo: int
    redo: int


class CommandStack:
    empty = object()

    def __init__(self):
        self._undo_stack: list[CommandSet] = []
        self._redo_stack: list[CommandSet] = []

    def __repr__(self):
        cls_name = type(self).__name__
        n_undo, n_redo = self.stack_lengths
        undo_stack = self._undo_stack
        redo_stack = self._redo_stack

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

    def undo(self):
        if len(self._undo_stack) == 0:
            return self.empty
        cmdset = self._undo_stack.pop()
        out = cmdset.cmd.revert(*cmdset.args, **cmdset.kwargs)
        self._redo_stack.append(cmdset)
        return out

    def redo(self) -> None:
        if len(self._redo_stack) == 0:
            return self.empty
        cmdset = self._redo_stack.pop()
        out = cmdset.cmd.call_raw(*cmdset.args, **cmdset.kwargs)
        self._undo_stack.append(cmdset)
        return out

    @property
    def undo_stack(self) -> FrozenList[CommandSet]:
        stack = FrozenList(self._undo_stack)
        stack.freeze()
        return stack

    @property
    def redo_stack(self) -> FrozenList[CommandSet]:
        stack = FrozenList(self._redo_stack)
        stack.freeze()
        return stack

    @property
    def stack_lengths(self) -> LengthPair:
        return LengthPair(undo=len(self._undo_stack), redo=len(self._redo_stack))

    def append(self, commandset: CommandSet) -> None:
        self._undo_stack.append(commandset)
        self._redo_stack.clear()
        return None

    def _append_command(self, cmd, *args, **kwargs):
        cmd_set = CommandSet(cmd=cmd, args=args, kwargs=kwargs)
        return self.append(cmd_set)

    def clear(self) -> None:
        self._undo_stack.clear()
        self._redo_stack.clear()

    def __getitem__(self, index: int) -> CommandSet:
        return self._undo_stack[index]

    def __iter__(self) -> Iterator[CommandSet]:
        return iter(self._undo_stack)

    def command(self, f) -> ForwardCommand:
        return ForwardCommand(f, callback=self._append_command)
