
from django.db import models


class Account(models.Model):
    num = models.IntegerField()


class Person(models.Model):
    GENDER_CHOICES = (
        ('M', 'Male'),
        ('F', 'Female'),
    )
    name = models.CharField(max_length=20)
    gender = models.CharField(max_length=1, choices=GENDER_CHOICES)
    pid = models.IntegerField(null=True, default=None)

    def __str__(self):
        return self.name


class Employee(Person):
    employee_num = models.IntegerField(default=0)
    profile = models.ForeignKey('Profile', models.SET_NULL, related_name='profiles', null=True)
    accounts = models.ManyToManyField('Account', related_name='employees', blank=True)


class Profile(models.Model):
    name = models.CharField(max_length=200)
    salary = models.FloatField(default=1000.0)

    def __str__(self):
        return self.name


class ProxyEmployee(Employee):
    class Meta:
        proxy = True
