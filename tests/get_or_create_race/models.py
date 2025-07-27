from django.db import models


class Parent(models.Model):
    name = models.CharField(max_length=100)


class Child(models.Model):
    parent = models.OneToOneField(
        Parent, on_delete=models.CASCADE, related_name="child"
    )
    name = models.CharField(max_length=100)
