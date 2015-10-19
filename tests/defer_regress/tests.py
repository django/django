from __future__ import unicode_literals

from operator import attrgetter

from django.apps import apps
from django.apps.registry import Apps
from django.contrib.contenttypes.models import ContentType
from django.contrib.sessions.backends.db import SessionStore
from django.db import models
from django.db.models import Count
from django.db.models.query_utils import (
    DeferredAttribute, deferred_class_factory,
)
from django.test import TestCase, override_settings

from .models import (
    Base, Child, Derived, Feature, Item, ItemAndSimpleItem, Leaf, Location,
    OneToOneItem, Proxy, ProxyRelated, RelatedItem, Request, ResolveThis,
    SimpleItem, SpecialFeature,
)


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

        results = Leaf.objects.only(
            "name", "child", "second_child", "child__name", "second_child__name"
        ).select_related()
        self.assertEqual(results[0].child.name, "c1")
        self.assertEqual(results[0].second_child.name, "c2")

        # Regression for #16409 - make sure defer() and only() work with annotate()
        self.assertIsInstance(
            list(SimpleItem.objects.annotate(Count('feature')).defer('name')),
            list)
        self.assertIsInstance(
            list(SimpleItem.objects.annotate(Count('feature')).only('name')),
            list)

    def test_ticket_11936(self):
        app_config = apps.get_app_config("defer_regress")
        # Regression for #11936 - get_models should not return deferred models
        # by default. Run a couple of defer queries so that app registry must
        # contain some deferred classes. It might contain a lot more classes
        # depending on the order the tests are ran.
        list(Item.objects.defer("name"))
        list(Child.objects.defer("value"))
        klasses = {model.__name__ for model in app_config.get_models()}
        self.assertIn("Child", klasses)
        self.assertIn("Item", klasses)
        self.assertNotIn("Child_Deferred_value", klasses)
        self.assertNotIn("Item_Deferred_name", klasses)
        self.assertFalse(any(k._deferred for k in app_config.get_models()))

        klasses_with_deferred = {model.__name__ for model in app_config.get_models(include_deferred=True)}
        self.assertIn("Child", klasses_with_deferred)
        self.assertIn("Item", klasses_with_deferred)
        self.assertIn("Child_Deferred_value", klasses_with_deferred)
        self.assertIn("Item_Deferred_name", klasses_with_deferred)
        self.assertTrue(any(k._deferred for k in app_config.get_models(include_deferred=True)))

    @override_settings(SESSION_SERIALIZER='django.contrib.sessions.serializers.PickleSerializer')
    def test_ticket_12163(self):
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

    def test_ticket_16409(self):
        # Regression for #16409 - make sure defer() and only() work with annotate()
        self.assertIsInstance(
            list(SimpleItem.objects.annotate(Count('feature')).defer('name')),
            list)
        self.assertIsInstance(
            list(SimpleItem.objects.annotate(Count('feature')).only('name')),
            list)

    def test_ticket_23270(self):
        Derived.objects.create(text="foo", other_text="bar")
        with self.assertNumQueries(1):
            obj = Base.objects.select_related("derived").defer("text")[0]
            self.assertIsInstance(obj.derived, Derived)
            self.assertEqual("bar", obj.derived.other_text)
            self.assertNotIn("text", obj.__dict__)
            self.assertEqual(1, obj.derived.base_ptr_id)

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
        ResolveThis.objects.create(num=5.0, name='Foobar')
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
        ItemAndSimpleItem.objects.create(item=item1, simple=simple)

        obj = ItemAndSimpleItem.objects.defer('item').select_related('simple').get()
        self.assertEqual(obj.item, item1)
        self.assertEqual(obj.item_id, item1.id)

        obj.item = item2
        obj.save()

        obj = ItemAndSimpleItem.objects.defer('item').select_related('simple').get()
        self.assertEqual(obj.item, item2)
        self.assertEqual(obj.item_id, item2.id)

    def test_proxy_model_defer_with_select_related(self):
        # Regression for #22050
        item = Item.objects.create(name="first", value=47)
        RelatedItem.objects.create(item=item)
        # Defer fields with only()
        obj = ProxyRelated.objects.all().select_related().only('item__name')[0]
        with self.assertNumQueries(0):
            self.assertEqual(obj.item.name, "first")
        with self.assertNumQueries(1):
            self.assertEqual(obj.item.value, 47)

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
        new_class = deferred_class_factory(
            Item,
            ('this_is_some_very_long_attribute_name_so_modelname_truncation_is_triggered',))
        self.assertEqual(
            new_class.__name__,
            'Item_Deferred_this_is_some_very_long_attribute_nac34b1f495507dad6b02e2cb235c875e')

    def test_deferred_class_factory_already_deferred(self):
        deferred_item1 = deferred_class_factory(Item, ('name',))
        deferred_item2 = deferred_class_factory(deferred_item1, ('value',))
        self.assertIs(deferred_item2._meta.proxy_for_model, Item)
        self.assertNotIsInstance(deferred_item2.__dict__.get('name'), DeferredAttribute)
        self.assertIsInstance(deferred_item2.__dict__.get('value'), DeferredAttribute)

    def test_deferred_class_factory_no_attrs(self):
        deferred_cls = deferred_class_factory(Item, ())
        self.assertFalse(deferred_cls._deferred)

    def test_deferred_class_factory_apps_reuse(self):
        """
        #25563 - model._meta.apps should be used for caching and
        retrieval of the created proxy class.
        """
        isolated_apps = Apps(['defer_regress'])

        class BaseModel(models.Model):
            field = models.BooleanField()

            class Meta:
                apps = isolated_apps
                app_label = 'defer_regress'

        deferred_model = deferred_class_factory(BaseModel, ['field'])
        self.assertIs(deferred_model._meta.apps, isolated_apps)
        self.assertIs(deferred_class_factory(BaseModel, ['field']), deferred_model)


class DeferAnnotateSelectRelatedTest(TestCase):
    def test_defer_annotate_select_related(self):
        location = Location.objects.create()
        Request.objects.create(location=location)
        self.assertIsInstance(list(Request.objects
            .annotate(Count('items')).select_related('profile', 'location')
            .only('profile', 'location')), list)
        self.assertIsInstance(list(Request.objects
            .annotate(Count('items')).select_related('profile', 'location')
            .only('profile__profile1', 'location__location1')), list)
        self.assertIsInstance(list(Request.objects
            .annotate(Count('items')).select_related('profile', 'location')
            .defer('request1', 'request2', 'request3', 'request4')), list)
