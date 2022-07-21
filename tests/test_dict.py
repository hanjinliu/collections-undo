from undo import UndoableDict

def test_dict():
    d = UndoableDict({"a": 1, "b": 2, "c": 3})
    assert d._dict == {"a": 1, "b": 2, "c": 3}
    assert d["a"] == 1
    d["d"] = 4
    assert d._dict == {"a": 1, "b": 2, "c": 3, "d": 4}
    del d["a"]
    assert d._dict == {"b": 2, "c": 3, "d": 4}
    d.undo()
    assert d._dict == {"a": 1, "b": 2, "c": 3, "d": 4}
    d.undo()
    assert d._dict == {"a": 1, "b": 2, "c": 3}
    d.redo()
    assert d._dict == {"a": 1, "b": 2, "c": 3, "d": 4}
    d.redo()
    assert d._dict == {"b": 2, "c": 3, "d": 4}

def test_clear():
    d = UndoableDict({"a": 1, "b": 2, "c": 3})
    d.clear()
    assert d._dict == {}
    d.undo()
    assert d._dict == {"a": 1, "b": 2, "c": 3}
    d.redo()
    assert d._dict == {}

def test_update():
    d = UndoableDict({"a": 1, "b": 2, "c": 3})
    d.update({"c": 10, "d": 11})
    assert d._dict == {"a": 1, "b": 2, "c": 10, "d": 11}
    d.undo()
    assert d._dict == {"a": 1, "b": 2, "c": 3}
    d.redo()
    assert d._dict == {"a": 1, "b": 2, "c": 10, "d": 11}
