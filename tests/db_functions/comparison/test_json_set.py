from django.db import NotSupportedError
from django.db.models import F, Value, TextField, JSONField, CharField
from django.db.models.expressions import RawSQL
from django.db.models.functions import JSONObject, JSONSet, Upper, Concat, Cast, Replace
from django.test import TestCase
from django.test.testcases import skipIfDBFeature, skipUnlessDBFeature
from django.db import connection
from ..models import Flying


class TestDataMixin:
    @classmethod
    def setUpTestData(cls):
        cls.c1 = Flying.objects.create(
            circus={
                "id": 1,
                "name": "Bingo Monty DuClownPort I",
                "profession": {"active": False, "specialization": ["physical", "bits"]},
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
class JSONSetTests(TestDataMixin, TestCase):
    def test_empty(self):
        objs = Flying.objects.all()

        with self.assertRaises(AttributeError):
            objs.update(circus=JSONSet())

        with self.assertRaises(AttributeError):
            objs.update(circus=JSONSet({}))

    def test_replace_all(self):
        objs = Flying.objects.all()
        name = "Ringo Monty DuClownTown I"
        key = "$.name"
        if connection.vendor == "postgresql":
            key = "{name}"
            name = '"Ringo Monty DuClownTown I"'
        ready = JSONSet(field="circus", fields={key: Value(name)})
        objs.update(circus=ready)
        self.assertTrue(
            all([obj.circus["name"] == name.replace('"', "") for obj in objs])
        )

    def test_replace_array_one(self):
        objs = Flying.objects.filter(circus__id=1)
        key = "$.profession.specialization[1]"
        value = Value("flips")
        if connection.vendor == "postgresql":
            key = "{profession,specialization,1}"
            value = Value('"flips"')
        ready = JSONSet(field="circus", fields={key: value})
        objs.update(circus=ready)
        self.assertEqual(
            "physical flips",
            " ".join(objs.first().circus["profession"]["specialization"]),
        )

    def test_replace_array_one_insert(self):
        objs = Flying.objects.filter(circus__id=2)
        key = "$.profession.specialization[1]"
        value = Value("flips")
        if connection.vendor == "postgresql":
            key = "{profession,specialization,1}"
            value = Value('"flips"')
        ready = JSONSet(field="circus", fields={key: value})
        objs.update(circus=ready)
        self.assertEqual(
            "tumbling flips",
            " ".join(objs.first().circus["profession"]["specialization"]),
        )

    def test_filter_and_replace(self):
        if connection.vendor == "sqlite":
            objs = Flying.objects.filter(circus__profession__active=False)
            key = "$.profession.active"
            ready = JSONSet(field="circus", fields={key: Value(True)})
            objs.update(circus=ready)
            self.assertTrue(all([obj.circus["profession"]["active"] for obj in objs]))
        else:
            pass
            # objs = Flying.objects.filter(circus__profession__active=False)
            # key = "{profession,active}"
            # ready = JSONSet(field="circus", fields={key: Value(True)})
            # objs.update(circus=ready)
            # self.assertTrue(all([obj.circus["profession"]["active"] for obj in objs]))

    def test_filter_and_replace_annotate_all(self):
        if connection.vendor == "sqlite":
            objs = Flying.objects.all()
            upper = JSONSet(
                field="circus",
                fields={
                    "$.name": Upper(F("circus__name")),
                    "$.profession.specialization[1]": Value("flips"),
                },
            )
            objs.update(circus=upper)
            items = Flying.objects.annotate(
                screaming_circus=JSONObject(
                    name=F("circus__name"),
                    s=Upper(
                        Replace(
                            Concat(
                                F("circus__profession__specialization__0"),
                                Value(" "),
                                F("circus__profession__specialization__1"),
                            ),
                            Value('"'),
                            Value(""),
                        )
                    ),
                )
            )
            self.assertSetEqual(
                {
                    " ".join(
                        [item.screaming_circus["name"], item.screaming_circus["s"]]
                    )
                    for item in items
                },
                {
                    "BINGO MONTY DUCLOWNPORT I PHYSICAL FLIPS",
                    "BINGO MONTY DUCLOWNPORT II TUMBLING FLIPS",
                    "BINGO MONTY DUCLOWNPORT III FIRE TUMBLING FLIPS",
                },
            )

    def XXX_test_filter_and_replace_annotate_all_postgreql(self):
        if connection.vendor == "postgresql":
            objs = Flying.objects.all()
            upper = JSONSet(
                field="circus",
                fields={
                    "{name}": Upper(RawSQL("(circus ->> '%s')::varchar")),
                },
            )
            objs.update(circus=upper)
            flips = JSONSet(
                field="circus",
                fields={
                    "{profession,specialization,1}": Value('"flips"'),
                },
            )
            objs.update(circus=flips)


@skipIfDBFeature("has_json_object_function")
class JSONObjectNotSupportedTests(TestCase):
    def test_not_supported(self):
        msg = "JSONSet() is not supported on this database backend."
        with self.assertRaisesMessage(NotSupportedError, msg):
            Flying.objects.annotate(crying_circus=JSONSet())
