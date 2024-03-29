[![Python package index download statistics](https://img.shields.io/pypi/dm/collections-undo.svg)](https://pypistats.org/packages/collections-undo)
[![PyPI version](https://badge.fury.io/py/collections-undo.svg)](https://badge.fury.io/py/collections-undo)

# collections-undo

General undo/redo implementation in Python.
[&rarr; Documentation](https://hanjinliu.github.io/collections-undo/)

### Installation

```shell
pip install -U collections-undo
```

#### Basic usage

You'll have to create reversible functions using `UndoManager`.

```python
from collections_undo import UndoManager

class A:
    mgr = UndoManager()

    @mgr.undoable  # create a reversible function
    def f(self, x):
        print("do", x)

    @f.undo_def  # define undo
    def f(self, x):
        print("undo", x)

a = A()

a.f(0)  # Out: "do" 0
a.mgr.undo()  # Out: "undo" 0
a.mgr.redo()  # Out: "do" 0
```

#### ABC-like undo implementation

To avoid careless errors, ABC-like interface will be useful.

```python
from collections_undo.abc import UndoableABC, undoablemethod, undo_def

class A(UndoableABC):
    @undoablemethod
    def f(self, x):
        print("do", x)

    @undo_def(f)
    def f(self, x):
        print("undo", x)

a = A()  # OK

a.f(0)  # Out: "do" 0
a.undo()  # Out: "undo" 0
a.redo()  # Out: "do" 0
```

If undo is not defined, construction fails.

```python
class A(UndoableABC):
    @undoablemethod
    def f(self, x):
        ...

a = A()  # TypeError

class B(A):
    @undo_def(A.f)
    def f(self, x):
        ...

b = B()  # OK
```

#### Builtin undoable objects

These mutable classes have `undo` and `redo` method to handle operations that mutate the object.

- Ready-to-use classes
  - `UndoableList` ... `insert`, `__setitem__`, `extend` etc. are undoable.
  - `UndoableDict` ... `__setitem__`, `update` etc. are undoable.
  - `UndoableSet` ... `add`, `discard` etc. are undoable.

- Abstract classes
  - `AbstractUndoableList`
  - `AbstractUndoableDict`
  - `AbstractUndoableSet`
