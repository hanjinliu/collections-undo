from unittest.mock import MagicMock
from undo import UndoStack

def test_property():
    class A:
        stack = UndoStack()
        def __init__(self):
            self._a = 10

        @stack.property
        def a(self):
            return self._a

        @a.setter
        def a(self, val):
            self._a = val

    x = A()
    x.a = 11
    x.a = 12
    assert x.a == 12
    assert A.stack.stack_lengths == (0, 0)
    assert x.stack.stack_lengths == (2, 0)

    x.stack.undo()
    assert x.a == 11

    x.stack.undo()
    assert x.a == 10
    assert x.stack.stack_lengths == (0, 2)

    x.stack.undo()
    assert x.a == 10
    assert x.stack.stack_lengths == (0, 2)

    x.stack.redo()
    assert x.a == 11
    assert x.stack.stack_lengths == (1, 1)

def test_stack_independency():
    class A:
        stack = UndoStack()
        def __init__(self):
            self._a = 10

        @stack.property
        def a(self):
            return self._a

        @a.setter
        def a(self, val):
            self._a = val

    x = A()
    y = A()

    assert x.stack is not y.stack

    x.a = 1
    x.a = 2
    x.a = 3

    y.a = -1
    y.a = -2

    assert x.stack.stack_lengths == (3, 0)
    assert y.stack.stack_lengths == (2, 0)

def test_method():
    mock = MagicMock()

    class A:
        stack = UndoStack()

        @stack.command
        def f(self, a):
            mock("do", self, a)

        @f.undo_def
        def f(self, a):
            mock("undo", self, a)

    x = A()

    mock.assert_not_called()
    x.f(3)
    mock.assert_called_with("do", x, 3)
    x.f(5)
    mock.assert_called_with("do", x, 5)
    assert x.stack.stack_lengths == (2, 0)
    x.stack.undo()
    mock.assert_called_with("undo", x, 5)
    assert x.stack.stack_lengths == (1, 1)

def test_undoable_function():
    class A:
        stack = UndoStack()

        def __init__(self):
            self.ans_add = 0
            self.ans_sub = 0

        @property
        def ans(self):
            return self.ans_add, self.ans_sub

        @stack.setitem
        def calc(self, a, b):
            self.ans_add = a + b
            self.ans_sub = a - b

        @calc.getter
        def _add_init(self, a, b):
            add = self.ans_add
            sub = self.ans_sub
            a = (add + sub) / 2
            b = (add - sub) / 2
            return (a, b), {}

    x = A()
    x.calc(3, 5)
    assert x.ans == (8, -2)
    x.calc(4, 2)
    assert x.ans == (6, 2)
    assert x.stack.stack_lengths == (2, 0)
    x.stack.undo()
    assert x.ans == (8, -2)
    x.stack.undo()
    assert x.ans == (0, 0)

def test_setitem():
    class Arr:
        stack = UndoStack()

        def __init__(self, arr: list):
            self.arr = arr

        @stack.setitem
        def __setitem__(self, sl, val):
            self.arr[sl] = val

        @__setitem__.getter
        def _setitem_getter(self, sl, val):
            return (sl, self.arr[sl]), {}

    a = Arr([0, 0, 0, 0, 0])
    a[1] = 1
    a[3] = 3
    assert a.arr == [0, 1, 0, 3, 0]
    a.stack.undo()
    assert a.arr == [0, 1, 0, 0, 0]
    a.stack.undo()
    assert a.arr == [0, 0, 0, 0, 0]
    a.stack.redo()
    assert a.arr == [0, 1, 0, 0, 0]
    a.stack.redo()
    assert a.arr == [0, 1, 0, 3, 0]
    a.stack.redo()
    assert a.arr == [0, 1, 0, 3, 0]
