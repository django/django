from pathlib import Path

from django.db.backends.sqlite3.client import DatabaseClient
from django.test import SimpleTestCase


class SqliteDbshellCommandTestCase(SimpleTestCase):
    def settings_to_cmd_args_env(self, settings_dict, parameters=None):
        if parameters is None:
            parameters = []
        return DatabaseClient.settings_to_cmd_args_env(settings_dict, parameters)

    def test_path_name(self):
        self.assertEqual(
            self.settings_to_cmd_args_env({'NAME': Path('test.db.sqlite3')}),
            (['sqlite3', 'test.db.sqlite3'], None),
        )

    def test_parameters(self):
        self.assertEqual(
            self.settings_to_cmd_args_env({'NAME': 'test.db.sqlite3'}, ['-help']),
            (['sqlite3', 'test.db.sqlite3', '-help'], None),
        )
