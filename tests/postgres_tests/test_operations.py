import unittest

from django.db import connection, models
from django.db.utils import NotSupportedError
from django.test import modify_settings

from tests.migrations.test_base import OperationTestBase

try:
    from django.contrib.postgres.operations import CreateIndexConcurrently
except ImportError:
    pass


@unittest.skipUnless(connection.vendor == 'postgresql', 'CreateIndexConcurrently is PostgreSQL-specific')
@modify_settings(INSTALLED_APPS={'append': 'migrations'})
class CreateIndexConcurrentlyTests(OperationTestBase):
    def test_create_index_concurrently_requires_name(self):
        with self.assertRaisesRegex(ValueError, 'require a name argument'):
            CreateIndexConcurrently('Pony', models.Index(fields=['pink']))

    def test_create_index_concurrently_description(self):
        operation = CreateIndexConcurrently('Pony', models.Index(fields=['pink'], name='pony_pink_idx'))
        self.assertEqual(
            operation.describe(),
            'Concurrently create index pony_pink_idx on field(s) pink of model Pony'
        )

    def test_create_index_concurrently_requires_atomic_false(self):
        app_label = 'test_pgcicraf'

        project_state = self.set_up_test_model(app_label)
        new_state = project_state.clone()

        operation = CreateIndexConcurrently('Pony', models.Index(fields=['pink'], name='pony_pink_idx'))

        with self.assertRaisesRegex(NotSupportedError, r'cannot be executed inside a transaction'):
            with connection.schema_editor(atomic=True) as editor:
                operation.database_forwards(app_label, editor, project_state, new_state)

    def test_create_index_concurrently(self):
        app_label = 'test_pgcic'

        project_state = self.set_up_test_model(app_label)
        new_state = project_state.clone()

        operation = CreateIndexConcurrently('Pony', models.Index(fields=['pink'], name='pony_pink_idx'))
        operation.state_forwards(app_label, new_state)
        self.assertEqual(len(new_state.models[app_label, 'pony'].options['indexes']), 1)

        definition = operation.deconstruct()
        self.assertEqual(definition[0], 'CreateIndexConcurrently')
        self.assertEqual(definition[1], [])
        self.assertEqual(definition[2], {
            'model_name': 'Pony',
            'index': models.Index(fields=['pink'], name='pony_pink_idx')
        })

        with connection.schema_editor(atomic=False) as editor:
            operation.database_forwards(app_label, editor, project_state, new_state)

        self.assertIndexExists('%s_pony' % app_label, ['pink'])

        with connection.schema_editor(atomic=False) as editor:
            operation.database_backwards(app_label, editor, project_state, new_state)

        self.assertIndexNotExists('%s_pony' % app_label, ['pink'])
