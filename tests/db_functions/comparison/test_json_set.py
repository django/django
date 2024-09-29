import json
from django.test import TestCase
from django.db import connection
from django.db.models import F, Value, TextField, BooleanField, Func, SmallIntegerField, Q
from django.db.models.functions import JSONSet, JSONRemove, Cast, JSONExtract, JSONObject

from django.test.testcases import skipUnlessDBFeature
from django.db import connection

from django.contrib.postgres.fields.array import ArrayField

from ..models import Flying

class DataMixin:
    @classmethod
    def setUpTestData(cls):
        cls.c1 = Flying.objects.create(
            circus={
                "id": 1,
                "name": "Bingo Monty DuClownPort I",
                "profession": {"active": False, "specialization": ["physical", "bits"], "mixed": "no"},
            }
        )
        cls.c2 = Flying.objects.create(
            circus={
                "id": 2,
                "name": "Bingo Monty DuClownPort II",
                "profession": {"active": True, "specialization": ["tumbling"]},
            }
        )
        cls.c3 = Flying.objects.create(
            circus={
                "id": 3,
                "name": "Bingo Monty DuClownPort III",
                "profession": {"active": False, "specialization": ["fire tumbling"]},
            }
        )

@skipUnlessDBFeature("has_json_set_function")
class JSONSetTests(DataMixin, TestCase):

    def test_json_set_replace_all(self):
        objs = Flying.objects.all()
        name = "Ringo Monty DuClownTown I"
        objs.update(circus=JSONSet(name=Cast(Value(name), output_field=TextField())))
        objs = Flying.objects.all()
        self.assertTrue(all(obj.circus["name"] == name for obj in objs))

    def test_json_set_replace_nested_existing(self):
        objs = Flying.objects.filter(circus__id=1)
        self.assertEqual(
            "physical bits",
            " ".join(objs.first().circus["profession"]["specialization"]),
        )
        objs.update(circus=JSONSet(profession__specialization__1=Cast(Value("flips"), output_field=TextField())))
        updated_obj = Flying.objects.get(circus__id=1)
        self.assertEqual(
            "physical flips",
            " ".join(updated_obj.circus["profession"]["specialization"]),
        )

    def test_json_set_replace_nested_new(self):
        objs = Flying.objects.filter(circus__id=1)
        objs.update(circus=JSONSet(profession__nested=JSONObject(
            one=JSONObject(
                two=JSONObject(
                    three=Cast(Value("flips"), output_field=TextField())))
                )
            )
        )
        updated_obj = Flying.objects.get(circus__id=1)
        self.assertEqual(
            "flips",
            updated_obj.circus["profession"]["nested"]["one"]["two"]["three"],
        )


    def test_json_set_insert_array(self):
        objs = Flying.objects.filter(circus__id=2)
        objs.update(circus=JSONSet(profession__specialization__1=Cast(Value("flips"), output_field=TextField())))
        updated_obj = Flying.objects.get(circus__id=2)
        self.assertEqual(
            "tumbling flips",
            " ".join(updated_obj.circus["profession"]["specialization"]),
        )

    def test_json_set_with_f_expression(self):
        active = Cast(Value(True), output_field=BooleanField())
        if connection.vendor in ["mariadb", "mysql"]:
            active = Cast(Value(1), output_field=SmallIntegerField())
        objs = Flying.objects.filter(circus__profession__active=False)
        objs.update(circus=JSONSet(profession__active=active))
        updated_objs = Flying.objects.all()
        self.assertTrue(all(obj.circus["profession"]["active"] for obj in updated_objs))

    def test_json_set_multiple_operations_upper(self):
        value = Value('name')
        if connection.vendor == 'postgresql':
            value = Cast(value, output_field=TextField())
        objs = Flying.objects.all()
        objs.update(
            circus=JSONSet(
                name=Func(
                    Cast(JSONExtract('circus', value), output_field=TextField()),
                    function='UPPER'
                ),
                profession__specialization__1=Cast(Value("flips"), output_field=TextField()),
            )
        )
        updated_names = set(obj.circus["name"] for obj in Flying.objects.all())
        expected_names = {
            "BINGO MONTY DUCLOWNPORT I",
            "BINGO MONTY DUCLOWNPORT II",
            "BINGO MONTY DUCLOWNPORT III",
        }
        self.assertEqual(updated_names, expected_names)

    def test_json_set_multiple_operations_lower(self):
        value = Value('name')
        if connection.vendor == 'postgresql':
            value = Cast(value, output_field=TextField())

        objs = Flying.objects.all()
        objs.update(
            circus=JSONSet(
                name=Func(
                    Cast(JSONExtract('circus', value), output_field=TextField()),
                    function='LOWER'
                ),
                profession__specialization__1=Cast(Value("flips"), output_field=TextField()),
            )
        )
        updated_names = set(obj.circus["name"] for obj in Flying.objects.all())
        expected_names = {
            "bingo monty duclownport i",
            "bingo monty duclownport ii",
            "bingo monty duclownport iii",
        }
        self.assertEqual(updated_names, expected_names)


@skipUnlessDBFeature("has_json_set_function")
class JSONRemoveTests(DataMixin, TestCase):

    def test_json_remove_single_key(self):
        Flying.objects.filter(circus__id=1).update(circus=JSONRemove("profession.active"))
        updated_obj = Flying.objects.get(circus__id=1)
        self.assertNotIn("active", updated_obj.circus["profession"])

    def test_json_remove_multiple_keys(self):
        Flying.objects.filter(circus__id=2).update(circus=JSONRemove("profession.active", "profession.specialization"))
        updated_obj = Flying.objects.get(circus__id=2)
        self.assertNotIn("active", updated_obj.circus["profession"])
        self.assertNotIn("specialization", updated_obj.circus["profession"])

    def test_json_remove_array_element(self):
        remove_array_zero = "profession.specialization[0]"
        if connection.vendor == 'postgresql':
            remove_array_zero = "profession.specialization.0"
        Flying.objects.filter(circus__id=1).update(circus=JSONRemove(remove_array_zero))
        updated_obj = Flying.objects.get(circus__id=1)
        self.assertEqual(len(updated_obj.circus["profession"]["specialization"]), 1, updated_obj.circus["profession"]["specialization"])
        self.assertEqual(updated_obj.circus["profession"]["specialization"][0], "bits")

    def test_json_remove_nonexistent_key(self):
        Flying.objects.filter(circus__id=3).update(circus=JSONRemove("nonexistent_key"))
        updated_obj = Flying.objects.get(circus__id=3)
        self.assertEqual(updated_obj.circus, self.c3.circus)  # Should remain unchanged


@skipUnlessDBFeature("has_json_set_function")
class JSONExtractTests(DataMixin, TestCase):

    def test_json_extract_single_value(self):
        value = Value('name', output_field=TextField())
        if connection.vendor == 'postgresql':
            value = Cast(value, output_field=TextField())
        result = Flying.objects.filter(circus__id=1).annotate(
            extracted_name=Cast(JSONExtract('circus', value), output_field=TextField())
        ).values_list('extracted_name', flat=True).first()
        self.assertEqual(result, "Bingo Monty DuClownPort I")

    def test_json_extract_nested_value(self):
        path = Value('profession.active')
        output_field = BooleanField()

        if connection.vendor in ['mariadb', 'mysql']:
            output_field = SmallIntegerField()

        elif connection.vendor == "postgresql":
            path = Cast(Value('profession,active'), output_field=TextField())

        result = Flying.objects.filter(circus__id=1).annotate(
            is_active=Cast(JSONExtract('circus', path), output_field=output_field)
        ).values_list('is_active', flat=True).first()
        self.assertEqual(result, False)

    def test_json_extract_multiple(self):
        output_field = TextField()
        single_path = Value('name', output_field=output_field)
        nested_path = Value('profession.mixed')
        if connection.vendor == "postgresql":
            nested_path = Cast(Value('profession,mixed'), output_field=output_field)
            output_field = ArrayField(base_field=output_field)

        result = Flying.objects.filter(circus__id=1).annotate(
            multi=Cast(JSONExtract('circus', single_path, nested_path), output_field=output_field)
        ).values_list("multi", flat=True).first()
        array_field = ['Bingo Monty DuClownPort I', 'no']
        if connection.vendor == "postgresql":
            self.assertEqual(result, array_field)
        else:
            self.assertEqual(json.loads(result), array_field)

    def test_json_extract_array_element(self):
        v = 'profession,specialization,0' if connection.vendor == 'postgresql' else 'profession.specialization[0]'
        result = Flying.objects.filter(circus__id=1).annotate(
            first_specialization=Cast(JSONExtract('circus', Value(v)), output_field=TextField())
        ).values_list('first_specialization', flat=True).first()
        self.assertEqual(result, "physical")

    def test_json_extract_nonexistent_key(self):
        result = Flying.objects.filter(circus__id=1).annotate(
            nonexistent=Cast(JSONExtract('circus', Value('nonexistent_key')), output_field=TextField())
        ).values_list('nonexistent', flat=True).first()
        self.assertIsNone(result)