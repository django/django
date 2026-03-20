import pickle

from django.db.models.utils import create_namedtuple_class
from django.test import SimpleTestCase


class NamedTupleClassTests(SimpleTestCase):
    def test_immutability(self):
        row_class = create_namedtuple_class("field1", "field2")
        row = row_class("value1", "value2")
        with self.assertRaises(AttributeError):
            row.field3 = "value3"

    def test_field_access_by_name(self):
        row_class = create_namedtuple_class("name", "age")
        row = row_class("Alice", 30)
        self.assertEqual(row.name, "Alice")
        self.assertEqual(row.age, 30)

    def test_field_access_by_index(self):
        row_class = create_namedtuple_class("x", "y")
        row = row_class(10, 20)
        self.assertEqual(row[0], 10)
        self.assertEqual(row[1], 20)

    def test_equality(self):
        row_class = create_namedtuple_class("a", "b")
        row1 = row_class(1, 2)
        row2 = row_class(1, 2)
        self.assertEqual(row1, row2)

    def test_inequality(self):
        row_class = create_namedtuple_class("a", "b")
        row1 = row_class(1, 2)
        row2 = row_class(3, 4)
        self.assertNotEqual(row1, row2)

    def test_single_field(self):
        row_class = create_namedtuple_class("only")
        row = row_class("value")
        self.assertEqual(row.only, "value")
        self.assertEqual(len(row), 1)

    def test_repr(self):
        row_class = create_namedtuple_class("x", "y")
        row = row_class(1, 2)
        result = repr(row)
        self.assertIn("1", result)
        self.assertIn("2", result)

    def test_caching(self):
        cls1 = create_namedtuple_class("a", "b")
        cls2 = create_namedtuple_class("a", "b")
        self.assertIs(cls1, cls2)

    def test_pickle_roundtrip(self):
        row_class = create_namedtuple_class("x", "y")
        row = row_class(10, 20)
        pickled = pickle.dumps(row)
        restored = pickle.loads(pickled)
        self.assertEqual(row, restored)
