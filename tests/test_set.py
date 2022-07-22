from collections_undo import UndoableSet

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

def test_clear():
    s = UndoableSet([1, 2, 3])
    s.clear()
    assert s._set == set()
    s.undo()
    assert s._set == {1, 2, 3}
    s.redo()
    assert s._set == set()

def test_ior():
    s = UndoableSet([1, 2, 3])
    s |= {3, 4, 5}
    assert s._set == {1, 2, 3, 4, 5}
    s.undo()
    assert s._set == {1, 2, 3}
    s.redo()
    assert s._set == {1, 2, 3, 4, 5}

def test_iand():
    s = UndoableSet([1, 2, 3])
    s &= {2, 3, 4, 5}
    assert s._set == {2, 3}
    s.undo()
    assert s._set == {1, 2, 3}
    s.redo()
    assert s._set == {2, 3}

def test_ixor():
    s = UndoableSet([1, 2, 3])
    s ^= {2, 3, 4, 5}
    assert s._set == {1, 4, 5}
    s.undo()
    assert s._set == {1, 2, 3}
    s.redo()
    assert s._set == {1, 4, 5}

def test_isub():
    s = UndoableSet([1, 2, 3])
    s -= {2, 3, 4, 5}
    assert s._set == {1}
    s.undo()
    assert s._set == {1, 2, 3}
    s.redo()
    assert s._set == {1}
