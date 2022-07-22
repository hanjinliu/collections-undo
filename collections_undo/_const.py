class _Empty:
    def __repr__(self) -> str:
        return "<undo.CommandStack.empty>"

    def __str__(self) -> str:
        return "<empty>"


empty = _Empty()
