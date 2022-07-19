from undo import CommandStack
from unittest.mock import MagicMock

def test_stack_operations():
    mock = MagicMock()
    stack = CommandStack()

    @stack.command
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
    assert stack.stack_lengths == (1, 0)
    mock.assert_called_with("do", 1, 2)

    out = a(3, 4)
    assert out == 0
    assert stack.stack_lengths == (2, 0)
    mock.assert_called_with("do", 3, 4)

    out = stack.undo()
    assert out == -1
    assert stack.stack_lengths == (1, 1)
    mock.assert_called_with("undo", 3, 4)

    out = stack.undo()
    assert out == -1
    assert stack.stack_lengths == (0, 2)
    mock.assert_called_with("undo", 1, 2)
    mock.reset_mock()

    out = stack.undo()
    assert out == CommandStack.empty
    assert stack.stack_lengths == (0, 2)
    mock.assert_not_called()

    out = stack.redo()
    assert out == 0
    assert stack.stack_lengths == (1, 1)
    mock.assert_called_with("do", 1, 2)

    out = stack.redo()
    assert out == 0
    assert stack.stack_lengths == (2, 0)
    mock.assert_called_with("do", 3, 4)
    mock.reset_mock()

    out = stack.redo()
    assert out == CommandStack.empty
    assert stack.stack_lengths == (2, 0)
    mock.assert_not_called()

def test_repeat():
    mock = MagicMock()
    stack = CommandStack()

    @stack.command
    def a(x, y):
        mock("do", x, y)
        return 0

    @a.undo_def
    def a(x, y):
        mock("undo", x, y)
        return -1

    mock.assert_not_called()

    out = stack.repeat()
    assert out == CommandStack.empty
    mock.assert_not_called()

    out = a(1, 2)
    out = stack.repeat()
    assert out == 0
    mock.assert_called_with("do", 1, 2)
    assert stack.stack_lengths == (2, 0)
    mock.reset_mock()

    out = stack.repeat()
    assert out == 0
    mock.assert_called_with("do", 1, 2)
    assert stack.stack_lengths == (3, 0)
