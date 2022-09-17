from django.db import IntegrityError, transaction
from django.test import TestCase, skipIfDBFeature, skipUnlessDBFeature

from .models import Employee, Employee2

class CompositePKTests(TestCase):
    def test_custom_pk_create(self):
        """
        New objects can be created both with pk and the custom name
        """
        Employee.objects.create(branch="root", employee_code=1234, first_name="Foo", last_name="Bar")
        Employee.objects.create(pk=("root", 1235), first_name="Foo", last_name="Baz")

        self.assertEqual(Employee(pk=("root", 1235)).pk, ('root', 1235))
        self.assertEqual(Employee2(pk=("root", 1235)).pk, ('root', 1235))

        self.assertEqual(Employee(composite_pk=("root", 1235)).pk, ('root', 1235))
        self.assertEqual(Employee2(composite_pk=("root", 1235)).pk, ('root', 1235))

        self.assertRaises(TypeError, Employee, composite_pk=("root", 1235), branch="")
        self.assertRaises(TypeError, Employee2, composite_pk=("root", 1235), branch="")
