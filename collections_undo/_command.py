from __future__ import annotations
from abc import ABC, abstractmethod, abstractproperty
from typing import Any, Callable, Iterable, Iterator, Union, TYPE_CHECKING
from dataclasses import dataclass

from ._reversible import ReversibleFunction

FormatterType = Union[Callable[["Command"], str], str]

if TYPE_CHECKING:
    from typing_extensions import Self


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

    @classmethod
    def merge(cls, cmds: Iterable[Command], formatter=None) -> CommandGroup:
        group = CommandGroup(cmds, formatter=formatter)
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
    def __init__(
        self,
        commands: Iterable[Command],
        formatter: Callable[[Self], str] | None = None,
    ):
        self._commands = list(commands)
        if formatter is None:
            self._formatter = type(self)._format_default
        else:
            self._formatter = formatter

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

    def _call_with_callback(self) -> Any:
        for cmd in self._commands:
            out = cmd._call_with_callback()
        return out

    def _call_raw(self) -> Any:
        for cmd in self._commands:
            out = cmd._call_raw()
        return out

    def _revert(self) -> Any:
        for cmd in reversed(self._commands):
            out = cmd._revert()
        return out

    @property
    def size(self) -> int:
        """The total size of the command."""
        return sum(cmd.size for cmd in self._commands)

    def format(self, fmt: Callable | None = None) -> str:
        if fmt is not None:
            return fmt(self.commands)
        return self._formatter(self)

    def _format_default(self) -> str:
        return "\n".join(cmd.format() for cmd in self)
