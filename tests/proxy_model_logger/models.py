from django.db import models


class Parent(models.Model):
    name = models.CharField(max_length=50)


class Child(Parent):
    class Meta:
        proxy = True