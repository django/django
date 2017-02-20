from django.core.exceptions import ImproperlyConfigured
from django.db.backends.utils import truncate_name
from django.db.utils import load_backend
from django.test import SimpleTestCase


class TestLoadBackend(SimpleTestCase):
    def test_load_backend_invalid_name(self):
        msg = (
            "'foo' isn't an available database backend.\n"
            "Try using 'django.db.backends.XXX', where XXX is one of:\n"
            "    'mysql', 'oracle', 'postgresql', 'sqlite3'"
        )
        with self.assertRaisesMessage(ImproperlyConfigured, msg) as cm:
            load_backend('foo')
        self.assertEqual(str(cm.exception.__cause__), "No module named 'foo'")

    def test_truncate_name(self):
        self.assertEqual(truncate_name('some_table', 10), 'some_table')
        self.assertEqual(truncate_name('some_long_table', 10), 'some_la38a')
        self.assertEqual(truncate_name('some_long_table', 10, 3), 'some_loa38')
        self.assertEqual(truncate_name('some_long_table'), 'some_long_table')
        # "user"."table" syntax
        self.assertEqual(truncate_name('username"."some_table', 10), 'username"."some_table')
        self.assertEqual(truncate_name('username"."some_long_table', 10), 'username"."some_la38a')
        self.assertEqual(truncate_name('username"."some_long_table', 10, 3), 'username"."some_loa38')
