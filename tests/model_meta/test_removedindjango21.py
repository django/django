import warnings

from django.test import SimpleTestCase

from .models import Person


class HasAutoFieldTests(SimpleTestCase):

    def test_get_warns(self):
        with warnings.catch_warnings(record=True) as warns:
            warnings.simplefilter('always')
            Person._meta.has_auto_field
        self.assertEqual(len(warns), 1)
        self.assertEqual(
            str(warns[0].message),
            'Model._meta.has_auto_field is deprecated in favor of checking if '
            'Model._meta.auto_field is not None.',
        )

    def test_set_does_nothing(self):
        Person._meta.has_auto_field = True
