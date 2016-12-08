from django.db.models.expressions import F, Value
from django.db.models.functions import Lower
from django.test import TestCase

from .models import Employee


class ModelSaveFieldRefreshTests(TestCase):
    def test_insert(self):
        employee = Employee.objects.create(firstname=Lower(Value('David')), lastname='Smith')
        refreshed = Employee.objects.get(pk=employee.pk)
        self.assertEqual(refreshed.firstname, 'david')
        self.assertEqual(employee.firstname, 'david')

    def test_update(self):
        employee = Employee.objects.create(firstname='David', lastname='Smith')
        employee.firstname = Lower('firstname')
        employee.save()
        refreshed = Employee.objects.get(pk=employee.pk)
        self.assertEqual(refreshed.firstname, 'david')
        self.assertEqual(employee.firstname, 'david')

    def test_update_fields(self):
        employee = Employee.objects.create(firstname='David', lastname='Smith')
        employee.firstname = Lower('firstname')
        employee.save(update_fields=['lastname'])
        self.assertNotEqual(employee.firstname, 'david')  # Lower(F(firstname))
        employee.save(update_fields=['firstname'])
        self.assertEqual(employee.firstname, 'david')

    def test_f_refreshed(self):
        employee = Employee.objects.create(firstname='David', lastname='Smith', salary=0)
        employee.salary = F('salary') + 1
        employee.save()
        self.assertEqual(employee.salary, 1)
