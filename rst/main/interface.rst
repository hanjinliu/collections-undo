=========================
Server-receiver Framework
=========================

Previous :doc:`reversible` section showed how to define undoable operations.
Although it covers the fundamental functionalities, it is not convenient to
use -- you always have to pass the old state and the new state to the function.
For more complicated functions, the arguments will be more cumbersome.

In most cases, you will pass the current state of an instance as the old state.
In the previous example,

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

the :meth:`set_value` method uses ``self.x`` to describe current instance state.

.. code-block:: python

    def set_value(self, x):
        return self._set_value(x, self.x)

Define serve/receiver interface
-------------------------------

A new framework for this type of implementation is the "server-receiver"
framework. The most important point here is that the "set_value" function
is called both in do and undo, as long as proper "old_value" is provided.

.. code-block:: python

    self.set_value(new_value)  # do
    self.set_value(old_value)  # undo

Providing ``new_value`` is totally dependent on user input so it is beyond
management by the undo manager. What an undo manager should do is to record the
current state as the ``old_value`` before actually calling the :meth:`set_value`
function. Therefore, all you have to do is to define a function that will
**serve** the current state as arguments.

Here's the precise definition of "server" and "receiver".

* **Server** -- a function that returns the current state as a ``tuple`` and a
  ``dict`` (positional and keyword arguments). Using ``args`` function is highly
  recommended.
* **Receiver** -- a function that receive arguments and do something (you can consider
  it identical to the forward function in the last section).

.. note::

    The signature of server, receiver and the returned values of server must be the
    same.

Example of using the interface
------------------------------

Following example uses the server-receiver interface to implement the previous
example. Note that again, the definition is very similar to ``property``.

.. code-block:: python

    from collections_undo import UndoManager, args

    class A:
        mgr = UndoManager()

        def __init__(self):
            self.x = 0

        @mgr.interface  # receiver
        def set_value(self, x):
            # this function should look identical to what you do without thinking
            # of undoing this.
            self.x = x

        @set_value.server  # define the server
        def set_value(self, x):  # x is useless here
            return args(self.x)

When a value is set

.. code-block:: python

    a = A()
    a.set_value(10)

the current state (``self.x == 0``) is recorded (served) to the undo manager by
the server ``a.set_value._server(10)`` before actually setting the new value.
When this operation is undone,

.. code-block:: python

    a.mgr.undo()

receiver function receives the arguments from the previously called server. This
undo operation is almost equivalent to the following:

.. code-block:: python

    args, kwargs = a.set_value._server(10)
    a.set_value(*args, **kwargs)
