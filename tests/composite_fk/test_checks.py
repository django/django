from django.core import checks
from django.db import models
from django.test import TestCase
from django.test.utils import isolate_apps


@isolate_apps("composite_fk")
class CompositeFKChecksTests(TestCase):
    def test_from_and_to_fields_must_be_same_length(self):
        test_cases = [
            {"to_fields": ("foo_id", "id")},
            {"from_fields": ("foo_id", "id")},
            {"from_fields": ("id",), "to_fields": ("foo_id", "id")},
            {"from_fields": (), "to_fields": ()},
        ]

        for kwargs in test_cases:
            with (
                self.subTest(kwargs=kwargs),
                self.assertRaisesMessage(
                    ValueError,
                    "Foreign Object from and to fields must be the same non-zero "
                    "length",
                ),
            ):
                fk = models.ForeignKey("Foo", on_delete=models.CASCADE, **kwargs)
                self.assertIsNotNone(fk.related_fields)

    def test_to_field_conflicts_with_to_fields(self):
        with self.assertRaisesMessage(
            ValueError, "Cannot specify both 'to_field' and 'to_fields'."
        ):
            self.assertIsNotNone(
                models.ForeignKey(
                    "Foo",
                    on_delete=models.CASCADE,
                    to_field="foo_id",
                    to_fields=["bar_id"],
                )
            )

    def test_to_fields_doesnt_exist(self):
        class Foo(models.Model):
            pass

        class Bar(models.Model):
            foo_id = models.IntegerField()
            foo = models.ForeignKey(
                Foo,
                on_delete=models.CASCADE,
                from_fields=["foo_id", "id"],
                to_fields=["id", "bar_id"],
            )

        self.assertEqual(
            Bar.check(),
            [
                checks.Error(
                    "The to_field 'bar_id' doesn't exist on the related model "
                    "'composite_fk.Foo'.",
                    obj=Bar._meta.get_field("foo"),
                    id="fields.E312",
                )
            ],
        )

    def test_from_fields_doesnt_exist(self):
        class Foo(models.Model):
            bar_id = models.IntegerField()

        class Bar(models.Model):
            foo_id = models.IntegerField()
            foo = models.ForeignKey(
                Foo,
                on_delete=models.CASCADE,
                from_fields=["foo_id", "baz_id"],
                to_fields=["id", "bar_id"],
            )

        self.assertEqual(
            Bar.check(),
            [
                checks.Error(
                    "The from_field 'baz_id' doesn't exist on the model "
                    "'composite_fk.Bar'.",
                    obj=Bar._meta.get_field("foo"),
                    id="fields.E312",
                )
            ],
        )

    def test_self_cant_be_used_in_from_fields(self):
        class Foo(models.Model):
            bar_id = models.IntegerField()

        class Bar(models.Model):
            foo_id = models.IntegerField()
            foo = models.ForeignKey(
                Foo,
                on_delete=models.CASCADE,
                from_fields=["self", "foo_id"],
                to_fields=["bar_id", "id"],
            )

        self.assertEqual(
            Bar.check(),
            [
                checks.Error(
                    "The from_field 'self' doesn't exist on the model "
                    "'composite_fk.Bar'.",
                    obj=Bar._meta.get_field("foo"),
                    id="fields.E312",
                )
            ],
        )
