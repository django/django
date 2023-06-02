from django.db import models


class Foo(models.Model):
    """Initial model named Foo"""


class Bar(models.Model):
    foo = models.ForeignKey(
        Foo,
        on_delete=models.DB_CASCADE,
    )
