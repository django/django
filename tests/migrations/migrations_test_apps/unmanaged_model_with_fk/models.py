from django.db import models


class Foo(models.Model):
    class Meta:
        managed = True


class Boo(models.Model):
    foo = models.ForeignKey("Foo", on_delete=models.CASCADE)

    class Meta:
        managed = False
