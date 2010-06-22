from django.test import TestCase
from django.db.models.query import CollectedObjects
from django.db.models.query_utils import CyclicDependency
from django.db.models.loading import cache
import django.db.models.sql

from models import A, B, C, D, E, F

test_last_cleared_field = ''

def clear_rel_obj_caches(models):
     for m in models:
         if hasattr(m._meta, '_related_objects_cache'):
             del m._meta._related_objects_cache

class LoggingUpdateQuery(django.db.models.sql.UpdateQuery):
    def clear_related(self, related_field, pk_list, using):
        global test_last_cleared_field
        test_last_cleared_field = related_field.name
        return super(LoggingUpdateQuery, self).clear_related(related_field, pk_list, using)

class DeleteTestCase(TestCase):
    ### Tests for models A,B,C,D ###
    def test_collected_objects_data_structure(self):
        ## Test the CollectedObjects data structure directly

        g = CollectedObjects()
        self.assertFalse(g.add("key1", 1, "item1", None))
        self.assertEqual(g["key1"], {1: 'item1'})
        self.assertFalse(g.add("key2", 1, "item1", "key1"))
        self.assertFalse(g.add("key2", 2, "item2", "key1"))
        self.assertEqual(g["key2"], {1: 'item1', 2: 'item2'})
        self.assertFalse(g.add("key3", 1, "item1", "key1"))
        self.assertTrue(g.add("key3", 1, "item1", "key2"))
        self.assertEqual(g.ordered_keys(), ['key3', 'key2', 'key1'])
        self.assertTrue(g.add("key2", 1, "item1", "key3"))
        self.assertRaises(CyclicDependency,
                          g.ordered_keys)

    def test_collected_objects_by_model_delete(self):
        ## Test the usage of CollectedObjects by Model.delete()

        # Due to the way that transactions work in the test harness,
        # doing m.delete() here can work but fail in a real situation,
        # since it may delete all objects, but not in the right order.
        # So we manually check that the order of deletion is correct.
        
        # Also, it is possible that the order is correct 'accidentally', due
        # solely to order of imports etc.  To check this, we set the order
        # that 'get_models()' will retrieve to a known 'nice' order, and
        # then try again with a known 'tricky' order.  Slightly naughty
        # access to internals here :-)

        # If implementation changes, then the tests may need to be simplified:
        #  - remove the lines that set the .keyOrder and clear the related
        #    object caches
        #  - remove the second set of tests (with a2, b2 etc)

        # Nice order
        cache.app_models['delete'].keyOrder = ['a', 'b', 'c', 'd']
        clear_rel_obj_caches([A, B, C, D])

        a1 = A()
        a1.save()
        b1 = B(a=a1)
        b1.save()
        c1 = C(b=b1)
        c1.save()
        d1 = D(c=c1, a=a1)
        d1.save()

        o = CollectedObjects()
        a1._collect_sub_objects(o)
        self.assertQuerysetEqual(o.keys(), 
                                 ["<class 'modeltests.delete.models.D'>",
                                  "<class 'modeltests.delete.models.C'>",
                                  "<class 'modeltests.delete.models.B'>",
                                  "<class 'modeltests.delete.models.A'>"])
        a1.delete()

        # Same again with a known bad order
        cache.app_models['delete'].keyOrder = ['d', 'c', 'b', 'a']
        clear_rel_obj_caches([A, B, C, D])

        a2 = A()
        a2.save()
        b2 = B(a=a2)
        b2.save()
        c2 = C(b=b2)
        c2.save()
        d2 = D(c=c2, a=a2)
        d2.save()

        o = CollectedObjects()
        a2._collect_sub_objects(o)
        self.assertQuerysetEqual(o.keys(),
                                 ["<class 'modeltests.delete.models.D'>",
                                  "<class 'modeltests.delete.models.C'>", 
                                  "<class 'modeltests.delete.models.B'>",
                                  "<class 'modeltests.delete.models.A'>"])
        a2.delete()

    ### Tests for models E,F - nullable related fields ###
    def test_nullable_related_fields_collected_objects(self):

        ## First, test the CollectedObjects data structure directly
        g = CollectedObjects()
        self.assertFalse(g.add("key1", 1, "item1", None))
        self.assertFalse(g.add("key2", 1, "item1", "key1", nullable=True))
        self.assertTrue(g.add("key1", 1, "item1", "key2"))
        self.assertEqual(g.ordered_keys(), ['key1', 'key2'])

    def test_nullable_related_fields_collected_objects_model_delete(self):
        ## Second, test the usage of CollectedObjects by Model.delete()

        e1 = E()
        e1.save()
        f1 = F(e=e1)
        f1.save()
        e1.f = f1
        e1.save()

        # Since E.f is nullable, we should delete F first (after nulling out
        # the E.f field), then E.

        o = CollectedObjects()
        e1._collect_sub_objects(o)
        self.assertQuerysetEqual(o.keys(),
                                 ["<class 'modeltests.delete.models.F'>",
                                  "<class 'modeltests.delete.models.E'>"])

        # temporarily replace the UpdateQuery class to verify that E.f
        # is actually nulled out first

        original_class = django.db.models.sql.UpdateQuery
        django.db.models.sql.UpdateQuery = LoggingUpdateQuery

        # this is ugly, but it works
        global test_last_cleared_field
        test_last_cleared_field = ''
        e1.delete()
        self.assertEqual(test_last_cleared_field, 'f')
        

        e2 = E()
        e2.save()
        f2 = F(e=e2)
        f2.save()
        e2.f = f2
        e2.save()

        # Same deal as before, though we are starting from the other object.

        o = CollectedObjects()
        f2._collect_sub_objects(o)
        o.keys()
        ["<class 'modeltests.delete.models.F'>", "<class 'modeltests.delete.models.E'>"]

        test_last_cleared_field = ''
        f2.delete()
        self.assertEqual(test_last_cleared_field, 'f')

        # Put this back to normal
        django.db.models.sql.UpdateQuery = original_class

        # Restore the app cache to previous condition so that all
        # models are accounted for.
        cache.app_models['delete'].keyOrder = ['a', 'b', 'c', 'd', 'e', 'f']
        clear_rel_obj_caches([A, B, C, D, E, F])
