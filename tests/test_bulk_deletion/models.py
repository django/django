from django.db import models


class Foo(models.Model):
    pass


class Bar(models.Model):
    foo = models.ForeignKey(Foo, on_delete=models.CASCADE)


class AnotherBar(models.Model):
    foo = models.ForeignKey(Foo, on_delete=models.SET_NULL, null=True)


class Baz(models.Model):
    bar = models.ForeignKey(Bar, on_delete=models.CASCADE)
