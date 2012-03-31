from django.contrib.auth.models import User
from django.db import models


class Book(models.Model):
    title = models.CharField(max_length=50)
    year = models.PositiveIntegerField(null=True, blank=True)
    author = models.ForeignKey(User, verbose_name="Verbose Author", related_name='books_authored', blank=True, null=True)
    contributors = models.ManyToManyField(User, verbose_name="Verbose Contributors", related_name='books_contributed', blank=True, null=True)
    is_best_seller = models.NullBooleanField(default=0)
    date_registered = models.DateField(null=True)
    no = models.IntegerField(verbose_name=u'number', blank=True, null=True) # This field is intentionally 2 characters long. See #16080.

    def __unicode__(self):
        return self.title


class Department(models.Model):
    code = models.CharField(max_length=4, unique=True)
    description = models.CharField(max_length=50, blank=True, null=True)

    def __unicode__(self):
        return self.description

class Employee(models.Model):
    department = models.ForeignKey(Department, to_field="code")
    name = models.CharField(max_length=100)

    def __unicode__(self):
        return self.name