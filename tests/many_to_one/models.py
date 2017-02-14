"""
Many-to-one relationships

To define a many-to-one relationship, use ``ForeignKey()``.
"""
from django.db import models


class Reporter(models.Model):
    first_name = models.CharField(max_length=30)
    last_name = models.CharField(max_length=30)
    email = models.EmailField()

    def __str__(self):
        return "%s %s" % (self.first_name, self.last_name)


class Article(models.Model):
    headline = models.CharField(max_length=100)
    pub_date = models.DateField()
    reporter = models.ForeignKey(Reporter, models.CASCADE)

    def __str__(self):
        return self.headline

    class Meta:
        ordering = ('headline',)


class City(models.Model):
    id = models.BigAutoField(primary_key=True)
    name = models.CharField(max_length=50)

    def __str__(self):
        return self.name


class District(models.Model):
    city = models.ForeignKey(City, models.CASCADE, related_name='districts', null=True)
    name = models.CharField(max_length=50)

    def __str__(self):
        return self.name


# If ticket #1578 ever slips back in, these models will not be able to be
# created (the field names being lower-cased versions of their opposite
# classes is important here).
class First(models.Model):
    second = models.IntegerField()


class Second(models.Model):
    first = models.ForeignKey(First, models.CASCADE, related_name='the_first')


# Protect against repetition of #1839, #2415 and #2536.
class Third(models.Model):
    name = models.CharField(max_length=20)
    third = models.ForeignKey('self', models.SET_NULL, null=True, related_name='child_set')


class Parent(models.Model):
    name = models.CharField(max_length=20, unique=True)
    bestchild = models.ForeignKey('Child', models.SET_NULL, null=True, related_name='favored_by')


class Child(models.Model):
    name = models.CharField(max_length=20)
    parent = models.ForeignKey(Parent, models.CASCADE)


class ToFieldChild(models.Model):
    parent = models.ForeignKey(Parent, models.CASCADE, to_field='name')


# Multiple paths to the same model (#7110, #7125)
class Category(models.Model):
    name = models.CharField(max_length=20)

    def __str__(self):
        return self.name


class Record(models.Model):
    category = models.ForeignKey(Category, models.CASCADE)


class Relation(models.Model):
    left = models.ForeignKey(Record, models.CASCADE, related_name='left_set')
    right = models.ForeignKey(Record, models.CASCADE, related_name='right_set')

    def __str__(self):
        return "%s - %s" % (self.left.category.name, self.right.category.name)


# Test related objects visibility.
class SchoolManager(models.Manager):
    def get_queryset(self):
        return super().get_queryset().filter(is_public=True)


class School(models.Model):
    is_public = models.BooleanField(default=False)
    objects = SchoolManager()


class Student(models.Model):
    school = models.ForeignKey(School, models.CASCADE)
