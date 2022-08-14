=======================
Property-like Framework
=======================

.. code-block:: python

    from collections_undo import UndoManager

    class A:
        mgr = UndoManager()

        def __init__(self, a=0):
            self._a = 0

        @mgr.property
        def a(self) -> int:
            return self._a

        @a.setter
        def a(self, val: int):
            self._a = val
