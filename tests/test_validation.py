"""MAX-VALIDATION L2 coverage — jsui/v8ui message-handler checks."""

import unittest


class JsuiHandlerCoverageTests(unittest.TestCase):
    """MAX-VALIDATION L2 — see m4l_builder/jsui_coverage.py."""

    def _run(self, js, selector_box):
        from m4l_builder.jsui_coverage import jsui_coverage_issues
        boxes = [
            {"box": {"id": "disp", "maxclass": "v8ui", "filename": "d.js"}},
            {"box": selector_box},
        ]
        lines = [{"patchline": {"source": [selector_box["id"], 0],
                                "destination": ["disp", 0]}}]
        return jsui_coverage_issues(boxes, lines, {"d.js": {"content": js}})

    def test_flags_prepend_with_no_handler(self):
        found = self._run("function paint(){}\n",
                          {"id": "p", "maxclass": "newobj",
                           "text": "prepend set_missing"})
        self.assertEqual([(f[0], f[1]) for f in found], [("disp", "set_missing")])

    def test_flags_message_box_and_loadmess(self):
        for text in ("set_missing 1", None):
            box = ({"id": "p", "maxclass": "message", "text": "set_missing 1"}
                   if text else
                   {"id": "p", "maxclass": "newobj", "text": "loadmess set_missing 1"})
            self.assertEqual(len(self._run("function paint(){}\n", box)), 1)

    def test_declared_handler_is_clean(self):
        self.assertEqual(self._run("function set_value(v){}\n",
                                   {"id": "p", "maxclass": "newobj",
                                    "text": "prepend set_value"}), [])

    def test_anything_covers_everything(self):
        self.assertEqual(self._run("function anything(){}\n",
                                   {"id": "p", "maxclass": "newobj",
                                    "text": "prepend whatever"}), [])

    def test_bare_number_is_not_a_selector(self):
        # "42" lands on msg_int, not on a function called 42.
        self.assertEqual(self._run("function paint(){}\n",
                                   {"id": "p", "maxclass": "message",
                                    "text": "42"}), [])

    def test_object_level_messages_never_reach_the_script(self):
        self.assertEqual(self._run("function paint(){}\n",
                                   {"id": "p", "maxclass": "message",
                                    "text": "bringtofront"}), [])

    def test_int_maps_to_msg_int_not_to_a_function_named_int(self):
        self.assertEqual(self._run("function msg_int(v){}\n",
                                   {"id": "p", "maxclass": "newobj",
                                    "text": "prepend int"}), [])
