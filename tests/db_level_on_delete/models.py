from django.db import models


class Foo(models.Model):
    """Initial model named Foo"""


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


class GrandParent(models.Model):
    pass


class Child(GrandParent):
    grandparent_ptr = models.OneToOneField(
        GrandParent, primary_key=True, parent_link=True, on_delete=models.DB_RESTRICT
    )


class Parent(GrandParent):
    grandparent_ptr = models.OneToOneField(
        GrandParent, primary_key=True, parent_link=True, on_delete=models.DB_CASCADE
    )


class DiamondParent(GrandParent):
    gp_ptr = models.OneToOneField(
        GrandParent, primary_key=True, parent_link=True, on_delete=models.DB_CASCADE
    )


class DiamondChild(Parent, DiamondParent):
    parent_ptr = models.OneToOneField(
        Parent, primary_key=True, parent_link=True, on_delete=models.DB_CASCADE
    )

    diamondparent_ptr = models.OneToOneField(
        DiamondParent, parent_link=True, on_delete=models.DB_CASCADE
    )
