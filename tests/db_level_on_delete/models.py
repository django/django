from django.db import models


class Foo(models.Model):
    """Initial model named Foo"""


class ChildFoo(Foo):
    foo_ptr = models.OneToOneField(
        Foo,
        on_delete=models.DB_CASCADE,
        parent_link=True,
        primary_key=True,
    )


class Bar(models.Model):
    """First level foreignkey child for Foo
    Implemented using database level cascading"""

    foo = models.ForeignKey(
        Foo,
        on_delete=models.DB_CASCADE,
    )


class Baz(models.Model):
    """Second level foreignkey child for Foo
    Implemented using in DB cascading"""

    bar = models.ForeignKey(
        Bar,
        on_delete=models.DB_CASCADE,
    )


class RestrictBar(models.Model):
    """First level child of foo with cascading set to restrict"""

    foo = models.ForeignKey(
        Foo,
        on_delete=models.DB_RESTRICT,
    )


class RestrictBaz(models.Model):
    """Second level child of foo with cascading set to restrict"""

    bar = models.ForeignKey(
        Bar,
        on_delete=models.DB_RESTRICT,
    )


class SetNullBar(models.Model):
    """First level child of foo with cascading set to null"""

    foo = models.ForeignKey(
        Foo,
        on_delete=models.DB_SET_NULL,
        null=True,
    )
    another_field = models.CharField(max_length=20)


class SetNullBaz(models.Model):
    """Second level child of foo with cascading set to null"""

    bar = models.ForeignKey(
        Bar,
        on_delete=models.DB_SET_NULL,
        null=True,
    )
    another_field = models.CharField(max_length=20)


class AnotherSetNullBaz(models.Model):
    """Second level child of foo with cascading set to null"""

    setnullbar = models.ForeignKey(
        SetNullBar,
        on_delete=models.DB_SET_NULL,
        null=True,
    )
    another_field = models.CharField(max_length=20)
