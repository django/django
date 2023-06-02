from django.db.models.signals import post_delete, pre_delete
from django.test import TestCase

from .models import AnotherBar, Bar, Baz, Foo


class BulkDeletionTests(TestCase):
    def post_delete_listener(self, *args, **kwargs):
        self.post_delete_signals_count += 1

    def pre_delete_listener(self, *args, **kwargs):
        self.pre_delete_signals_count += 1

    def setUp(self):
        self.post_delete_signals_count = 0
        self.pre_delete_signals_count = 0
        pre_delete.connect(self.pre_delete_listener, sender=Baz)
        post_delete.connect(self.post_delete_listener, sender=Baz)

    def setDown(self):
        self.post_delete_signals_count = 0
        self.pre_delete_signals_count = 0

    def test_query_in_bulk_deletion(self):
        self.pre_delete_signal_was_called = False
        self.post_delete_signal_was_called = False

        foo = Foo.objects.create()
        for i in range(3):
            bar = Bar.objects.create(foo=foo)
            AnotherBar.objects.create(foo=foo)
            for j in range(3):
                Baz.objects.create(bar=bar)

        with self.assertNumQueries(6):
            # 2 SELECTS for models with cascaded foreignkey childs
            # 1 UPDATE for the models with SET NULL foreignkey
            # 3 DELETES for 3 deleted models
            foo_objs = Foo.objects.filter(pk=foo.pk)
            foo_objs.bulk_delete()

        self.assertIsNone(AnotherBar.objects.first().foo)
        self.assertEqual(self.pre_delete_signals_count, 0)
        self.assertEqual(self.post_delete_signals_count, 0)
        self.setDown()

    def test_query_in_normal_deletion(self):
        self.pre_delete_signal_was_called = False
        self.post_delete_signal_was_called = False

        foo = Foo.objects.create()
        for i in range(3):
            bar = Bar.objects.create(foo=foo)
            AnotherBar.objects.create(foo=foo)
            for j in range(3):
                Baz.objects.create(bar=bar)

        with self.assertNumQueries(7):
            # 2 SELECTS for models with cascaded foreignkey childs
            # 1 SELECT for the model with signals
            # 1 UPDATE for the models with SET NULL foreignkey
            # 3 DELETES for 3 deleted models
            foo_objs = Foo.objects.filter(pk=foo.pk)
            foo_objs.delete()

        self.assertIsNone(AnotherBar.objects.first().foo)
        self.assertEqual(self.pre_delete_signals_count, 9)
        self.assertEqual(self.post_delete_signals_count, 9)
        self.setDown()
