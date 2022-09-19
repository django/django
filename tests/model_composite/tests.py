from django.db import IntegrityError, transaction
from django.test import TestCase, skipIfDBFeature, skipUnlessDBFeature

from .models import Employee, Employee2

class CompositePKTests(TestCase):
    def test_custom_pk_create(self):
        """
        New objects can be created both with pk and the custom name
        """

        self.assertEqual(Employee(pk=("root", 1235)).pk, ('root', 1235))
        self.assertEqual(Employee2(pk=("root", 1235)).pk, ('root', 1235))

        self.assertEqual(Employee(composite_pk=("root", 1235)).pk, ('root', 1235))
        self.assertEqual(Employee2(composite_pk=("root", 1235)).pk, ('root', 1235))

        self.assertEqual(Employee().pk, ('', None))
        self.assertEqual(Employee2().pk, ('', None))

        self.assertEqual(Employee(composite_pk=("root", 1235)).pk, ('root', 1235))
        self.assertEqual(Employee2(composite_pk=("root", 1235)).pk, ('root', 1235))

        self.assertRaises(TypeError, Employee, composite_pk=("root", 1235), branch="")
        self.assertRaises(TypeError, Employee2, composite_pk=("root", 1235), branch="")

        # This won't throw, just like what other pk do
        # self.assertRaises(TypeError, Employee, pk=("root", 1235), branch="")
        # self.assertRaises(TypeError, Employee2, pk=("root", 1235), branch="")

        Employee.objects.create(branch="root", employee_code=1234, first_name="Foo", last_name="Bar")
        Employee.objects.create(pk=("root", 1235), first_name="Foo", last_name="Baz")

        Employee.objects.get(pk=("root", 1235))
        Employee.objects.filter(pk__in=[("root", 1234), ("root", 1235)]).last()
