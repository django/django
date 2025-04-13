from django.db import models


class Car(models.Model):
    name = models.CharField(max_length=100)


class Person(models.Model):
    name = models.CharField(max_length=100)
    cars = models.ManyToManyField(Car, through="PossessedCar")
    data = models.BinaryField(null=True)


class PossessedCar(models.Model):
    car = models.ForeignKey(Car, models.CASCADE)
    belongs_to = models.ForeignKey(
        Person, models.CASCADE, related_name="possessed_cars"
    )


class Department(models.Model):
    name = models.CharField(max_length=100)


class Employee(models.Model):
    name = models.CharField(max_length=100)
    department = models.ForeignKey(Department, models.CASCADE, db_constraint=False)


class Role(models.Model):
    name = models.CharField(max_length=100)
    employee = models.ForeignKey(Employee, models.CASCADE, db_constraint=False)
