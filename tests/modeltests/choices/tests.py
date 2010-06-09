from django.test import TestCase

from models import Person

class ChoicesFieldTestCase(TestCase):
    fixtures = ['choices_testdata.json']

    def setUp(self):
        self.a = Person.objects.get(name='Adrian')
        self.s = Person.objects.get(name='Sara')

    def test_choice_storage(self):
        self.assertEqual(self.a.gender,
                         'M')
        self.assertEqual(self.s.gender,
                         'F')

    def test_gender_display(self):
        self.assertEqual(self.a.get_gender_display(),
                         u'Male')
        self.assertEqual(self.s.get_gender_display(),
                         u'Female')
        
        # If the value for the field doesn't correspond to a valid choice,
        # the value itself is provided as a display value.
        self.a.gender = ''
        self.assertEqual(self.a.get_gender_display(),
                         u'')
        self.a.gender = 'U'
        self.assertEqual(self.a.get_gender_display(),
                         u'U')
