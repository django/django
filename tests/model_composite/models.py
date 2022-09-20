"""
Using a composite primary key
"""

from django.db import models

class Employee(models.Model):
    composite_pk = models.CompositeField('branch', 'employee_code', primary_key=True)
    branch = models.TextField()
    employee_code = models.IntegerField(db_column="code")
    first_name = models.CharField(max_length=20)
    last_name = models.CharField(max_length=20)

    def __str__(self):
        return "%s %s" % (self.first_name, self.last_name)

class Employee2(models.Model):
    branch = models.TextField()
    employee_code = models.IntegerField(db_column="code")
    first_name = models.CharField(max_length=20)
    last_name = models.CharField(max_length=20)
    composite_pk = models.CompositeField('branch', 'employee_code', primary_key=True)

    class Meta:
        ordering = ("last_name", "first_name")

    def __str__(self):
        return "%s %s" % (self.first_name, self.last_name)

Employee2._meta.local_fields = [f for f in Employee2._meta.local_fields if f != Employee2._meta.pk] + [Employee2._meta.pk]

class User(models.Model):
    employee_id = models.CompositeField('employee_branch', 'employee_code')
    employee_branch = models.TextField()
    employee_code = models.IntegerField()
    employee = models.ForeignObject(Employee, models.DO_NOTHING, from_fields=('employee_id',), to_fields=('composite_pk',))
    employee2 = models.ForeignObject(Employee, models.DO_NOTHING, from_fields=('employee_branch', 'employee_code'), to_fields=('branch', 'employee_code'), related_name='user2')
