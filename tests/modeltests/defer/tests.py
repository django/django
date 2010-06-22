from django.test import TestCase
from django.db.models.query_utils import DeferredAttribute

from models import Secondary, Primary, Child, BigChild

def count_delayed_fields(obj, debug=False):
    """
    Returns the number of delayed attributes on the given model instance.
    """
    count = 0
    for field in obj._meta.fields:
        if isinstance(obj.__class__.__dict__.get(field.attname),
                DeferredAttribute):
            if debug:
                print field.name, field.attname
            count += 1
    return count

class DeferAndOnlyTestCase(TestCase):
    fixtures = ['defer_and_only_testdata.json']

    def setUp(self):
        self.p1 = Primary.objects.get(name="p1")
        self.s1 = Secondary.objects.get(first="x1", second="y1")

    #To all outward appearances, instances with deferred fields look
    #the same as normal instances when we examine attribute
    #values. Therefore we test for the number of deferred fields on
    #returned instances (by poking at the internals), as a way to
    #observe what is going on.
    def test_basic_defered_fields(self):
        qs = Primary.objects.all()
        self.assertEqual(count_delayed_fields(qs.defer('name')[0]), 1)
        self.assertEqual(count_delayed_fields(qs.only('name')[0]), 2)
        self.assertEqual(count_delayed_fields(qs.defer('related__first')[0]), 0)

        obj = qs.select_related().only('related__first')[0]
        self.assertEqual(count_delayed_fields(obj), 2)

        s1 = self.s1
        self.assertEqual(obj.related_id, s1.pk)
        
        self.assertEqual(count_delayed_fields(qs.defer('name').extra(select={'a': 1})[0]), 1)
        self.assertEqual(count_delayed_fields(qs.extra(select={'a': 1}).defer('name')[0]), 1)
        self.assertEqual(count_delayed_fields(qs.defer('name').defer('value')[0]), 2)
        self.assertEqual(count_delayed_fields(qs.only('name').only('value')[0]), 2)
        self.assertEqual(count_delayed_fields(qs.only('name').defer('value')[0]), 2)
        self.assertEqual(count_delayed_fields(qs.only('name', 'value').defer('value')[0]), 2)
        self.assertEqual(count_delayed_fields(qs.defer('name').only('value')[0]), 2)
        
        obj = qs.only()[0]
        self.assertEqual(count_delayed_fields(qs.defer(None)[0]), 0)
        self.assertEqual(count_delayed_fields(qs.only('name').defer(None)[0]), 0)

        p1 = self.p1
        #User values() won't defer anything (you get the full list of
        #dictionaries back), but it still works.
        self.assertEqual(qs.defer('name').values()[0],
                         {'id': p1.id, 'name': u'p1', 'value': 'xx', 'related_id': s1.id})
        
        self.assertEqual(qs.only('name').values()[0],
                         {'id': p1.id, 'name': u'p1', 'value': 'xx', 'related_id': s1.id})

        #Using defer() and only() with get() is also valid.
        self.assertEqual(count_delayed_fields(qs.defer('name').get(pk=p1.pk)), 1)
        self.assertEqual(count_delayed_fields(qs.only('name').get(pk=p1.pk)), 2)

        #Previous code had these marked as not working. Seems correct now.
        self.assertEqual(count_delayed_fields(qs.only('name').select_related('related')[0]), 1)
        self.assertEqual(count_delayed_fields(qs.defer('related').select_related('related')[0]), 0)

    def test_save_model_with_deferred_fields(self):
        # Saving models with deferred fields is possible (but inefficient, since every
        # field has to be retrieved first).
        obj = Primary.objects.defer("value").get(name="p1")
        obj.name = "a new name"
        obj.save()
        self.assertEqual(repr(Primary.objects.get(pk=1)),
                                 '<Primary: a new name>')

    def test_defer_fields_subclass(self):
        # Regression for #10572 - A subclass with no extra fields can
        # defer fields from the base class
        Child.objects.create(name="c1", value="foo", related=self.s1)

        # You can defer a field on a baseclass when the subclass has no fields
        obj = Child.objects.defer("value").get(name="c1")
        self.assertEqual(count_delayed_fields(obj), 1)
        self.assertEqual(obj.name, u"c1")
        self.assertEqual(obj.value, u"foo")
        obj.name = "c2"
        obj.save()

        # You can retrieve a single column on a base class with no fields
        obj = Child.objects.only("name").get(name="c2")
        self.assertEqual(count_delayed_fields(obj), 3)
        self.assertEqual(obj.name, u"c2")
        self.assertEqual(obj.value, u"foo")
        obj.name = "cc"
        obj.save()

    def test_defer_fields(self):
        BigChild.objects.create(name="b1", value="foo", related=self.s1, other="bar")

        # You can defer a field on a baseclass
        obj = BigChild.objects.defer("value").get(name="b1")
        self.assertEqual(count_delayed_fields(obj), 1)
        self.assertEqual(obj.name, u"b1")
        self.assertEqual(obj.value, u"foo")
        self.assertEqual(obj.other, u"bar")
        obj.name = "b2"
        obj.save()

        # You can defer a field on a subclass
        obj = BigChild.objects.defer("other").get(name="b2")
        self.assertEqual(count_delayed_fields(obj), 1)
        self.assertEqual(obj.name, u"b2")
        self.assertEqual(obj.value, u"foo")
        self.assertEqual(obj.other, u"bar")
        obj.name = "b3"
        obj.save()

        # You can retrieve a single field on a baseclass
        obj = BigChild.objects.only("name").get(name="b3")
        self.assertEqual(count_delayed_fields(obj), 4)
        self.assertEqual(obj.name, u"b3")
        self.assertEqual(obj.value, u"foo")
        self.assertEqual(obj.other, u"bar")
        obj.name = "b4"
        obj.save()

        # You can retrieve a single field on a baseclass
        obj = BigChild.objects.only("other").get(name="b4")
        self.assertEqual(count_delayed_fields(obj), 4)
        self.assertEqual(obj.name, u"b4")
        self.assertEqual(obj.value, u"foo")
        self.assertEqual(obj.other, u"bar")
        obj.name = "bb"
        obj.save()
