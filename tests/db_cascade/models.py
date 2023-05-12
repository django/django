from django.db import models


class Foo(models.Model):
    """Initial model named Foo"""

    pass


class Bar(models.Model):
    """First level foreignkey child for Foo
    Implemented using database level cascading"""

    foo = models.ForeignKey(
        Foo,
        on_delete=models.DB_CASCADE,
        on_delete_db=models.ON_DELETE_DB_CHOICES.CASCADE_DB,
    )


class Baz(models.Model):
    """Second level foreignkey child for Foo
    Implemented using in DB cascading"""

    bar = models.ForeignKey(
        Bar,
        on_delete=models.DB_CASCADE,
        on_delete_db=models.ON_DELETE_DB_CHOICES.CASCADE_DB,
    )


# class Fiz(models.Model):
#     """Third level foreignkey child for Foo
#     Implemented using in python cascading"""
#     baz = models.ForeignKey(
#         Baz,
#         on_delete=models.CASCADE
#     )


class RestrictBar(models.Model):
    """First level child of foo with cascading set to restrict"""

    foo = models.ForeignKey(
        Foo,
        on_delete=models.DB_CASCADE,
        on_delete_db=models.ON_DELETE_DB_CHOICES.RESTRICT_DB,
    )


class RestrictBaz(models.Model):
    """Second level child of foo with cascading set to restrict"""

    bar = models.ForeignKey(
        Bar,
        on_delete=models.DB_CASCADE,
        on_delete_db=models.ON_DELETE_DB_CHOICES.RESTRICT_DB,
    )


class SetNullBar(models.Model):
    """First level child of foo with cascading set to null"""

    foo = models.ForeignKey(
        Foo,
        on_delete=models.DB_CASCADE,
        on_delete_db=models.ON_DELETE_DB_CHOICES.SET_NULL_DB,
        null=True,
    )
    another_field = models.CharField(max_length=20)


class SetNullBaz(models.Model):
    """Second level child of foo with cascading set to null"""

    bar = models.ForeignKey(
        Bar,
        on_delete=models.DB_CASCADE,
        on_delete_db=models.ON_DELETE_DB_CHOICES.SET_NULL_DB,
        null=True,
    )
    another_field = models.CharField(max_length=20)
