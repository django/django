from django.db.models import sql
from django.db.models.loading import cache
from django.db.models.query import CollectedObjects
from django.db.models.query_utils import CyclicDependency
from django.test import TestCase

from models import A, B, C, D, E, F


class DeleteTests(TestCase):
    def clear_rel_obj_caches(self, *models):
        for m in models:
            if hasattr(m._meta, '_related_objects_cache'):
                del m._meta._related_objects_cache

    def order_models(self, *models):
        cache.app_models["delete"].keyOrder = models

    def setUp(self):
        self.order_models("a", "b", "c", "d", "e", "f")
        self.clear_rel_obj_caches(A, B, C, D, E, F)

    def tearDown(self):
        self.order_models("a", "b", "c", "d", "e", "f")
        self.clear_rel_obj_caches(A, B, C, D, E, F)

    def test_collected_objects(self):
        g = CollectedObjects()
        self.assertFalse(g.add("key1", 1, "item1", None))
        self.assertEqual(g["key1"], {1: "item1"})

        self.assertFalse(g.add("key2", 1, "item1", "key1"))
        self.assertFalse(g.add("key2", 2, "item2", "key1"))

        self.assertEqual(g["key2"], {1: "item1", 2: "item2"})

        self.assertFalse(g.add("key3", 1, "item1", "key1"))
        self.assertTrue(g.add("key3", 1, "item1", "key2"))
        self.assertEqual(g.ordered_keys(), ["key3", "key2", "key1"])

        self.assertTrue(g.add("key2", 1, "item1", "key3"))
        self.assertRaises(CyclicDependency, g.ordered_keys)

    def test_delete(self):
        ## Second, test the usage of CollectedObjects by Model.delete()

        # Due to the way that transactions work in the test harness, doing
        # m.delete() here can work but fail in a real situation, since it may
        # delete all objects, but not in the right order. So we manually check
        # that the order of deletion is correct.

        # Also, it is possible that the order is correct 'accidentally', due
        # solely to order of imports etc.  To check this, we set the order that
        # 'get_models()' will retrieve to a known 'nice' order, and then try
        # again with a known 'tricky' order.  Slightly naughty access to
        # internals here :-)

        # If implementation changes, then the tests may need to be simplified:
        #  - remove the lines that set the .keyOrder and clear the related
        #    object caches
        #  - remove the second set of tests (with a2, b2 etc)

        a1 = A.objects.create()
        b1 = B.objects.create(a=a1)
        c1 = C.objects.create(b=b1)
        d1 = D.objects.create(c=c1, a=a1)

        o = CollectedObjects()
        a1._collect_sub_objects(o)
        self.assertEqual(o.keys(), [D, C, B, A])
        a1.delete()

        # Same again with a known bad order
        self.order_models("d", "c", "b", "a")
        self.clear_rel_obj_caches(A, B, C, D)

        a2 = A.objects.create()
        b2 = B.objects.create(a=a2)
        c2 = C.objects.create(b=b2)
        d2 = D.objects.create(c=c2, a=a2)

        o = CollectedObjects()
        a2._collect_sub_objects(o)
        self.assertEqual(o.keys(), [D, C, B, A])
        a2.delete()

    def test_collected_objects_null(self):
        g = CollectedObjects()
        self.assertFalse(g.add("key1", 1, "item1", None))
        self.assertFalse(g.add("key2", 1, "item1", "key1", nullable=True))
        self.assertTrue(g.add("key1", 1, "item1", "key2"))
        self.assertEqual(g.ordered_keys(), ["key1", "key2"])

    def test_delete_nullable(self):
        e1 = E.objects.create()
        f1 = F.objects.create(e=e1)
        e1.f = f1
        e1.save()

        # Since E.f is nullable, we should delete F first (after nulling out
        # the E.f field), then E.

        o = CollectedObjects()
        e1._collect_sub_objects(o)
        self.assertEqual(o.keys(), [F, E])

        # temporarily replace the UpdateQuery class to verify that E.f is
        # actually nulled out first

        logged = []
        class LoggingUpdateQuery(sql.UpdateQuery):
            def clear_related(self, related_field, pk_list, using):
                logged.append(related_field.name)
                return super(LoggingUpdateQuery, self).clear_related(related_field, pk_list, using)
        original = sql.UpdateQuery
        sql.UpdateQuery = LoggingUpdateQuery

        e1.delete()
        self.assertEqual(logged, ["f"])
        logged = []

        e2 = E.objects.create()
        f2 = F.objects.create(e=e2)
        e2.f = f2
        e2.save()

        # Same deal as before, though we are starting from the other object.
        o = CollectedObjects()
        f2._collect_sub_objects(o)
        self.assertEqual(o.keys(), [F, E])
        f2.delete()
        self.assertEqual(logged, ["f"])
        logged = []

        sql.UpdateQuery = original
