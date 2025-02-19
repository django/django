import datetime
from io import StringIO
from unittest import mock

from django.core.management.base import OutputWrapper
from django.db.migrations.questioner import (
    InteractiveMigrationQuestioner,
    MigrationQuestioner,
)
from django.db.models import NOT_PROVIDED
from django.test import SimpleTestCase
from django.test.utils import override_settings


class FakeDirEntry:
    def __init__(self, name):
        self.name = name


class QuestionerTests(SimpleTestCase):
    def setUp(self):
        self.questioner = MigrationQuestioner()

    @override_settings(
        INSTALLED_APPS=["migrations"],
        MIGRATION_MODULES={"migrations": None},
    )
    def test_ask_initial_with_disabled_migrations(self):
        questioner = MigrationQuestioner()
        self.assertIs(False, questioner.ask_initial("migrations"))

    def simulate_migration_files(self, file_names):
        """Helper to create a list of FakeDirEntry based on provided file names"""
        return [FakeDirEntry(name) for name in file_names]

    def test_ask_initial_scenarios(self):
        scenarios = [
            (
                ["__init__.py"],
                True,
                """
                Simulate a migrations module with only an __init__.py file.
                In this case, ask_initial should return True.
                """,
            ),
            (
                ["__init__.py", "0001_initial.py"],
                False,
                """
                Simulate a migrations module with a __file__ attribute where the
                directory contains an extra .py file. In this case, ask_initial
                should return False.
                """,
            ),
            (
                ["__init__.py", "README.md"],
                True,
                """
                Simulate a migrations module with a __file__ attribute where the
                directory contains no other .py files except __init__.py. In this
                case, ask_initial should return True.
                """,
            ),
        ]
        for file_names, expected, msg in scenarios:
            with self.subTest(file_names=file_names):
                with (
                    mock.patch(
                        "django.db.migrations.questioner.os.scandir"
                    ) as mock_scandir,
                    mock.patch("importlib.import_module") as mock_import_module,
                ):

                    fake_module = type(
                        "FakeModule",
                        (),
                        {"__file__": "/fake/path/__init__.py"},
                    )()
                    mock_import_module.return_value = fake_module

                    mock_scandir.return_value.__enter__.return_value = (
                        self.simulate_migration_files(file_names)
                    )
                    self.assertEqual(
                        self.questioner.ask_initial("migrations"),
                        expected,
                        msg,
                    )

    def test_ask_initial_with_module_path_multiple(self):
        """Test scenarios with multiple paths"""
        paths_scenarios = [
            (
                ["/fake/path1", "/fake/path2"],
                False,
                """
                Simulate a migrations module with a __path__ attribute containing
                multiple entries. When multiple paths are present, the method
                returns False regardless of the directory contents.
                """,
            ),
            (
                ["/fake/path1"],
                True,
                """
                Simulate a migrations module with a __path__ attribute containing
                a single entry. It should work as if the module had a __file__
                attribute.
                """,
            ),
        ]
        for paths, expected, msg in paths_scenarios:
            with self.subTest(paths=paths):
                with (
                    mock.patch(
                        "django.db.migrations.questioner.os.scandir"
                    ) as mock_scandir,
                    mock.patch("importlib.import_module") as mock_import_module,
                ):

                    fake_module = type("FakeModule", (), {"__path__": paths})()
                    mock_import_module.return_value = fake_module
                    mock_scandir.return_value.__enter__.return_value = (
                        self.simulate_migration_files(["__init__.py"])
                    )

                    self.assertEqual(
                        self.questioner.ask_initial("migrations"),
                        expected,
                        msg,
                    )

    def test_ask_not_null_alteration(self):
        questioner = MigrationQuestioner()
        self.assertIsNone(
            questioner.ask_not_null_alteration("field_name", "model_name")
        )

    @mock.patch("builtins.input", return_value="2")
    def test_ask_not_null_alteration_not_provided(self, mock):
        questioner = InteractiveMigrationQuestioner(
            prompt_output=OutputWrapper(StringIO())
        )
        question = questioner.ask_not_null_alteration("field_name", "model_name")
        self.assertEqual(question, NOT_PROVIDED)


class QuestionerHelperMethodsTests(SimpleTestCase):
    def setUp(self):
        self.prompt = OutputWrapper(StringIO())
        self.questioner = InteractiveMigrationQuestioner(prompt_output=self.prompt)

    @mock.patch("builtins.input", return_value="datetime.timedelta(days=1)")
    def test_questioner_default_timedelta(self, mock_input):
        value = self.questioner._ask_default()
        self.assertEqual(value, datetime.timedelta(days=1))

    @mock.patch("builtins.input", return_value="")
    def test_questioner_default_no_user_entry(self, mock_input):
        value = self.questioner._ask_default(default="datetime.timedelta(days=1)")
        self.assertEqual(value, datetime.timedelta(days=1))

    @mock.patch("builtins.input", side_effect=["", "exit"])
    def test_questioner_no_default_no_user_entry(self, mock_input):
        with self.assertRaises(SystemExit):
            self.questioner._ask_default()
        self.assertIn(
            "Please enter some code, or 'exit' (without quotes) to exit.",
            self.prompt.getvalue(),
        )

    @mock.patch("builtins.input", side_effect=["bad code", "exit"])
    def test_questioner_no_default_syntax_error(self, mock_input):
        with self.assertRaises(SystemExit):
            self.questioner._ask_default()
        self.assertIn("SyntaxError: invalid syntax", self.prompt.getvalue())

    @mock.patch("builtins.input", side_effect=["datetim", "exit"])
    def test_questioner_no_default_name_error(self, mock_input):
        with self.assertRaises(SystemExit):
            self.questioner._ask_default()
        self.assertIn(
            "NameError: name 'datetim' is not defined", self.prompt.getvalue()
        )

    @mock.patch("builtins.input", side_effect=["datetime.dat", "exit"])
    def test_questioner_no_default_attribute_error(self, mock_input):
        with self.assertRaises(SystemExit):
            self.questioner._ask_default()
        self.assertIn(
            "AttributeError: module 'datetime' has no attribute 'dat'",
            self.prompt.getvalue(),
        )

    @mock.patch("builtins.input", side_effect=[KeyboardInterrupt()])
    def test_questioner_no_default_keyboard_interrupt(self, mock_input):
        with self.assertRaises(SystemExit):
            self.questioner._ask_default()
        self.assertIn("Cancelled.\n", self.prompt.getvalue())

    @mock.patch("builtins.input", side_effect=["", "n"])
    def test_questioner_no_default_no_user_entry_boolean(self, mock_input):
        value = self.questioner._boolean_input("Proceed?")
        self.assertIs(value, False)

    @mock.patch("builtins.input", return_value="")
    def test_questioner_default_no_user_entry_boolean(self, mock_input):
        value = self.questioner._boolean_input("Proceed?", default=True)
        self.assertIs(value, True)

    @mock.patch("builtins.input", side_effect=[10, "garbage", 1])
    def test_questioner_bad_user_choice(self, mock_input):
        question = "Make a choice:"
        value = self.questioner._choice_input(question, choices="abc")
        expected_msg = f"{question}\n" f" 1) a\n" f" 2) b\n" f" 3) c\n"
        self.assertIn(expected_msg, self.prompt.getvalue())
        self.assertEqual(value, 1)

    @mock.patch("builtins.input", side_effect=[KeyboardInterrupt()])
    def test_questioner_no_choice_keyboard_interrupt(self, mock_input):
        question = "Make a choice:"
        with self.assertRaises(SystemExit):
            self.questioner._choice_input(question, choices="abc")
        expected_msg = (
            f"{question}\n"
            f" 1) a\n"
            f" 2) b\n"
            f" 3) c\n"
            f"Select an option: \n"
            f"Cancelled.\n"
        )
        self.assertIn(expected_msg, self.prompt.getvalue())
