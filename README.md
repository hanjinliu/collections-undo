# collections-undo

General undo/redo implementation in Python.

### Installation

```
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

- Ready-for-use classes
  - `UndoableList`
  - `UndoableDict`
  - `UndoableSet`

- Abstract classes
  - `AbstractUndoableList`
  - `AbstractUndoableDict`
  - `AbstractUndoableSet`
