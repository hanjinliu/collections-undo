===============
Reduce Commands
===============

Reduction is a simplification of commands that came from the same function but with (possibly)
different arguments.

Why reduction, and how?
=======================

Reduction is needed in several cases. For example, if a parameter changes continuously, such as
moving a point by pushing an arrow key for a long time, you should not record all the
intermediate state.

.. code-block:: python

    from collections_undo import UndoManager, arguments as args

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
            return args(args_new["x"], args_old["x_old"])

The function wrapped by :meth:`reduce_rule` will be called to concatenate two commands,
in which ``args_old`` and ``args_new`` are the arguments of the two commands.
Reduction rule must return a new argument that will be used to create a new command. In
the example above, ``args_new["x"]`` and ``args_old["x_old"]`` correspond to ``x`` and
``x_old`` respectively.

The type of ``args_old`` (and ``args_new``) is an immutable, sequential mapping object.
You can also get any of the arguments by the key, index or unpacking.

.. code-block:: python

    def _move_to_reduce_rule(self, args_old, args_new):
        return args(args_new["x"], args_old["x_old"])

    def _move_to_reduce_rule(self, args_old, args_new):
        return args(args_new[0], args_old[1])

    def _move_to_reduce_rule(self, args_old, args_new):
        x_old, _ = args_old
        _, x_new= args_new
        return args(x_new, x_old)

This reduction mode will be activated by calling ``mgr.set_reducing(True)`` or temporarily
by ``with mgr.reducing()``.

.. code-block:: python

    a = A()
    with a.mgr.reducing():
        # moving from 0 to 1, 2, and finally 3
        a.move(1)
        a.move(2)
        a.move(3)

Here ``pos`` is set to 3, but single undo will revert ``pos`` to ``0``.

Default reduction rule
======================

In the server/receiver framework and property-like framework, reduction rule is defined
by default.

.. code-block:: python

    from collections_undo import UndoManager, arguments as args

    class A:
        mgr = UndoManager()

        def __init__(self):
            self.pos = 0

        @mgr.interface
        def move(self, x):
            self.pos = x

        @move.server
        def move(self, x):
            return args(x)
