import sys
import unittest
from unittest import mock

from django import __version__
from django.contrib.auth.models import Group, Permission, User
from django.contrib.contenttypes.models import ContentType
from django.core.management import CommandError, call_command
from django.core.management.commands import shell
from django.db import models
from django.test import SimpleTestCase
from django.test.utils import (
    captured_stdin,
    captured_stdout,
    isolate_apps,
    override_settings,
)
from django.urls.base import resolve, reverse

from .models import Marker, Phone


class ShellCommandTestCase(SimpleTestCase):
    script_globals = 'print("__name__" in globals() and "Phone" in globals())'
    script_with_inline_function = (
        "import django\ndef f():\n    print(django.__version__)\nf()"
    )

    def test_command_option(self):
        with self.assertLogs("test", "INFO") as cm:
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
            call_command("shell", command=self.script_globals)
        self.assertEqual(stdout.getvalue().strip(), "True")

    def test_command_option_inline_function_call(self):
        with captured_stdout() as stdout:
            call_command("shell", command=self.script_with_inline_function)
        self.assertEqual(stdout.getvalue().strip(), __version__)

    @unittest.skipIf(
        sys.platform == "win32", "Windows select() doesn't support file descriptors."
    )
    @mock.patch("django.core.management.commands.shell.select")
    def test_stdin_read(self, select):
        with captured_stdin() as stdin, captured_stdout() as stdout:
            stdin.write("print(100)\n")
            stdin.seek(0)
            call_command("shell")
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
            call_command("shell")
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
            call_command("shell")
        self.assertEqual(stdout.getvalue().strip(), __version__)

    def test_ipython(self):
        cmd = shell.Command()
        mock_ipython = mock.Mock(start_ipython=mock.MagicMock())

        with mock.patch.dict(sys.modules, {"IPython": mock_ipython}):
            cmd.ipython({"verbosity": 0, "no_imports": False})

        self.assertEqual(
            mock_ipython.start_ipython.mock_calls,
            [mock.call(argv=[], user_ns=cmd.get_and_report_namespace(0))],
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

        with mock.patch.dict(sys.modules, {"bpython": mock_bpython}):
            cmd.bpython({"verbosity": 0, "no_imports": False})

        self.assertEqual(
            mock_bpython.embed.mock_calls, [mock.call(cmd.get_and_report_namespace(0))]
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

        with mock.patch.dict(sys.modules, {"code": mock_code}):
            cmd.python({"verbosity": 0, "no_startup": True, "no_imports": False})

        self.assertEqual(
            mock_code.interact.mock_calls,
            [mock.call(local=cmd.get_and_report_namespace(0))],
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

    @override_settings(INSTALLED_APPS=["basic", "shell"])
    @isolate_apps("basic", "shell", kwarg_name="apps")
    def test_get_namespace_precedence(self, apps):
        class Article(models.Model):
            class Meta:
                app_label = "basic"

        winner_article = Article

        class Article(models.Model):
            class Meta:
                app_label = "shell"

        with mock.patch("django.apps.apps.get_models", return_value=apps.get_models()):
            namespace = shell.Command().get_namespace()
            self.assertEqual(namespace, {"Article": winner_article})

    @override_settings(
        INSTALLED_APPS=["shell", "django.contrib.auth", "django.contrib.contenttypes"]
    )
    def test_get_namespace_overridden(self):
        class TestCommand(shell.Command):
            def get_namespace(self):
                from django.urls.base import resolve, reverse

                return {
                    **super().get_namespace(),
                    "resolve": resolve,
                    "reverse": reverse,
                }

        namespace = TestCommand().get_namespace()

        self.assertEqual(
            namespace,
            {
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
                namespace = shell.Command().get_and_report_namespace(
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
            namespace = cmd.get_and_report_namespace(verbosity=0)
        self.assertEqual(namespace, cmd.get_namespace())
        self.assertEqual(stdout.getvalue().strip(), "")

    @override_settings(
        INSTALLED_APPS=["shell", "django.contrib.auth", "django.contrib.contenttypes"]
    )
    def test_verbosity_one(self):
        with captured_stdout() as stdout:
            cmd = shell.Command()
            namespace = cmd.get_and_report_namespace(verbosity=1)
        self.assertEqual(namespace, cmd.get_namespace())
        self.assertEqual(
            stdout.getvalue().strip(),
            "6 objects imported automatically (use -v 2 for details).",
        )

    @override_settings(INSTALLED_APPS=["shell", "django.contrib.contenttypes"])
    @mock.patch.dict(sys.modules, {"isort": None})
    def test_message_with_stdout_listing_objects_with_isort_not_installed(self):
        class TestCommand(shell.Command):
            def get_namespace(self):
                class MyClass:
                    pass

                constant = "constant"

                return {
                    **super().get_namespace(),
                    "MyClass": MyClass,
                    "constant": constant,
                }

        with captured_stdout() as stdout:
            TestCommand().get_and_report_namespace(verbosity=2)

        self.assertEqual(
            stdout.getvalue().strip(),
            "5 objects imported automatically, including:\n\n"
            "  from django.contrib.contenttypes.models import ContentType\n"
            "  from shell.models import Phone, Marker",
        )

    @override_settings(INSTALLED_APPS=["shell", "django.contrib.contenttypes"])
    def test_message_with_stdout_listing_objects_with_isort(self):
        sorted_imports = (
            "  from shell.models import Marker, Phone\n\n"
            "  from django.contrib.contenttypes.models import ContentType"
        )
        mock_isort_code = mock.Mock(code=mock.MagicMock(return_value=sorted_imports))

        class TestCommand(shell.Command):
            def get_namespace(self):
                class MyClass:
                    pass

                constant = "constant"

                return {
                    **super().get_namespace(),
                    "MyClass": MyClass,
                    "constant": constant,
                }

        with (
            mock.patch.dict(sys.modules, {"isort": mock_isort_code}),
            captured_stdout() as stdout,
        ):
            TestCommand().get_and_report_namespace(verbosity=2)

        self.assertEqual(
            stdout.getvalue().strip(),
            "5 objects imported automatically, including:\n\n"
            "  from shell.models import Marker, Phone\n\n"
            "  from django.contrib.contenttypes.models import ContentType",
        )
