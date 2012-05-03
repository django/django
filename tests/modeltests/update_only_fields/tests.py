from __future__ import absolute_import

from django.test import TestCase
from django.db.models.signals import pre_save, post_save
from .models import Person, Employee, ProxyEmployee, Profile, Account


class UpdateOnlyFieldsTests(TestCase):
    def test_update_fields_basic(self):
        s = Person.objects.create(name='Sara', gender='F')
        self.assertEqual(s.gender, 'F')

        s.gender = 'M'
        s.name = 'Ian'
        s.save(update_fields=['name'])

        s = Person.objects.get(pk=s.pk)
        self.assertEqual(s.gender, 'F')
        self.assertEqual(s.name, 'Ian')

    def test_update_fields_m2n(self):
        profile_boss = Profile.objects.create(name='Boss', salary=3000)
        e1 = Employee.objects.create(name='Sara', gender='F',
            employee_num=1, profile=profile_boss)

        a1 = Account.objects.create(num=1)
        a2 = Account.objects.create(num=2)

        e1.accounts = [a1,a2]

        with self.assertRaises(ValueError):
            e1.save(update_fields=['accounts'])

    def test_update_fields_inheritance(self):
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

    def test_update_fields_inheritance_with_proxy_model(self):
        profile_boss = Profile.objects.create(name='Boss', salary=3000)
        profile_receptionist = Profile.objects.create(name='Receptionist', salary=1000)

        e1 = ProxyEmployee.objects.create(name='Sara', gender='F',
            employee_num=1, profile=profile_boss)

        e1.name = 'Ian'
        e1.gender = 'M'
        e1.save(update_fields=['name'])

        e2 = ProxyEmployee.objects.get(pk=e1.pk)
        self.assertEqual(e2.name, 'Ian')
        self.assertEqual(e2.gender, 'F')
        self.assertEqual(e2.profile, profile_boss)

        e2.profile = profile_receptionist
        e2.name = 'Sara'
        e2.save(update_fields=['profile'])

        e3 = ProxyEmployee.objects.get(pk=e1.pk)
        self.assertEqual(e3.name, 'Ian')
        self.assertEqual(e3.profile, profile_receptionist)

    def test_update_fields_signals(self):
        p = Person.objects.create(name='Sara', gender='F')
        pre_save_data = []
        def pre_save_receiver(**kwargs):
            pre_save_data.append(kwargs['update_fields'])
        pre_save.connect(pre_save_receiver)
        post_save_data = []
        def post_save_receiver(**kwargs):
            post_save_data.append(kwargs['update_fields'])
        post_save.connect(post_save_receiver)
        p.save(update_fields=['name'])
        self.assertEqual(len(pre_save_data), 1)
        self.assertEqual(len(pre_save_data[0]), 1)
        self.assertTrue('name' in pre_save_data[0])
        self.assertEqual(len(post_save_data), 1)
        self.assertEqual(len(post_save_data[0]), 1)
        self.assertTrue('name' in post_save_data[0])

    def test_update_fields_incorrect_params(self):
        s = Person.objects.create(name='Sara', gender='F')

        with self.assertRaises(ValueError):
            s.save(update_fields=['first_name'])

        with self.assertRaises(ValueError):
            s.save(update_fields="name")

    def test_empty_update_fields(self):
        s = Person.objects.create(name='Sara', gender='F')
        pre_save_data = []
        def pre_save_receiver(**kwargs):
            pre_save_data.append(kwargs['update_fields'])
        pre_save.connect(pre_save_receiver)
        post_save_data = []
        def post_save_receiver(**kwargs):
            post_save_data.append(kwargs['update_fields'])
        post_save.connect(post_save_receiver)
        # Save is skipped.
        with self.assertNumQueries(0):
            s.save(update_fields=[])
        # Signals were skipped, too...
        self.assertEqual(len(pre_save_data), 0)
        self.assertEqual(len(post_save_data), 0)

    def test_num_queries_inheritance(self):
        s = Employee.objects.create(name='Sara', gender='F')
        s.employee_num = 1
        s.name = 'Emily'
        with self.assertNumQueries(1):
            s.save(update_fields=['employee_num'])
        s = Employee.objects.get(pk=s.pk)
        self.assertEqual(s.employee_num, 1)
        self.assertEqual(s.name, 'Sara')
        s.employee_num = 2
        s.name = 'Emily'
        with self.assertNumQueries(1):
            s.save(update_fields=['name'])
        s = Employee.objects.get(pk=s.pk)
        self.assertEqual(s.name, 'Emily')
        self.assertEqual(s.employee_num, 1)
        # A little sanity check that we actually did updates...
        self.assertEqual(Employee.objects.count(), 1)
        self.assertEqual(Person.objects.count(), 1)
        with self.assertNumQueries(2):
            s.save(update_fields=['name', 'employee_num'])
