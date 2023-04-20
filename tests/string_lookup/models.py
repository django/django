from django.db import models


class Foo(models.Model):
    name = models.CharField(max_length=50)
    friend = models.CharField(max_length=50, blank=True)


class Bar(models.Model):
    name = models.CharField(max_length=50)
    normal = models.ForeignKey(Foo, models.CASCADE, related_name="normal_foo")
    fwd = models.ForeignKey("Whiz", models.CASCADE)
    back = models.ForeignKey("Foo", models.CASCADE)


class Whiz(models.Model):
    name = models.CharField(max_length=50)


class Child(models.Model):
    parent = models.OneToOneField("Base", models.CASCADE)
    name = models.CharField(max_length=50)


class Base(models.Model):
    name = models.CharField(max_length=50)


class Article(models.Model):
    name = models.CharField(max_length=50)
    text = models.TextField()
    submitted_from = models.GenericIPAddressField(blank=True, null=True)
