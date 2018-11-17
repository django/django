from django.db import connection, models
from django.test import TestCase


class SchemaEditorTests(TestCase):

    def test_effective_default_callable(self):
        """SchemaEditor.effective_default() shouldn't call callable defaults."""
        class MyStr(str):
            def __call__(self):
                return self

        class MyCharField(models.CharField):
            def _get_default(self):
                return self.default

            def get_db_prep_save(self, default, connection):
                return default

        field = MyCharField(max_length=1, default=MyStr)
        with connection.schema_editor() as editor:
            self.assertEqual(editor.effective_default(field), MyStr)
