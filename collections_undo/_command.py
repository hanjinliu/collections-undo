from __future__ import annotations
from abc import ABC, abstractmethod, abstractproperty
from typing import Any, Callable, Iterable, Iterator, Union
from dataclasses import dataclass

from ._reversible import ReversibleFunction

FormatterType = Union[Callable[["Command"], str], str]


class _CommandBase(ABC):
    @abstractmethod
    def _call_with_callback(self):
        """Call the command and call the callback if it is defined."""

    @abstractmethod
    def _call_raw(self):
        """Call the command without calling the callback."""

    @abstractmethod
    def _revert(self):
        """Revert the command."""

    @abstractproperty
    def size(self) -> str:
        """The size of the command."""


@dataclass(repr=False)
class Command(_CommandBase):
    """
    Undoable command object.

    A command is a function call with arguments and keyword arguments.

    Parameters
    ----------
    func : callable
        The reversible function.
    args : tuple
        The positional arguments.
    kwargs : dict
        The keyword arguments.
    size : float
        The size of the command. This value is used to determine when older commands
        should be removed from the stack.
    """

    func: ReversibleFunction
    args: tuple[Any, ...]
    kwargs: dict[str, Any]
    size: float = 0.0

    def __repr__(self) -> str:
        _cls = type(self).__name__
        return f"{_cls}<{self.func.format_forward_call(*self.args, *self.kwargs)}>"

    def _call_with_callback(self):
        return self.func._call_with_callback(*self.args, **self.kwargs)

    def _call_raw(self):
        return self.func._call_raw(*self.args, **self.kwargs)

    def _revert(self):
        return self.func._revert(*self.args, **self.kwargs)

    # @classmethod
    # def merge(cls, cmds: Iterable[Command], name: str | None = None) -> Command:
    #     """
    #     Merge multiple commands into one.

    #     This method is used to reduce command set stack by merging simple operations.
    #     For instance, if you defined a undoable "append" method and intend to define
    #     "extend" method by repeating "append" operation, a lot of "append" command
    #     will be generated. To avoid this, you can use this method to merge "append".

    #     Parameters
    #     ----------
    #     cmds : Iterable[CommandSet]
    #         List of command sets to merge.

    #     Returns
    #     -------
    #     CommandSet
    #         Merged command set.
    #     """
    #     arguments: list[tuple, dict[str, Any]] = []
    #     funcs: list[ReversibleFunction] = []
    #     total_size = 0.0

    #     for cmd in cmds:
    #         funcs.append(cmd.func)
    #         arguments.append((cmd.args, cmd.kwargs))
    #         total_size += cmd.size

    #     fn_merged = ReversibleFunction.merge(funcs)
    #     if name is not None:
    #         fn_merged.__name__ = name
    #     return cls(fn_merged, (arguments,), {}, size=total_size)

    @classmethod
    def merge(cls, cmds: Iterable[Command], name: str | None = None) -> CommandGroup:
        group = CommandGroup(cmds)
        return group

    def to_code(self, ns: str | None = None) -> str:
        """
        Convert command to code.

        Parameters
        ----------
        ns : str, optional
            The namespace of the command. If None, the command will be converted
            to a simple expression.

        Returns
        -------
        str
            The code of the command.
        """
        from ._codegen import generate

        return generate(self, ns)

    def format(self, fmt: FormatterType | None = None) -> str:
        """
        Format command to string.

        A format string or a callable can be used to format the command.
        Following formatters are equivalent.

        >>> cmd.format("{}({})")
        >>> cmd.format(lambda f, x: f"{f}({x})")

        Parameters
        ----------
        fmt : str or callable, optional
            The formatter. If None, the default formatter will be used.

        Returns
        -------
        str
            The formatted command string.
        """
        rf = self.func
        func, args, kwargs = rf.unpartial(self.args, self.kwargs)
        if fmt is None:
            _fmt = self.func._default_formatter
        else:
            args, kwargs = rf.map_args(args, kwargs)
            if isinstance(fmt, str):
                _fmt = fmt.format
            elif callable(fmt):
                _fmt = fmt
            else:
                raise TypeError(f"Cannot use {type(fmt)} as a formatter.")
        fn = getattr(func, "__name__", str(func))
        return _fmt(fn, *args, **kwargs)


class CommandGroup(_CommandBase):
    def __init__(self, commands: Iterable[Command]):
        self._commands = list(commands)

    @property
    def commands(self) -> list[Command]:
        """List of commands."""
        return list(self._commands)

    def __iter__(self) -> Iterator[Command]:
        """Iterate over all the commands."""
        return iter(self._commands)

    def __hash__(self) -> int:
        return hash(tuple(self._commands))

    def __repr__(self) -> str:
        cls = type(self).__name__
        s = ", \n\t".join(repr(cmd) for cmd in self)
        return f"{cls}([{s}\n])"

    def _call_with_callback(self):
        for cmd in self._commands:
            cmd._call_with_callback()

    def _call_raw(self):
        for cmd in self._commands:
            cmd._call_raw()

    def _revert(self):
        for cmd in reversed(self._commands):
            cmd._revert()

    @property
    def size(self):
        return sum(cmd.size for cmd in self._commands)
