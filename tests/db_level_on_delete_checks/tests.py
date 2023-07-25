from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.core.checks import Error
from django.db import models
from django.test import TestCase

from .models import Bar, Foo


class DatabaseLevelCascadeCheckTests(TestCase):
    def test_system_check_on_nested_db_with_non_db_cascading(self):
        class BadBar(models.Model):
            foo = models.ForeignKey(Foo, on_delete=models.CASCADE)

        class Baz(models.Model):
            """First level child"""

            bar = models.ForeignKey(
                Bar,
                on_delete=models.CASCADE,
            )

        baz_field = Baz._meta.get_field("bar")
        related_model_status = {"model": Bar, "field": Bar._meta.get_field("foo")}
        self.assertEqual(
            baz_field.check(),
            [
                Error(
                    "Using python based on_delete with database "
                    "level on_delete referenced model is prohibited "
                    f"Related field is {related_model_status.get('field')}.",
                    hint="Use database level cascading for foreignkeys",
                    obj=baz_field,
                    id="fields.E323",
                ),
            ],
        )

        bad_bar_field = BadBar._meta.get_field("foo")
        self.assertEqual(bad_bar_field.check(), [])

        bar_field = Bar._meta.get_field("foo")
        self.assertEqual(bar_field.check(), [])

    def test_null_condition_with_set_null_db(self):
        class SetNullDbNotNullModel(models.Model):
            foo = models.ForeignKey(
                Foo,
                on_delete=models.DB_SET_NULL,
            )

            class Meta:
                managed = False

        field = SetNullDbNotNullModel._meta.get_field("foo")
        self.assertEqual(
            field.check(),
            [
                Error(
                    "Field specifies on_delete=DB_SET_NULL, but cannot be null.",
                    hint=(
                        "Set null=True argument on the field, or change the "
                        "on_delete rule."
                    ),
                    obj=field,
                    id="fields.E320",
                )
            ],
        )

    def test_check_on_inherited_models(self):
        class GrandParent(models.Model):
            pass

        class Parent(GrandParent):
            pass

        class DiamondParent(GrandParent):
            gp_ptr = models.OneToOneField(
                GrandParent,
                primary_key=True,
                parent_link=True,
                on_delete=models.DB_CASCADE,
            )

        class DiamondChild(Parent, DiamondParent):
            parent_ptr = models.OneToOneField(
                Parent, primary_key=True, parent_link=True, on_delete=models.DB_CASCADE
            )

        field = DiamondChild._meta.get_field("diamondparent_ptr")
        rel_field = DiamondParent._meta.get_field("gp_ptr")
        # error for having DB_CASCADE over normal cascade
        self.assertEqual(
            field.check(),
            [
                Error(
                    "Using python based on_delete with database "
                    "level on_delete referenced model is prohibited "
                    f"Related field is {rel_field}.",
                    hint="Use database level cascading for foreignkeys",
                    obj=field,
                    id="fields.E323",
                )
            ],
        )
        # No error for entire django cascade
        field = Parent._meta.get_field("grandparent_ptr")
        self.assertEqual(
            field.check(),
            [],
        )

    def test_check_on_generic_foreign_key(self):
        class SomeModel(models.Model):
            some_fk = models.ForeignKey(
                ContentType,
                on_delete=models.DB_CASCADE,
                related_name="ctcmnt",
            )
            object_id = models.PositiveIntegerField()
            content_object = GenericForeignKey("some_fk", "object_id")

            class Meta:
                abstract = True

        class SomeAnotherModel(models.Model):
            another_fk = models.ForeignKey(
                ContentType, on_delete=models.CASCADE, related_name="anfk"
            )
            object_id = models.PositiveIntegerField()
            content_object = GenericForeignKey("another_fk", "object_id")

            class Meta:
                abstract = True

        comment_field = SomeModel._meta.get_field("some_fk")
        self.assertEqual(
            comment_field.check(),
            [
                Error(
                    "Field specifies unsupported on_delete=DB_CASCADE on model "
                    "declaring a GenericForeignKey.",
                    hint="Change the on_delete rule to a non DB_* method",
                    obj=comment_field,
                    id="fields.E345",
                )
            ],
        )

        photo_field = SomeAnotherModel._meta.get_field("another_fk")
        self.assertEqual(
            photo_field.check(),
            [],
        )
