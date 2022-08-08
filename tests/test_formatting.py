from collections_undo import UndoManager

def test_interface():
    mgr = UndoManager()

    @mgr.interface
    def f(a, b, c):
        ...

    @f.server
    def f(a, b, c):
        return (a, b, c), {}

    f(1, 2, 3)

    repr(mgr)  # assert it works
    assert repr(mgr.stack_undo[0]) == "Command<f(1, 2, 3)>"
