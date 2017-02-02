from django.core.exceptions import ImproperlyConfigured
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
