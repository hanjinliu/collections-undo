=========================
Forward-reverse Framework
=========================

The forward-reverse framework is the simplest way to implement undo.


You'll have
to correctly define a

.. code-block:: python

    from collections_undo import UndoManager

    mgr = UndoManager()  # prepare undo manager

    @mgr.undoable  # decorate any functions you want
    def f(a):
        print("do", a)

    @f.undo_def
    def f(a):
        print("undo", a)

Function ``f`` can be used as usual. To undo or redo the action, call :meth:`undo`
and :meth:`redo` from the :class:`UndoManager` instance.

.. code-block:: python

    >>> f(10)
    do 10
    >>> mgr.undo()
    undo 10
    >>> mgr.undo()  # nothing happens
    >>> mgr.redo()
    do 10
    >>> mgr.redo()  # nothing happens

Undo implementation for a custom class
======================================

.. code-block:: python

    from collections_undo import UndoManager

    class A:
        mgr = UndoManager()  # prepare undo manager

        def __init__(self):
            self.a = 0

        @mgr.undoable  # decorate any functions you want
        def set_value(self, a):
            self.a

        @f.undo_def
        def f(a):
            print("undo", a)
