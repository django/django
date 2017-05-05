import json

from django.core import exceptions, serializers
from django.forms import Form
from django.test.utils import modify_settings

from . import PostgreSQLTestCase
from .models import HStoreModel

try:
    from django.contrib.postgres import forms
    from django.contrib.postgres.fields import HStoreField
    from django.contrib.postgres.validators import KeysValidator
except ImportError:
    pass


@modify_settings(INSTALLED_APPS={'append': 'django.contrib.postgres'})
class HStoreTestCase(PostgreSQLTestCase):
    pass


class SimpleTests(HStoreTestCase):
    def test_save_load_success(self):
        value = {'a': 'b'}
        instance = HStoreModel(field=value)
        instance.save()
        reloaded = HStoreModel.objects.get()
        self.assertEqual(reloaded.field, value)

    def test_null(self):
        instance = HStoreModel(field=None)
        instance.save()
        reloaded = HStoreModel.objects.get()
        self.assertIsNone(reloaded.field)

    def test_value_null(self):
        value = {'a': None}
        instance = HStoreModel(field=value)
        instance.save()
        reloaded = HStoreModel.objects.get()
        self.assertEqual(reloaded.field, value)

    def test_key_val_cast_to_string(self):
        value = {'a': 1, 'b': 'B', 2: 'c', 'ï': 'ê'}
        expected_value = {'a': '1', 'b': 'B', '2': 'c', 'ï': 'ê'}

        instance = HStoreModel.objects.create(field=value)
        instance = HStoreModel.objects.get()
        self.assertEqual(instance.field, expected_value)

        instance = HStoreModel.objects.get(field__a=1)
        self.assertEqual(instance.field, expected_value)

        instance = HStoreModel.objects.get(field__has_keys=[2, 'a', 'ï'])
        self.assertEqual(instance.field, expected_value)

    def test_array_field(self):
        value = [
            {'a': 1, 'b': 'B', 2: 'c', 'ï': 'ê'},
            {'a': 1, 'b': 'B', 2: 'c', 'ï': 'ê'},
        ]
        expected_value = [
            {'a': '1', 'b': 'B', '2': 'c', 'ï': 'ê'},
            {'a': '1', 'b': 'B', '2': 'c', 'ï': 'ê'},
        ]
        instance = HStoreModel.objects.create(array_field=value)
        instance.refresh_from_db()
        self.assertEqual(instance.array_field, expected_value)


class TestQuerying(HStoreTestCase):

    def setUp(self):
        self.objs = [
            HStoreModel.objects.create(field={'a': 'b'}),
            HStoreModel.objects.create(field={'a': 'b', 'c': 'd'}),
            HStoreModel.objects.create(field={'c': 'd'}),
            HStoreModel.objects.create(field={}),
            HStoreModel.objects.create(field=None),
        ]

    def test_exact(self):
        self.assertSequenceEqual(
            HStoreModel.objects.filter(field__exact={'a': 'b'}),
            self.objs[:1]
        )

    def test_contained_by(self):
        self.assertSequenceEqual(
            HStoreModel.objects.filter(field__contained_by={'a': 'b', 'c': 'd'}),
            self.objs[:4]
        )

    def test_contains(self):
        self.assertSequenceEqual(
            HStoreModel.objects.filter(field__contains={'a': 'b'}),
            self.objs[:2]
        )

    def test_in_generator(self):
        def search():
            yield {'a': 'b'}
        self.assertSequenceEqual(
            HStoreModel.objects.filter(field__in=search()),
            self.objs[:1]
        )

    def test_has_key(self):
        self.assertSequenceEqual(
            HStoreModel.objects.filter(field__has_key='c'),
            self.objs[1:3]
        )

    def test_has_keys(self):
        self.assertSequenceEqual(
            HStoreModel.objects.filter(field__has_keys=['a', 'c']),
            self.objs[1:2]
        )

    def test_has_any_keys(self):
        self.assertSequenceEqual(
            HStoreModel.objects.filter(field__has_any_keys=['a', 'c']),
            self.objs[:3]
        )

    def test_key_transform(self):
        self.assertSequenceEqual(
            HStoreModel.objects.filter(field__a='b'),
            self.objs[:2]
        )

    def test_keys(self):
        self.assertSequenceEqual(
            HStoreModel.objects.filter(field__keys=['a']),
            self.objs[:1]
        )

    def test_values(self):
        self.assertSequenceEqual(
            HStoreModel.objects.filter(field__values=['b']),
            self.objs[:1]
        )

    def test_field_chaining(self):
        self.assertSequenceEqual(
            HStoreModel.objects.filter(field__a__contains='b'),
            self.objs[:2]
        )

    def test_keys_contains(self):
        self.assertSequenceEqual(
            HStoreModel.objects.filter(field__keys__contains=['a']),
            self.objs[:2]
        )

    def test_values_overlap(self):
        self.assertSequenceEqual(
            HStoreModel.objects.filter(field__values__overlap=['b', 'd']),
            self.objs[:3]
        )

    def test_key_isnull(self):
        obj = HStoreModel.objects.create(field={'a': None})
        self.assertSequenceEqual(
            HStoreModel.objects.filter(field__a__isnull=True),
            self.objs[2:5] + [obj]
        )
        self.assertSequenceEqual(
            HStoreModel.objects.filter(field__a__isnull=False),
            self.objs[:2]
        )

    def test_usage_in_subquery(self):
        self.assertSequenceEqual(
            HStoreModel.objects.filter(id__in=HStoreModel.objects.filter(field__a='b')),
            self.objs[:2]
        )


class TestSerialization(HStoreTestCase):
    test_data = json.dumps([{
        'model': 'postgres_tests.hstoremodel',
        'pk': None,
        'fields': {
            'field': json.dumps({'a': 'b'}),
            'array_field': json.dumps([
                json.dumps({'a': 'b'}),
                json.dumps({'b': 'a'}),
            ]),
        },
    }])

    def test_dumping(self):
        instance = HStoreModel(field={'a': 'b'}, array_field=[{'a': 'b'}, {'b': 'a'}])
        data = serializers.serialize('json', [instance])
        self.assertEqual(json.loads(data), json.loads(self.test_data))

    def test_loading(self):
        instance = list(serializers.deserialize('json', self.test_data))[0].object
        self.assertEqual(instance.field, {'a': 'b'})
        self.assertEqual(instance.array_field, [{'a': 'b'}, {'b': 'a'}])

    def test_roundtrip_with_null(self):
        instance = HStoreModel(field={'a': 'b', 'c': None})
        data = serializers.serialize('json', [instance])
        new_instance = list(serializers.deserialize('json', data))[0].object
        self.assertEqual(instance.field, new_instance.field)


class TestValidation(HStoreTestCase):

    def test_not_a_string(self):
        field = HStoreField()
        with self.assertRaises(exceptions.ValidationError) as cm:
            field.clean({'a': 1}, None)
        self.assertEqual(cm.exception.code, 'not_a_string')
        self.assertEqual(cm.exception.message % cm.exception.params, 'The value of "a" is not a string or null.')

    def test_none_allowed_as_value(self):
        field = HStoreField()
        self.assertEqual(field.clean({'a': None}, None), {'a': None})


class TestFormField(HStoreTestCase):

    def test_valid(self):
        field = forms.HStoreField()
        value = field.clean('{"a": "b"}')
        self.assertEqual(value, {'a': 'b'})

    def test_invalid_json(self):
        field = forms.HStoreField()
        with self.assertRaises(exceptions.ValidationError) as cm:
            field.clean('{"a": "b"')
        self.assertEqual(cm.exception.messages[0], 'Could not load JSON data.')
        self.assertEqual(cm.exception.code, 'invalid_json')

    def test_non_dict_json(self):
        field = forms.HStoreField()
        msg = 'Input must be a JSON dictionary.'
        with self.assertRaisesMessage(exceptions.ValidationError, msg) as cm:
            field.clean('["a", "b", 1]')
        self.assertEqual(cm.exception.code, 'invalid_format')

    def test_not_string_values(self):
        field = forms.HStoreField()
        value = field.clean('{"a": 1}')
        self.assertEqual(value, {'a': '1'})

    def test_none_value(self):
        field = forms.HStoreField()
        value = field.clean('{"a": null}')
        self.assertEqual(value, {'a': None})

    def test_empty(self):
        field = forms.HStoreField(required=False)
        value = field.clean('')
        self.assertEqual(value, {})

    def test_model_field_formfield(self):
        model_field = HStoreField()
        form_field = model_field.formfield()
        self.assertIsInstance(form_field, forms.HStoreField)

    def test_field_has_changed(self):
        class HStoreFormTest(Form):
            f1 = forms.HStoreField()
        form_w_hstore = HStoreFormTest()
        self.assertFalse(form_w_hstore.has_changed())

        form_w_hstore = HStoreFormTest({'f1': '{"a": 1}'})
        self.assertTrue(form_w_hstore.has_changed())

        form_w_hstore = HStoreFormTest({'f1': '{"a": 1}'}, initial={'f1': '{"a": 1}'})
        self.assertFalse(form_w_hstore.has_changed())

        form_w_hstore = HStoreFormTest({'f1': '{"a": 2}'}, initial={'f1': '{"a": 1}'})
        self.assertTrue(form_w_hstore.has_changed())

        form_w_hstore = HStoreFormTest({'f1': '{"a": 1}'}, initial={'f1': {"a": 1}})
        self.assertFalse(form_w_hstore.has_changed())

        form_w_hstore = HStoreFormTest({'f1': '{"a": 2}'}, initial={'f1': {"a": 1}})
        self.assertTrue(form_w_hstore.has_changed())


class TestValidator(HStoreTestCase):

    def test_simple_valid(self):
        validator = KeysValidator(keys=['a', 'b'])
        validator({'a': 'foo', 'b': 'bar', 'c': 'baz'})

    def test_missing_keys(self):
        validator = KeysValidator(keys=['a', 'b'])
        with self.assertRaises(exceptions.ValidationError) as cm:
            validator({'a': 'foo', 'c': 'baz'})
        self.assertEqual(cm.exception.messages[0], 'Some keys were missing: b')
        self.assertEqual(cm.exception.code, 'missing_keys')

    def test_strict_valid(self):
        validator = KeysValidator(keys=['a', 'b'], strict=True)
        validator({'a': 'foo', 'b': 'bar'})

    def test_extra_keys(self):
        validator = KeysValidator(keys=['a', 'b'], strict=True)
        with self.assertRaises(exceptions.ValidationError) as cm:
            validator({'a': 'foo', 'b': 'bar', 'c': 'baz'})
        self.assertEqual(cm.exception.messages[0], 'Some unknown keys were provided: c')
        self.assertEqual(cm.exception.code, 'extra_keys')

    def test_custom_messages(self):
        messages = {
            'missing_keys': 'Foobar',
        }
        validator = KeysValidator(keys=['a', 'b'], strict=True, messages=messages)
        with self.assertRaises(exceptions.ValidationError) as cm:
            validator({'a': 'foo', 'c': 'baz'})
        self.assertEqual(cm.exception.messages[0], 'Foobar')
        self.assertEqual(cm.exception.code, 'missing_keys')
        with self.assertRaises(exceptions.ValidationError) as cm:
            validator({'a': 'foo', 'b': 'bar', 'c': 'baz'})
        self.assertEqual(cm.exception.messages[0], 'Some unknown keys were provided: c')
        self.assertEqual(cm.exception.code, 'extra_keys')

    def test_deconstruct(self):
        messages = {
            'missing_keys': 'Foobar',
        }
        validator = KeysValidator(keys=['a', 'b'], strict=True, messages=messages)
        path, args, kwargs = validator.deconstruct()
        self.assertEqual(path, 'django.contrib.postgres.validators.KeysValidator')
        self.assertEqual(args, ())
        self.assertEqual(kwargs, {'keys': ['a', 'b'], 'strict': True, 'messages': messages})
