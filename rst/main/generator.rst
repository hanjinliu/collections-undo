===================
Generator Framework
===================

Python generator is a versatile tool. In :mod:`collections-undo` you can also use
generator functions to define undoable functions, in a similar way as you define
context managers with :meth:`contextlib.contextmanager`.

Following example shows how to define an undoable setter.

.. code-block:: python

    from collections_undo import UndoManager

    class A:
        mgr = UndoManager()

        def __init__(self):
        self._state = 0

        @mgr.undoable_gen
        def set_state(self, x):
            # do-statement before yield
            old = x
            self._state = x
            yield
            # undo-statement after yield
            self._state = old
