from django.utils import unittest
from django.utils._os import safe_join


class SafeJoinTests(unittest.TestCase):
    def test_base_path_ends_with_sep(self):
        self.assertEqual(
            safe_join("/abc/", "abc"),
            "/abc/abc",
        )

    def test_root_path(self):
        self.assertEqual(
            safe_join("/", "path"),
            "/path",
        )

        self.assertEqual(
            safe_join("/", ""),
            "/",
        )
