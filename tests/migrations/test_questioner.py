import datetime
from unittest import mock

from django.db.migrations.questioner import (
    InteractiveMigrationQuestioner, MigrationQuestioner,
)
from django.test import SimpleTestCase
from django.test.utils import captured_stdout, override_settings


class QuestionerTests(SimpleTestCase):
    @override_settings(
        INSTALLED_APPS=['migrations'],
        MIGRATION_MODULES={'migrations': None},
    )
    def test_ask_initial_with_disabled_migrations(self):
        questioner = MigrationQuestioner()
        self.assertIs(False, questioner.ask_initial('migrations'))

    @mock.patch('builtins.input', return_value='datetime.timedelta(days=1)')
    def test_timedelta_default(self, mock):
        questioner = InteractiveMigrationQuestioner()
        with captured_stdout():
            value = questioner._ask_default()
        self.assertEqual(value, datetime.timedelta(days=1))
