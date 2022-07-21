from undo import UndoableSet

def test_set():
    s = UndoableSet([1, 2, 3])
    s.add(4)
    assert s._set == {1, 2, 3, 4}
    s.remove(1)
    assert s._set == {2, 3, 4}
    s.undo()
    assert s._set == {1, 2, 3, 4}
    s.undo()
    assert s._set == {1, 2, 3}
    s.redo()
    assert s._set == {1, 2, 3, 4}
    s.redo()
    assert s._set == {2, 3, 4}
