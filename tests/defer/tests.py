from __future__ import unicode_literals

from django.db.models.query_utils import DeferredAttribute, InvalidQuery
from django.test import TestCase

from .models import Secondary, Primary, Child, BigChild, ChildProxy, RefreshPrimaryProxy

class TestAssertDelayed(TestCase):
    
    def assert_delayed(self, obj, num):
        """
        To all outward appearances, instances with deferred fields look the
        same as normal instances when we examine attribute values. Therefore,
        this method returns the number of deferred fields on returned 
        instances.
        """
        count = 0
        for field in obj._meta.fields:
            if isinstance(obj.__class__.__dict__.get(field.attname),
                    DeferredAttribute):
                count += 1
        self.assertEqual(count, num)
    
class DeferTests(TestAssertDelayed):

    @classmethod   
    def setUpTestData(cls):
        cls.s1 = Secondary.objects.create(first="x1", second="y1")
        cls.p1 = Primary.objects.create(name="p1", value="xx", related=cls.s1)
    
    def test_defer(self):
        queryset = Primary.objects.all()
        self.assert_delayed(queryset.defer("name")[0], 1)
        self.assert_delayed(queryset.defer("name").get(pk=self.s1.pk), 1)
        self.assert_delayed(queryset.defer("related__first")[0], 0)
        self.assert_delayed(queryset.defer("name").defer("value")[0], 2)
    
    def test_only(self):
        queryset = Primary.objects.all()
        self.assert_delayed(queryset.only("name")[0], 2)
        self.assert_delayed(queryset.only("name").get(pk=self.p1.pk), 2)
        self.assert_delayed(queryset.only("name").only("value")[0], 2)
        self.assert_delayed(queryset.only("related__first")[0], 2)
        # Using 'pk' with only() should result in 3 deferred fields.        
        self.assert_delayed(queryset.only("pk")[0], 3)
        self.assert_delayed(self.s1.primary_set.all().only('pk')[0], 3)

    def test_defer_only_chaining(self):
        queryset = Primary.objects.all()
        self.assert_delayed(queryset.only("name", "value").defer("name")[0], 2)
        self.assert_delayed(queryset.defer("name").only("value", "name")[0], 2)
        self.assert_delayed(queryset.defer("name").only("value")[0], 2)
        self.assert_delayed(queryset.only("name").defer("value")[0], 2)
    
    def test_defer_on_an_already_deferred_field(self):
        queryset = Primary.objects.all()
        obj = queryset.defer("name")[0]
        self.assert_delayed(obj, 1)
        self.assert_delayed(queryset.defer("name")[0], 1)

    def test_defer_None_to_clear_deferred_set(self):
        queryset = Primary.objects.all()
        self.assert_delayed(queryset.defer("name", "value")[0], 2)
        self.assert_delayed(queryset.defer(None)[0], 0)
        self.assert_delayed(queryset.only("name").defer(None)[0], 0)

    def test_only_None_raises_TypeError(self):
        queryset = Primary.objects.all()
        with self.assertRaises(TypeError):
            queryset.only(None)
 
    def test_defer_values_does_not_defer(self):
        queryset = Primary.objects.all()
        self.assertEqual(queryset.defer("name").values()[0], {
            "id": self.p1.id,
            "name": "p1",
            "value": "xx",
            "related_id": self.s1.id,
        })
    
    def test_only_values_does_not_defer(self):
        queryset = Primary.objects.all()
        self.assertEqual(queryset.only("name").values()[0], {
            "id": self.p1.id,
            "name": "p1",
            "value": "xx",
            "related_id": self.s1.id,
        })
    
    def test_defer_with_select_related(self):
        queryset = Primary.objects.all()
        obj = queryset.select_related().defer("related__first", "related__second")[0]
        self.assert_delayed(obj.related, 2)
        self.assert_delayed(obj, 0) 

    def test_only_with_select_related(self):
        queryset = Primary.objects.all()
        obj = queryset.select_related().only("related__first")[0]
        self.assert_delayed(obj, 2)
        self.assert_delayed(obj.related, 1)
        self.assertEqual(obj.related_id, self.s1.pk)
        self.assertEqual(obj.name, "p1")
    
    def test_defer_selected_related_raises_InvalidQuery(self):
        queryset = Primary.objects.all()
        with self.assertRaises(InvalidQuery):
            queryset.defer("related").select_related("related")[0]
        
    def test_only_selected_related_raises_InvalidQuery(self):
        queryset = Primary.objects.all()
        with self.assertRaises(InvalidQuery):
            queryset.only("name").select_related("related")[0]
    
    def test_defer_ForeignKeys_are_deferred_and_not_traversed(self):
        queryset = Primary.objects.all()
        with self.assertNumQueries(3):
            obj = queryset.defer("related").select_related()[0]
            self.assert_delayed(obj, 1)
            self.assertEqual(obj.related.id, self.s1.pk)
 
    def test_saving_object_with_deferred_field(self):
        Primary.objects.create(name="p2", value="xy", related=self.s1)
        obj = Primary.objects.defer("value").get(name="p2")
        obj.name = "a new name"
        obj.save()
        self.assertQuerysetEqual(
            Primary.objects.all(), [
               "p1", "a new name",
            ],
            lambda p: p.name,
            ordered=False,
        )

    def test_defer_baseclass_when_subclass_has_no_added_fields(self):
        Child.objects.create(name="c1", value="foo", related=self.s1)
        queryset = Child.objects.all()
        obj = queryset.defer("value").get(name="c1")
        self.assert_delayed(obj, 1)
        self.assertEqual(obj.name, "c1")
        self.assertEqual(obj.value, "foo")
                
    def test_only_baseclass_when_subclass_has_no_added_fields(self):
        Child.objects.create(name="c1", value="foo", related=self.s1)
        queryset = Child.objects.all() 
        obj = queryset.only("name").get(name="c1")
        # when inherited model, its PK is also fetched, hence '3' deferred fields.
        self.assert_delayed(obj, 3)
        self.assertEqual(obj.name, "c1")
        self.assertEqual(obj.value, "foo")
   
    def test_defer_baseclass_when_subclass_has_added_field(self):
        BigChild.objects.create(name="b1", value="foo", related=self.s1, other="bar")
        queryset = BigChild.objects.all()
        obj = queryset.defer("value").get(name="b1")
        self.assert_delayed(obj, 1)
        self.assertEqual(obj.name, "b1")
        self.assertEqual(obj.value, "foo")
        self.assertEqual(obj.other, "bar")
       
    def test_only_baseclass_when_subclass_has_added_field(self):
        BigChild.objects.create(name="b1", value="foo", related=self.s1, other="bar")
        queryset = BigChild.objects.all()
        obj = queryset.only("name").get(name="b1")
        # when inherited model, its PK is also fetched, hence '4' deferred fields.
        self.assert_delayed(obj, 4)
        self.assertEqual(obj.name, "b1")
        self.assertEqual(obj.value, "foo")
        self.assertEqual(obj.other, "bar")
     
    def test_defer_proxy(self):
        """
        Ensure select_related together with only on a proxy model behaves
        as expected. See #17876.
        """
        related = Secondary.objects.create(first='x1', second='x2')
        ChildProxy.objects.create(name='p1', value='xx', related=related)
        children = ChildProxy.objects.all().select_related().only('id', 'name')
        self.assertEqual(len(children), 1)
        child = children[0]
        self.assert_delayed(child, 2)
        self.assertEqual(child.name, 'p1')
        self.assertEqual(child.value, 'xx')

    def test_defer_inheritance_pk_chaining(self):
        """
        When an inherited model is fetched from the DB, its PK is also fetched.
        When getting the PK of the parent model it is useful to use the already
        fetched parent model PK if it happens to be available. Tests that this
        is done.
        """
        s1 = Secondary.objects.create(first="x1", second="y1")
        bc = BigChild.objects.create(name="b1", value="foo", related=s1,
                                     other="bar")
        bc_deferred = BigChild.objects.only('name').get(pk=bc.pk)
        with self.assertNumQueries(0):
            bc_deferred.id
        self.assertEqual(bc_deferred.pk, bc_deferred.id)

    def test_eq(self):
        s1 = Secondary.objects.create(first="x1", second="y1")
        s1_defer = Secondary.objects.only('pk').get(pk=s1.pk)
        self.assertEqual(s1, s1_defer)
        self.assertEqual(s1_defer, s1)

    def test_refresh_not_loading_deferred_fields(self):
        s = Secondary.objects.create()
        rf = Primary.objects.create(name='foo', value='bar', related=s)
        rf2 = Primary.objects.only('related', 'value').get(pk=s.pk)
        rf.name = 'new foo'
        rf.value = 'new bar'
        rf.save()
        with self.assertNumQueries(1):
            rf2.refresh_from_db()
            self.assertEqual(rf2.value, 'new bar')
        with self.assertNumQueries(1):
            self.assertEqual(rf2.name, 'new foo')

    def test_custom_refresh_on_deferred_loading(self):
        s = Secondary.objects.create()
        rf = RefreshPrimaryProxy.objects.create(name='foo', value='bar', related=s)
        rf2 = RefreshPrimaryProxy.objects.only('related').get(pk=s.pk)
        rf.name = 'new foo'
        rf.value = 'new bar'
        rf.save()
        with self.assertNumQueries(1):
            # Customized refresh_from_db() reloads all deferred fields on
            # access of any of them.
            self.assertEqual(rf2.name, 'new foo')
            self.assertEqual(rf2.value, 'new bar')
