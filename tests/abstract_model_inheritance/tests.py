from __future__ import unicode_literals

from django.apps import apps
from django.contrib.contenttypes.fields import (
    GenericForeignKey, GenericRelation,
)
from django.contrib.contenttypes.models import ContentType
from django.core.checks import Error
from django.core.exceptions import FieldDoesNotExist, FieldError
from django.db import models
from django.test import TestCase
from django.utils import six


class IsolatedModelsTestCase(TestCase):

    def setUp(self):
        # The unmanaged models need to be removed after the test in order to
        # prevent bad interactions with the flush operation in other tests.
        self._old_models = apps.app_configs['abstract_model_inheritance'].models.copy()

    def tearDown(self):
        apps.app_configs['abstract_model_inheritance'].models = self._old_models
        apps.all_models['abstract_model_inheritance'] = self._old_models
        apps.clear_cache()


class AbstractInheritanceTests(IsolatedModelsTestCase):
    def test_single_parent(self):
        class Parent(models.Model):
            name = models.CharField(max_length=30)

            class Meta:
                abstract = True

        class Child(Parent):
            name = models.CharField(max_length=50)

            class Meta:
                abstract = True

        class Cousin(Parent):
            name = models.CharField(max_length=50)

        class GrandChild(Child):
            pass

        self.assertEqual(Child._meta.get_field('name').max_length, 50)
        self.assertEqual(Cousin._meta.get_field('name').max_length, 50)
        self.assertEqual(GrandChild._meta.get_field('name').max_length, 50)

    def test_multiple_parents(self):
        class GrandMother(models.Model):
            class Meta:
                abstract = True

        class GrandFather(models.Model):
            name = models.CharField(max_length=30)

            class Meta:
                abstract = True

        class Mother(GrandMother, GrandFather):
            class Meta:
                abstract = True

        class Father(GrandMother, GrandFather):
            name = models.CharField(max_length=50)

            class Meta:
                abstract = True

        class Child(Mother, Father):
            pass

        self.assertEqual(Mother._meta.get_field('name').max_length, 30)
        self.assertEqual(Father._meta.get_field('name').max_length, 50)
        self.assertEqual(Child._meta.get_field('name').max_length, 30)

    def test_ignore_field(self):
        class Parent(models.Model):
            name = models.CharField(max_length=30)

            class Meta:
                abstract = True

        class Child(Parent):
            name = None

            class Meta:
                abstract = True

        class SecondChild(Parent):
            name = None

        with self.assertRaises(FieldDoesNotExist):
            Child._meta.get_field('name')

        with self.assertRaises(FieldDoesNotExist):
            SecondChild._meta.get_field('name')

    def test_foreign_key(self):
        class Foo(models.Model):
            pass

        class Father(models.Model):
            foo = models.CharField(max_length=30)
            foo_id = models.IntegerField()

            class Meta:
                abstract = True

        class Mother(models.Model):
            foo = models.ForeignKey(Foo)

            class Meta:
                abstract = True

        class FathersChild(Father):
            foo = models.ForeignKey(Foo)

        class MothersChild(Mother):
            foo = models.CharField(max_length=30)
            foo_id = models.IntegerField()

        self.assertTrue(isinstance(FathersChild._meta.get_field('foo'), models.ForeignKey))
        self.assertTrue(isinstance(FathersChild._meta.get_field('foo_id'), models.ForeignKey))
        self.assertTrue(isinstance(MothersChild._meta.get_field('foo'), models.CharField))
        self.assertTrue(isinstance(MothersChild._meta.get_field('foo_id'), models.IntegerField))

    def test_reverse_foreign_key(self):
        class Parent(models.Model):
            foo = models.CharField(max_length=100)

            class Meta:
                abstract = True

        class Child(Parent):
            pass

        class OtherChild(Parent):
            foo = None

        class Foo(models.Model):
            bar = models.ForeignKey(Child, related_name='foo')
            baz = models.ForeignKey(OtherChild, related_name='foo')

        errors = Foo._meta.get_field('bar').check()
        errors.extend(Foo._meta.get_field('baz').check())
        expected = [
            Error(
                "Reverse accessor for 'Foo.bar' clashes with field name 'Child.foo'.",
                hint=("Rename field 'Child.foo', or add/change "
                      "a related_name argument to the definition "
                      "for field 'Foo.bar'."),
                obj=Foo._meta.get_field('bar'),
                id='fields.E302',
            ),
            Error(
                "Reverse query name for 'Foo.bar' clashes with field name 'Child.foo'.",
                hint=("Rename field 'Child.foo', or add/change "
                      "a related_name argument to the definition "
                      "for field 'Foo.bar'."),
                obj=Foo._meta.get_field('bar'),
                id='fields.E303',
            ),
        ]
        self.assertEqual(errors, expected)

    def test_virtual_field(self):
        class FamilyMember(models.Model):
            content_type = models.ForeignKey(ContentType)
            object_id = models.PositiveIntegerField()
            content_object = GenericForeignKey('content_type', 'object_id')

        class Father(models.Model):
            family_member = GenericRelation(FamilyMember)

            class Meta:
                abstract = True

        class FathersChild(Father):
            family_member = models.CharField(max_length=100)

        class Mother(models.Model):
            family_member = models.CharField(max_length=100)

            class Meta:
                abstract = True

        class MothersChild(Mother):
            family_member = GenericRelation(FamilyMember)

        self.assertTrue(isinstance(FathersChild._meta.get_field('family_member'), models.CharField))
        self.assertTrue(isinstance(MothersChild._meta.get_field('family_member'), GenericRelation))

    def test_locked_field(self):
        class Mother(models.Model):
            name = models.CharField(max_length=30, locked=True)

            class Meta:
                abstract = True

        class Father(models.Model):
            name = models.CharField(max_length=50)

            class Meta:
                abstract = True

        with six.assertRaisesRegex(self, FieldError, "Local field 'name' in class 'Child' clashes"):
            class Child(Mother):
                name = models.CharField(max_length=50)

        with six.assertRaisesRegex(self, FieldError, "Local field 'name' in class 'SecondChild' clashes"):
            class SecondChild(Father, Mother):
                pass

        class ThirdChild(Mother, Father):
            pass

        errors = ThirdChild.check()
        self.assertEqual(errors, [])

    def test_extended_inheritance(self):
        class GrandParent(models.Model):
            name = models.CharField(max_length=30)

            class Meta:
                abstract = True

        class Parent(GrandParent):
            pass

        class Child(Parent):
            class Meta:
                abstract = True

        class GrandChild(Child):
            name = models.CharField(max_length=100)

        errors = GrandChild.check()
        expected = [
            Error(
                "The field 'name' clashes with the field 'name' from model 'abstract_model_inheritance.parent'.",
                hint=None,
                obj=GrandChild._meta.get_field('name'),
                id="models.E006",
            ),
        ]
        self.assertEqual(errors, expected)

    def test_shadowed_attname(self):
        class Foo(models.Model):
            pass

        class Parent(models.Model):
            foo = models.ForeignKey(Foo)

            class Meta:
                abstract = True

        class Child(Parent):
            foo_id = models.IntegerField()

        field = Child._meta.get_field('foo_id')
        errors = Child.check()
        expected = [
            Error(
                "The field 'foo_id' clashes with the field 'foo' from model 'abstract_model_inheritance.child'.",
                hint=None,
                obj=field,
                id='models.E006',
            )
        ]
        self.assertEqual(errors, expected)

    def test_shadowed_concrete_field(self):
        class Father(models.Model):
            name = models.CharField(max_length=30)

        class Mother(models.Model):
            name = models.CharField(max_length=50)

            class Meta:
                abstract = True

        with six.assertRaisesRegex(self, FieldError, "Local field 'name' in class 'Child' clashes"):
            class Child(Mother, Father):
                pass
