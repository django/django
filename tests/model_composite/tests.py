from django.test import TestCase

from .models import Employee, Employee2, User

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
        Employee.objects.only("pk").get(pk=("root", 1235))
        Employee.objects.defer("pk").get(pk=("root", 1235))
        Employee.objects.filter(pk__in=[("root", 1234), ("root", 1235)]).last()

    def test_relation(self):
        Employee.objects.create(branch="root", employee_code=1234, first_name="Foo", last_name="Bar")
        Employee.objects.create(branch="other", employee_code=1234, first_name="Foo", last_name="Baz")
        user_id = User.objects.create(employee_branch="root", employee_code=1234).id

        self.assertEqual(User.objects.get(employee_branch="root", employee_code=1234).employee.last_name, "Bar")
        self.assertEqual(User.objects.get(employee_branch="root", employee_code=1234).employee2.last_name, "Bar")

        self.assertEqual(User.objects.order_by('employee__pk').get(employee_code=1234, employee__branch="root").employee.last_name, "Bar")
        self.assertEqual(User.objects.get(employee__pk=("root", 1234)).employee.last_name, "Bar")
        self.assertEqual(User.objects.order_by('employee2__pk').get(employee_code=1234, employee2__branch="root").employee2.last_name, "Bar")
        self.assertEqual(User.objects.get(employee2__pk=("root", 1234)).employee.last_name, "Bar")

        self.assertEqual(Employee.objects.get(user__id=user_id).last_name, "Bar")
        self.assertEqual(Employee.objects.get(user__employee_id=("root", 1234)).last_name, "Bar")
        self.assertEqual(Employee.objects.get(user2__id=user_id).last_name, "Bar")
        self.assertEqual(Employee.objects.get(user2__employee_id=("root", 1234)).last_name, "Bar")
        self.assertEqual(Employee.objects.get(user2__id=user_id, user__employee_id=("root", 1234)).last_name, "Bar")
