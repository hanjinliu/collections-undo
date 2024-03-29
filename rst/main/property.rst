=======================
Property-like Framework
=======================

In Python, simple operations can be implemented as a property. ``UndoManager``
has a ``property`` decorator method for this purpose.

.. code-block:: python

    from collections_undo import UndoManager

    class A:
        mgr = UndoManager()

        def __init__(self):
            self._x = 0

        @mgr.property
        def x(self) -> int:
            return self._x

        @x.setter
        def x(self, val: int):
            self._x = val

:attr:`x` is now a undoable property.

.. code-block:: python

    >>> a = A()
    >>> a.x = 10
    >>> a.x
    10
    >>> a.mgr.undo()
    >>> a.x
    0
    >>> a.mgr.redo()
    >>> a.x
    10

.. note::

    You can consider this as a special case of :doc:`interface`.
