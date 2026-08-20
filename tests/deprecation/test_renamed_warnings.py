from django.test import SimpleTestCase
from django.utils.deprecation import (
    RemovedInDjango2028Warning,
    RemovedInDjango2029Warning,
)


class RenamedWarningsTests(SimpleTestCase):
    def test_removed_in_django_70_warning_alias(self):
        msg = (
            "RemovedInDjango70Warning is deprecated. "
            "Use RemovedInDjango2028Warning instead."
        )
        with self.assertWarnsMessage(RemovedInDjango2028Warning, msg):
            from django.utils.deprecation import RemovedInDjango70Warning

        self.assertIs(RemovedInDjango70Warning, RemovedInDjango2028Warning)

    def test_removed_in_django_71_warning_alias(self):
        msg = (
            "RemovedInDjango71Warning is deprecated. "
            "Use RemovedInDjango2029Warning instead."
        )
        with self.assertWarnsMessage(RemovedInDjango2029Warning, msg):
            from django.utils.deprecation import RemovedInDjango71Warning

        self.assertIs(RemovedInDjango71Warning, RemovedInDjango2029Warning)
