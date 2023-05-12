from django.db import models


class Foo(models.Model):
    """Initial model named Foo"""

    pass


class Bar(models.Model):
    foo = models.ForeignKey(
        Foo,
        on_delete=models.DB_CASCADE,
        on_delete_db=models.ON_DELETE_DB_CHOICES.CASCADE_DB,
    )
