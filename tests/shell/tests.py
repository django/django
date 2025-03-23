import os
import subprocess
import sys
import unittest
from unittest import mock

from django import __version__
from django.contrib.auth.models import Group, Permission, User
from django.contrib.contenttypes.models import ContentType
from django.core.management import CommandError, call_command
from django.core.management.commands import shell
from django.db import connection
from django.test import SimpleTestCase
from django.test.utils import captured_stdin, captured_stdout, override_settings
from django.urls import resolve, reverse

from .models import Marker, Phone


class ShellCommandTestCase(SimpleTestCase):
    script_globals = 'print("__name__" in globals() and "Phone" in globals())'
    script_with_inline_function = (
        "import django\ndef f():\n    print(django.__version__)\nf()"
    )

    def test_command_option(self):
        with self.assertLogs("test", "INFO") as cm:
            with captured_stdout():
                call_command(
                    "shell",
                    command=(
                        "import django; from logging import getLogger; "
                        'getLogger("test").info(django.__version__)'
                    ),
                )
        self.assertEqual(cm.records[0].getMessage(), __version__)

    def test_command_option_globals(self):
        with captured_stdout() as stdout:
            call_command("shell", command=self.script_globals, verbosity=0)
        self.assertEqual(stdout.getvalue().strip(), "True")

    def test_command_option_inline_function_call(self):
        with captured_stdout() as stdout:
            call_command("shell", command=self.script_with_inline_function, verbosity=0)
        self.assertEqual(stdout.getvalue().strip(), __version__)

    @override_settings(INSTALLED_APPS=["shell"])
    def test_no_settings(self):
        test_environ = os.environ.copy()
        if "DJANGO_SETTINGS_MODULE" in test_environ:
            del test_environ["DJANGO_SETTINGS_MODULE"]
        error = (
            "Automatic imports are disabled since settings are not configured.\n"
            "DJANGO_SETTINGS_MODULE value is None.\n"
            "HINT: Ensure that the settings module is configured and set.\n\n"
        )
        for verbosity, assertError in [
            ("0", self.assertNotIn),
            ("1", self.assertIn),
            ("2", self.assertIn),
        ]:
            with self.subTest(verbosity=verbosity, get_auto_imports="models"):
                p = subprocess.run(
                    [
                        sys.executable,
                        "-m",
                        "django",
                        "shell",
                        "-c",
                        "print(globals())",
                        "-v",
                        verbosity,
                    ],
                    capture_output=True,
                    env=test_environ,
                    text=True,
                    umask=-1,
                )
                assertError(error, p.stdout)
                self.assertNotIn("Marker", p.stdout)

            with self.subTest(verbosity=verbosity, get_auto_imports="without-models"):
                with mock.patch(
                    "django.core.management.commands.shell.Command.get_auto_imports",
                    return_value=["django.urls.resolve"],
                ):
                    p = subprocess.run(
                        [
                            sys.executable,
                            "-m",
                            "django",
                            "shell",
                            "-c",
                            "print(globals())",
                            "-v",
                            verbosity,
                        ],
                        capture_output=True,
                        env=test_environ,
                        text=True,
                        umask=-1,
                    )
                    assertError(error, p.stdout)
                    self.assertNotIn("resolve", p.stdout)

    @unittest.skipIf(
        sys.platform == "win32", "Windows select() doesn't support file descriptors."
    )
    @mock.patch("django.core.management.commands.shell.select")
    def test_stdin_read(self, select):
        with captured_stdin() as stdin, captured_stdout() as stdout:
            stdin.write("print(100)\n")
            stdin.seek(0)
            call_command("shell", verbosity=0)
        self.assertEqual(stdout.getvalue().strip(), "100")

    @unittest.skipIf(
        sys.platform == "win32",
        "Windows select() doesn't support file descriptors.",
    )
    @mock.patch("django.core.management.commands.shell.select")  # [1]
    def test_stdin_read_globals(self, select):
        with captured_stdin() as stdin, captured_stdout() as stdout:
            stdin.write(self.script_globals)
            stdin.seek(0)
            call_command("shell", verbosity=0)
        self.assertEqual(stdout.getvalue().strip(), "True")

    @unittest.skipIf(
        sys.platform == "win32",
        "Windows select() doesn't support file descriptors.",
    )
    @mock.patch("django.core.management.commands.shell.select")  # [1]
    def test_stdin_read_inline_function_call(self, select):
        with captured_stdin() as stdin, captured_stdout() as stdout:
            stdin.write(self.script_with_inline_function)
            stdin.seek(0)
            call_command("shell", verbosity=0)
        self.assertEqual(stdout.getvalue().strip(), __version__)

    def test_ipython(self):
        cmd = shell.Command()
        mock_ipython = mock.Mock(start_ipython=mock.MagicMock())
        options = {"verbosity": 0, "no_imports": False}

        with mock.patch.dict(sys.modules, {"IPython": mock_ipython}):
            cmd.ipython(options)

        self.assertEqual(
            mock_ipython.start_ipython.mock_calls,
            [mock.call(argv=[], user_ns=cmd.get_namespace(**options))],
        )

    @mock.patch("django.core.management.commands.shell.select.select")  # [1]
    @mock.patch.dict("sys.modules", {"IPython": None})
    def test_shell_with_ipython_not_installed(self, select):
        select.return_value = ([], [], [])
        with self.assertRaisesMessage(
            CommandError, "Couldn't import ipython interface."
        ):
            call_command("shell", interface="ipython")

    def test_bpython(self):
        cmd = shell.Command()
        mock_bpython = mock.Mock(embed=mock.MagicMock())
        options = {"verbosity": 0, "no_imports": False}

        with mock.patch.dict(sys.modules, {"bpython": mock_bpython}):
            cmd.bpython(options)

        self.assertEqual(
            mock_bpython.embed.mock_calls, [mock.call(cmd.get_namespace(**options))]
        )

    @mock.patch("django.core.management.commands.shell.select.select")  # [1]
    @mock.patch.dict("sys.modules", {"bpython": None})
    def test_shell_with_bpython_not_installed(self, select):
        select.return_value = ([], [], [])
        with self.assertRaisesMessage(
            CommandError, "Couldn't import bpython interface."
        ):
            call_command("shell", interface="bpython")

    def test_python(self):
        cmd = shell.Command()
        mock_code = mock.Mock(interact=mock.MagicMock())
        options = {"verbosity": 0, "no_startup": True, "no_imports": False}

        with mock.patch.dict(sys.modules, {"code": mock_code}):
            cmd.python(options)

        self.assertEqual(
            mock_code.interact.mock_calls,
            [mock.call(local=cmd.get_namespace(**options))],
        )

    # [1] Patch select to prevent tests failing when the test suite is run
    # in parallel mode. The tests are run in a subprocess and the subprocess's
    # stdin is closed and replaced by /dev/null. Reading from /dev/null always
    # returns EOF and so select always shows that sys.stdin is ready to read.
    # This causes problems because of the call to select.select() toward the
    # end of shell's handle() method.


class ShellCommandAutoImportsTestCase(SimpleTestCase):

    @override_settings(
        INSTALLED_APPS=["shell", "django.contrib.auth", "django.contrib.contenttypes"]
    )
    def test_get_namespace(self):
        namespace = shell.Command().get_namespace()

        self.assertEqual(
            namespace,
            {
                "Marker": Marker,
                "Phone": Phone,
                "ContentType": ContentType,
                "Group": Group,
                "Permission": Permission,
                "User": User,
            },
        )

    @override_settings(
        INSTALLED_APPS=["model_forms", "contenttypes_tests", "forms_tests"]
    )
    def test_get_namespace_precedence(self):
        # All of these apps define an `Article` model. The one defined first in
        # INSTALLED_APPS, takes precedence.
        import model_forms.models

        namespace = shell.Command().get_namespace()
        self.assertIs(namespace.get("Article"), model_forms.models.Article)

    @override_settings(
        INSTALLED_APPS=["shell", "django.contrib.auth", "django.contrib.contenttypes"]
    )
    def test_get_namespace_overridden(self):
        class TestCommand(shell.Command):
            def get_auto_imports(self):
                return super().get_auto_imports() + [
                    "django.urls.reverse",
                    "django.urls.resolve",
                    "django.db.connection",
                ]

        namespace = TestCommand().get_namespace()

        self.assertEqual(
            namespace,
            {
                "connection": connection,
                "resolve": resolve,
                "reverse": reverse,
                "Marker": Marker,
                "Phone": Phone,
                "ContentType": ContentType,
                "Group": Group,
                "Permission": Permission,
                "User": User,
            },
        )

    @override_settings(
        INSTALLED_APPS=["shell", "django.contrib.auth", "django.contrib.contenttypes"]
    )
    def test_no_imports_flag(self):
        for verbosity in (0, 1, 2, 3):
            with self.subTest(verbosity=verbosity), captured_stdout() as stdout:
                namespace = shell.Command().get_namespace(
                    verbosity=verbosity, no_imports=True
                )
            self.assertEqual(namespace, {})
            self.assertEqual(stdout.getvalue().strip(), "")

    @override_settings(
        INSTALLED_APPS=["shell", "django.contrib.auth", "django.contrib.contenttypes"]
    )
    def test_verbosity_zero(self):
        with captured_stdout() as stdout:
            cmd = shell.Command()
            namespace = cmd.get_namespace(verbosity=0)
        self.assertEqual(len(namespace), len(cmd.get_auto_imports()))
        self.assertEqual(stdout.getvalue().strip(), "")

    @override_settings(
        INSTALLED_APPS=["shell", "django.contrib.auth", "django.contrib.contenttypes"]
    )
    def test_verbosity_one(self):
        with captured_stdout() as stdout:
            cmd = shell.Command()
            namespace = cmd.get_namespace(verbosity=1)
        self.assertEqual(len(namespace), len(cmd.get_auto_imports()))
        self.assertEqual(
            stdout.getvalue().strip(),
            "6 objects imported automatically (use -v 2 for details).",
        )

    @override_settings(INSTALLED_APPS=["shell", "django.contrib.contenttypes"])
    @mock.patch.dict(sys.modules, {"isort": None})
    def test_message_with_stdout_listing_objects_with_isort_not_installed(self):
        class TestCommand(shell.Command):
            def get_auto_imports(self):
                # Include duplicate import strings to ensure proper handling,
                # independent of isort's deduplication (#36252).
                return super().get_auto_imports() + [
                    "django.urls.reverse",
                    "django.urls.resolve",
                    "shell",
                    "django",
                    "django.urls.reverse",
                    "shell",
                    "django",
                ]

        with captured_stdout() as stdout:
            TestCommand().get_namespace(verbosity=2)

        self.assertEqual(
            stdout.getvalue().strip(),
            "7 objects imported automatically:\n\n"
            "  import shell\n"
            "  import django\n"
            "  from django.contrib.contenttypes.models import ContentType\n"
            "  from shell.models import Phone, Marker\n"
            "  from django.urls import reverse, resolve",
        )

    def test_message_with_stdout_one_object(self):
        class TestCommand(shell.Command):
            def get_auto_imports(self):
                return ["django.db.connection"]

        with captured_stdout() as stdout:
            TestCommand().get_namespace(verbosity=2)

        cases = {
            0: "",
            1: "1 object imported automatically (use -v 2 for details).",
            2: (
                "1 object imported automatically:\n\n"
                "  from django.db import connection"
            ),
        }
        for verbosity, expected in cases.items():
            with self.subTest(verbosity=verbosity):
                with captured_stdout() as stdout:
                    TestCommand().get_namespace(verbosity=verbosity)
                    self.assertEqual(stdout.getvalue().strip(), expected)

    @override_settings(INSTALLED_APPS=[])
    def test_message_with_stdout_no_installed_apps(self):
        cases = {
            0: "",
            1: "0 objects imported automatically.",
            2: "0 objects imported automatically.",
        }
        for verbosity, expected in cases.items():
            with self.subTest(verbosity=verbosity):
                with captured_stdout() as stdout:
                    shell.Command().get_namespace(verbosity=verbosity)
                    self.assertEqual(stdout.getvalue().strip(), expected)

    def test_message_with_stdout_overriden_none_result(self):
        class TestCommand(shell.Command):
            def get_auto_imports(self):
                return None

        for verbosity in [0, 1, 2]:
            with self.subTest(verbosity=verbosity):
                with captured_stdout() as stdout:
                    result = TestCommand().get_namespace(verbosity=verbosity)
                    self.assertEqual(result, {})
                    self.assertEqual(stdout.getvalue().strip(), "")

    @override_settings(INSTALLED_APPS=["shell", "django.contrib.contenttypes"])
    def test_message_with_stdout_listing_objects_with_isort(self):
        sorted_imports = (
            "  from shell.models import Marker, Phone\n\n"
            "  from django.contrib.contenttypes.models import ContentType"
        )
        mock_isort_code = mock.Mock(code=mock.MagicMock(return_value=sorted_imports))

        class TestCommand(shell.Command):
            def get_auto_imports(self):
                return super().get_auto_imports() + [
                    "django.urls.reverse",
                    "django.urls.resolve",
                    "django",
                ]

        with (
            mock.patch.dict(sys.modules, {"isort": mock_isort_code}),
            captured_stdout() as stdout,
        ):
            TestCommand().get_namespace(verbosity=2)

        self.assertEqual(
            stdout.getvalue().strip(),
            "6 objects imported automatically:\n\n" + sorted_imports,
        )

    def test_override_get_auto_imports(self):
        class TestCommand(shell.Command):
            def get_auto_imports(self):
                return [
                    "model_forms",
                    "shell",
                    "does.not.exist",
                    "doesntexisteither",
                ]

        with captured_stdout() as stdout:
            TestCommand().get_namespace(verbosity=2)

        expected = (
            "2 objects could not be automatically imported:\n\n"
            "  does.not.exist\n"
            "  doesntexisteither\n\n"
            "2 objects imported automatically:\n\n"
            "  import model_forms\n"
            "  import shell\n\n"
        )
        self.assertEqual(stdout.getvalue(), expected)

    def test_override_get_auto_imports_one_error(self):
        class TestCommand(shell.Command):
            def get_auto_imports(self):
                return [
                    "foo",
                ]

        expected = (
            "1 object could not be automatically imported:\n\n  foo\n\n"
            "0 objects imported automatically.\n\n"
        )
        for verbosity, expected in [(0, ""), (1, expected), (2, expected)]:
            with self.subTest(verbosity=verbosity):
                with captured_stdout() as stdout:
                    TestCommand().get_namespace(verbosity=verbosity)
                    self.assertEqual(stdout.getvalue(), expected)

    def test_override_get_auto_imports_many_errors(self):
        class TestCommand(shell.Command):
            def get_auto_imports(self):
                return [
                    "does.not.exist",
                    "doesntexisteither",
                ]

        expected = (
            "2 objects could not be automatically imported:\n\n"
            "  does.not.exist\n"
            "  doesntexisteither\n\n"
            "0 objects imported automatically.\n\n"
        )
        for verbosity, expected in [(0, ""), (1, expected), (2, expected)]:
            with self.subTest(verbosity=verbosity):
                with captured_stdout() as stdout:
                    TestCommand().get_namespace(verbosity=verbosity)
                    self.assertEqual(stdout.getvalue(), expected)
