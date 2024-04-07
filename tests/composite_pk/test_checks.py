from django.core import checks
from django.db import models
from django.test import TestCase
from django.test.utils import isolate_apps


@isolate_apps("composite_pk")
class CompositePKChecksTests(TestCase):
    maxDiff = None

    def test_composite_pk_must_be_unique_strings(self):
        test_cases = (
            (),
            (0,),
            (1,),
            ("id", False),
            ("id", "id"),
            (("id",),),
        )

        for i, args in enumerate(test_cases):
            with (
                self.subTest(args=args),
                self.assertRaisesMessage(
                    ValueError, "CompositePrimaryKey args must be unique strings."
                ),
            ):
                models.CompositePrimaryKey(*args)

    def test_composite_pk_must_not_have_other_pk_field(self):
        class Foo(models.Model):
            pk = models.CompositePrimaryKey("foo_id", "id")
            foo_id = models.IntegerField()
            id = models.IntegerField(primary_key=True)

        self.assertEqual(
            Foo.check(databases=self.databases),
            [
                checks.Error(
                    "The model cannot have more than one field with "
                    "'primary_key=True'.",
                    obj=Foo,
                    id="models.E026",
                ),
            ],
        )

    def test_composite_pk_cannot_include_nullable_field(self):
        class Foo(models.Model):
            pk = models.CompositePrimaryKey("foo_id", "id")
            foo_id = models.IntegerField()
            id = models.IntegerField(null=True)

        self.assertEqual(
            Foo.check(databases=self.databases),
            [
                checks.Error(
                    "'id' cannot be included in the composite primary key.",
                    hint="'id' field may not set 'null=True'.",
                    obj=Foo,
                    id="models.E042",
                ),
            ],
        )

    def test_composite_pk_can_include_fk_name(self):
        class Foo(models.Model):
            pass

        class Bar(models.Model):
            pk = models.CompositePrimaryKey("foo", "id")
            foo = models.ForeignKey(Foo, on_delete=models.CASCADE)
            id = models.SmallIntegerField()

        self.assertEqual(Foo.check(databases=self.databases), [])
        self.assertEqual(Bar.check(databases=self.databases), [])

    def test_composite_pk_cannot_include_same_field(self):
        class Foo(models.Model):
            pass

        class Bar(models.Model):
            pk = models.CompositePrimaryKey("foo", "foo_id")
            foo = models.ForeignKey(Foo, on_delete=models.CASCADE)
            id = models.SmallIntegerField()

        self.assertEqual(Foo.check(databases=self.databases), [])
        self.assertEqual(
            Bar.check(databases=self.databases),
            [
                checks.Error(
                    "'foo_id' cannot be included in the composite primary key.",
                    hint="'foo_id' is an alias of 'foo'.",
                    obj=Bar,
                    id="models.E042",
                ),
            ],
        )

    def test_composite_pk_cannot_include_composite_pk_field(self):
        class Foo(models.Model):
            pk = models.CompositePrimaryKey("id", "pk")
            id = models.SmallIntegerField()

        self.assertEqual(
            Foo.check(databases=self.databases),
            [
                checks.Error(
                    "'pk' cannot be included in the composite primary key.",
                    hint="'pk' field has no column.",
                    obj=Foo,
                    id="models.E042",
                ),
            ],
        )

    def test_composite_pk_can_include_db_column(self):
        class Foo(models.Model):
            pk = models.CompositePrimaryKey("id")
            id = models.SmallIntegerField(db_column="foo")

        class Bar(models.Model):
            pk = models.CompositePrimaryKey("bar")
            id = models.SmallIntegerField(db_column="bar")

        self.assertEqual(Foo.check(databases=self.databases), [])
        self.assertEqual(
            Bar.check(databases=self.databases),
            [
                checks.Error(
                    "'bar' cannot be included in the composite primary key.",
                    hint="'bar' is not a valid field.",
                    obj=Bar,
                    id="models.E042",
                ),
            ],
        )

    def test_foreign_object_can_refer_composite_pk(self):
        class Foo(models.Model):
            pass

        class Bar(models.Model):
            pk = models.CompositePrimaryKey("foo_id", "id")
            foo = models.ForeignKey(Foo, on_delete=models.CASCADE)
            id = models.IntegerField()

        class Baz(models.Model):
            pk = models.CompositePrimaryKey("foo_id", "id")
            foo = models.ForeignKey(Foo, on_delete=models.CASCADE)
            id = models.IntegerField()
            bar_id = models.IntegerField()
            bar = models.ForeignObject(
                Bar,
                on_delete=models.CASCADE,
                from_fields=("foo_id", "bar_id"),
                to_fields=("foo_id", "id"),
            )

        self.assertEqual(Foo.check(databases=self.databases), [])
        self.assertEqual(Bar.check(databases=self.databases), [])
        self.assertEqual(Baz.check(databases=self.databases), [])

    def test_composite_pk_must_be_named_pk(self):
        class Foo(models.Model):
            primary_key = models.CompositePrimaryKey("foo_id", "id")
            foo_id = models.IntegerField()
            id = models.IntegerField()

        self.assertEqual(
            Foo.check(databases=self.databases),
            [
                checks.Error(
                    "'CompositePrimaryKey' must be named 'pk'.",
                    obj=Foo._meta.get_field("primary_key"),
                    id="fields.E013",
                ),
            ],
        )
