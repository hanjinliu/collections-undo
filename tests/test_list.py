from undo import UndoableList

def test_setitem():
    l = UndoableList([1, 2, 3])
    l.append(4)
    assert l._list == [1, 2, 3, 4]
    l.insert(1, 10)
    assert l._list == [1, 10, 2, 3, 4]
    l[2] = -1
    assert l._list == [1, 10, -1, 3, 4]
    l.undo()
    assert l._list == [1, 10, 2, 3, 4]
    l.undo()
    assert l._list == [1, 2, 3, 4]
    l.undo()
    assert l._list == [1, 2, 3]
    l.undo()
    assert l._list == [1, 2, 3]

def test_setitem_sequence():
    l = UndoableList([1, 2, 3])
    l.extend([10, 11, 12])
    assert l._list == [1, 2, 3, 10, 11, 12]
    l[1:4] = [-1, -2, -3]
    assert l._list == [1, -1, -2, -3, 11, 12]
    l.undo()
    assert l._list == [1, 2, 3, 10, 11, 12]
    l.undo()
    assert l._list == [1, 2, 3]
    l.redo()
    assert l._list == [1, 2, 3, 10, 11, 12]
    l.redo()
    assert l._list == [1, -1, -2, -3, 11, 12]


def test_del():
    ...

def test_del_sequence():
    ...
