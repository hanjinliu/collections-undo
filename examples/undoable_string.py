from collections_undo.containers import AbstractUndoableList

class UndoableString(AbstractUndoableList):
    def __init__(self, string: str = "", /):
        self._list = list(string)

    def __str__(self):
        return ''.join(self._list)

    def __getitem__(self, i):
        return ''.join(self._list[i])

    def __len__(self):
        return len(self._list)

    def _raw_setitem(self, key, val: str) -> None:
        if isinstance(key, int):
            if len(val) != 1:
                raise ValueError('Only single-character strings can be inserted')
            self._list[key] = val
        else:
            self._list[key] = list(val)

    def _raw_delitem(self, key) -> None:
        del self._list[key]

    def __iter__(self):
        return iter(self._list)

    def _raw_insert(self, index: int, val: str):
        if len(val) == 1:
            self._list.insert(index, val)
        else:
            raise ValueError('Only single-character strings can be inserted')


if __name__ == "__main__":
    s = UndoableString("My name is ")

    # edit string
    s.extend("John")
    assert str(s) == "My name is John"

    del s[-4:]
    assert str(s) == "My name is "

    s.extend("Mary")
    assert str(s) == "My name is Mary"

    s.undo()
    assert str(s) == "My name is "

    s.undo()
    assert str(s) == "My name is John"

    s.redo()
    s.redo()
    assert str(s) == "My name is Mary"
