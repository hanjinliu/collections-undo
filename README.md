# undo

General undo/redo implementation in Python.



### Installation

```
pip install -U undo
```

### Examples

##### Undoable property

```python

from undo import UndoStack

class MyClass:
    stack = UndoStack()

    def __init__(self):
        self._a = 0

    @stack.property
    def a(self):
        return self._a

    @a.setter
    def a(self, val):
        self._a = val

x = MyClass()

# it works in a same way as the builtin property
x.a = 1
x.a = 2
assert x.a == 2

# undo property updates
x.stack.undo()
assert x.a == 1
x.stack.undo()
assert x.a == 0

# redo property updates
x.stack.redo()
assert x.a == 1

```

##### Undoable method

```python

from undo import UndoStack

class MyClass:
    stack = UndoStack()

    def __init__(self):
        self.result = None

    @stack.function
    def add(self, a, b):
        """function that updates something."""
        self.result = a + b

    @add.state_getter
    def _add_getter(self):
        return self.result

    @add.state_setter
    def _add_setter(self, val):
        self.result = val

x = MyClass()

# method call
x.add(1, 2)
assert x.result == 3
x.add(5, 6)
assert x.result == 11

x.stack.undo()
assert x.result == 3
x.stack.redo()
assert x.result == 11
```
