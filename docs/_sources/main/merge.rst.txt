==============
Merge Commands
==============

Why merge?
==========

Suppose you have many undoable objects in a class. Undoable commands may also be called
in other methods, like the :meth:`combo` method defined below.

.. code-block:: python

    from collections_undo import UndoManager

    class A:
        mgr = UndoManager()

        @mgr.undoable
        def f(self): ...

        @mgr.interface
        def g(self): ...

        @mgr.property
        def h(self): ...

        def combo(self):
            self.f()
            self.g()
            self.h = 1


There's no problem in principle, but the undo stack will be cluttered with many commands after
calling :meth:`combo`. Intuitively, you may want to undo the whole combo in a single step, like
pushing "Ctrl+Z" once.

In this case, you can use the :meth:`merge` context manager. All the command generated within
the context will be merged into a single command. Upon undo, all the child commands will be
undone in a reversed order.

.. code-block:: python

    def combo(self):
        with self.mgr.merging():
            self.f()
            self.g()
            self.h = 1


Formatting merged commands
==========================

TODO
