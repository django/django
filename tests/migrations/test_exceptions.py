from thibaud.db.migrations.exceptions import NodeNotFoundError
from thibaud.test import SimpleTestCase


class ExceptionTests(SimpleTestCase):
    def test_node_not_found_error_repr(self):
        node = ("some_app_label", "some_migration_label")
        error_repr = repr(NodeNotFoundError("some message", node))
        self.assertEqual(
            error_repr, "NodeNotFoundError(('some_app_label', 'some_migration_label'))"
        )
