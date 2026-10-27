"""Bounded undo/redo of whole timeline documents (small JSON, so snapshots are cheap)."""
import copy


class History:
    def __init__(self, limit=50):
        self.limit = limit
        self.past, self.future = [], []

    def checkpoint(self, doc):
        """Remember ``doc`` as it is before a change; a new change discards the redo branch."""
        if self.past and self.past[-1] == doc:
            return
        self.past.append(copy.deepcopy(doc))
        del self.past[:-self.limit]
        self.future.clear()

    def undo(self, current):
        if not self.past:
            return None
        self.future.append(copy.deepcopy(current))
        return self.past.pop()

    def redo(self, current):
        if not self.future:
            return None
        self.past.append(copy.deepcopy(current))
        return self.future.pop()

    def clear(self):
        self.past.clear()
        self.future.clear()

    def can_undo(self):
        return bool(self.past)

    def can_redo(self):
        return bool(self.future)
