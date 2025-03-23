"""
Tests for F() query expression syntax.
"""

import uuid

from django.db import models


class Manager(models.Model):
    name = models.CharField(max_length=50)
    secretary = models.ForeignKey(
        "Employee", models.CASCADE, null=True, related_name="managers"
    )


class Employee(models.Model):
    firstname = models.CharField(max_length=50)
    lastname = models.CharField(max_length=50)
    salary = models.IntegerField(blank=True, null=True)
    manager = models.ForeignKey(Manager, models.CASCADE, null=True)
    based_in_eu = models.BooleanField(default=False)

    def __str__(self):
        return "%s %s" % (self.firstname, self.lastname)


class RemoteEmployee(Employee):
    adjusted_salary = models.IntegerField()


class Company(models.Model):
    name = models.CharField(max_length=100)
    num_employees = models.PositiveIntegerField()
    num_chairs = models.PositiveIntegerField()
    ceo = models.ForeignKey(
        Employee,
        models.CASCADE,
        related_name="company_ceo_set",
    )
    point_of_contact = models.ForeignKey(
        Employee,
        models.SET_NULL,
        related_name="company_point_of_contact_set",
        null=True,
    )
    based_in_eu = models.BooleanField(default=False)

    def __str__(self):
        return self.name


class Number(models.Model):
    integer = models.BigIntegerField(db_column="the_integer")
    float = models.FloatField(null=True, db_column="the_float")
    decimal_value = models.DecimalField(max_digits=20, decimal_places=17, null=True)

    def __str__(self):
        return "%i, %s, %s" % (
            self.integer,
            "%.3f" % self.float if self.float is not None else None,
            "%.17f" % self.decimal_value if self.decimal_value is not None else None,
        )


class Experiment(models.Model):
    name = models.CharField(max_length=24)
    assigned = models.DateField()
    completed = models.DateField()
    estimated_time = models.DurationField()
    start = models.DateTimeField()
    end = models.DateTimeField()
    scalar = models.IntegerField(null=True)

    class Meta:
        db_table = "expressions_ExPeRiMeNt"
        ordering = ("name",)

    def duration(self):
        return self.end - self.start


class Result(models.Model):
    experiment = models.ForeignKey(Experiment, models.CASCADE)
    result_time = models.DateTimeField()

    def __str__(self):
        return "Result at %s" % self.result_time


class Time(models.Model):
    time = models.TimeField(null=True)

    def __str__(self):
        return str(self.time)


class SimulationRun(models.Model):
    start = models.ForeignKey(Time, models.CASCADE, null=True, related_name="+")
    end = models.ForeignKey(Time, models.CASCADE, null=True, related_name="+")
    midpoint = models.TimeField()

    def __str__(self):
        return "%s (%s to %s)" % (self.midpoint, self.start, self.end)


class UUIDPK(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4)


class UUID(models.Model):
    uuid = models.UUIDField(null=True)
    uuid_fk = models.ForeignKey(UUIDPK, models.CASCADE, null=True)


class Text(models.Model):
    name = models.TextField()


class JSONFieldModel(models.Model):
    data = models.JSONField(null=True)

    class Meta:
        required_db_features = {"supports_json_field"}
