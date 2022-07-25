from unittest.mock import MagicMock
import pytest
from collections_undo.abc import UndoableABC, undoablemethod, undo_def

def test_error():
    class A(UndoableABC):
        @undoablemethod
        def f(self):
            pass

    with pytest.raises(TypeError):
        A()  # undo is not defined for f

    class B(A):
        pass

    class C(B):
        pass

    with pytest.raises(TypeError):
        B()

    with pytest.raises(TypeError):
        C()

def test_undo_def():
    mock = MagicMock()

    class A(UndoableABC):
        @undoablemethod
        def f(self, x):
            mock("do", x)

        @undo_def(f)
        def f(self, x):
            mock("undo", x)

    a = A()
    mock.assert_not_called()
    a.f(0)
    mock.assert_called_with("do", 0)
    a.undo()
    mock.assert_called_with("undo", 0)
    a.redo()
    mock.assert_called_with("do", 0)

def test_undo_def_inheritance():
    mock = MagicMock()

    class A(UndoableABC):
        @undoablemethod
        def f(self, x):
            mock("do", x)

    class B(A):
        @undo_def(A.f)
        def f(self, x):
            mock("undo", x)

    class C(A):
        pass

    with pytest.raises(TypeError):
        C()

    b = B()
    mock.assert_not_called()
    b.f(0)
    mock.assert_called_with("do", 0)
    b.undo()
    mock.assert_called_with("undo", 0)
    b.redo()
    mock.assert_called_with("do", 0)
