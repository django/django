from django.test import TestCase

from .models import Person


class ChoicesTests(TestCase):
    def test_display(self):
        a = Person.objects.create(name='Adrian', gender='M')
        s = Person.objects.create(name='Sara', gender='F')
        self.assertEqual(a.gender, 'M')
        self.assertEqual(s.gender, 'F')

        self.assertEqual(a.get_gender_display(), 'Male')
        self.assertEqual(s.get_gender_display(), 'Female')

        # If the value for the field doesn't correspond to a valid choice,
        # the value itself is provided as a display value.
        a.gender = ''
        self.assertEqual(a.get_gender_display(), '')

        a.gender = 'U'
        self.assertEqual(a.get_gender_display(), 'U')

        # _get_FIELD_display() coerces lazy strings.
        self.assertIsInstance(a.get_gender_display(), str)
