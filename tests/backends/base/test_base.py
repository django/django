from unittest.mock import MagicMock

from django.db import DEFAULT_DB_ALIAS, connection, connections
from django.db.backends.base.base import BaseDatabaseWrapper
from django.test import SimpleTestCase, TestCase

from ..models import Square


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
            ("client_class", "client"),
            ("creation_class", "creation"),
            ("features_class", "features"),
            ("introspection_class", "introspection"),
            ("ops_class", "ops"),
            ("validation_class", "validation"),
        ]
        for class_attr_name, instance_attr_name in attr_names:
            class_attr_value = getattr(conn_class, class_attr_name)
            self.assertIsNotNone(class_attr_value)
            instance_attr_value = getattr(conn, instance_attr_name)
            self.assertIsInstance(instance_attr_value, class_attr_value)

    def test_initialization_display_name(self):
        self.assertEqual(BaseDatabaseWrapper.display_name, "unknown")
        self.assertNotEqual(connection.display_name, "unknown")


class ExecuteWrapperTests(TestCase):
    @staticmethod
    def call_execute(connection, params=None):
        ret_val = "1" if params is None else "%s"
        sql = "SELECT " + ret_val + connection.features.bare_select_suffix
        with connection.cursor() as cursor:
            cursor.execute(sql, params)

    def call_executemany(self, connection, params=None):
        # executemany() must use an update query. Make sure it does nothing
        # by putting a false condition in the WHERE clause.
        sql = "DELETE FROM {} WHERE 0=1 AND 0=%s".format(Square._meta.db_table)
        if params is None:
            params = [(i,) for i in range(3)]
        with connection.cursor() as cursor:
            cursor.executemany(sql, params)

    @staticmethod
    def mock_wrapper():
        return MagicMock(side_effect=lambda execute, *args: execute(*args))

    def test_wrapper_invoked(self):
        wrapper = self.mock_wrapper()
        with connection.execute_wrapper(wrapper):
            self.call_execute(connection)
        self.assertTrue(wrapper.called)
        (_, sql, params, many, context), _ = wrapper.call_args
        self.assertIn("SELECT", sql)
        self.assertIsNone(params)
        self.assertIs(many, False)
        self.assertEqual(context["connection"], connection)

    def test_wrapper_invoked_many(self):
        wrapper = self.mock_wrapper()
        with connection.execute_wrapper(wrapper):
            self.call_executemany(connection)
        self.assertTrue(wrapper.called)
        (_, sql, param_list, many, context), _ = wrapper.call_args
        self.assertIn("DELETE", sql)
        self.assertIsInstance(param_list, (list, tuple))
        self.assertIs(many, True)
        self.assertEqual(context["connection"], connection)

    def test_database_queried(self):
        wrapper = self.mock_wrapper()
        with connection.execute_wrapper(wrapper):
            with connection.cursor() as cursor:
                sql = "SELECT 17" + connection.features.bare_select_suffix
                cursor.execute(sql)
                seventeen = cursor.fetchall()
                self.assertEqual(list(seventeen), [(17,)])
            self.call_executemany(connection)

    def test_nested_wrapper_invoked(self):
        outer_wrapper = self.mock_wrapper()
        inner_wrapper = self.mock_wrapper()
        with connection.execute_wrapper(outer_wrapper), connection.execute_wrapper(
            inner_wrapper
        ):
            self.call_execute(connection)
            self.assertEqual(inner_wrapper.call_count, 1)
            self.call_executemany(connection)
            self.assertEqual(inner_wrapper.call_count, 2)

    def test_outer_wrapper_blocks(self):
        def blocker(*args):
            pass

        wrapper = self.mock_wrapper()
        c = connection  # This alias shortens the next line.
        with c.execute_wrapper(wrapper), c.execute_wrapper(blocker), c.execute_wrapper(
            wrapper
        ):
            with c.cursor() as cursor:
                cursor.execute("The database never sees this")
                self.assertEqual(wrapper.call_count, 1)
                cursor.executemany("The database never sees this %s", [("either",)])
                self.assertEqual(wrapper.call_count, 2)

    def test_wrapper_gets_sql(self):
        wrapper = self.mock_wrapper()
        sql = "SELECT 'aloha'" + connection.features.bare_select_suffix
        with connection.execute_wrapper(wrapper), connection.cursor() as cursor:
            cursor.execute(sql)
        (_, reported_sql, _, _, _), _ = wrapper.call_args
        self.assertEqual(reported_sql, sql)

    def test_wrapper_connection_specific(self):
        wrapper = self.mock_wrapper()
        with connections["other"].execute_wrapper(wrapper):
            self.assertEqual(connections["other"].execute_wrappers, [wrapper])
            self.call_execute(connection)
        self.assertFalse(wrapper.called)
        self.assertEqual(connection.execute_wrappers, [])
        self.assertEqual(connections["other"].execute_wrappers, [])
