import os
from argparse import ArgumentDefaultsHelpFormatter
from io import StringIO
from unittest import mock

from admin_scripts.tests import AdminScriptTestCase

from django.apps import apps
from django.core import management
from django.core.checks import Tags
from django.core.management import BaseCommand, CommandError, find_commands
from django.core.management.utils import (
    find_command,
    get_random_secret_key,
    is_ignored_path,
    normalize_path_patterns,
    popen_wrapper,
)
from django.db import connection
from django.test import SimpleTestCase, override_settings
from django.test.utils import captured_stderr, extend_sys_path
from django.utils import translation

from .management.commands import dance


# A minimal set of apps to avoid system checks running on all apps.
@override_settings(
    INSTALLED_APPS=[
        "django.contrib.auth",
        "django.contrib.contenttypes",
        "user_commands",
    ],
)
class CommandTests(SimpleTestCase):
    def test_command(self):
        out = StringIO()
        management.call_command("dance", stdout=out)
        self.assertIn("I don't feel like dancing Rock'n'Roll.\n", out.getvalue())

    def test_command_style(self):
        out = StringIO()
        management.call_command("dance", style="Jive", stdout=out)
        self.assertIn("I don't feel like dancing Jive.\n", out.getvalue())
        # Passing options as arguments also works (thanks argparse)
        management.call_command("dance", "--style", "Jive", stdout=out)
        self.assertIn("I don't feel like dancing Jive.\n", out.getvalue())

    def test_language_preserved(self):
        with translation.override("fr"):
            management.call_command("dance", verbosity=0)
            self.assertEqual(translation.get_language(), "fr")

    def test_explode(self):
        """An unknown command raises CommandError"""
        with self.assertRaisesMessage(CommandError, "Unknown command: 'explode'"):
            management.call_command(("explode",))

    def test_system_exit(self):
        """Exception raised in a command should raise CommandError with
        call_command, but SystemExit when run from command line
        """
        with self.assertRaises(CommandError) as cm:
            management.call_command("dance", example="raise")
        self.assertEqual(cm.exception.returncode, 3)
        dance.Command.requires_system_checks = []
        try:
            with captured_stderr() as stderr, self.assertRaises(SystemExit) as cm:
                management.ManagementUtility(
                    ["manage.py", "dance", "--example=raise"]
                ).execute()
            self.assertEqual(cm.exception.code, 3)
        finally:
            dance.Command.requires_system_checks = "__all__"
        self.assertIn("CommandError", stderr.getvalue())

    def test_no_translations_deactivate_translations(self):
        """
        When the Command handle method is decorated with @no_translations,
        translations are deactivated inside the command.
        """
        current_locale = translation.get_language()
        with translation.override("pl"):
            result = management.call_command("no_translations")
            self.assertIsNone(result)
        self.assertEqual(translation.get_language(), current_locale)

    def test_find_command_without_PATH(self):
        """
        find_command should still work when the PATH environment variable
        doesn't exist (#22256).
        """
        current_path = os.environ.pop("PATH", None)

        try:
            self.assertIsNone(find_command("_missing_"))
        finally:
            if current_path is not None:
                os.environ["PATH"] = current_path

    def test_discover_commands_in_eggs(self):
        """
        Management commands can also be loaded from Python eggs.
        """
        egg_dir = "%s/eggs" % os.path.dirname(__file__)
        egg_name = "%s/basic.egg" % egg_dir
        with extend_sys_path(egg_name):
            with self.settings(INSTALLED_APPS=["commandegg"]):
                cmds = find_commands(
                    os.path.join(apps.get_app_config("commandegg").path, "management")
                )
        self.assertEqual(cmds, ["eggcommand"])

    def test_call_command_option_parsing(self):
        """
        When passing the long option name to call_command, the available option
        key is the option dest name (#22985).
        """
        out = StringIO()
        management.call_command("dance", stdout=out, opt_3=True)
        self.assertIn("option3", out.getvalue())
        self.assertNotIn("opt_3", out.getvalue())
        self.assertNotIn("opt-3", out.getvalue())

    def test_call_command_option_parsing_non_string_arg(self):
        """
        It should be possible to pass non-string arguments to call_command.
        """
        out = StringIO()
        management.call_command("dance", 1, verbosity=0, stdout=out)
        self.assertIn("You passed 1 as a positional argument.", out.getvalue())

    def test_calling_a_command_with_only_empty_parameter_should_ends_gracefully(self):
        out = StringIO()
        management.call_command("hal", "--empty", stdout=out)
        self.assertEqual(out.getvalue(), "\nDave, I can't do that.\n")

    def test_calling_command_with_app_labels_and_parameters_should_be_ok(self):
        out = StringIO()
        management.call_command("hal", "myapp", "--verbosity", "3", stdout=out)
        self.assertIn(
            "Dave, my mind is going. I can feel it. I can feel it.\n", out.getvalue()
        )

    def test_calling_command_with_parameters_and_app_labels_at_the_end_should_be_ok(
        self,
    ):
        out = StringIO()
        management.call_command("hal", "--verbosity", "3", "myapp", stdout=out)
        self.assertIn(
            "Dave, my mind is going. I can feel it. I can feel it.\n", out.getvalue()
        )

    def test_calling_a_command_with_no_app_labels_and_parameters_raise_command_error(
        self,
    ):
        with self.assertRaises(CommandError):
            management.call_command("hal")

    def test_output_transaction(self):
        output = management.call_command(
            "transaction", stdout=StringIO(), no_color=True
        )
        self.assertTrue(
            output.strip().startswith(connection.ops.start_transaction_sql())
        )
        self.assertTrue(output.strip().endswith(connection.ops.end_transaction_sql()))

    def test_call_command_no_checks(self):
        """
        By default, call_command should not trigger the check framework, unless
        specifically asked.
        """
        self.counter = 0

        def patched_check(self_, **kwargs):
            self.counter += 1
            self.kwargs = kwargs

        saved_check = BaseCommand.check
        BaseCommand.check = patched_check
        try:
            management.call_command("dance", verbosity=0)
            self.assertEqual(self.counter, 0)
            management.call_command("dance", verbosity=0, skip_checks=False)
            self.assertEqual(self.counter, 1)
            self.assertEqual(self.kwargs, {})
        finally:
            BaseCommand.check = saved_check

    def test_requires_system_checks_empty(self):
        with mock.patch(
            "django.core.management.base.BaseCommand.check"
        ) as mocked_check:
            management.call_command("no_system_checks")
        self.assertIs(mocked_check.called, False)

    def test_requires_system_checks_specific(self):
        with mock.patch(
            "django.core.management.base.BaseCommand.check"
        ) as mocked_check:
            management.call_command("specific_system_checks", skip_checks=False)
        mocked_check.assert_called_once_with(tags=[Tags.staticfiles, Tags.models])

    def test_requires_system_checks_invalid(self):
        class Command(BaseCommand):
            requires_system_checks = "x"

        msg = "requires_system_checks must be a list or tuple."
        with self.assertRaisesMessage(TypeError, msg):
            Command()

    def test_check_migrations(self):
        requires_migrations_checks = dance.Command.requires_migrations_checks
        self.assertIs(requires_migrations_checks, False)
        try:
            with mock.patch.object(BaseCommand, "check_migrations") as check_migrations:
                management.call_command("dance", verbosity=0)
                self.assertFalse(check_migrations.called)
                dance.Command.requires_migrations_checks = True
                management.call_command("dance", verbosity=0)
                self.assertTrue(check_migrations.called)
        finally:
            dance.Command.requires_migrations_checks = requires_migrations_checks

    def test_call_command_unrecognized_option(self):
        msg = (
            "Unknown option(s) for dance command: unrecognized. Valid options "
            "are: example, force_color, help, integer, no_color, opt_3, "
            "option3, pythonpath, settings, skip_checks, stderr, stdout, "
            "style, traceback, verbosity, version."
        )
        with self.assertRaisesMessage(TypeError, msg):
            management.call_command("dance", unrecognized=1)

        msg = (
            "Unknown option(s) for dance command: unrecognized, unrecognized2. "
            "Valid options are: example, force_color, help, integer, no_color, "
            "opt_3, option3, pythonpath, settings, skip_checks, stderr, "
            "stdout, style, traceback, verbosity, version."
        )
        with self.assertRaisesMessage(TypeError, msg):
            management.call_command("dance", unrecognized=1, unrecognized2=1)

    def test_call_command_with_required_parameters_in_options(self):
        out = StringIO()
        management.call_command(
            "required_option", need_me="foo", needme2="bar", stdout=out
        )
        self.assertIn("need_me", out.getvalue())
        self.assertIn("needme2", out.getvalue())

    def test_call_command_with_required_parameters_in_mixed_options(self):
        out = StringIO()
        management.call_command(
            "required_option", "--need-me=foo", needme2="bar", stdout=out
        )
        self.assertIn("need_me", out.getvalue())
        self.assertIn("needme2", out.getvalue())

    def test_command_add_arguments_after_common_arguments(self):
        out = StringIO()
        management.call_command("common_args", stdout=out)
        self.assertIn("Detected that --version already exists", out.getvalue())

    def test_mutually_exclusive_group_required_options(self):
        out = StringIO()
        management.call_command("mutually_exclusive_required", foo_id=1, stdout=out)
        self.assertIn("foo_id", out.getvalue())
        management.call_command(
            "mutually_exclusive_required", foo_name="foo", stdout=out
        )
        self.assertIn("foo_name", out.getvalue())
        msg = (
            "Error: one of the arguments --foo-id --foo-name --foo-list "
            "--append_const --const --count --flag_false --flag_true is "
            "required"
        )
        with self.assertRaisesMessage(CommandError, msg):
            management.call_command("mutually_exclusive_required", stdout=out)

    def test_mutually_exclusive_group_required_const_options(self):
        tests = [
            ("append_const", [42]),
            ("const", 31),
            ("count", 1),
            ("flag_false", False),
            ("flag_true", True),
        ]
        for arg, value in tests:
            out = StringIO()
            expected_output = "%s=%s" % (arg, value)
            with self.subTest(arg=arg):
                management.call_command(
                    "mutually_exclusive_required",
                    "--%s" % arg,
                    stdout=out,
                )
                self.assertIn(expected_output, out.getvalue())
                out.truncate(0)
                management.call_command(
                    "mutually_exclusive_required",
                    **{arg: value, "stdout": out},
                )
                self.assertIn(expected_output, out.getvalue())

    def test_mutually_exclusive_group_required_with_same_dest_options(self):
        tests = [
            {"until": "2"},
            {"for": "1", "until": "2"},
        ]
        msg = (
            "Cannot pass the dest 'until' that matches multiple arguments via "
            "**options."
        )
        for options in tests:
            with self.subTest(options=options):
                with self.assertRaisesMessage(TypeError, msg):
                    management.call_command(
                        "mutually_exclusive_required_with_same_dest",
                        **options,
                    )

    def test_mutually_exclusive_group_required_with_same_dest_args(self):
        tests = [
            ("--until=1",),
            ("--until", 1),
            ("--for=1",),
            ("--for", 1),
        ]
        for args in tests:
            out = StringIO()
            with self.subTest(options=args):
                management.call_command(
                    "mutually_exclusive_required_with_same_dest",
                    *args,
                    stdout=out,
                )
                output = out.getvalue()
                self.assertIn("until=1", output)

    def test_required_list_option(self):
        tests = [
            (("--foo-list", [1, 2]), {}),
            ((), {"foo_list": [1, 2]}),
        ]
        for command in ["mutually_exclusive_required", "required_list_option"]:
            for args, kwargs in tests:
                with self.subTest(command=command, args=args, kwargs=kwargs):
                    out = StringIO()
                    management.call_command(
                        command,
                        *args,
                        **{**kwargs, "stdout": out},
                    )
                    self.assertIn("foo_list=[1, 2]", out.getvalue())

    def test_required_const_options(self):
        args = {
            "append_const": [42],
            "const": 31,
            "count": 1,
            "flag_false": False,
            "flag_true": True,
        }
        expected_output = "\n".join(
            "%s=%s" % (arg, value) for arg, value in args.items()
        )
        out = StringIO()
        management.call_command(
            "required_constant_option",
            "--append_const",
            "--const",
            "--count",
            "--flag_false",
            "--flag_true",
            stdout=out,
        )
        self.assertIn(expected_output, out.getvalue())
        out.truncate(0)
        management.call_command("required_constant_option", **{**args, "stdout": out})
        self.assertIn(expected_output, out.getvalue())

    def test_subparser(self):
        out = StringIO()
        management.call_command("subparser", "foo", 12, stdout=out)
        self.assertIn("bar", out.getvalue())

    def test_subparser_dest_args(self):
        out = StringIO()
        management.call_command("subparser_dest", "foo", bar=12, stdout=out)
        self.assertIn("bar", out.getvalue())

    def test_subparser_dest_required_args(self):
        out = StringIO()
        management.call_command(
            "subparser_required", "foo_1", "foo_2", bar=12, stdout=out
        )
        self.assertIn("bar", out.getvalue())

    def test_subparser_invalid_option(self):
        msg = "invalid choice: 'test' (choose from 'foo')"
        with self.assertRaisesMessage(CommandError, msg):
            management.call_command("subparser", "test", 12)
        msg = "Error: the following arguments are required: subcommand"
        with self.assertRaisesMessage(CommandError, msg):
            management.call_command("subparser_dest", subcommand="foo", bar=12)

    def test_create_parser_kwargs(self):
        """BaseCommand.create_parser() passes kwargs to CommandParser."""
        epilog = "some epilog text"
        parser = BaseCommand().create_parser(
            "prog_name",
            "subcommand",
            epilog=epilog,
            formatter_class=ArgumentDefaultsHelpFormatter,
        )
        self.assertEqual(parser.epilog, epilog)
        self.assertEqual(parser.formatter_class, ArgumentDefaultsHelpFormatter)

    def test_outputwrapper_flush(self):
        out = StringIO()
        with mock.patch.object(out, "flush") as mocked_flush:
            management.call_command("outputwrapper", stdout=out)
        self.assertIn("Working...", out.getvalue())
        self.assertIs(mocked_flush.called, True)


class CommandRunTests(AdminScriptTestCase):
    """
    Tests that need to run by simulating the command line, not by call_command.
    """

    def test_script_prefix_set_in_commands(self):
        self.write_settings(
            "settings.py",
            apps=["user_commands"],
            sdict={
                "ROOT_URLCONF": '"user_commands.urls"',
                "FORCE_SCRIPT_NAME": '"/PREFIX/"',
            },
        )
        out, err = self.run_manage(["reverse_url"])
        self.assertNoOutput(err)
        self.assertEqual(out.strip(), "/PREFIX/some/url/")

    def test_disallowed_abbreviated_options(self):
        """
        To avoid conflicts with custom options, commands don't allow
        abbreviated forms of the --setting and --pythonpath options.
        """
        self.write_settings("settings.py", apps=["user_commands"])
        out, err = self.run_manage(["set_option", "--set", "foo"])
        self.assertNoOutput(err)
        self.assertEqual(out.strip(), "Set foo")

    def test_skip_checks(self):
        self.write_settings(
            "settings.py",
            apps=["django.contrib.staticfiles", "user_commands"],
            sdict={
                # (staticfiles.E001) The STATICFILES_DIRS setting is not a tuple or
                # list.
                "STATICFILES_DIRS": '"foo"',
            },
        )
        out, err = self.run_manage(["set_option", "--skip-checks", "--set", "foo"])
        self.assertNoOutput(err)
        self.assertEqual(out.strip(), "Set foo")


class UtilsTests(SimpleTestCase):
    def test_no_existent_external_program(self):
        msg = "Error executing a_42_command_that_doesnt_exist_42"
        with self.assertRaisesMessage(CommandError, msg):
            popen_wrapper(["a_42_command_that_doesnt_exist_42"])

    def test_get_random_secret_key(self):
        key = get_random_secret_key()
        self.assertEqual(len(key), 50)
        for char in key:
            self.assertIn(char, "abcdefghijklmnopqrstuvwxyz0123456789!@#$%^&*(-_=+)")

    def test_is_ignored_path_true(self):
        patterns = (
            ["foo/bar/baz"],
            ["baz"],
            ["foo/bar/baz"],
            ["*/baz"],
            ["*"],
            ["b?z"],
            ["[abc]az"],
            ["*/ba[!z]/baz"],
        )
        for ignore_patterns in patterns:
            with self.subTest(ignore_patterns=ignore_patterns):
                self.assertIs(
                    is_ignored_path("foo/bar/baz", ignore_patterns=ignore_patterns),
                    True,
                )

    def test_is_ignored_path_false(self):
        self.assertIs(
            is_ignored_path(
                "foo/bar/baz", ignore_patterns=["foo/bar/bat", "bar", "flub/blub"]
            ),
            False,
        )

    def test_normalize_path_patterns_truncates_wildcard_base(self):
        expected = [os.path.normcase(p) for p in ["foo/bar", "bar/*/"]]
        self.assertEqual(normalize_path_patterns(["foo/bar/*", "bar/*/"]), expected)
