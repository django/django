from django.core.management import call_command
from django.test import TestCase
from django.test.utils import override_settings
from django.utils.six import StringIO


def fake_test():
    return set(["SOME_WARNING"])

fake_test.messages = {
    "SOME_WARNING": "This is the warning message."
}


def nomsg_test():
    return set(["OTHER WARNING"])


def passing_test():
    return []


class RunChecksTest(TestCase):
    @property
    def func(self):
        from ..checks import run_checks
        return run_checks

    @override_settings(
        SECURE_CHECKS=[
            "django.contrib.secure.tests.test_commands.fake_test",
            "django.contrib.secure.tests.test_commands.nomsg_test"])
    def test_returns_warnings(self):
        self.assertEqual(self.func(), set(["SOME_WARNING", "OTHER WARNING"]))


class CheckSettingsCommandTest(TestCase):
    def call(self, **options):
        stdout = options.setdefault("stdout", StringIO())
        stderr = options.setdefault("stderr", StringIO())

        call_command("checksecure", **options)

        stderr.seek(0)
        stdout.seek(0)

        return stdout.read(), stderr.read()

    @override_settings(SECURE_CHECKS=["django.contrib.secure.tests.test_commands.fake_test"])
    def test_prints_messages(self):
        stdout, stderr = self.call()
        self.assertIn("This is the warning message.", stderr)

    @override_settings(SECURE_CHECKS=["django.contrib.secure.tests.test_commands.nomsg_test"])
    def test_prints_code_if_no_message(self):
        stdout, stderr = self.call()
        self.assertIn("OTHER WARNING", stderr)

    @override_settings(SECURE_CHECKS=["django.contrib.secure.tests.test_commands.fake_test"])
    def test_prints_code_if_verbosity_0(self):
        stdout, stderr = self.call(verbosity=0)
        self.assertIn("SOME_WARNING", stderr)

    @override_settings(SECURE_CHECKS=["django.contrib.secure.tests.test_commands.fake_test"])
    def test_prints_check_names(self):
        stdout, stderr = self.call()
        self.assertTrue("django.contrib.secure.tests.test_commands.fake_test" in stdout)

    @override_settings(SECURE_CHECKS=["django.contrib.secure.tests.test_commands.fake_test"])
    def test_no_verbosity(self):
        stdout, stderr = self.call(verbosity=0)
        self.assertEqual(stdout, "")

    @override_settings(SECURE_CHECKS=["django.contrib.secure.tests.test_commands.passing_test"])
    def test_all_clear(self):
        stdout, stderr = self.call()
        self.assertIn("All clear!", stdout)
