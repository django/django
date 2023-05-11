from django.db import models


class Foo(models.Model):
    """Initial model named Foo"""

    pass


class Bar(models.Model):
    """First level foreignkey child for Foo
    Implemented using database level cascading"""

    foo = models.ForeignKey(
        Foo,
        on_delete=models.DO_NOTHING,
        on_delete_db=models.ON_DELETE_DB_CHOICES.CASCADE_DB,
    )


class Baz(models.Model):
    """Second level foreignkey child for Foo
    Implemented using in python cascading"""

    bar = models.ForeignKey(Bar, on_delete=models.CASCADE)
