from __future__ import unicode_literals

import inspect

from django.core import exceptions, serializers
from django.db import connection
from django.test import TestCase

from .fields import CustomTypedField, Small
from .models import ChoicesModel, DataModel, MyModel, OtherModel


class CustomField(TestCase):
    def test_refresh(self):
        d = DataModel.objects.create(data=[1, 2, 3])
        d.refresh_from_db(fields=['data'])
        self.assertIsInstance(d.data, list)
        self.assertEqual(d.data, [1, 2, 3])

    def test_defer(self):
        d = DataModel.objects.create(data=[1, 2, 3])

        self.assertIsInstance(d.data, list)

        d = DataModel.objects.get(pk=d.pk)
        self.assertIsInstance(d.data, list)
        self.assertEqual(d.data, [1, 2, 3])

        d = DataModel.objects.defer("data").get(pk=d.pk)
        self.assertIsInstance(d.data, list)
        self.assertEqual(d.data, [1, 2, 3])
        # Refetch for save
        d = DataModel.objects.defer("data").get(pk=d.pk)
        d.save()

        d = DataModel.objects.get(pk=d.pk)
        self.assertIsInstance(d.data, list)
        self.assertEqual(d.data, [1, 2, 3])

    def test_custom_field(self):
        # Creating a model with custom fields is done as per normal.
        s = Small(1, 2)
        self.assertEqual(str(s), "12")

        m = MyModel.objects.create(name="m", data=s)
        # Custom fields still have normal field's attributes.
        self.assertEqual(m._meta.get_field("data").verbose_name, "small field")

        # The m.data attribute has been initialized correctly. It's a Small
        # object.
        self.assertEqual((m.data.first, m.data.second), (1, 2))

        # The data loads back from the database correctly and 'data' has the
        # right type.
        m1 = MyModel.objects.get(pk=m.pk)
        self.assertIsInstance(m1.data, Small)
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
        self.assertJSONEqual(stream, [{
            "pk": m1.pk,
            "model": "field_subclassing.mymodel",
            "fields": {"data": "12", "name": "m"}
        }])

        obj = list(serializers.deserialize("json", stream))[0]
        self.assertEqual(obj.object, m)

        # Test retrieving custom field data
        m.delete()

        m1 = MyModel.objects.create(name="1", data=Small(1, 2))
        MyModel.objects.create(name="2", data=Small(2, 3))

        self.assertQuerysetEqual(
            MyModel.objects.all(), [
                "12",
                "23",
            ],
            lambda m: str(m.data),
            ordered=False
        )

    def test_field_subclassing(self):
        o = OtherModel.objects.create(data=Small("a", "b"))
        o = OtherModel.objects.get()
        self.assertEqual(o.data.first, "a")
        self.assertEqual(o.data.second, "b")

    def test_subfieldbase_plays_nice_with_module_inspect(self):
        """
        Custom fields should play nice with python standard module inspect.

        http://users.rcn.com/python/download/Descriptor.htm#properties
        """
        # Even when looking for totally different properties, SubfieldBase's
        # non property like behavior made inspect crash. Refs #12568.
        data = dict(inspect.getmembers(MyModel))
        self.assertIn('__module__', data)
        self.assertEqual(data['__module__'], 'field_subclassing.models')

    def test_validation_of_choices_for_custom_field(self):
        # a valid choice
        o = ChoicesModel.objects.create(data=Small('a', 'b'))
        o.full_clean()

        # an invalid choice
        o = ChoicesModel.objects.create(data=Small('d', 'e'))
        with self.assertRaises(exceptions.ValidationError):
            o.full_clean()


class TestDbType(TestCase):

    def test_db_parameters_respects_db_type(self):
        f = CustomTypedField()
        self.assertEqual(f.db_parameters(connection)['type'], 'custom_field')
