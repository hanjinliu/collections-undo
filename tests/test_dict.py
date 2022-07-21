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
