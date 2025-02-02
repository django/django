from django.core import checks
from django.db import connection, models
from django.db.models import F
from django.test import TestCase, skipUnlessAnyDBFeature
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

    def test_composite_pk_must_include_at_least_2_fields(self):
        expected_message = "CompositePrimaryKey must include at least two fields."
        with self.assertRaisesMessage(ValueError, expected_message):
            models.CompositePrimaryKey("id")

    def test_composite_pk_cannot_have_a_default(self):
        expected_message = "CompositePrimaryKey cannot have a default."
        with self.assertRaisesMessage(ValueError, expected_message):
            models.CompositePrimaryKey("tenant_id", "id", default=(1, 1))

    def test_composite_pk_cannot_have_a_database_default(self):
        expected_message = "CompositePrimaryKey cannot have a database default."
        with self.assertRaisesMessage(ValueError, expected_message):
            models.CompositePrimaryKey("tenant_id", "id", db_default=models.F("id"))

    def test_composite_pk_cannot_have_a_db_column(self):
        expected_message = "CompositePrimaryKey cannot have a db_column."
        with self.assertRaisesMessage(ValueError, expected_message):
            models.CompositePrimaryKey("tenant_id", "id", db_column="tenant_pk")

    def test_composite_pk_cannot_be_editable(self):
        expected_message = "CompositePrimaryKey cannot be editable."
        with self.assertRaisesMessage(ValueError, expected_message):
            models.CompositePrimaryKey("tenant_id", "id", editable=True)

    def test_composite_pk_must_be_a_primary_key(self):
        expected_message = "CompositePrimaryKey must be a primary key."
        with self.assertRaisesMessage(ValueError, expected_message):
            models.CompositePrimaryKey("tenant_id", "id", primary_key=False)

    def test_composite_pk_must_be_blank(self):
        expected_message = "CompositePrimaryKey must be blank."
        with self.assertRaisesMessage(ValueError, expected_message):
            models.CompositePrimaryKey("tenant_id", "id", blank=False)

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
                    hint="'foo_id' and 'foo' are the same fields.",
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

    def test_composite_pk_cannot_include_db_column(self):
        class Foo(models.Model):
            pk = models.CompositePrimaryKey("foo", "bar")
            foo = models.SmallIntegerField(db_column="foo_id")
            bar = models.SmallIntegerField(db_column="bar_id")

        class Bar(models.Model):
            pk = models.CompositePrimaryKey("foo_id", "bar_id")
            foo = models.SmallIntegerField(db_column="foo_id")
            bar = models.SmallIntegerField(db_column="bar_id")

        self.assertEqual(Foo.check(databases=self.databases), [])
        self.assertEqual(
            Bar.check(databases=self.databases),
            [
                checks.Error(
                    "'foo_id' cannot be included in the composite primary key.",
                    hint="'foo_id' is not a valid field.",
                    obj=Bar,
                    id="models.E042",
                ),
                checks.Error(
                    "'bar_id' cannot be included in the composite primary key.",
                    hint="'bar_id' is not a valid field.",
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

    @skipUnlessAnyDBFeature(
        "supports_virtual_generated_columns",
        "supports_stored_generated_columns",
    )
    def test_composite_pk_cannot_include_generated_field(self):
        class Foo(models.Model):
            pk = models.CompositePrimaryKey("id", "foo")
            id = models.IntegerField()
            foo = models.GeneratedField(
                expression=F("id"),
                output_field=models.IntegerField(),
                db_persist=connection.features.supports_stored_generated_columns,
            )

        self.assertEqual(
            Foo.check(databases=self.databases),
            [
                checks.Error(
                    "'foo' cannot be included in the composite primary key.",
                    hint="'foo' field is a generated field.",
                    obj=Foo,
                    id="models.E042",
                ),
            ],
        )

    def test_composite_pk_cannot_include_non_local_field(self):
        class Foo(models.Model):
            a = models.SmallIntegerField()

        class Bar(Foo):
            pk = models.CompositePrimaryKey("a", "b")
            b = models.SmallIntegerField()

        self.assertEqual(Foo.check(databases=self.databases), [])
        self.assertEqual(
            Bar.check(databases=self.databases),
            [
                checks.Error(
                    "'a' cannot be included in the composite primary key.",
                    hint="'a' field is not a local field.",
                    obj=Bar,
                    id="models.E042",
                ),
            ],
        )
