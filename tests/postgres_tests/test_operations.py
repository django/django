import unittest

from tests.migrations.test_base import OperationTestBase

from django.db import connection, models
from django.db.utils import NotSupportedError
from django.test import modify_settings

try:
    from django.contrib.postgres.operations import AddIndexConcurrently, RemoveIndexConcurrently
    from django.contrib.postgres.indexes import BrinIndex
except ImportError:
    pass


@unittest.skipUnless(connection.vendor == 'postgresql', 'AddIndexConcurrently is PostgreSQL-specific')
@modify_settings(INSTALLED_APPS={'append': 'migrations'})
class AddIndexConcurrentlyTests(OperationTestBase):
    def test_add_index_concurrently_requires_name(self):
        with self.assertRaisesRegex(ValueError, 'require a name argument'):
            AddIndexConcurrently('Pony', models.Index(fields=['pink']))

    def test_add_index_concurrently_description(self):
        operation = AddIndexConcurrently('Pony', models.Index(fields=['pink'], name='pony_pink_idx'))
        self.assertEqual(
            operation.describe(),
            'Concurrently create index pony_pink_idx on field(s) pink of model Pony'
        )

    def test_add_index_concurrently_requires_atomic_false(self):
        app_label = 'test_pgcicraf'

        project_state = self.set_up_test_model(app_label)
        new_state = project_state.clone()

        operation = AddIndexConcurrently('Pony', models.Index(fields=['pink'], name='pony_pink_idx'))

        with self.assertRaisesRegex(NotSupportedError, r'cannot be executed inside a transaction'):
            with connection.schema_editor(atomic=True) as editor:
                operation.database_forwards(app_label, editor, project_state, new_state)

    def test_add_index_concurrently(self):
        app_label = 'test_pgcic'

        project_state = self.set_up_test_model(app_label)
        new_state = project_state.clone()

        operation = AddIndexConcurrently('Pony', models.Index(fields=['pink'], name='pony_pink_idx'))
        operation.state_forwards(app_label, new_state)
        self.assertEqual(len(new_state.models[app_label, 'pony'].options['indexes']), 1)

        definition = operation.deconstruct()
        self.assertEqual(definition[0], 'AddIndexConcurrently')
        self.assertEqual(definition[1], [])
        self.assertEqual(definition[2], {
            'model_name': 'Pony',
            'index': models.Index(fields=['pink'], name='pony_pink_idx')
        })

        with connection.schema_editor(atomic=False) as editor:
            operation.database_forwards(app_label, editor, project_state, new_state)

        self.assertIndexExists('%s_pony' % app_label, ['pink'])

        with connection.schema_editor(atomic=False) as editor:
            operation.database_backwards(app_label, editor, new_state, project_state)

        self.assertIndexNotExists('%s_pony' % app_label, ['pink'])

    def test_add_brin_index_concurrently(self):
        """
        The AddIndexConcurrently operation should support all index types.

        Verify that the operation properly handles the creation of a BRIN index
        as a spot check, ensuring it does not always use the default (B-tree).
        """
        app_label = 'test_pgcbic'

        project_state = self.set_up_test_model(app_label)
        new_state = project_state.clone()

        operation = AddIndexConcurrently('Pony', BrinIndex(fields=['pink'], name='pony_pink_brin_idx'))

        with connection.schema_editor(atomic=False) as editor:
            operation.database_forwards(app_label, editor, project_state, new_state)

        self.assertIndexExists('%s_pony' % app_label, ['pink'], index_type='brin')

        with connection.schema_editor(atomic=False) as editor:
            operation.database_backwards(app_label, editor, new_state, project_state)

        self.assertIndexNotExists('%s_pony' % app_label, ['pink'])


@unittest.skipUnless(connection.vendor == 'postgresql', 'RemoveIndexConcurrently is PostgreSQL-specific')
@modify_settings(INSTALLED_APPS={'append': 'migrations'})
class RemoveIndexConcurrentlyTests(OperationTestBase):
    def test_remove_index_concurrently_description(self):
        operation = RemoveIndexConcurrently('Pony', 'pony_pink_idx')
        self.assertEqual(
            operation.describe(),
            'Concurrently remove index pony_pink_idx from Pony'
        )

    def test_remove_index_concurrently_requires_atomic_false(self):
        app_label = 'test_pgdicraf'

        project_state = self.set_up_test_model(app_label, index=True)
        new_state = project_state.clone()

        operation = RemoveIndexConcurrently('Pony', 'pony_pink_idx')

        with self.assertRaisesRegex(NotSupportedError, r'cannot be executed inside a transaction'):
            with connection.schema_editor(atomic=True) as editor:
                operation.database_forwards(app_label, editor, project_state, new_state)

    def test_remove_index_concurrently(self):
        app_label = 'test_pgdic'

        project_state = self.set_up_test_model(app_label, index=True)
        new_state = project_state.clone()

        operation = RemoveIndexConcurrently('Pony', 'pony_pink_idx')
        operation.state_forwards(app_label, new_state)
        self.assertEqual(len(new_state.models[app_label, 'pony'].options['indexes']), 0)

        definition = operation.deconstruct()
        self.assertEqual(definition[0], 'RemoveIndexConcurrently')
        self.assertEqual(definition[1], [])
        self.assertEqual(definition[2], {
            'model_name': 'Pony',
            'name': 'pony_pink_idx'
        })

        with connection.schema_editor(atomic=False) as editor:
            operation.database_forwards(app_label, editor, project_state, new_state)

        self.assertIndexNotExists('%s_pony' % app_label, ['pink'])

        with connection.schema_editor(atomic=False) as editor:
            operation.database_backwards(app_label, editor, new_state, project_state)

        self.assertIndexExists('%s_pony' % app_label, ['pink'])
