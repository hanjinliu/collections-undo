from unittest.mock import MagicMock

import pytest
from collections_undo import UndoManager

def test_called():
    mock = MagicMock()

    mgr = UndoManager()

    @mgr.undoable
    def f(x):
        pass

    @f.undo_def
    def f(x):
        pass

    @mgr.called.append
    def callback(cmd, tp):
        mock(cmd, tp)

    f(0)
    assert mock.call_count == 1
    cmd, tp = mock.call_args.args
    assert cmd.args == (0,)
    assert cmd.kwargs == {}
    assert tp == "call"

    mgr.undo()
    cmd, tp = mock.call_args.args
    assert cmd.args == (0,)
    assert cmd.kwargs == {}
    assert tp == "undo"

    mgr.redo()
    cmd, tp = mock.call_args.args
    assert cmd.args == (0,)
    assert cmd.kwargs == {}
    assert tp == "redo"

def test_errored():
    mock = MagicMock()

    mgr = UndoManager()

    class TestException(Exception):
        pass

    @mgr.undoable
    def f(raises: bool):
        if raises:
            raise TestException("call")

    @f.undo_def
    def f(raises: bool):
        if not raises:
            raise TestException("undo")

    @mgr.errored.append
    def callback(e):
        mock(e)

    with pytest.raises(TestException):
        f(True)
    ex = mock.call_args.args[0]
    assert type(ex) == TestException
    assert ex.args == ("call",)

    f(False)
    with pytest.raises(TestException):
        mgr.undo()
    ex = mock.call_args.args[0]
    assert type(ex) == TestException
    assert ex.args == ("undo",)
