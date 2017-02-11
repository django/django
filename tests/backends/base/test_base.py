from django.db import DEFAULT_DB_ALIAS, connection, connections
from django.db.backends.base.base import BaseDatabaseWrapper
from django.test import SimpleTestCase


class DatabaseWrapperTests(SimpleTestCase):

    def test_initialization_class_attributes(self):
        """
        The "initialization" class attributes like client_class and
        creation_class should be set on the class and reflected in the
        corresponding instance attributes of the instantiated backend.
        """
        conn = connections[DEFAULT_DB_ALIAS]
        conn_class = type(conn)
        attr_names = [
            ('client_class', 'client'),
            ('creation_class', 'creation'),
            ('features_class', 'features'),
            ('introspection_class', 'introspection'),
            ('ops_class', 'ops'),
            ('validation_class', 'validation'),
        ]
        for class_attr_name, instance_attr_name in attr_names:
            class_attr_value = getattr(conn_class, class_attr_name)
            self.assertIsNotNone(class_attr_value)
            instance_attr_value = getattr(conn, instance_attr_name)
            self.assertIsInstance(instance_attr_value, class_attr_value)

    def test_initialization_display_name(self):
        self.assertEqual(BaseDatabaseWrapper.display_name, 'unknown')
        self.assertNotEqual(connection.display_name, 'unknown')
