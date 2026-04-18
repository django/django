from io import StringIO
from unittest import mock


class AssertFormatterFailureCaughtContext:

    def __init__(self, test, shutil_which_result="nonexistent"):
        self.stdout = StringIO()
        self.stderr = StringIO()
        self.test = test
        self.shutil_which_result = shutil_which_result

    def __enter__(self):
        self.mocker = mock.patch(
            "django.core.management.utils.shutil.which",
            return_value=self.shutil_which_result,
        )
        self.mocker.start()
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.mocker.stop()
        self.test.assertIn("Formatters failed to launch", self.stderr.getvalue())
