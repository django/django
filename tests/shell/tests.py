import sys
import unittest
from unittest import mock

from django import __version__
from django.contrib.auth import models as auth_model_module
from django.contrib.auth.models import Group, Permission, User
from django.contrib.contenttypes import models as contenttypes_model_module
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

from . import models as shell_models


class ShellCommandTestCase(SimpleTestCase):
    script_globals_import = 'print("Phone" in globals())'
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

    def test_command_option_inline_function_call(self):
        with captured_stdout() as stdout:
            call_command("shell", command=self.script_with_inline_function)
        self.assertEqual(stdout.getvalue().strip(), __version__)

    def test_command_option_with_imports(self):
        with captured_stdout() as stdout:
            call_command("shell", command=self.script_globals_import)
        self.assertEqual(stdout.getvalue().strip(), "True")

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
    def test_stdin_read_globals_import(self, select):
        with captured_stdin() as stdin, captured_stdout() as stdout:
            stdin.write(self.script_globals_import)
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
            cmd.ipython({"verbosity": 0})

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
            cmd.bpython({"verbosity": 0})

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
            cmd.python({"verbosity": 0, "no_startup": True})

        self.assertEqual(
            mock_code.interact.mock_calls,
            [mock.call(local=cmd.get_and_report_namespace(0))],
        )

    # [1] Patch select to prevent tests failing when when the test suite is run
    # in parallel mode. The tests are run in a subprocess and the subprocess's
    # stdin is closed and replaced by /dev/null. Reading from /dev/null always
    # returns EOF and so select always shows that sys.stdin is ready to read.
    # This causes problems because of the call to select.select() toward the
    # end of shell's handle() method.

    @override_settings(
        INSTALLED_APPS=["shell", "django.contrib.auth", "django.contrib.contenttypes"]
    )
    def test_get_namespace(self):
        cmd = shell.Command()
        namespace = cmd.get_namespace()

        self.assertEqual(
            namespace,
            {
                "Marker": shell_models.Marker,
                "Phone": shell_models.Phone,
                "ContentType": ContentType,
                "Group": Group,
                "Permission": Permission,
                "User": User,
                "auth_models": auth_model_module,
                "contenttypes_models": contenttypes_model_module,
                "shell_models": shell_models,
            },
        )

    @override_settings(INSTALLED_APPS=["basic", "shell"])
    @isolate_apps("basic", "shell", kwarg_name="apps")
    def test_get_namespace_precedence(self, apps):
        class Article(models.Model):
            class Meta:
                app_label = "basic"

        article_basic = Article

        class Article(models.Model):
            class Meta:
                app_label = "shell"

        article_shell = Article

        cmd = shell.Command()

        with mock.patch("django.apps.apps.get_models", return_value=apps.get_models()):
            namespace = cmd.get_namespace()
            self.assertIn(article_basic, namespace.values())
            self.assertNotIn(article_shell, namespace.values())

    @override_settings(INSTALLED_APPS=["shell", "basic"])
    @isolate_apps("shell", "basic", kwarg_name="apps")
    def test_get_namespace_precedence_1(self, apps):
        class Article(models.Model):
            class Meta:
                app_label = "basic"

        article_basic = Article

        class Article(models.Model):
            class Meta:
                app_label = "shell"

        article_shell = Article

        cmd = shell.Command()

        with mock.patch("django.apps.apps.get_models", return_value=apps.get_models()):
            namespace = cmd.get_namespace()
            self.assertIn(article_shell, namespace.values())
            self.assertNotIn(article_basic, namespace.values())

    @override_settings(
        INSTALLED_APPS=["shell", "django.contrib.auth", "django.contrib.contenttypes"]
    )
    def test_overridden_get_namespace(self):
        class Command(shell.Command):
            def get_namespace(self):
                from django.urls.base import resolve, reverse

                return {
                    **super().get_namespace(),
                    "resolve": resolve,
                    "reverse": reverse,
                }

        cmd = Command()
        namespace = cmd.get_namespace()

        self.assertEqual(
            namespace,
            {
                "resolve": resolve,
                "reverse": reverse,
                "Marker": shell_models.Marker,
                "Phone": shell_models.Phone,
                "ContentType": ContentType,
                "Group": Group,
                "Permission": Permission,
                "User": User,
                "auth_models": auth_model_module,
                "contenttypes_models": contenttypes_model_module,
                "shell_models": shell_models,
            },
        )
