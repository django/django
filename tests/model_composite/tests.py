from django.test import TestCase

from .models import Employee, User


class CompositePKTests(TestCase):
    def test_custom_pk_create(self):
        """
        New objects can be created both with pk and the custom name
        """

        Employee.objects.create(
            branch="root", employee_code=1234, first_name="Foo", last_name="Bar"
        )
        Employee.objects.create(pk=("root", 1235), first_name="Foo", last_name="Baz")

        Employee.objects.get(pk=("root", 1235))
        Employee.objects.only("pk").get(pk=("root", 1235))
        Employee.objects.defer("pk").get(pk=("root", 1235))
        Employee.objects.filter(pk__in=[("root", 1234), ("root", 1235)]).last()

    def test_set_composite_field(self):
        self.assertEqual(Employee(composite_pk=("root", 1235)).pk, ("root", 1235))

    def test_set_pk(self):
        self.assertEqual(Employee(pk=("root", 1235)).pk, ("root", 1235))

    def test_composite_field_empty(self):
        self.assertEqual(Employee().composite_pk, ("", None))

    def test_pk_empty(self):
        self.assertEqual(Employee().pk, ("", None))

    def test_set_composite_field_and_component(self):
        with self.assertRaisesMessage(
            TypeError, "Employee() set field 'branch' twice, via field 'branch'."
        ):
            Employee(composite_pk=("root", 1235), branch="")

    def test_set_pk_and_component_edge_case(self):
        employee = Employee(pk=("root", 1235), branch="other")
        self.assertEqual(employee.branch, "root")

    def test_relation(self):
        Employee.objects.create(
            branch="root", employee_code=1234, first_name="Foo", last_name="Bar"
        )
        Employee.objects.create(
            branch="other", employee_code=1234, first_name="Foo", last_name="Baz"
        )
        user_id = User.objects.create(employee_branch="root", employee_code=1234).id

        self.assertEqual(
            User.objects.get(
                employee_branch="root", employee_code=1234
            ).employee.last_name,
            "Bar",
        )
        self.assertEqual(
            User.objects.get(
                employee_branch="root", employee_code=1234
            ).employee2.last_name,
            "Bar",
        )

        self.assertEqual(
            User.objects.order_by("employee__pk")
            .get(employee_code=1234, employee__branch="root")
            .employee.last_name,
            "Bar",
        )
        self.assertEqual(
            User.objects.get(employee__pk=("root", 1234)).employee.last_name, "Bar"
        )
        self.assertEqual(
            User.objects.order_by("employee2__pk")
            .get(employee_code=1234, employee2__branch="root")
            .employee2.last_name,
            "Bar",
        )
        self.assertEqual(
            User.objects.get(employee2__pk=("root", 1234)).employee.last_name, "Bar"
        )

        self.assertEqual(Employee.objects.get(user__id=user_id).last_name, "Bar")
        self.assertEqual(
            Employee.objects.get(user__employee_id=("root", 1234)).last_name, "Bar"
        )
        self.assertEqual(Employee.objects.get(user2__id=user_id).last_name, "Bar")
        self.assertEqual(
            Employee.objects.get(user2__employee_id=("root", 1234)).last_name, "Bar"
        )
        self.assertEqual(
            Employee.objects.get(
                user2__id=user_id, user__employee_id=("root", 1234)
            ).last_name,
            "Bar",
        )
