from __future__ import absolute_import

from django.test import TestCase
from django.db.models.query import QuerySet

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

    def test_choices_for_FOO(self):
        a = Person.objects.create(name='Adrian', gender='M')
        s = Person.objects.create(name='Simon', gender='M', parent=a)
        k = Person.objects.create(name='Karen', gender='F', parent=a)
        b = Person.objects.create(name='Brian', gender='M', parent=s)

        queryset = b._meta.get_field('parent').queryset
        self.assertIsInstance(queryset, QuerySet)
        self.assertQuerysetEqual(
            queryset, [
                'Adrian',
                'Simon',
                'Karen'
            ], lambda p: p.name, ordered=False)
