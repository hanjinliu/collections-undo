===============
Reduce Commands
===============

Reduction is a simplification of commands that came from the same function but with (possibly)
different arguments.

Why reduction?
==============

Reduction is needed in several cases. For example,

Examples
========

.. code-block:: python

    from collections_undo import UndoManager

    class A:
        mgr = UndoManager()

        def __init__(self):
            self.pos = 0

        def move(self, x):
            self._move_to(x, self.pos)

        @mgr.undoable
        def _move_to(self, x, x_old):
            self.pos = x

        @_move_to.undo_def
        def _move_to(self, x, x_old):
            self.pos = x_old

        @_move_to.reduce_rule
        def _move_to_reduce_rule(self, args_old, args_new):
            return (args_new["x"], args_old["x_old"]), {}
