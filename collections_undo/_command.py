from __future__ import annotations

import inspect
from abc import ABC, abstractmethod
from functools import lru_cache
from typing import TYPE_CHECKING, Any, Callable, Iterable, Iterator, Mapping

from collections_undo._reversible import ReversibleFunction

FormatterType = Callable[["Command"], str]

if TYPE_CHECKING:
    from typing_extensions import Self


class _CommandBase(ABC):
    size: int

    @abstractmethod
    def _call_with_callback(self):
        """Call the command and call the callback if it is defined."""

    @abstractmethod
    def _call_raw(self):
        """Call the command without calling the callback."""

    @abstractmethod
    def _revert(self):
        """Revert the command."""

    @abstractmethod
    def format(self) -> str:
        """Format the command."""


@lru_cache(maxsize=128)
def _bind_args(self: Command):
    return inspect.signature(self.func._func_fw).bind(*self.args, **self.kwargs)


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

    def __init__(
        self,
        func: ReversibleFunction,
        args: tuple[Any, ...],
        kwargs: dict[str, Any],
        size: float = 0.0,
    ):
        self.func = func
        self.args = args
        self.kwargs = kwargs
        self.size = size

    def __repr__(self) -> str:
        _cls = type(self).__name__
        return f"{_cls}<{self.func.format_forward_call(*self.args, *self.kwargs)}>"

    def _call_with_callback(self):
        return self.func._call_with_callback(*self.args, **self.kwargs)

    def _call_raw(self):
        return self.func._call_raw(*self.args, **self.kwargs)

    def _revert(self):
        return self.func._revert(*self.args, **self.kwargs)

    @property
    def function_id(self) -> int:
        """Return the function id."""
        return self.func.function_id

    def bind_args(self) -> inspect.BoundArguments:
        return _bind_args(self)

    @classmethod
    def merge(
        cls,
        cmds: Iterable[Command],
        formatter: FormatterType | None = None,
        invert: bool = False,
    ) -> CommandGroup:
        group = CommandGroup(cmds, formatter=formatter, invert=invert)
        return group

    def format(self, inv: bool = False) -> str:
        """
        Format command to string.

        Parameters
        ----------
        inv : bool, default si False
            Format as a reverse command if true.


        Returns
        -------
        str
            The formatted command string.
        """
        if inv:
            return self.func.format_reverse_call(*self.args, **self.kwargs)
        return self.func.format_forward_call(*self.args, **self.kwargs)

    def reduce_with(self, cmd: Command) -> Self:
        """Automatically merge the command with the given command."""
        rule = cmd.func._reduce_rule
        if rule is None:
            raise ValueError(f"Automerge rule is not defined for {cmd.func}.")
        if self.func is not cmd.func:
            raise ValueError("Cannot merge different functions.")
        _args, _kwargs = rule(
            Arguments(self.bind_args().arguments),
            Arguments(cmd.bind_args().arguments),
        )
        return self.__class__(self.func, _args, _kwargs)


class CommandGroup(_CommandBase):
    """A group of commands."""

    def __init__(
        self,
        commands: Iterable[_CommandBase],
        formatter: Callable[[Self], str] | None = None,
        invert: bool = False,
    ):
        self._commands = list(commands)
        if formatter is None:
            self._formatter = type(self)._format_default
        else:
            self._formatter = formatter
        self._invert = invert

    @property
    def commands(self) -> list[_CommandBase]:
        """List of commands."""
        return list(self._commands)

    def append(self, cmd: _CommandBase) -> None:
        """Append a command to the group."""
        if not isinstance(cmd, _CommandBase):
            raise TypeError(f"{cmd} is not a command")
        self._commands.append(cmd)

    def pop(self) -> _CommandBase:
        """Pop the last command."""
        return self._commands.pop()

    def __getitem__(self, index: int) -> _CommandBase:
        """Get the command at the given index."""
        return self._commands[index]

    def __iter__(self) -> Iterator[_CommandBase]:
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
        out = None
        if self._invert:
            for cmd in self._commands:
                out = cmd._revert()
        else:
            for cmd in reversed(self._commands):
                out = cmd._revert()
        return out

    @property
    def size(self) -> int:
        """The total size of the command."""
        return sum(cmd.size for cmd in self._commands)

    def format(self, fmt: Callable | None = None) -> str:
        if fmt is not None:
            return fmt(self)
        return self._formatter(self)

    def _format_default(self) -> str:
        return "\n".join(cmd.format() for cmd in self)


class Arguments(Mapping[str, Any]):
    def __init__(self, *args, **kwargs):
        self._dict = dict(*args, **kwargs)
        self._keys = list(self._dict.keys())

    def __repr__(self):
        d = repr(self._dict)
        return f"Arguments({d[1:-1]})"

    def __getitem__(self, key: str | int) -> Any:
        if not isinstance(key, str):
            key = self._keys[key]
        return self._dict[key]

    def __getattr__(self, key: str):
        return self.__getitem__(key)

    def __iter__(self):
        return iter(self._keys)

    def __len__(self):
        return len(self._keys)

    def keys(self):
        return self._keys

    def values(self):
        return self._dict.values()

    def items(self):
        return self._dict.items()
