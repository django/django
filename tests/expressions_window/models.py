from django.db import models


class Employee(models.Model):
    name = models.CharField(max_length=40, blank=False, null=False)
    salary = models.PositiveIntegerField()
    department = models.CharField(max_length=40, blank=False, null=False)
    hire_date = models.DateField(blank=False, null=False)

    def __str__(self):
        return '{}, {}, {}, {}'.format(self.name, self.department, self.salary, self.hire_date)
