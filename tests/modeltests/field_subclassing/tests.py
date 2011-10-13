from __future__ import absolute_import

from django.core import serializers
from django.test import TestCase

from .fields import Small
from .models import DataModel, MyModel, OtherModel


class CustomField(TestCase):
    def test_defer(self):
        d = DataModel.objects.create(data=[1, 2, 3])

        self.assertTrue(isinstance(d.data, list))

        d = DataModel.objects.get(pk=d.pk)
        self.assertTrue(isinstance(d.data, list))
        self.assertEqual(d.data, [1, 2, 3])

        d = DataModel.objects.defer("data").get(pk=d.pk)
        d.save()

        d = DataModel.objects.get(pk=d.pk)
        self.assertTrue(isinstance(d.data, list))
        self.assertEqual(d.data, [1, 2, 3])

    def test_custom_field(self):
        # Creating a model with custom fields is done as per normal.
        s = Small(1, 2)
        self.assertEqual(str(s), "12")

        m = MyModel.objects.create(name="m", data=s)
        # Custom fields still have normal field's attributes.
        self.assertEqual(m._meta.get_field("data").verbose_name, "small field")

        # The m.data attribute has been initialised correctly. It's a Small
        # object.
        self.assertEqual((m.data.first, m.data.second), (1, 2))

        # The data loads back from the database correctly and 'data' has the
        # right type.
        m1 = MyModel.objects.get(pk=m.pk)
        self.assertTrue(isinstance(m1.data, Small))
        self.assertEqual(str(m1.data), "12")

        # We can do normal filtering on the custom field (and will get an error
        # when we use a lookup type that does not make sense).
        s1 = Small(1, 3)
        s2 = Small("a", "b")
        self.assertQuerysetEqual(
            MyModel.objects.filter(data__in=[s, s1, s2]), [
                "m",
            ],
            lambda m: m.name,
        )
        self.assertRaises(TypeError, lambda: MyModel.objects.filter(data__lt=s))

        # Serialization works, too.
        stream = serializers.serialize("json", MyModel.objects.all())
        self.assertEqual(stream, '[{"pk": %d, "model": "field_subclassing.mymodel", "fields": {"data": "12", "name": "m"}}]' % m1.pk)

        obj = list(serializers.deserialize("json", stream))[0]
        self.assertEqual(obj.object, m)

        # Test retrieving custom field data
        m.delete()

        m1 = MyModel.objects.create(name="1", data=Small(1, 2))
        m2 = MyModel.objects.create(name="2", data=Small(2, 3))

        self.assertQuerysetEqual(
            MyModel.objects.all(), [
                "12",
                "23",
            ],
            lambda m: str(m.data)
        )

    def test_field_subclassing(self):
        o = OtherModel.objects.create(data=Small("a", "b"))
        o = OtherModel.objects.get()
        self.assertEqual(o.data.first, "a")
        self.assertEqual(o.data.second, "b")
