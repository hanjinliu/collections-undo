.. collections-undo documentation master file, created by
   sphinx-quickstart on Sun Aug 14 11:59:58 2022.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

collections-undo
================

``collections-undo`` is a general undo/redo framework for Python.

This module makes it easier to record actions and implement undo/redo.

Installation
------------

.. code-block:: bash

   pip install -U collections-undo

Basic usage
-----------

``collections-undo`` uses ``UndoManager`` for command registration.
``UndoManager`` has several decorators that convert functions into undoable
ones. The history of function call is recorded in the ``UndoManager``.

.. code-block:: python

   from collections_undo import UndoManager

   mgr = UndoManager()

Here are three most practically useful decorators listed up below.

.. toctree::
   :maxdepth: 1

   ./main/reversible
   ./main/interface
   ./main/property

Undo-implemented abstract classes
---------------------------------

Python ``list``, ``dict`` and ``set`` are the fundamental objects of programs.
If you can attribute all the operations

.. toctree::
   :maxdepth: 1

   ./main/undoable_list
   ./main/undoable_dict
   ./main/undoable_set



Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
