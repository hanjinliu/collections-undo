from __future__ import annotations
from functools import wraps
from typing import Any, Callable, TYPE_CHECKING, Literal, TypeVar
from ._command import ReversibleFunction
from ._const import empty

if TYPE_CHECKING:
    from typing_extensions import ParamSpec
    from ._stack import UndoManager

    _P = ParamSpec("_P")
    _R = TypeVar("_R")
    _Args = TypeVar("_Args", bound=tuple[tuple, dict[str, Any]])


def _dummy_func(*args, **kwargs) -> None:
    return None


class UndoableInterface:
    """
    An undoable object described by server/receiver interface.

    A "server" provides arguments that reproduce the state of the object.
    A "receiver" updates the object using given arguments.
    Before calling receiver(*args, **kwargs), arguments are retrieved from:
    >>> _args, _kwargs = server(*args, **kwargs)
    and ``receiver(*_args, **_kwargs)`` reproduces the current state of the object.
    """

    def __init__(
        self,
        freceive: Callable[_P, _R] | None = None,
        fserve: Callable[_P, _Args] | None = None,
        mgr: UndoManager = None,
    ):
        if freceive is None:
            freceive = _dummy_func
        else:
            wraps(freceive)(self)
        if fserve is None:
            fserve = _dummy_func
        self.freceive = freceive
        self.fserve = fserve
        self._mgr = mgr
        self._func = None
        self._instances: dict[int, UndoableInterface] = {}

    def server(self, fserve: Callable[_P, _Args]) -> Callable[_P, _Args]:
        """Set the server function."""
        return UndoableInterface(
            fserve=fserve,
            freceive=self.freceive,
            mgr=self._mgr,
        )

    def receiver(self, freceive: Callable[_P, _R]) -> Callable[_P, _R]:
        """Set the receiver function."""
        return UndoableInterface(
            fserve=self.fserve,
            freceive=freceive,
            mgr=self._mgr,
        )

    @property
    def func(self) -> ReversibleFunction:
        if self._func is None:
            self._func = self._create_function()
        return self._func

    def __call__(self, *args: _P.args, **kwargs: _P.kwargs) -> _R:
        _old_state = self.fserve(*args, **kwargs)
        out = self.freceive(*args, **kwargs)
        self._mgr._append_command(self.func, (args, kwargs), _old_state)
        return out

    def __get__(self, obj, objtype=None) -> UndoableInterface:
        if obj is None:
            return self
        _id = id(obj)
        if (out := self._instances.get(_id, None)) is None:
            out = UndoableInterface(
                freceive=self.freceive.__get__(obj, objtype),
                fserve=self.fserve.__get__(obj, objtype),
                mgr=self._mgr.__get__(obj, objtype),
            )
            self._instances[_id] = out
        return out

    def __repr__(self) -> str:
        return f"{type(self).__name__}<{self.freceive!r}>"

    def _create_function(self) -> ReversibleFunction:
        def fw(new, old):
            args, kwargs = new
            return self.freceive(*args, **kwargs)

        def rv(new, old):
            if old is None:
                return empty
            args, kwargs = old
            return self.freceive(*args, **kwargs)

        fn = ReversibleFunction(fw, self._mgr, rv)
        wraps(self)(fn)
        return fn


class UndoableProperty(property):
    """A property class implemented with undo."""

    def __init__(
        self,
        fget: Callable[[Any], Any] | None = None,
        fset: Callable[[Any], Any] | None = None,
        fdel: Literal[None] = None,
        doc: str | None = None,
        *,
        parent: UndoManager = None,
    ):
        self._cmd_stack = parent
        super().__init__(fget, fset, fdel, doc)

    def getter(self, fget: Callable[[Any], Any], /) -> UndoableProperty:
        return UndoableProperty(
            fget=fget,
            fset=self.fset,
            fdel=self.fdel,
            doc=self.__doc__,
            parent=self._cmd_stack,
        )

    def setter(self, fset: Callable[[Any, Any], None], /) -> UndoableProperty:
        @self._cmd_stack.undoable
        def fset_cmd(obj, val, old_val):
            fset(obj, val)

        @fset_cmd.undo_def
        def fset_cmd(obj, val, old_val):
            fset(obj, old_val)

        @wraps(fset)
        def nfset(obj, val):
            old_val = self.fget(obj)
            fset_cmd.__get__(obj)(val, old_val)

        return UndoableProperty(
            fget=self.fget,
            fset=nfset,
            fdel=self.fdel,
            doc=self.__doc__,
            parent=self._cmd_stack,
        )

    def deleter(self, fdel: Callable[[Any], None], /) -> UndoableProperty:
        raise TypeError("undoable_property object does not support deleter.")
