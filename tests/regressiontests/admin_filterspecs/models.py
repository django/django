from django.db import models
from django.contrib.auth.models import User

class Book(models.Model):
    title = models.CharField(max_length=25)
    year = models.PositiveIntegerField(null=True, blank=True)
    author = models.ForeignKey(User, related_name='books_authored', blank=True, null=True)
    contributors = models.ManyToManyField(User, related_name='books_contributed', blank=True, null=True)

    def __unicode__(self):
        return self.title

class BoolTest(models.Model):
    NO = False
    YES = True
    YES_NO_CHOICES = (
        (NO, 'no'),
        (YES, 'yes')
    )
    completed = models.BooleanField(
        default=NO,
        choices=YES_NO_CHOICES
    )


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
