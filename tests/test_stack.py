from collections_undo import UndoManager, empty
from unittest.mock import MagicMock

def test_stack_operations():
    mock = MagicMock()
    mgr = UndoManager()

    @mgr.undoable
    def a(x: int, y: int):
        mock("do", x, y)
        return 0

    @a.undo_def
    def a(x: int, y: int):
        mock("undo", x, y)
        return -1

    mock.assert_not_called()

    out = a(1, 2)
    assert out == 0
    assert mgr.stack_lengths == (1, 0)
    mock.assert_called_with("do", 1, 2)

    out = a(3, 4)
    assert out == 0
    assert mgr.stack_lengths == (2, 0)
    mock.assert_called_with("do", 3, 4)

    out = mgr.undo()
    assert out == -1
    assert mgr.stack_lengths == (1, 1)
    mock.assert_called_with("undo", 3, 4)

    out = mgr.undo()
    assert out == -1
    assert mgr.stack_lengths == (0, 2)
    mock.assert_called_with("undo", 1, 2)
    mock.reset_mock()

    out = mgr.undo()
    assert out == empty
    assert mgr.stack_lengths == (0, 2)
    mock.assert_not_called()

    out = mgr.redo()
    assert out == 0
    assert mgr.stack_lengths == (1, 1)
    mock.assert_called_with("do", 1, 2)

    out = mgr.redo()
    assert out == 0
    assert mgr.stack_lengths == (2, 0)
    mock.assert_called_with("do", 3, 4)
    mock.reset_mock()

    out = mgr.redo()
    assert out == empty
    assert mgr.stack_lengths == (2, 0)
    mock.assert_not_called()

def test_size():
    def nargs(*args, **kwargs):
        return len(args) + len(kwargs)

    mgr = UndoManager(measure=nargs, maxsize=10)

    @mgr.undoable
    def f(*args, **kwargs):
        pass

    @f.undo_def
    def f(*args, **kwargs):
        pass

    f(0)
    f(0, 0)
    f(0, 0, 0)
    assert mgr.stack_size == 6
    mgr.undo()
    assert mgr.stack_size == 6
    mgr.redo()
    assert mgr.stack_size == 6
    mgr.undo()
    assert mgr.stack_size == 6
    f(0)
    assert mgr.stack_size == 4
    assert mgr.stack_lengths == (3, 0)
    f(0, 0, 0, 0, 0)
    assert mgr.stack_size == 9
    assert mgr.stack_lengths == (4, 0)
    f(0, 0, 0)
    assert mgr.stack_size == 9
    assert mgr.stack_lengths == (3, 0)

def test_repr():
    mgr = UndoManager()

    @mgr.undoable
    def a():
        return 0

    @a.undo_def
    def a():
        return -1

    a()
    repr(mgr)
    [a() for _ in range(20)]
    repr(mgr)
    [mgr.undo() for _ in range(12)]
    repr(mgr)

def test_pre_link():
    mgr0 = UndoManager()
    mgr1 = UndoManager()

    mgr0.link(mgr1)


    @mgr0.undoable
    def a():
        return 0

    @a.undo_def
    def a():
        return -1

    a()
    assert mgr0.stack_lengths == (1, 0)
    assert mgr1.stack_lengths == (1, 0)

    mgr0.undo()
    assert mgr0.stack_lengths == (0, 1)
    assert mgr1.stack_lengths == (0, 1)


def test_post_link():
    mgr0 = UndoManager()
    mgr1 = UndoManager()

    @mgr0.undoable
    def a():
        return 0

    @a.undo_def
    def a():
        return -1

    a()

    mgr0.link(mgr1)

    assert mgr0.stack_lengths == (1, 0)
    assert mgr1.stack_lengths == (1, 0)

    mgr0.undo()
    assert mgr0.stack_lengths == (0, 1)
    assert mgr1.stack_lengths == (0, 1)

def test_link_blocked():
    mgr0 = UndoManager()
    mgr1 = UndoManager()

    @mgr0.undoable
    def a():
        return 0

    @a.undo_def
    def a():
        return -1

    mgr0.link(mgr1)

    with mgr0.blocked():
        a()

    assert mgr0.stack_lengths == (0, 0)
    assert mgr1.stack_lengths == (0, 0)


    with mgr1.blocked():
        a()

    assert mgr0.stack_lengths == (0, 0)
    assert mgr1.stack_lengths == (0, 0)

def test_group():
    class A:
        mgr = UndoManager()

        def __init__(self):
            self.x = self.y = self.z = 0
            self._hist = []

        @mgr.interface
        def setx(self, x):
            self.x = x
            self._hist.append("x")

        @setx.server
        def setx(self, x):
            return (self.x,), {}

        @mgr.interface
        def sety(self, y):
            self.y = y
            self._hist.append("y")

        @sety.server
        def sety(self, y):
            return (self.y,), {}

        @mgr.interface
        def setz(self, z):
            self.z = z
            self._hist.append("z")

        @setz.server
        def setz(self, z):
            return (self.z,), {}

        def set(self, x, y, z):
            with self.mgr.merging():
                self.setx(x)
                self.sety(y)
                self.setz(z)

    a = A()
    a.set(1, 2, 3)
    assert a.mgr.stack_lengths == (1, 0)
    assert a._hist[-3:] == ["x", "y", "z"]
    a.mgr.undo()
    assert a.mgr.stack_lengths == (0, 1)
    assert a._hist[-3:] == ["z", "y", "x"]

def test_blocked():
    mgr = UndoManager()

    @mgr.undoable
    def a(x):
        return x

    @mgr.undoable
    def b():
        a(0)

    def c():
        with mgr.merging():
            a(1)
            b()

    @mgr.undoable
    def d():
        c()

    assert mgr.stack_lengths == (0, 0)
    c()
    assert mgr.stack_lengths == (1, 0)
    d()
    assert mgr.stack_lengths == (2, 0)

def test_nested_merge():
    mgr = UndoManager()
    state = 0

    @mgr.interface
    def a(x):
        nonlocal state
        state = x

    @a.server
    def a(x):
        return (state,), {}

    with mgr.merging():
        a(0)
        with mgr.merging():
            a(1)
            a(2)
        a(3)

    assert mgr.stack_lengths == (1, 0)
    assert state == 3
    mgr.undo()
    assert state == 0
    mgr.redo()
    assert state == 3

def test_reduce_reversible():
    class A:
        mgr = UndoManager()

        def __init__(self):
            self.x = 0

        def move(self, x):
            return self._move(self.x, x)

        @mgr.undoable
        def _move(self, x0, x1):
            self.x = x1

        @_move.undo_def
        def _move(self, x0, x1):
            self.x = x0

        @_move.reduce_rule
        def _move_rule(self, args0, args1):
            x0 = args0["x0"]
            x1 = args1["x1"]
            return (x0, x1), {}

    a = A()
    with a.mgr.reducing():
        a.move(10)
        a.move(20)
        a.move(15)

    assert a.x == 15
    assert a.mgr.stack_lengths == (1, 0)
    assert a.mgr.stack_undo[0].args == (0, 15)
    a.mgr.undo()
    assert a.x == 0
    a.mgr.redo()
    assert a.x == 15

def test_reduce_interface():
    class A:
        mgr = UndoManager()

        def __init__(self):
            self.x = 0

        @mgr.interface
        def move(self, x):
            self.x = x

        @move.server
        def move(self, x):
            return (self.x,), {}

    a = A()
    with a.mgr.reducing():
        a.move(10)
        a.move(20)
        a.move(15)

    assert a.x == 15
    assert a.mgr.stack_lengths == (1, 0)
    a.mgr.undo()
    assert a.x == 0
    a.mgr.redo()
    assert a.x == 15


def test_reduce_property():
    class A:
        mgr = UndoManager()

        def __init__(self):
            self._x = 0

        @mgr.property
        def x(self):
            return self._x

        @x.setter
        def x(self, x):
            self._x = x

    a = A()
    with a.mgr.reducing():
        a.x = 10
        a.x = 20
        a.x = 15

    assert a.x == 15
    assert a.mgr.stack_lengths == (1, 0)
    a.mgr.undo()
    assert a.x == 0
    a.mgr.redo()
    assert a.x == 15
