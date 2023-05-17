from django.db import IntegrityError
from django.test import TestCase

from .models import (
    AnotherSetNullBaz,
    Bar,
    Baz,
    Foo,
    RestrictBar,
    RestrictBaz,
    SetNullBar,
    SetNullBaz,
)


class DatabaseLevelOnDeleteTests(TestCase):
    def test_deletion_on_nested_cascades(self):
        foo = Foo.objects.create()
        bar = Bar.objects.create(foo=foo)
        baz = Baz.objects.create(bar=bar)

        self.assertEqual(bar, Bar.objects.get(pk=bar.pk))
        self.assertEqual(baz, Baz.objects.get(pk=baz.pk))

        foo.delete()

        with self.assertRaises(Bar.DoesNotExist):
            Bar.objects.get(pk=bar.pk)

        with self.assertRaises(Baz.DoesNotExist):
            Baz.objects.get(pk=baz.pk)

    def test_restricted_deletion(self):
        foo = Foo.objects.create()
        RestrictBar.objects.create(foo=foo)

        with self.assertRaises(IntegrityError):
            foo.delete()

    def test_restricted_deletion_by_cascade(self):
        foo = Foo.objects.create()
        bar = Bar.objects.create(foo=foo)
        RestrictBaz.objects.create(bar=bar)
        with self.assertRaises(IntegrityError):
            foo.delete()

    def test_deletion_on_set_null(self):
        foo = Foo.objects.create()
        bar = SetNullBar.objects.create(foo=foo, another_field="Some Value")
        foo.delete()
        orphan_bar = SetNullBar.objects.get(pk=bar.pk)
        self.assertEqual(bar.pk, orphan_bar.pk)
        self.assertEqual(bar.another_field, orphan_bar.another_field)
        self.assertNotEqual(bar.foo, orphan_bar.foo)
        self.assertIsNone(orphan_bar.foo)

    def test_set_null_on_cascade_deletion(self):
        foo = Foo.objects.create()
        bar = Bar.objects.create(foo=foo)
        baz = SetNullBaz.objects.create(bar=bar, another_field="Some Value")
        foo.delete()
        orphan_baz = SetNullBaz.objects.get(pk=baz.pk)
        self.assertEqual(baz.pk, orphan_baz.pk)
        self.assertEqual(baz.another_field, orphan_baz.another_field)
        self.assertNotEqual(baz.bar, orphan_baz.bar)
        self.assertIsNone(orphan_baz.bar)

    def test_nested_set_null_on_deletion(self):
        foo = Foo.objects.create()
        bar = SetNullBar.objects.create(foo=foo)
        baz = AnotherSetNullBaz.objects.create(setnullbar=bar)
        foo.delete()

        orphan_bar = SetNullBar.objects.get(pk=bar.pk)
        self.assertEqual(bar.pk, orphan_bar.pk)
        self.assertEqual(bar.another_field, orphan_bar.another_field)
        self.assertNotEqual(bar.foo, orphan_bar.foo)
        self.assertIsNone(orphan_bar.foo)

        orphan_baz = AnotherSetNullBaz.objects.get(pk=baz.pk)
        self.assertEqual(baz.pk, orphan_baz.pk)
        self.assertEqual(baz.another_field, orphan_baz.another_field)
        self.assertEqual(baz.setnullbar, orphan_baz.setnullbar)
        self.assertIsNotNone(orphan_baz.setnullbar)


class DatabaseLevelOnDeleteQueryAssertionTests(TestCase):
    def test_queries_on_nested_cascade(self):
        foo = Foo.objects.create()

        for i in range(3):
            Bar.objects.create(foo=foo)

        for bar in Bar.objects.all():
            for i in range(3):
                Baz.objects.create(bar=bar)

        # one is the deletion
        # three select queries for Bar, SetNullBar and RestrictBar
        with self.assertNumQueries(4):
            foo.delete()

    def test_queries_on_nested_set_null(self):
        foo = Foo.objects.create()

        for i in range(3):
            SetNullBar.objects.create(foo=foo)

        for setnullbar in SetNullBar.objects.all():
            for i in range(3):
                AnotherSetNullBaz.objects.create(setnullbar=setnullbar)

        # one is the deletion
        # three select queries for Bar, SetNullBar and RestrictBar
        with self.assertNumQueries(4):
            foo.delete()

    def test_queries_on_nested_set_null_cascade(self):
        foo = Foo.objects.create()

        for i in range(3):
            Bar.objects.create(foo=foo)

        for bar in Bar.objects.all():
            for i in range(3):
                SetNullBaz.objects.create(bar=bar)

        # one is the deletion
        # three select queries for Bar, SetNullBar and RestrictBar
        with self.assertNumQueries(4):
            foo.delete()
