from collections_undo import UndoManager

mgr = UndoManager()

@mgr.command
def f(x):
    print(f"do {x}")

@f.undo_def
def f(x):
    print(f"undo {x}")

if __name__ == "__main__":
    f(0)
    f(1)
    f(2)
    mgr.undo()
    mgr.undo()
    mgr.redo()

    print("\n\ncurrent state of UndoManager\n")
    print(mgr)
