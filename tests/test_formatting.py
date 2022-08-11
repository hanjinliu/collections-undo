from collections_undo import UndoManager
from collections_undo import fmt

# fmt: off
class mylist(list): ...
class mytuple(tuple): ...
class myset(set): ...
class mydict(dict): ...
# fmt: on

def test_object_mapping():
    assert fmt.map_object(1) == "1"
    assert fmt.map_object("") == "''"
    assert fmt.map_object(None) == "None"
    assert fmt.map_object(()) == "()"
    assert fmt.map_object((1,)) == "(1,)"
    assert fmt.map_object([(), (1,), set()]) == "[(), (1,), set()]"
    assert fmt.map_object(True) == "True"
    assert fmt.map_object(slice(3, 10, 2)) == "slice(3, 10, 2)"
    assert fmt.map_object(slice(3, 10, None)) == "slice(3, 10)"
    assert fmt.map_object(slice(None, 3, None)) == "slice(3)"
    assert fmt.map_object(range(3, 10, 2)) == "range(3, 10, 2)"
    assert fmt.map_object(range(3, 10)) == "range(3, 10)"
    assert fmt.map_object(range(0, 10)) == "range(10)"
    assert fmt.map_object(1 - 3j) == "(1-3j)"
    assert fmt.map_object(bytes("a", encoding="utf-8")) == "b'a'"
    assert fmt.map_object({"a": [1, 2], "b": [0.1, 0.2]}) == "{'a': [1, 2], 'b': [0.1, 0.2]}"
    assert fmt.map_object(set()) == "set()"
    assert fmt.map_object({1, 2, 3}) == "{1, 2, 3}"
    assert fmt.map_object(frozenset()) == "frozenset([])"
    assert fmt.map_object(frozenset([1, 2])) == "frozenset([1, 2])"

    assert fmt.map_object(mylist([1, 2])) == "mylist([1, 2])"
    assert fmt.map_object(mytuple([1, 2])) == "mytuple([1, 2])"
    assert fmt.map_object(myset([1, 2])) == "myset([1, 2])"
    assert fmt.map_object(mydict(a=1, b=2)) == "mydict({'a': 1, 'b': 2})"

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

def test_interface_in_class():
    class A:
        mgr = UndoManager()

        @mgr.interface
        def f(self, a, b, c):
            ...

        @f.server
        def f(self, a, b, c):
            return (a, b, c), {}

    a = A()
    a.f(1, 2, 3)

    assert repr(a.mgr.stack_undo[0]) == "Command<f(1, 2, 3)>"

def test_format_command():
    class A:
        mgr = UndoManager()

        @mgr.interface
        def f(self, a, b, c):
            ...

        @f.server
        def f(self, a, b, c):
            return (a, b, c), {}

    a = A()
    a.f(1, 2, 3)

    assert a.mgr.stack_undo[0].format() == "f(1, 2, 3)"

def test_custom_formatter():
    mgr = UndoManager()

    @mgr.interface
    def f(a, b, c):
        ...

    @f.server
    def f(a, b, c):
        return (a, b, c), {}

    @f.set_formatter
    def _f_fmt(a, b, c):
        return f"F({a}, {b}, {c})"

    f(1, 2, 3)

    assert mgr.stack_undo[0].format() == "F(1, 2, 3)"

    f(1, b=2, c=4)
    assert mgr.stack_undo[-1].format() == "F(1, 2, 4)"


def test_custom_formatter_in_class():
    class A:
        mgr = UndoManager()

        @mgr.interface
        def f(self, a, b, c):
            ...

        @f.server
        def f(self, a, b, c):
            return (a, b, c), {}

        @f.set_formatter
        def _f_fmt(self, a, b, c):
            return f"F({a}, {b}, {c})"

    a = A()
    a.f(1, 2, 3)

    assert a.mgr.stack_undo[0].format() == "F(1, 2, 3)"

    a.f(1, b=2, c=4)

    assert a.mgr.stack_undo[-1].format() == "F(1, 2, 4)"
