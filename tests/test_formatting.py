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
    class A:
        mgr = UndoManager()

        @mgr.interface
        def f(self, a, b, c):
            ...

        @f.server
        def f(self, a, b, c):
            return (a, b, c), {}

        @f.set_mapper
        def _f_fmt(self, a, b, c):
            return (a + 1, b + 1, c + 1), {}

    a = A()
    a.f(1, 2, 3)

    assert a.mgr.stack_undo[0].format() == "f(2, 3, 4)"

def test_custom_mapping():
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
