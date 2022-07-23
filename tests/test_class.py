from unittest.mock import MagicMock
from collections_undo import UndoManager

def test_property():
    class A:
        mgr = UndoManager()
        def __init__(self):
            self._a = 10

        @mgr.property
        def a(self):
            return self._a

        @a.setter
        def a(self, val):
            self._a = val

    x = A()
    x.a = 11
    x.a = 12
    assert x.a == 12
    assert A.mgr.stack_lengths == (0, 0)
    assert x.mgr.stack_lengths == (2, 0)

    x.mgr.undo()
    assert x.a == 11

    x.mgr.undo()
    assert x.a == 10
    assert x.mgr.stack_lengths == (0, 2)

    x.mgr.undo()
    assert x.a == 10
    assert x.mgr.stack_lengths == (0, 2)

    x.mgr.redo()
    assert x.a == 11
    assert x.mgr.stack_lengths == (1, 1)

def test_stack_independency():
    class A:
        mgr = UndoManager()
        def __init__(self):
            self._a = 10

        @mgr.property
        def a(self):
            return self._a

        @a.setter
        def a(self, val):
            self._a = val

    x = A()
    y = A()

    assert x.mgr is not y.mgr

    x.a = 1
    x.a = 2
    x.a = 3

    y.a = -1
    y.a = -2

    assert x.mgr.stack_lengths == (3, 0)
    assert y.mgr.stack_lengths == (2, 0)

def test_method():
    mock = MagicMock()

    class A:
        mgr = UndoManager()

        @mgr.undoable
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
    assert x.mgr.stack_lengths == (2, 0)
    x.mgr.undo()
    mock.assert_called_with("undo", x, 5)
    assert x.mgr.stack_lengths == (1, 1)

def test_undoable_interface():
    class A:
        mgr = UndoManager()

        def __init__(self):
            self.ans_add = 0
            self.ans_sub = 0

        @property
        def ans(self):
            return self.ans_add, self.ans_sub

        @mgr.interface
        def calc(self, a, b):
            self.ans_add = a + b
            self.ans_sub = a - b

        @calc.server
        def calc(self, a, b):
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
    assert x.mgr.stack_lengths == (2, 0)
    x.mgr.undo()
    assert x.ans == (8, -2)
    x.mgr.undo()
    assert x.ans == (0, 0)

def test_setitem():
    class Arr:
        mgr = UndoManager()

        def __init__(self, arr: list):
            self.arr = arr

        @mgr.interface
        def __setitem__(self, sl, val):
            self.arr[sl] = val

        @__setitem__.server
        def __setitem__(self, sl, val):
            return (sl, self.arr[sl]), {}

    a = Arr([0, 0, 0, 0, 0])
    a[1] = 1
    a[3] = 3
    assert a.arr == [0, 1, 0, 3, 0]
    a.mgr.undo()
    assert a.arr == [0, 1, 0, 0, 0]
    a.mgr.undo()
    assert a.arr == [0, 0, 0, 0, 0]
    a.mgr.redo()
    assert a.arr == [0, 1, 0, 0, 0]
    a.mgr.redo()
    assert a.arr == [0, 1, 0, 3, 0]
    a.mgr.redo()
    assert a.arr == [0, 1, 0, 3, 0]
