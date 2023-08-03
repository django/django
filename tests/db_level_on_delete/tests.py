from django.db import IntegrityError, transaction
from django.test import TestCase

from .models import (
    AnotherSetNullBaz,
    Bar,
    Baz,
    Child,
    DBDefaultsFK,
    DBDefaultsPK,
    DiamondChild,
    DiamondParent,
    Foo,
    Parent,
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

        foo.delete()

        with self.assertRaises(Bar.DoesNotExist):
            bar.refresh_from_db()

        with self.assertRaises(Baz.DoesNotExist):
            baz.refresh_from_db()

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

    def test_foreign_key_db_default(self):
        default_parent = DBDefaultsPK.objects.create(language_code="fr")
        parent = DBDefaultsPK.objects.create(language_code="en")
        child1 = DBDefaultsFK.objects.create(language_code=parent)
        with self.assertNumQueries(1):
            parent.delete()
        child1.refresh_from_db()
        self.assertEqual(child1.language_code, default_parent)


class DatabaseLevelOnDeleteQueryAssertionTests(TestCase):
    def test_queries_on_nested_cascade(self):
        foo = Foo.objects.create()

        for i in range(3):
            Bar.objects.create(foo=foo)

        for bar in Bar.objects.all():
            for i in range(3):
                Baz.objects.create(bar=bar)

        # one is the deletion
        with self.assertNumQueries(1):
            foo.delete()

    def test_queries_on_nested_set_null(self):
        foo = Foo.objects.create()

        for i in range(3):
            SetNullBar.objects.create(foo=foo)

        for setnullbar in SetNullBar.objects.all():
            for i in range(3):
                AnotherSetNullBaz.objects.create(setnullbar=setnullbar)

        # one is the deletion
        with self.assertNumQueries(1):
            foo.delete()

    def test_queries_on_nested_set_null_cascade(self):
        foo = Foo.objects.create()

        for i in range(3):
            Bar.objects.create(foo=foo)

        for bar in Bar.objects.all():
            for i in range(3):
                SetNullBaz.objects.create(bar=bar)

        # one is the deletion
        with self.assertNumQueries(1):
            foo.delete()

    def test_queries_on_inherited_model(self):
        gp = Foo.objects.create()
        parent = Parent.objects.create(grandparent_ptr=gp)
        diamond_parent = DiamondParent.objects.create(gp_ptr=gp)

        dc = DiamondChild.objects.create(
            parent_ptr=parent, diamondparent_ptr=diamond_parent
        )

        with self.assertNumQueries(1):
            gp.delete()

        with self.assertRaises(Parent.DoesNotExist):
            parent.refresh_from_db()

        with self.assertRaises(DiamondParent.DoesNotExist):
            diamond_parent.refresh_from_db()

        with self.assertRaises(DiamondChild.DoesNotExist):
            dc.refresh_from_db()

    def test_restrict_on_inherited_model(self):
        gp = Foo.objects.create()
        child = Child.objects.create(grandparent_ptr=gp)

        with transaction.atomic():
            with self.assertRaises(IntegrityError):
                gp.delete()

        child.refresh_from_db()
