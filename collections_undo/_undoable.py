from __future__ import annotations
from functools import partial, wraps
from typing import Any, Callable, TYPE_CHECKING, Literal, TypeVar
from ._reversible import ReversibleFunction
from ._const import empty, FormatterType

if TYPE_CHECKING:
    from typing_extensions import ParamSpec
    from ._stack import UndoManager

    _P = ParamSpec("_P")
    _R = TypeVar("_R")
    ArgsType = tuple[tuple, dict[str, Any]]
    _Args = TypeVar("_Args", bound=ArgsType)


def _dummy_func(*args, **kwargs) -> None:
    return None


_Fmt = TypeVar("_Fmt", bound=FormatterType)


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
        self._freceive = freceive
        self._fserve = fserve
        self._mgr = mgr
        self._func = None
        self._instances: dict[int, UndoableInterface] = {}
        self._formatter_fw = None
        self._formatter_rv = None

    def server(self, fserve: Callable[_P, _Args]) -> UndoableInterface:
        """Set the server function."""
        itf = UndoableInterface(
            fserve=fserve,
            freceive=self._freceive,
            mgr=self._mgr,
        )
        itf._formatter_fw = self._formatter_fw
        itf._formatter_rv = self._formatter_rv
        return itf

    def receiver(self, freceive: Callable[_P, _R]) -> UndoableInterface:
        """Set the receiver function."""
        itf = UndoableInterface(
            fserve=self._fserve,
            freceive=freceive,
            mgr=self._mgr,
        )
        itf._formatter_fw = self._formatter_fw
        itf._formatter_rv = self._formatter_rv
        return itf

    def set_formatter(
        self,
        formatter: _Fmt,
        /,
    ) -> _Fmt:
        if not callable(formatter):
            raise TypeError(f"{formatter!r} is not callable")
        self._formatter_fw = formatter
        return formatter

    def set_formatter_inv(
        self,
        formatter: _Fmt,
        /,
    ) -> _Fmt:
        if not callable(formatter):
            raise TypeError(f"{formatter!r} is not callable")
        self._formatter_rv = formatter
        return formatter

    @property
    def func(self) -> ReversibleFunction:
        if self._func is None:
            self._func = self._create_function()
        return self._func

    def __call__(self, *args: _P.args, **kwargs: _P.kwargs) -> _R:
        with self._mgr.blocked():
            _old_state = self._fserve(*args, **kwargs)
            out = self._freceive(*args, **kwargs)
        self._mgr._append_command(self.func, (args, kwargs), _old_state)
        return out

    def __set_name__(self, owner: type, name: str) -> None:
        self.__name__ = name

    def __get__(self, obj, objtype=None) -> UndoableInterface:
        if obj is None:
            return self
        _id = id(obj)
        if (out := self._instances.get(_id, None)) is None:
            self._instances[_id] = out = UndoableInterface(
                freceive=self._freceive.__get__(obj, objtype),
                fserve=self._fserve.__get__(obj, objtype),
                mgr=self._mgr.__get__(obj, objtype),
            )
            if self._formatter_fw is not None:
                out._formatter_fw = partial(self._formatter_fw, obj)
            if self._formatter_rv is not None:
                out._formatter_rv = partial(self._formatter_rv, obj)
        return out

    def __repr__(self) -> str:
        return f"{type(self).__name__}<{self._freceive!r}>"

    def _create_function(self) -> ReversibleFunction:
        def fw(new: ArgsType, old: ArgsType):
            args, kwargs = new
            return self._freceive(*args, **kwargs)

        fw.__name__ = self.__name__

        def rv(new: ArgsType, old: ArgsType):
            if old is None:
                return empty
            args, kwargs = old
            return self._freceive(*args, **kwargs)

        fn = ReversibleFunction(fw, rv, mgr=self._mgr)
        fn.__name__ = self.__name__

        if self._formatter_fw is not None:
            fn._formatter_fw = self._formatter_fw
        if self._formatter_rv is not None:
            fn._formatter_rv = self._formatter_rv

        fn._map_args = _mapping
        return fn


def _mapping(new, old):
    args, kwargs = new
    return args, kwargs


class UndoableProperty(property):
    """A property class implemented with undo."""

    def __init__(
        self,
        fget: Callable[[Any], Any] | None = None,
        fset: Callable[[Any], Any] | None = None,
        fdel: Literal[None] = None,
        doc: str | None = None,
        *,
        mgr: UndoManager = None,
    ):
        self._mgr = mgr
        super().__init__(fget, fset, fdel, doc)

    def getter(self, fget: Callable[[Any], Any], /) -> UndoableProperty:
        """
        Set the getter function.

        Note that the getter function must return something without exception. Returned
        value will be used in undoing setter function.
        """
        return UndoableProperty(
            fget=fget,
            fset=self.fset,
            fdel=self.fdel,
            doc=self.__doc__,
            mgr=self._mgr,
        )

    def setter(self, fset: Callable[[Any, Any], None], /) -> UndoableProperty:
        """Define the undoable setter function."""

        @self._mgr.undoable
        def setattr(obj, val, old_val):
            fset(obj, val)

        @setattr.undo_def
        def setattr(obj, val, old_val):
            fset(obj, old_val)

        @wraps(fset)
        def fset_ext(obj, val):
            old_val = self.fget(obj)
            setattr.__get__(obj)(val, old_val)

        # update names and the formatter

        return UndoableProperty(
            fget=self.fget,
            fset=fset_ext,
            fdel=self.fdel,
            doc=self.__doc__,
            mgr=self._mgr,
        )

    def deleter(self, fdel: Callable[[Any], None], /) -> UndoableProperty:
        """Define the undoable deleter function."""

        @self._mgr.undoable
        def delattr(obj, old_val):
            fdel(obj)

        @delattr.undo_def
        def delattr(obj, old_val):
            self.fset(obj, old_val)

        @wraps(fdel)
        def fdel_ext(obj):
            old_val = self.fget(obj)
            delattr.__get__(obj)(old_val)

        # update names and the formatter

        return UndoableProperty(
            fget=self.fget,
            fset=self.fset,
            fdel=fdel_ext,
            doc=self.__doc__,
            mgr=self._mgr,
        )

    @classmethod
    def from_property(self, prop: property, mgr: UndoManager) -> UndoableProperty:
        """Construct a new undoable property from a property object."""
        return UndoableProperty(prop.fget, prop.fset, prop.fdel, prop.__doc__, mgr=mgr)

    def _map_args(self, *args, **kwargs):
        return args, kwargs
