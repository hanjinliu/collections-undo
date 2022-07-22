from __future__ import annotations
from abc import ABC, abstractmethod, abstractproperty

from typing import (
    Generic,
    Hashable,
    Iterator,
    Mapping,
    Sequence,
    TypeVar,
    SupportsIndex,
)
from .._stack import UndoManager

_RV = TypeVar("_RV", bound=Hashable)  # row value
_CV = TypeVar("_CV", bound=Hashable)  # column value
_V = TypeVar("_V")  # data value


class AbstractUndoableDataFrame(ABC, Generic[_V, _RV, _CV]):
    _mgr = UndoManager()

    def __repr__(self) -> str:
        clsname = type(self).__name__
        return f"{clsname}({list(self)!r})"

    @abstractproperty
    def index(self) -> Sequence[_RV]:
        """Vertical header of data frame."""

    @abstractproperty
    def columns(self) -> Sequence[_CV]:
        """Horizontal header of data frame."""

    @property
    def shape(self) -> tuple[int, int]:
        """Shape of dataframe."""
        return (len(self.index), len(self.columns))

    @abstractmethod
    def __getitem__(
        self,
        key: tuple[SupportsIndex, SupportsIndex],
    ) -> _V | AbstractUndoableDataFrame[_V, _RV, _CV]:
        ...

    @abstractmethod
    def _raw_rename(
        self,
        index: Mapping[_RV, _RV] | None = None,
        columns: Mapping[_CV, _CV] | None = None,
    ) -> None:
        """Rename **inplace**"""

    @abstractmethod
    def _raw_insert_rows(self, start: int, count: int, other):
        ...

    @abstractmethod
    def _raw_insert_columns(self, start: int, count: int, other):
        ...

    @abstractmethod
    def _raw_remove_rows(self, start: int, count: int):  # TODO: not needed
        ...

    @abstractmethod
    def _raw_remove_columns(self, start: int, count: int):
        ...

    @abstractmethod
    def _raw_setitem(self, key: tuple[SupportsIndex, SupportsIndex], val) -> None:
        ...

    def __len__(self) -> int:
        return len(self.index)

    def __iter__(self) -> Iterator[_CV]:
        return iter(self.columns)

    def __setitem__(self, key: tuple[SupportsIndex, SupportsIndex], val):
        _key: list[SupportsIndex] = []
        for k in key:
            if isinstance(k, slice):
                k = slice(*k.indices(len(self)))
            elif k < 0:
                k += len(self)
            _key.append(_key)
        return self._setitem(tuple(_key), val)

    @_mgr.interface
    def _setitem(self, key, val):
        self._raw_setitem(key, val)

    @_setitem.descriptor
    def _setitem(self, key, val):
        _val = self[key]
        if isinstance(key, slice):
            _val = list(_val)
        return (key, _val), {}

    def insert_rows(self, start: int, count: int, values) -> None:
        """
        Insert rows at the given index.

        Parameters
        ----------
        start : int
            Index of row where array will be inserted.
        count : int
            Number of rows to insert.
        values : array_like
            Values to insert into the DataFrame.
        """
        return self._insert_rows(start, count, values)

    def insert_columns(self, start: int, count: int, values):
        """
        Insert columns at the given index.

        Parameters
        ----------
        start : int
            Index of column where array will be inserted.
        count : int
            Number of columns to insert.
        values : array_like
            Values to insert into the DataFrame.
        """
        return self._insert_columns(start, count, values)

    def remove_rows(self, start: int, count: int) -> None:
        """
        Remove rows from the DataFrame.

        Parameters
        ----------
        start : int
            Index of row where array will be removed.
        count : int
            Number of rows to remove.
        """
        stop = start + count
        return self._remove_rows(start, count, self[start:stop, :])

    def remove_columns(self, start: int, count: int):
        """
        Remove columns from the DataFrame.

        Parameters
        ----------
        start : int
            Index of column where array will be removed.
        count : int
            Number of columns to remove.
        """
        stop = start + count
        return self._remove_columns(start, count, self[:, start:stop])

    @_mgr.command
    def _insert_rows(self, start: int, count: int, values):
        return self._raw_insert_rows(start, count, values)

    @_insert_rows.undo_def
    def _insert_rows(self, start: int, count: int, values):
        return self._raw_remove_rows(start, count)

    @_mgr.command
    def _remove_rows(self, start: int, count: int, values):
        return self._raw_remove_rows(start, count)

    @_remove_rows.undo_def
    def _remove_rows(self, start: int, count: int, values):
        return self._raw_insert_rows(start, count, values)

    @_mgr.command
    def _insert_columns(self, start: int, count: int, values):
        return self._raw_insert_columns(start, count, values)

    @_insert_columns.undo_def
    def _insert_columns(self, start: int, count: int, values):
        return self._raw_remove_columns(start, count)

    @_mgr.command
    def _remove_columns(self, start: int, count: int, values):
        return self._raw_remove_columns(start, count)

    @_remove_columns.undo_def
    def _remove_columns(self, start: int, count: int, values):
        return self._raw_insert_columns(start, count, values)

    def undo(self):
        """Undo the last operation."""
        return self._mgr.undo()

    def redo(self):
        """Redo the last undo operation."""
        return self._mgr.redo()


class UndoableTableData(AbstractUndoableDataFrame):
    def __init__(
        self,
        data: dict[_CV, _V],
        *,
        index: Sequence[_RV] | None = None,
    ):
        columns = []
        lengths: set[int] = set()
        if isinstance(data, dict):
            for k, v in data.items():
                columns.append(k)
                lengths.add(len(v))

        if len(lengths) > 1:
            raise ValueError("All columns must have the same length")
        elif len(lengths) == 0:
            self._index = []
            self._columns = []
        else:
            length = lengths.pop()
            if index is None:
                index = range(length)
            self._index = list(index)
            self._columns = list(columns)
        self._data = data

    @property
    def index(self) -> Sequence[_RV]:
        """Vertical header of data frame."""
        return self._index

    @property
    def columns(self) -> Sequence[_CV]:
        """Horizontal header of data frame."""
        return self._columns

    def __getitem__(
        self,
        key: tuple[SupportsIndex, SupportsIndex],
    ) -> _V | AbstractUndoableDataFrame[_V, _RV, _CV]:
        r, c = key
        if isinstance(c, slice):
            out: dict[_CV, _V] = {}
            for colname in self.columns[c]:
                out[colname] = self._data[colname][r]
        else:
            column = self._data[self.columns[c]]
            return column[r]

    def _raw_rename(
        self,
        index: Mapping[_RV, _RV] | None = None,
        columns: Mapping[_CV, _CV] | None = None,
    ) -> None:
        """Rename **inplace**"""
        if index is not None:
            self._index = [index.get(k, k) for k in self.index]
        if columns is not None:
            for i, k in enumerate(self.columns):
                if k in columns:
                    old_col = k
                    new_col = columns[k]
                    self._columns[i] = new_col
                    self._data[new_col] = self._data.pop(old_col)
        return None

    @abstractmethod
    def _raw_insert_rows(self, start: int, count: int, other):
        ...

    @abstractmethod
    def _raw_insert_columns(self, start: int, count: int, other):
        ...

    @abstractmethod
    def _raw_remove_rows(self, start: int, count: int):
        ...

    @abstractmethod
    def _raw_remove_columns(self, start: int, count: int):
        ...

    @abstractmethod
    def _raw_setitem(self, key: tuple[SupportsIndex, SupportsIndex], val) -> None:
        ...
