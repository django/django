import os
from unittest import TestCase

from django.template import Engine

from .utils import TEMPLATE_DIR


class OriginTestCase(TestCase):
    def setUp(self):
        self.engine = Engine(dirs=[TEMPLATE_DIR])

    def test_origin_compares_equal(self):
        a = self.engine.get_template("index.html")
        b = self.engine.get_template("index.html")
        self.assertEqual(a.origin, b.origin)
        # Use assertIs() to test __eq__/__ne__.
        self.assertIs(a.origin == b.origin, True)
        self.assertIs(a.origin != b.origin, False)

    def test_origin_compares_not_equal(self):
        a = self.engine.get_template("first/test.html")
        b = self.engine.get_template("second/test.html")
        self.assertNotEqual(a.origin, b.origin)
        # Use assertIs() to test __eq__/__ne__.
        self.assertIs(a.origin == b.origin, False)
        self.assertIs(a.origin != b.origin, True)

    def test_repr(self):
        a = self.engine.get_template("index.html")
        name = os.path.join(TEMPLATE_DIR, "index.html")
        self.assertEqual(repr(a.origin), "<Origin name=%r>" % name)
