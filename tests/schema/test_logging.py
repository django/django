from django.db import connection
from django.test import TestCase
from django.test.utils import patch_logger


class SchemaLoggerTests(TestCase):

    def test_extra_args(self):
        editor = connection.schema_editor(collect_sql=True)
        sql = 'SELECT * FROM foo WHERE id in (%s, %s)'
        params = [42, 1337]
        with patch_logger('django.db.backends.schema', 'debug', log_kwargs=True) as logger:
            editor.execute(sql, params)
        self.assertEqual(
            logger,
            [(
                'SELECT * FROM foo WHERE id in (%s, %s); (params [42, 1337])',
                {'extra': {'sql': sql, 'params': params}},
            )]
        )
