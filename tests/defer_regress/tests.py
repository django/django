from __future__ import absolute_import

from operator import attrgetter

from django.contrib.contenttypes.models import ContentType
from django.contrib.sessions.backends.db import SessionStore
from django.db.models import Count
from django.db.models.loading import cache
from django.test import TestCase

from .models import (ResolveThis, Item, RelatedItem, Child, Leaf, Proxy,
    SimpleItem, Feature, ItemAndSimpleItem, OneToOneItem, SpecialFeature)


class DeferRegressionTest(TestCase):
    def test_basic(self):
        # Deferred fields should really be deferred and not accidentally use
        # the field's default value just because they aren't passed to __init__

        Item.objects.create(name="first", value=42)
        obj = Item.objects.only("name", "other_value").get(name="first")
        # Accessing "name" doesn't trigger a new database query. Accessing
        # "value" or "text" should.
        with self.assertNumQueries(0):
            self.assertEqual(obj.name, "first")
            self.assertEqual(obj.other_value, 0)

        with self.assertNumQueries(1):
            self.assertEqual(obj.value, 42)

        with self.assertNumQueries(1):
            self.assertEqual(obj.text, "xyzzy")

        with self.assertNumQueries(0):
            self.assertEqual(obj.text, "xyzzy")

        # Regression test for #10695. Make sure different instances don't
        # inadvertently share data in the deferred descriptor objects.
        i = Item.objects.create(name="no I'm first", value=37)
        items = Item.objects.only("value").order_by("-value")
        self.assertEqual(items[0].name, "first")
        self.assertEqual(items[1].name, "no I'm first")

        RelatedItem.objects.create(item=i)
        r = RelatedItem.objects.defer("item").get()
        self.assertEqual(r.item_id, i.id)
        self.assertEqual(r.item, i)

        # Some further checks for select_related() and inherited model
        # behavior (regression for #10710).
        c1 = Child.objects.create(name="c1", value=42)
        c2 = Child.objects.create(name="c2", value=37)
        Leaf.objects.create(name="l1", child=c1, second_child=c2)

        obj = Leaf.objects.only("name", "child").select_related()[0]
        self.assertEqual(obj.child.name, "c1")

        self.assertQuerysetEqual(
            Leaf.objects.select_related().only("child__name", "second_child__name"), [
                "l1",
            ],
            attrgetter("name")
        )

        # Models instances with deferred fields should still return the same
        # content types as their non-deferred versions (bug #10738).
        ctype = ContentType.objects.get_for_model
        c1 = ctype(Item.objects.all()[0])
        c2 = ctype(Item.objects.defer("name")[0])
        c3 = ctype(Item.objects.only("name")[0])
        self.assertTrue(c1 is c2 is c3)

        # Regression for #10733 - only() can be used on a model with two
        # foreign keys.
        results = Leaf.objects.only("name", "child", "second_child").select_related()
        self.assertEqual(results[0].child.name, "c1")
        self.assertEqual(results[0].second_child.name, "c2")

        results = Leaf.objects.only("name", "child", "second_child", "child__name", "second_child__name").select_related()
        self.assertEqual(results[0].child.name, "c1")
        self.assertEqual(results[0].second_child.name, "c2")

        # Test for #12163 - Pickling error saving session with unsaved model
        # instances.
        SESSION_KEY = '2b1189a188b44ad18c35e1baac6ceead'

        item = Item()
        item._deferred = False
        s = SessionStore(SESSION_KEY)
        s.clear()
        s["item"] = item
        s.save()

        s = SessionStore(SESSION_KEY)
        s.modified = True
        s.save()

        i2 = s["item"]
        self.assertFalse(i2._deferred)

        # Regression for #11936 - loading.get_models should not return deferred
        # models by default.
        klasses = sorted(
            cache.get_models(cache.get_app("defer_regress")),
            key=lambda klass: klass.__name__
        )
        self.assertEqual(
            klasses, [
                Child,
                Feature,
                Item,
                ItemAndSimpleItem,
                Leaf,
                OneToOneItem,
                Proxy,
                RelatedItem,
                ResolveThis,
                SimpleItem,
                SpecialFeature,
            ]
        )

        klasses = sorted(
            map(
                attrgetter("__name__"),
                cache.get_models(
                    cache.get_app("defer_regress"), include_deferred=True
                ),
            )
        )
        # FIXME: This is dependent on the order in which tests are run --
        # this test case has to be the first, otherwise a LOT more classes
        # appear.
        self.assertEqual(
            klasses, [
                "Child",
                "Child_Deferred_value",
                "Feature",
                "Item",
                "ItemAndSimpleItem",
                "Item_Deferred_name",
                "Item_Deferred_name_other_value_text",
                "Item_Deferred_name_other_value_value",
                "Item_Deferred_other_value_text_value",
                "Item_Deferred_text_value",
                "Leaf",
                "Leaf_Deferred_child_id_second_child_id_value",
                "Leaf_Deferred_name_value",
                "Leaf_Deferred_second_child_id_value",
                "Leaf_Deferred_value",
                "OneToOneItem",
                "Proxy",
                "RelatedItem",
                "RelatedItem_Deferred_",
                "RelatedItem_Deferred_item_id",
                "ResolveThis",
                "SimpleItem",
                "SpecialFeature",
            ]
        )

        # Regression for #16409 - make sure defer() and only() work with annotate()
        self.assertIsInstance(list(SimpleItem.objects.annotate(Count('feature')).defer('name')), list)
        self.assertIsInstance(list(SimpleItem.objects.annotate(Count('feature')).only('name')), list)

    def test_only_and_defer_usage_on_proxy_models(self):
        # Regression for #15790 - only() broken for proxy models
        proxy = Proxy.objects.create(name="proxy", value=42)

        msg = 'QuerySet.only() return bogus results with proxy models'
        dp = Proxy.objects.only('other_value').get(pk=proxy.pk)
        self.assertEqual(dp.name, proxy.name, msg=msg)
        self.assertEqual(dp.value, proxy.value, msg=msg)

        # also test things with .defer()
        msg = 'QuerySet.defer() return bogus results with proxy models'
        dp = Proxy.objects.defer('name', 'text', 'value').get(pk=proxy.pk)
        self.assertEqual(dp.name, proxy.name, msg=msg)
        self.assertEqual(dp.value, proxy.value, msg=msg)

    def test_resolve_columns(self):
        rt = ResolveThis.objects.create(num=5.0, name='Foobar')
        qs = ResolveThis.objects.defer('num')
        self.assertEqual(1, qs.count())
        self.assertEqual('Foobar', qs[0].name)

    def test_reverse_one_to_one_relations(self):
        # Refs #14694. Test reverse relations which are known unique (reverse
        # side has o2ofield or unique FK) - the o2o case
        item = Item.objects.create(name="first", value=42)
        o2o = OneToOneItem.objects.create(item=item, name="second")
        self.assertEqual(len(Item.objects.defer('one_to_one_item__name')), 1)
        self.assertEqual(len(Item.objects.select_related('one_to_one_item')), 1)
        self.assertEqual(len(Item.objects.select_related(
            'one_to_one_item').defer('one_to_one_item__name')), 1)
        self.assertEqual(len(Item.objects.select_related('one_to_one_item').defer('value')), 1)
        # Make sure that `only()` doesn't break when we pass in a unique relation,
        # rather than a field on the relation.
        self.assertEqual(len(Item.objects.only('one_to_one_item')), 1)
        with self.assertNumQueries(1):
            i = Item.objects.select_related('one_to_one_item')[0]
            self.assertEqual(i.one_to_one_item.pk, o2o.pk)
            self.assertEqual(i.one_to_one_item.name, "second")
        with self.assertNumQueries(1):
            i = Item.objects.select_related('one_to_one_item').defer(
                'value', 'one_to_one_item__name')[0]
            self.assertEqual(i.one_to_one_item.pk, o2o.pk)
            self.assertEqual(i.name, "first")
        with self.assertNumQueries(1):
            self.assertEqual(i.one_to_one_item.name, "second")
        with self.assertNumQueries(1):
            self.assertEqual(i.value, 42)

    def test_defer_with_select_related(self):
        item1 = Item.objects.create(name="first", value=47)
        item2 = Item.objects.create(name="second", value=42)
        simple = SimpleItem.objects.create(name="simple", value="23")
        related = ItemAndSimpleItem.objects.create(item=item1, simple=simple)

        obj = ItemAndSimpleItem.objects.defer('item').select_related('simple').get()
        self.assertEqual(obj.item, item1)
        self.assertEqual(obj.item_id, item1.id)

        obj.item = item2
        obj.save()

        obj = ItemAndSimpleItem.objects.defer('item').select_related('simple').get()
        self.assertEqual(obj.item, item2)
        self.assertEqual(obj.item_id, item2.id)

    def test_only_with_select_related(self):
        # Test for #17485.
        item = SimpleItem.objects.create(name='first', value=47)
        feature = Feature.objects.create(item=item)
        SpecialFeature.objects.create(feature=feature)

        qs = Feature.objects.only('item__name').select_related('item')
        self.assertEqual(len(qs), 1)

        qs = SpecialFeature.objects.only('feature__item__name').select_related('feature__item')
        self.assertEqual(len(qs), 1)

    def test_deferred_class_factory(self):
        from django.db.models.query_utils import deferred_class_factory
        new_class = deferred_class_factory(Item,
            ('this_is_some_very_long_attribute_name_so_modelname_truncation_is_triggered',))
        self.assertEqual(new_class.__name__,
            'Item_Deferred_this_is_some_very_long_attribute_nac34b1f495507dad6b02e2cb235c875e')
