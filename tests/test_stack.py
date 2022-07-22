from undo import UndoManager, empty
from unittest.mock import MagicMock

def test_stack_operations():
    mock = MagicMock()
    mgr = UndoManager()

    @mgr.command
    def a(x, y):
        mock("do", x, y)
        return 0

    @a.undo_def
    def a(x, y):
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

    @mgr.command
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
