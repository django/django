from __future__ import absolute_import
from __future__ import with_statement

from django.test import TestCase
from .models import Person, Employee, Profile

class UpdateOnlyFieldsTests(TestCase):
    def test_simple_update_fields(self):
        s = Person.objects.create(name='Sara', gender='F')
        self.assertEqual(s.gender, 'F')

        s.gender = 'M'
        s.name = 'Ian'
        s.save(update_fields=['name'])

        s = Person.objects.get(pk=s.pk)
        self.assertEqual(s.gender, 'F')
        self.assertEqual(s.name, 'Ian')

    def test_update_field_with_inherited(self):
        profile_boss = Profile.objects.create(name='Boss', salary=3000)
        profile_receptionist = Profile.objects.create(name='Receptionist', salary=1000)

        e1 = Employee.objects.create(name='Sara', gender='F',
            employee_num=1, profile=profile_boss)

        e1.name = 'Ian'
        e1.gender = 'M'
        e1.save(update_fields=['name'])

        e2 = Employee.objects.get(pk=e1.pk)
        self.assertEqual(e2.name, 'Ian')
        self.assertEqual(e2.gender, 'F')
        self.assertEqual(e2.profile, profile_boss)

        e2.profile = profile_receptionist
        e2.name = 'Sara'
        e2.save(update_fields=['profile'])

        e3 = Employee.objects.get(pk=e1.pk)
        self.assertEqual(e3.name, 'Ian')
        self.assertEqual(e3.profile, profile_receptionist)

    def test_update_field_with_incorrect_params(self):
        s = Person.objects.create(name='Sara', gender='F')

        with self.assertRaises(ValueError):
            s.save(update_fields=['first_name'])

        with self.assertRaises(ValueError):
            s.save(update_fields="name")

    def test_num_querys_on_save_with_empty_update_fields(self):
        s = Person.objects.create(name='Sara', gender='F')

        with self.assertNumQueries(0):
            s.save(update_fields=[])
