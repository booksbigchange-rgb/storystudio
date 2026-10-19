"""Test cartoon editor history without starting a graphical window."""
from pathlib import Path
import copy
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'integrations' / 'lemo-lite'))
import project
from studio_ui import StudioApp


class FakeStatus:
    def __init__(self):
        self.value = ''
    def set(self, value):
        self.value = value


class HistoryTests(unittest.TestCase):
    def make_editor(self):
        # Avoid Tk initialization; exercise the real editor history methods.
        editor = object.__new__(StudioApp)
        editor.document = project.new_project()
        editor.undo_stack = []
        editor.redo_stack = []
        editor.busy = False
        editor.status = FakeStatus()
        editor.selected = lambda: 0
        editor.mark_dirty = lambda: None
        editor.refresh = lambda index=0: None
        editor.select_scene = lambda: None
        editor.request_preview = lambda: None
        return editor

    def test_undo_redo_and_branching(self):
        editor = self.make_editor()
        original = copy.deepcopy(editor.document)
        editor.remember_edit()
        editor.document['scenes'][0]['title'] = 'First'
        editor.undo()
        self.assertEqual(editor.document, original)
        editor.redo()
        self.assertEqual(editor.document['scenes'][0]['title'], 'First')
        editor.undo()
        editor.remember_edit()
        editor.document['scenes'][0]['title'] = 'Different'
        self.assertEqual(editor.redo_stack, [])

    def test_history_is_bounded(self):
        editor = self.make_editor()
        for i in range(60):
            editor.remember_edit()
            editor.document['scenes'][0]['title'] = str(i)
        self.assertEqual(len(editor.undo_stack), 50)


if __name__ == '__main__':
    unittest.main()
