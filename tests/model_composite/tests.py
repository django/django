from django.test import TestCase

from .models import Employee, House, Owner, User


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

    def test_foreign_object_lookups(self):
        Employee.objects.create(
            branch="root", employee_code=1234, first_name="Foo", last_name="Bar"
        )
        user = User.objects.create(employee_branch="root", employee_code=1234)

        self.assertEqual(user.employee.last_name, "Bar")
        self.assertEqual(user.employee2.last_name, "Bar")

    def test_get_component_lookup(self):
        employee = Employee.objects.create(
            branch="root", employee_code=1234, first_name="Foo", last_name="Bar"
        )
        User.objects.create(employee_branch="root", employee_code=1234)

        user = User.objects.get(employee__branch="root", employee__employee_code=1234)
        self.assertEqual(user.employee_branch, "root")
        self.assertEqual(user.employee_code, 1234)
        self.assertEqual(user.employee, employee)
        self.assertEqual(user.employee2, employee)

        user2 = User.objects.get(
            employee2__branch="root", employee2__employee_code=1234
        )
        self.assertEqual(user2.employee_branch, "root")
        self.assertEqual(user2.employee_code, 1234)
        self.assertEqual(user2.employee, employee)
        self.assertEqual(user2.employee2, employee)

    def test_get_local_and_remote_lookup(self):
        employee = Employee.objects.create(
            branch="root", employee_code=1234, first_name="Foo", last_name="Bar"
        )
        User.objects.create(employee_branch="root", employee_code=1234)

        user = User.objects.get(employee_branch="root", employee__employee_code=1234)
        self.assertEqual(user.employee_branch, "root")
        self.assertEqual(user.employee_code, 1234)
        self.assertEqual(user.employee, employee)
        self.assertEqual(user.employee2, employee)

        user2 = User.objects.get(employee_branch="root", employee2__employee_code=1234)
        self.assertEqual(user2.employee_branch, "root")
        self.assertEqual(user2.employee_code, 1234)
        self.assertEqual(user2.employee, employee)
        self.assertEqual(user2.employee2, employee)

    def test_get_foreign_object_pk_lookup(self):
        employee = Employee.objects.create(
            branch="root", employee_code=1234, first_name="Foo", last_name="Bar"
        )
        User.objects.create(employee_branch="root", employee_code=1234)

        user = User.objects.get(employee__pk=employee.pk)
        self.assertEqual(user.employee_branch, "root")
        self.assertEqual(user.employee_code, 1234)
        self.assertEqual(user.employee, employee)
        self.assertEqual(user.employee2, employee)

        user2 = User.objects.get(employee2__pk=employee.pk)
        self.assertEqual(user2.employee_branch, "root")
        self.assertEqual(user2.employee_code, 1234)
        self.assertEqual(user2.employee, employee)
        self.assertEqual(user2.employee2, employee)

    def test_get_mixed_lookup(self):
        employee = Employee.objects.create(
            branch="root", employee_code=1234, first_name="Foo", last_name="Bar"
        )
        User.objects.create(employee_branch="root", employee_code=1234)

        user = User.objects.get(employee__branch="root", employee2__employee_code=1234)
        self.assertEqual(user.employee_branch, "root")
        self.assertEqual(user.employee_code, 1234)
        self.assertEqual(user.employee, employee)
        self.assertEqual(user.employee2, employee)

    def test_get_reverse(self):
        employee = Employee.objects.create(
            branch="root", employee_code=1234, first_name="Foo", last_name="Bar"
        )
        Employee.objects.create(
            branch="other", employee_code=1234, first_name="Foo", last_name="Baz"
        )
        user = User.objects.create(employee_branch="root", employee_code=1234)

        self.assertEqual(Employee.objects.get(user=user), employee)
        self.assertEqual(Employee.objects.get(user__id=user.pk), employee)
        self.assertEqual(Employee.objects.get(user__pk=user.pk), employee)
        self.assertEqual(Employee.objects.get(user__employee_id=employee.pk), employee)

        self.assertEqual(Employee.objects.get(user2=user), employee)
        self.assertEqual(Employee.objects.get(user2__id=user.pk), employee)
        self.assertEqual(Employee.objects.get(user2__pk=user.pk), employee)
        self.assertEqual(Employee.objects.get(user2__employee_id=employee.pk), employee)

    def test_get_reverse_mixed(self):
        employee = Employee.objects.create(
            branch="root", employee_code=1234, first_name="Foo", last_name="Bar"
        )
        Employee.objects.create(
            branch="other", employee_code=1234, first_name="Foo", last_name="Baz"
        )
        user = User.objects.create(employee_branch="root", employee_code=1234)

        self.assertEqual(
            Employee.objects.get(user2__id=user.id, user__employee_id=("root", 1234)),
            employee,
        )

        with self.assertRaises(Employee.DoesNotExist):
            Employee.objects.get(user2__id=user.id, user__employee_id=("other", 1234))

    def test_set_composite_foreign_key(self):
        house = House.objects.create(
            street="Candlewood Lane",
            number=698,
        )

        Owner.objects.create(name="Jessica Fletcher", home=house)
