from django.test import SimpleTestCase
from django.utils.connection import BaseConnectionHandler


class CustomConnectionHandler(BaseConnectionHandler):
    def create_connection(self, alias):
        return super().create_connection(alias)


class BaseConnectionHandlerTests(SimpleTestCase):
    def test_create_connection(self):
        handler = CustomConnectionHandler()
        msg = "Subclasses must implement create_connection()."
        with self.assertRaisesMessage(NotImplementedError, msg):
            handler.create_connection(None)

    def test_all_initialized_only(self):
        handler = CustomConnectionHandler({"default": {}})
        self.assertEqual(handler.all(initialized_only=True), [])
