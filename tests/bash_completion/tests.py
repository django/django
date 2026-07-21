"""
A series of tests to establish that the command-line bash completion works.
"""

import os
import shutil
import subprocess
import sys
import unittest
from pathlib import Path

from django.apps import apps
from django.core.management import ManagementUtility
from django.test.utils import captured_stdout

# extras/django_bash_completion, relative to the repository root. Only present
# in a source checkout, not in an installed Django.
DJANGO_BASH_COMPLETION = (
    Path(__file__).resolve().parent.parent.parent / "extras" / "django_bash_completion"
)


class BashCompletionTests(unittest.TestCase):
    """
    Testing the Python level bash completion code.
    This requires setting up the environment as if we got passed data
    from bash.
    """

    def setUp(self):
        self.old_DJANGO_AUTO_COMPLETE = os.environ.get("DJANGO_AUTO_COMPLETE")
        os.environ["DJANGO_AUTO_COMPLETE"] = "1"

    def tearDown(self):
        if self.old_DJANGO_AUTO_COMPLETE:
            os.environ["DJANGO_AUTO_COMPLETE"] = self.old_DJANGO_AUTO_COMPLETE
        else:
            del os.environ["DJANGO_AUTO_COMPLETE"]

    def _user_input(self, input_str):
        """
        Set the environment and the list of command line arguments.

        This sets the bash variables $COMP_WORDS and $COMP_CWORD. The former is
        an array consisting of the individual words in the current command
        line, the latter is the index of the current cursor position, so in
        case a word is completed and the cursor is placed after a whitespace,
        $COMP_CWORD must be incremented by 1:

          * 'django-admin start' -> COMP_CWORD=1
          * 'django-admin startproject' -> COMP_CWORD=1
          * 'django-admin startproject ' -> COMP_CWORD=2
        """
        os.environ["COMP_WORDS"] = input_str
        idx = len(input_str.split(" ")) - 1  # Index of the last word
        comp_cword = idx + 1 if input_str.endswith(" ") else idx
        os.environ["COMP_CWORD"] = str(comp_cword)
        sys.argv = input_str.split()

    def _run_autocomplete(self):
        util = ManagementUtility(argv=sys.argv)
        with captured_stdout() as stdout:
            try:
                util.autocomplete()
            except SystemExit:
                pass
        return stdout.getvalue().strip().split("\n")

    def test_django_admin_py(self):
        "django_admin.py will autocomplete option flags"
        self._user_input("django-admin sqlmigrate --verb")
        output = self._run_autocomplete()
        self.assertEqual(output, ["--verbosity="])

    def test_manage_py(self):
        "manage.py will autocomplete option flags"
        self._user_input("manage.py sqlmigrate --verb")
        output = self._run_autocomplete()
        self.assertEqual(output, ["--verbosity="])

    def test_custom_command(self):
        "A custom command can autocomplete option flags"
        self._user_input("django-admin test_command --l")
        output = self._run_autocomplete()
        self.assertEqual(output, ["--list"])

    def test_subcommands(self):
        "Subcommands can be autocompleted"
        self._user_input("django-admin sql")
        output = self._run_autocomplete()
        self.assertEqual(output, ["sqlflush sqlmigrate sqlsequencereset"])

    def test_completed_subcommand(self):
        "Show option flags in case a subcommand is completed"
        self._user_input("django-admin startproject ")  # Trailing whitespace
        output = self._run_autocomplete()
        for item in output:
            self.assertTrue(item.startswith("--"))

    def test_help(self):
        "No errors, just an empty list if there are no autocomplete options"
        self._user_input("django-admin help --")
        output = self._run_autocomplete()
        self.assertEqual(output, [""])

    def test_app_completion(self):
        "Application names will be autocompleted for an AppCommand"
        self._user_input("django-admin sqlmigrate a")
        output = self._run_autocomplete()
        a_labels = sorted(
            app_config.label
            for app_config in apps.get_app_configs()
            if app_config.label.startswith("a")
        )
        self.assertEqual(output, a_labels)


@unittest.skipUnless(
    shutil.which("bash"), "bash is required to exercise the completion script."
)
@unittest.skipUnless(
    DJANGO_BASH_COMPLETION.exists(),
    "django_bash_completion is only shipped in a source checkout.",
)
class BashCompletionScriptTests(unittest.TestCase):
    """
    Checks for the shipped extras/django_bash_completion script itself.

    Regression tests for #19806: sourcing the script must not register a
    completion hook for the ``python`` interpreter, which would clobber the
    upstream bash completion of ``python`` (e.g. its own option flags).
    """

    def _completion_specs(self, *commands):
        """
        Source the completion script in a fresh, non-interactive bash shell and
        return ``{command: registered completion spec}`` as reported by
        ``complete -p``. A command with no completion registered maps to "".

        The script path is passed as a positional argument ($1) rather than
        interpolated into the command string, to avoid quoting issues.
        """
        queries = "\n".join(
            f'printf "### %s\\n" {cmd}; complete -p {cmd} 2>/dev/null || true'
            for cmd in commands
        )
        snippet = f'. "$1" || exit 2\n{queries}\n'
        result = subprocess.run(
            ["bash", "-c", snippet, "bash", DJANGO_BASH_COMPLETION.as_posix()],
            capture_output=True,
            text=True,
        )
        self.assertEqual(
            result.returncode,
            0,
            msg="Sourcing django_bash_completion failed:\n%s" % result.stderr,
        )
        specs = {}
        current = None
        for line in result.stdout.splitlines():
            if line.startswith("### "):
                current = line[4:]
                specs[current] = ""
            elif current is not None and line.strip():
                specs[current] += line + "\n"
        return specs

    def test_python_completion_not_registered(self):
        """
        No Django completion hook is bound to python interpreters (#19806).
        """
        specs = self._completion_specs("python", "python3")
        self.assertEqual(sorted(specs), ["python", "python3"])
        for interpreter, spec in specs.items():
            with self.subTest(interpreter=interpreter):
                self.assertNotIn("_django_completion", spec)
                self.assertNotIn("_python_django_completion", spec)

    def test_manage_py_and_django_admin_still_registered(self):
        """
        Completion for the explicit manage.py and django-admin commands is
        left intact.
        """
        specs = self._completion_specs("manage.py", "django-admin")
        for command in ("manage.py", "django-admin"):
            with self.subTest(command=command):
                self.assertIn("_django_completion", specs[command])
