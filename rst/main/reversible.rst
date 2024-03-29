=========================
Forward-reverse Framework
=========================

The forward-reverse framework is the simplest way to implement undo.

The "forward" function is the "do" operation. Any function can be considered as a
forward function. The "reverse" function is a conjugative function to the forward
one and carries out the opposite operation.

When a ``UndoManager`` undoes a command, it passes all the arguments of forward
call to the reverse function. For instance, if you called ``f(10)`` and the
reverse function for ``f`` is ``g``, then the undo operation will be ``g(10)``.
Thus, you have to make sure that calling reverse function after the forward
function will restore the original state.

Here's a simple example. Defining a forward-reverse set is very similar to defining
getter and setter of a Python ``property``.

.. code-block:: python

    from collections_undo import UndoManager

    mgr = UndoManager()  # prepare undo manager

    @mgr.undoable  # decorate any functions you want
    def f(a):
        print("do", a)

    @f.undo_def  # define a reverse function
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

``UndoManager`` can be used as a field-like object of a class. This is the best way
to define object-specific undo managers.

Following example shows how to make the attribute :attr:`x` undoable.

.. code-block:: python

    from collections_undo import UndoManager

    class A:
        mgr = UndoManager()

        def __init__(self):
            self.x = 0

        def set_value(self, x):
            return self._set_value(x, self.x)

        @mgr.undoable
        def _set_value(self, x, x_old):
            self.x = x

        @_set_value.undo_def
        def _set_value(self, x, x_old):
            self.x = x_old

Note that to set an attribute in an undoable way, you have to pass the old value to
the forward function because it is needed for the reverse function.

.. note::

    If you feel this is too complicated, it's totally OK. That's why ``collections-undo``
    has other frameworks. See :doc:`interface` and :doc:`property` for the better way to
    do this.

Class :class:`A` works like this.

.. code-block:: python

    >>> a = A()
    >>> a.set_value(10)
    >>> a.x
    10
    >>> a.mgr.undo()
    >>> a.x
    0
    >>> a.mgr.redo()
    >>> a.x
    10
