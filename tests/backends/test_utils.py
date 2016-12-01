from django.core.exceptions import ImproperlyConfigured
from django.db.utils import load_backend
from django.test import SimpleTestCase


class TestLoadBackend(SimpleTestCase):
    def test_load_backend_invalid_name(self):
        msg = (
            "'foo' isn't an available database backend.\n"
            "Try using 'django.db.backends.XXX', where XXX is one of:\n"
            "    'mysql', 'oracle', 'postgresql', 'sqlite3'\n"
            "Error was: No module named 'foo'"
        )
        with self.assertRaisesMessage(ImproperlyConfigured, msg):
            load_backend('foo')
