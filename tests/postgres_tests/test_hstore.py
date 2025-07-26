import json

from django.core import checks, exceptions, serializers
from django.db import connection
from django.db.models import F, OuterRef, Subquery
from django.db.models.expressions import RawSQL
from django.forms import Form
from django.test.utils import CaptureQueriesContext, isolate_apps

from . import PostgreSQLSimpleTestCase, PostgreSQLTestCase
from .models import HStoreModel, PostgreSQLModel

try:
    from django.contrib.postgres import forms
    from django.contrib.postgres.fields import HStoreField
    from django.contrib.postgres.fields.hstore import KeyTransform
    from django.contrib.postgres.validators import KeysValidator
except ImportError:
    pass


class SimpleTests(PostgreSQLTestCase):
    def test_save_load_success(self):
        value = {"a": "b"}
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
        value = {"a": None}
        instance = HStoreModel(field=value)
        instance.save()
        reloaded = HStoreModel.objects.get()
        self.assertEqual(reloaded.field, value)

    def test_key_val_cast_to_string(self):
        value = {"a": 1, "b": "B", 2: "c", "ï": "ê"}
        expected_value = {"a": "1", "b": "B", "2": "c", "ï": "ê"}

        instance = HStoreModel.objects.create(field=value)
        instance = HStoreModel.objects.get()
        self.assertEqual(instance.field, expected_value)

        instance = HStoreModel.objects.get(field__a=1)
        self.assertEqual(instance.field, expected_value)

        instance = HStoreModel.objects.get(field__has_keys=[2, "a", "ï"])
        self.assertEqual(instance.field, expected_value)

    def test_array_field(self):
        value = [
            {"a": 1, "b": "B", 2: "c", "ï": "ê"},
            {"a": 1, "b": "B", 2: "c", "ï": "ê"},
        ]
        expected_value = [
            {"a": "1", "b": "B", "2": "c", "ï": "ê"},
            {"a": "1", "b": "B", "2": "c", "ï": "ê"},
        ]
        instance = HStoreModel.objects.create(array_field=value)
        instance.refresh_from_db()
        self.assertEqual(instance.array_field, expected_value)


class TestQuerying(PostgreSQLTestCase):
    @classmethod
    def setUpTestData(cls):
        cls.objs = HStoreModel.objects.bulk_create(
            [
                HStoreModel(field={"a": "b"}),
                HStoreModel(field={"a": "b", "c": "d"}),
                HStoreModel(field={"c": "d"}),
                HStoreModel(field={}),
                HStoreModel(field=None),
                HStoreModel(field={"cat": "TigrOu", "breed": "birman"}),
                HStoreModel(field={"cat": "minou", "breed": "ragdoll"}),
                HStoreModel(field={"cat": "kitty", "breed": "Persian"}),
                HStoreModel(field={"cat": "Kit Kat", "breed": "persian"}),
            ]
        )

    def test_exact(self):
        self.assertSequenceEqual(
            HStoreModel.objects.filter(field__exact={"a": "b"}), self.objs[:1]
        )

    def test_contained_by(self):
        self.assertSequenceEqual(
            HStoreModel.objects.filter(field__contained_by={"a": "b", "c": "d"}),
            self.objs[:4],
        )

    def test_contains(self):
        self.assertSequenceEqual(
            HStoreModel.objects.filter(field__contains={"a": "b"}), self.objs[:2]
        )

    def test_in_generator(self):
        def search():
            yield {"a": "b"}

        self.assertSequenceEqual(
            HStoreModel.objects.filter(field__in=search()), self.objs[:1]
        )

    def test_has_key(self):
        self.assertSequenceEqual(
            HStoreModel.objects.filter(field__has_key="c"), self.objs[1:3]
        )

    def test_has_keys(self):
        self.assertSequenceEqual(
            HStoreModel.objects.filter(field__has_keys=["a", "c"]), self.objs[1:2]
        )

    def test_has_any_keys(self):
        self.assertSequenceEqual(
            HStoreModel.objects.filter(field__has_any_keys=["a", "c"]), self.objs[:3]
        )

    def test_key_transform(self):
        self.assertSequenceEqual(
            HStoreModel.objects.filter(field__a="b"), self.objs[:2]
        )

    def test_key_transform_raw_expression(self):
        expr = RawSQL("%s::hstore", ["x => b, y => c"])
        self.assertSequenceEqual(
            HStoreModel.objects.filter(field__a=KeyTransform("x", expr)), self.objs[:2]
        )

    def test_key_transform_annotation(self):
        qs = HStoreModel.objects.annotate(a=F("field__a"))
        self.assertCountEqual(
            qs.values_list("a", flat=True),
            ["b", "b", None, None, None, None, None, None, None],
        )

    def test_keys(self):
        self.assertSequenceEqual(
            HStoreModel.objects.filter(field__keys=["a"]), self.objs[:1]
        )

    def test_values(self):
        self.assertSequenceEqual(
            HStoreModel.objects.filter(field__values=["b"]), self.objs[:1]
        )

    def test_field_chaining_contains(self):
        self.assertSequenceEqual(
            HStoreModel.objects.filter(field__a__contains="b"), self.objs[:2]
        )

    def test_field_chaining_icontains(self):
        self.assertSequenceEqual(
            HStoreModel.objects.filter(field__cat__icontains="INo"),
            [self.objs[6]],
        )

    def test_field_chaining_startswith(self):
        self.assertSequenceEqual(
            HStoreModel.objects.filter(field__cat__startswith="kit"),
            [self.objs[7]],
        )

    def test_field_chaining_istartswith(self):
        self.assertSequenceEqual(
            HStoreModel.objects.filter(field__cat__istartswith="kit"),
            self.objs[7:],
        )

    def test_field_chaining_endswith(self):
        self.assertSequenceEqual(
            HStoreModel.objects.filter(field__cat__endswith="ou"),
            [self.objs[6]],
        )

    def test_field_chaining_iendswith(self):
        self.assertSequenceEqual(
            HStoreModel.objects.filter(field__cat__iendswith="ou"),
            self.objs[5:7],
        )

    def test_field_chaining_iexact(self):
        self.assertSequenceEqual(
            HStoreModel.objects.filter(field__breed__iexact="persian"),
            self.objs[7:],
        )

    def test_field_chaining_regex(self):
        self.assertSequenceEqual(
            HStoreModel.objects.filter(field__cat__regex=r"ou$"),
            [self.objs[6]],
        )

    def test_field_chaining_iregex(self):
        self.assertSequenceEqual(
            HStoreModel.objects.filter(field__cat__iregex=r"oU$"),
            self.objs[5:7],
        )

    def test_order_by_field(self):
        more_objs = (
            HStoreModel.objects.create(field={"g": "637"}),
            HStoreModel.objects.create(field={"g": "002"}),
            HStoreModel.objects.create(field={"g": "042"}),
            HStoreModel.objects.create(field={"g": "981"}),
        )
        self.assertSequenceEqual(
            HStoreModel.objects.filter(field__has_key="g").order_by("field__g"),
            [more_objs[1], more_objs[2], more_objs[0], more_objs[3]],
        )

    def test_keys_contains(self):
        self.assertSequenceEqual(
            HStoreModel.objects.filter(field__keys__contains=["a"]), self.objs[:2]
        )

    def test_values_overlap(self):
        self.assertSequenceEqual(
            HStoreModel.objects.filter(field__values__overlap=["b", "d"]), self.objs[:3]
        )

    def test_key_isnull(self):
        obj = HStoreModel.objects.create(field={"a": None})
        self.assertSequenceEqual(
            HStoreModel.objects.filter(field__a__isnull=True),
            self.objs[2:9] + [obj],
        )
        self.assertSequenceEqual(
            HStoreModel.objects.filter(field__a__isnull=False), self.objs[:2]
        )

    def test_usage_in_subquery(self):
        self.assertSequenceEqual(
            HStoreModel.objects.filter(id__in=HStoreModel.objects.filter(field__a="b")),
            self.objs[:2],
        )

    def test_key_sql_injection(self):
        with CaptureQueriesContext(connection) as queries:
            self.assertFalse(
                HStoreModel.objects.filter(
                    **{
                        "field__test' = 'a') OR 1 = 1 OR ('d": "x",
                    }
                ).exists()
            )
        self.assertIn(
            """."field" -> 'test'' = ''a'') OR 1 = 1 OR (''d') = 'x' """,
            queries[0]["sql"],
        )

    def test_obj_subquery_lookup(self):
        qs = HStoreModel.objects.annotate(
            value=Subquery(
                HStoreModel.objects.filter(pk=OuterRef("pk")).values("field")
            ),
        ).filter(value__a="b")
        self.assertSequenceEqual(qs, self.objs[:2])


@isolate_apps("postgres_tests")
class TestChecks(PostgreSQLSimpleTestCase):
    def test_invalid_default(self):
        class MyModel(PostgreSQLModel):
            field = HStoreField(default={})

        model = MyModel()
        self.assertEqual(
            model.check(),
            [
                checks.Warning(
                    msg=(
                        "HStoreField default should be a callable instead of an "
                        "instance so that it's not shared between all field "
                        "instances."
                    ),
                    hint="Use a callable instead, e.g., use `dict` instead of `{}`.",
                    obj=MyModel._meta.get_field("field"),
                    id="fields.E010",
                )
            ],
        )

    def test_valid_default(self):
        class MyModel(PostgreSQLModel):
            field = HStoreField(default=dict)

        self.assertEqual(MyModel().check(), [])


class TestSerialization(PostgreSQLSimpleTestCase):
    field_values = [
        ({"a": "b"}, [{"a": "b"}, {"b": "a"}]),
        (
            {"все": "Трурль и Клапауций"},
            [{"Трурль": "Клапауций"}, {"Клапауций": "Трурль"}],
        ),
    ]

    @staticmethod
    def create_json_data(field_value, array_field_value):
        fields = {
            "field": json.dumps(field_value, ensure_ascii=False),
            "array_field": json.dumps(
                [json.dumps(item, ensure_ascii=False) for item in array_field_value],
                ensure_ascii=False,
            ),
        }
        return json.dumps(
            [{"model": "postgres_tests.hstoremodel", "pk": None, "fields": fields}]
        )

    def test_dumping(self):
        for field_value, array_field_value in self.field_values:
            with self.subTest(field_value=field_value, array_value=array_field_value):
                instance = HStoreModel(field=field_value, array_field=array_field_value)
                data = serializers.serialize("json", [instance])
                json_data = self.create_json_data(field_value, array_field_value)
                self.assertEqual(json.loads(data), json.loads(json_data))

    def test_loading(self):
        for field_value, array_field_value in self.field_values:
            with self.subTest(field_value=field_value, array_value=array_field_value):
                json_data = self.create_json_data(field_value, array_field_value)
                instance = list(serializers.deserialize("json", json_data))[0].object
                self.assertEqual(instance.field, field_value)
                self.assertEqual(instance.array_field, array_field_value)

    def test_roundtrip_with_null(self):
        for field_value in [
            {"a": "b", "c": None},
            {"Енеїда": "Ти знаєш, він який суціга", "Зефір": None},
        ]:
            with self.subTest(field_value=field_value):
                instance = HStoreModel(field=field_value)
                data = serializers.serialize("json", [instance])
                new_instance = list(serializers.deserialize("json", data))[0].object
                self.assertEqual(instance.field, new_instance.field)


class TestValidation(PostgreSQLSimpleTestCase):
    def test_not_a_string(self):
        field = HStoreField()
        with self.assertRaises(exceptions.ValidationError) as cm:
            field.clean({"a": 1}, None)
        self.assertEqual(cm.exception.code, "not_a_string")
        self.assertEqual(
            cm.exception.message % cm.exception.params,
            "The value of “a” is not a string or null.",
        )

    def test_none_allowed_as_value(self):
        field = HStoreField()
        self.assertEqual(field.clean({"a": None}, None), {"a": None})


class TestFormField(PostgreSQLSimpleTestCase):
    def test_valid(self):
        field = forms.HStoreField()
        value = field.clean('{"a": "b"}')
        self.assertEqual(value, {"a": "b"})

    def test_invalid_json(self):
        field = forms.HStoreField()
        with self.assertRaises(exceptions.ValidationError) as cm:
            field.clean('{"a": "b"')
        self.assertEqual(cm.exception.messages[0], "Could not load JSON data.")
        self.assertEqual(cm.exception.code, "invalid_json")

    def test_non_dict_json(self):
        field = forms.HStoreField()
        msg = "Input must be a JSON dictionary."
        with self.assertRaisesMessage(exceptions.ValidationError, msg) as cm:
            field.clean('["a", "b", 1]')
        self.assertEqual(cm.exception.code, "invalid_format")

    def test_not_string_values(self):
        field = forms.HStoreField()
        value = field.clean('{"a": 1}')
        self.assertEqual(value, {"a": "1"})

    def test_none_value(self):
        field = forms.HStoreField()
        value = field.clean('{"a": null}')
        self.assertEqual(value, {"a": None})

    def test_empty(self):
        field = forms.HStoreField(required=False)
        value = field.clean("")
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

        form_w_hstore = HStoreFormTest({"f1": '{"a": 1}'})
        self.assertTrue(form_w_hstore.has_changed())

        form_w_hstore = HStoreFormTest({"f1": '{"a": 1}'}, initial={"f1": '{"a": 1}'})
        self.assertFalse(form_w_hstore.has_changed())

        form_w_hstore = HStoreFormTest({"f1": '{"a": 2}'}, initial={"f1": '{"a": 1}'})
        self.assertTrue(form_w_hstore.has_changed())

        form_w_hstore = HStoreFormTest({"f1": '{"a": 1}'}, initial={"f1": {"a": 1}})
        self.assertFalse(form_w_hstore.has_changed())

        form_w_hstore = HStoreFormTest({"f1": '{"a": 2}'}, initial={"f1": {"a": 1}})
        self.assertTrue(form_w_hstore.has_changed())

    def test_prepare_value(self):
        field = forms.HStoreField()
        self.assertEqual(
            field.prepare_value({"aira_maplayer": "Αρδευτικό δίκτυο"}),
            '{"aira_maplayer": "Αρδευτικό δίκτυο"}',
        )


class TestValidator(PostgreSQLSimpleTestCase):
    def test_simple_valid(self):
        validator = KeysValidator(keys=["a", "b"])
        validator({"a": "foo", "b": "bar", "c": "baz"})

    def test_missing_keys(self):
        validator = KeysValidator(keys=["a", "b"])
        with self.assertRaises(exceptions.ValidationError) as cm:
            validator({"a": "foo", "c": "baz"})
        self.assertEqual(cm.exception.messages[0], "Some keys were missing: b")
        self.assertEqual(cm.exception.code, "missing_keys")

    def test_strict_valid(self):
        validator = KeysValidator(keys=["a", "b"], strict=True)
        validator({"a": "foo", "b": "bar"})

    def test_extra_keys(self):
        validator = KeysValidator(keys=["a", "b"], strict=True)
        with self.assertRaises(exceptions.ValidationError) as cm:
            validator({"a": "foo", "b": "bar", "c": "baz"})
        self.assertEqual(cm.exception.messages[0], "Some unknown keys were provided: c")
        self.assertEqual(cm.exception.code, "extra_keys")

    def test_custom_messages(self):
        messages = {
            "missing_keys": "Foobar",
        }
        validator = KeysValidator(keys=["a", "b"], strict=True, messages=messages)
        with self.assertRaises(exceptions.ValidationError) as cm:
            validator({"a": "foo", "c": "baz"})
        self.assertEqual(cm.exception.messages[0], "Foobar")
        self.assertEqual(cm.exception.code, "missing_keys")
        with self.assertRaises(exceptions.ValidationError) as cm:
            validator({"a": "foo", "b": "bar", "c": "baz"})
        self.assertEqual(cm.exception.messages[0], "Some unknown keys were provided: c")
        self.assertEqual(cm.exception.code, "extra_keys")

    def test_deconstruct(self):
        messages = {
            "missing_keys": "Foobar",
        }
        validator = KeysValidator(keys=["a", "b"], strict=True, messages=messages)
        path, args, kwargs = validator.deconstruct()
        self.assertEqual(path, "django.contrib.postgres.validators.KeysValidator")
        self.assertEqual(args, ())
        self.assertEqual(
            kwargs, {"keys": ["a", "b"], "strict": True, "messages": messages}
        )
