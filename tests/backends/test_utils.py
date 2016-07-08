from django.core.exceptions import ImproperlyConfigured
from django.db.utils import load_backend
from django.test import SimpleTestCase
from django.utils import six


class TestLoadBackend(SimpleTestCase):
    def test_load_backend_invalid_name(self):
        msg = (
            "'foo' isn't an available database backend.\n"
            "Try using 'django.db.backends.XXX', where XXX is one of:\n"
            "    'mysql', 'oracle', 'postgresql', 'sqlite3'\n"
            "Error was: No module named %s"
        ) % "foo.base" if six.PY2 else "'foo'"
        with self.assertRaisesMessage(ImproperlyConfigured, msg):
            load_backend('foo')
