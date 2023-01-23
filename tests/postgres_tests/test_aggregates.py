from django.db import connection, transaction
from django.db.models import (
    CharField,
    F,
    Func,
    IntegerField,
    JSONField,
    OuterRef,
    Q,
    Subquery,
    Value,
    Window,
)
from django.db.models.fields.json import KeyTextTransform, KeyTransform
from django.db.models.functions import Cast, Concat, Substr
from django.test import skipUnlessDBFeature
from django.test.utils import Approximate, ignore_warnings
from django.utils import timezone
from django.utils.deprecation import RemovedInDjango51Warning

from . import PostgreSQLTestCase
from .models import AggregateTestModel, HotelReservation, Room, StatTestModel

try:
    from django.contrib.postgres.aggregates import (
        ArrayAgg,
        BitAnd,
        BitOr,
        BitXor,
        BoolAnd,
        BoolOr,
        Corr,
        CovarPop,
        JSONBAgg,
        RegrAvgX,
        RegrAvgY,
        RegrCount,
        RegrIntercept,
        RegrR2,
        RegrSlope,
        RegrSXX,
        RegrSXY,
        RegrSYY,
        StatAggregate,
        StringAgg,
    )
    from django.contrib.postgres.fields import ArrayField
except ImportError:
    pass  # psycopg2 is not installed


class TestGeneralAggregate(PostgreSQLTestCase):
    @classmethod
    def setUpTestData(cls):
        cls.aggs = AggregateTestModel.objects.bulk_create(
            [
                AggregateTestModel(
                    boolean_field=True,
                    char_field="Foo1",
                    text_field="Text1",
                    integer_field=0,
                ),
                AggregateTestModel(
                    boolean_field=False,
                    char_field="Foo2",
                    text_field="Text2",
                    integer_field=1,
                    json_field={"lang": "pl"},
                ),
                AggregateTestModel(
                    boolean_field=False,
                    char_field="Foo4",
                    text_field="Text4",
                    integer_field=2,
                    json_field={"lang": "en"},
                ),
                AggregateTestModel(
                    boolean_field=True,
                    char_field="Foo3",
                    text_field="Text3",
                    integer_field=0,
                    json_field={"breed": "collie"},
                ),
            ]
        )

    def test_empty_result_set(self):
        AggregateTestModel.objects.all().delete()
        tests = [
            ArrayAgg("char_field"),
            ArrayAgg("integer_field"),
            ArrayAgg("boolean_field"),
            BitAnd("integer_field"),
            BitOr("integer_field"),
            BoolAnd("boolean_field"),
            BoolOr("boolean_field"),
            JSONBAgg("integer_field"),
            StringAgg("char_field", delimiter=";"),
        ]
        if connection.features.has_bit_xor:
            tests.append((BitXor("integer_field"), None))
        for aggregation in tests:
            with self.subTest(aggregation=aggregation):
                # Empty result with non-execution optimization.
                with self.assertNumQueries(0):
                    values = AggregateTestModel.objects.none().aggregate(
                        aggregation=aggregation,
                    )
                    self.assertEqual(values, {"aggregation": None})
                # Empty result when query must be executed.
                with self.assertNumQueries(1):
                    values = AggregateTestModel.objects.aggregate(
                        aggregation=aggregation,
                    )
                    self.assertEqual(values, {"aggregation": None})

    def test_default_argument(self):
        AggregateTestModel.objects.all().delete()
        tests = [
            (ArrayAgg("char_field", default=["<empty>"]), ["<empty>"]),
            (ArrayAgg("integer_field", default=[0]), [0]),
            (ArrayAgg("boolean_field", default=[False]), [False]),
            (BitAnd("integer_field", default=0), 0),
            (BitOr("integer_field", default=0), 0),
            (BoolAnd("boolean_field", default=False), False),
            (BoolOr("boolean_field", default=False), False),
            (JSONBAgg("integer_field", default=["<empty>"]), ["<empty>"]),
            (
                JSONBAgg("integer_field", default=Value(["<empty>"], JSONField())),
                ["<empty>"],
            ),
            (StringAgg("char_field", delimiter=";", default="<empty>"), "<empty>"),
            (
                StringAgg("char_field", delimiter=";", default=Value("<empty>")),
                "<empty>",
            ),
        ]
        if connection.features.has_bit_xor:
            tests.append((BitXor("integer_field", default=0), 0))
        for aggregation, expected_result in tests:
            with self.subTest(aggregation=aggregation):
                # Empty result with non-execution optimization.
                with self.assertNumQueries(0):
                    values = AggregateTestModel.objects.none().aggregate(
                        aggregation=aggregation,
                    )
                    self.assertEqual(values, {"aggregation": expected_result})
                # Empty result when query must be executed.
                with transaction.atomic(), self.assertNumQueries(1):
                    values = AggregateTestModel.objects.aggregate(
                        aggregation=aggregation,
                    )
                    self.assertEqual(values, {"aggregation": expected_result})

    @ignore_warnings(category=RemovedInDjango51Warning)
    def test_jsonb_agg_default_str_value(self):
        AggregateTestModel.objects.all().delete()
        queryset = AggregateTestModel.objects.all()
        self.assertEqual(
            queryset.aggregate(
                aggregation=JSONBAgg("integer_field", default=Value("<empty>"))
            ),
            {"aggregation": "<empty>"},
        )

    def test_jsonb_agg_default_str_value_deprecation(self):
        queryset = AggregateTestModel.objects.all()
        msg = (
            "Passing a Value() with an output_field that isn't a JSONField as "
            "JSONBAgg(default) is deprecated. Pass default=Value('<empty>', "
            "output_field=JSONField()) instead."
        )
        with self.assertWarnsMessage(RemovedInDjango51Warning, msg):
            queryset.aggregate(
                aggregation=JSONBAgg("integer_field", default=Value("<empty>"))
            )
        with self.assertWarnsMessage(RemovedInDjango51Warning, msg):
            queryset.none().aggregate(
                aggregation=JSONBAgg("integer_field", default=Value("<empty>"))
            ),

    @ignore_warnings(category=RemovedInDjango51Warning)
    def test_jsonb_agg_default_encoded_json_string(self):
        AggregateTestModel.objects.all().delete()
        queryset = AggregateTestModel.objects.all()
        self.assertEqual(
            queryset.aggregate(
                aggregation=JSONBAgg("integer_field", default=Value("[]"))
            ),
            {"aggregation": []},
        )

    def test_jsonb_agg_default_encoded_json_string_deprecation(self):
        queryset = AggregateTestModel.objects.all()
        msg = (
            "Passing an encoded JSON string as JSONBAgg(default) is deprecated. Pass "
            "default=[] instead."
        )
        with self.assertWarnsMessage(RemovedInDjango51Warning, msg):
            queryset.aggregate(
                aggregation=JSONBAgg("integer_field", default=Value("[]"))
            )
        with self.assertWarnsMessage(RemovedInDjango51Warning, msg):
            queryset.none().aggregate(
                aggregation=JSONBAgg("integer_field", default=Value("[]"))
            )

    def test_array_agg_charfield(self):
        values = AggregateTestModel.objects.aggregate(arrayagg=ArrayAgg("char_field"))
        self.assertEqual(values, {"arrayagg": ["Foo1", "Foo2", "Foo4", "Foo3"]})

    def test_array_agg_charfield_ordering(self):
        ordering_test_cases = (
            (F("char_field").desc(), ["Foo4", "Foo3", "Foo2", "Foo1"]),
            (F("char_field").asc(), ["Foo1", "Foo2", "Foo3", "Foo4"]),
            (F("char_field"), ["Foo1", "Foo2", "Foo3", "Foo4"]),
            (
                [F("boolean_field"), F("char_field").desc()],
                ["Foo4", "Foo2", "Foo3", "Foo1"],
            ),
            (
                (F("boolean_field"), F("char_field").desc()),
                ["Foo4", "Foo2", "Foo3", "Foo1"],
            ),
            ("char_field", ["Foo1", "Foo2", "Foo3", "Foo4"]),
            ("-char_field", ["Foo4", "Foo3", "Foo2", "Foo1"]),
            (Concat("char_field", Value("@")), ["Foo1", "Foo2", "Foo3", "Foo4"]),
            (Concat("char_field", Value("@")).desc(), ["Foo4", "Foo3", "Foo2", "Foo1"]),
            (
                (
                    Substr("char_field", 1, 1),
                    F("integer_field"),
                    Substr("char_field", 4, 1).desc(),
                ),
                ["Foo3", "Foo1", "Foo2", "Foo4"],
            ),
        )
        for ordering, expected_output in ordering_test_cases:
            with self.subTest(ordering=ordering, expected_output=expected_output):
                values = AggregateTestModel.objects.aggregate(
                    arrayagg=ArrayAgg("char_field", ordering=ordering)
                )
                self.assertEqual(values, {"arrayagg": expected_output})

    def test_array_agg_integerfield(self):
        values = AggregateTestModel.objects.aggregate(
            arrayagg=ArrayAgg("integer_field")
        )
        self.assertEqual(values, {"arrayagg": [0, 1, 2, 0]})

    def test_array_agg_integerfield_ordering(self):
        values = AggregateTestModel.objects.aggregate(
            arrayagg=ArrayAgg("integer_field", ordering=F("integer_field").desc())
        )
        self.assertEqual(values, {"arrayagg": [2, 1, 0, 0]})

    def test_array_agg_booleanfield(self):
        values = AggregateTestModel.objects.aggregate(
            arrayagg=ArrayAgg("boolean_field")
        )
        self.assertEqual(values, {"arrayagg": [True, False, False, True]})

    def test_array_agg_booleanfield_ordering(self):
        ordering_test_cases = (
            (F("boolean_field").asc(), [False, False, True, True]),
            (F("boolean_field").desc(), [True, True, False, False]),
            (F("boolean_field"), [False, False, True, True]),
        )
        for ordering, expected_output in ordering_test_cases:
            with self.subTest(ordering=ordering, expected_output=expected_output):
                values = AggregateTestModel.objects.aggregate(
                    arrayagg=ArrayAgg("boolean_field", ordering=ordering)
                )
                self.assertEqual(values, {"arrayagg": expected_output})

    def test_array_agg_jsonfield(self):
        values = AggregateTestModel.objects.aggregate(
            arrayagg=ArrayAgg(
                KeyTransform("lang", "json_field"),
                filter=Q(json_field__lang__isnull=False),
            ),
        )
        self.assertEqual(values, {"arrayagg": ["pl", "en"]})

    def test_array_agg_jsonfield_ordering(self):
        values = AggregateTestModel.objects.aggregate(
            arrayagg=ArrayAgg(
                KeyTransform("lang", "json_field"),
                filter=Q(json_field__lang__isnull=False),
                ordering=KeyTransform("lang", "json_field"),
            ),
        )
        self.assertEqual(values, {"arrayagg": ["en", "pl"]})

    def test_array_agg_filter(self):
        values = AggregateTestModel.objects.aggregate(
            arrayagg=ArrayAgg("integer_field", filter=Q(integer_field__gt=0)),
        )
        self.assertEqual(values, {"arrayagg": [1, 2]})

    def test_array_agg_lookups(self):
        aggr1 = AggregateTestModel.objects.create()
        aggr2 = AggregateTestModel.objects.create()
        StatTestModel.objects.create(related_field=aggr1, int1=1, int2=0)
        StatTestModel.objects.create(related_field=aggr1, int1=2, int2=0)
        StatTestModel.objects.create(related_field=aggr2, int1=3, int2=0)
        StatTestModel.objects.create(related_field=aggr2, int1=4, int2=0)
        qs = (
            StatTestModel.objects.values("related_field")
            .annotate(array=ArrayAgg("int1"))
            .filter(array__overlap=[2])
            .values_list("array", flat=True)
        )
        self.assertCountEqual(qs.get(), [1, 2])

    def test_bit_and_general(self):
        values = AggregateTestModel.objects.filter(integer_field__in=[0, 1]).aggregate(
            bitand=BitAnd("integer_field")
        )
        self.assertEqual(values, {"bitand": 0})

    def test_bit_and_on_only_true_values(self):
        values = AggregateTestModel.objects.filter(integer_field=1).aggregate(
            bitand=BitAnd("integer_field")
        )
        self.assertEqual(values, {"bitand": 1})

    def test_bit_and_on_only_false_values(self):
        values = AggregateTestModel.objects.filter(integer_field=0).aggregate(
            bitand=BitAnd("integer_field")
        )
        self.assertEqual(values, {"bitand": 0})

    def test_bit_or_general(self):
        values = AggregateTestModel.objects.filter(integer_field__in=[0, 1]).aggregate(
            bitor=BitOr("integer_field")
        )
        self.assertEqual(values, {"bitor": 1})

    def test_bit_or_on_only_true_values(self):
        values = AggregateTestModel.objects.filter(integer_field=1).aggregate(
            bitor=BitOr("integer_field")
        )
        self.assertEqual(values, {"bitor": 1})

    def test_bit_or_on_only_false_values(self):
        values = AggregateTestModel.objects.filter(integer_field=0).aggregate(
            bitor=BitOr("integer_field")
        )
        self.assertEqual(values, {"bitor": 0})

    @skipUnlessDBFeature("has_bit_xor")
    def test_bit_xor_general(self):
        AggregateTestModel.objects.create(integer_field=3)
        values = AggregateTestModel.objects.filter(
            integer_field__in=[1, 3],
        ).aggregate(bitxor=BitXor("integer_field"))
        self.assertEqual(values, {"bitxor": 2})

    @skipUnlessDBFeature("has_bit_xor")
    def test_bit_xor_on_only_true_values(self):
        values = AggregateTestModel.objects.filter(
            integer_field=1,
        ).aggregate(bitxor=BitXor("integer_field"))
        self.assertEqual(values, {"bitxor": 1})

    @skipUnlessDBFeature("has_bit_xor")
    def test_bit_xor_on_only_false_values(self):
        values = AggregateTestModel.objects.filter(
            integer_field=0,
        ).aggregate(bitxor=BitXor("integer_field"))
        self.assertEqual(values, {"bitxor": 0})

    def test_bool_and_general(self):
        values = AggregateTestModel.objects.aggregate(booland=BoolAnd("boolean_field"))
        self.assertEqual(values, {"booland": False})

    def test_bool_and_q_object(self):
        values = AggregateTestModel.objects.aggregate(
            booland=BoolAnd(Q(integer_field__gt=2)),
        )
        self.assertEqual(values, {"booland": False})

    def test_bool_or_general(self):
        values = AggregateTestModel.objects.aggregate(boolor=BoolOr("boolean_field"))
        self.assertEqual(values, {"boolor": True})

    def test_bool_or_q_object(self):
        values = AggregateTestModel.objects.aggregate(
            boolor=BoolOr(Q(integer_field__gt=2)),
        )
        self.assertEqual(values, {"boolor": False})

    def test_string_agg_requires_delimiter(self):
        with self.assertRaises(TypeError):
            AggregateTestModel.objects.aggregate(stringagg=StringAgg("char_field"))

    def test_string_agg_delimiter_escaping(self):
        values = AggregateTestModel.objects.aggregate(
            stringagg=StringAgg("char_field", delimiter="'")
        )
        self.assertEqual(values, {"stringagg": "Foo1'Foo2'Foo4'Foo3"})

    def test_string_agg_charfield(self):
        values = AggregateTestModel.objects.aggregate(
            stringagg=StringAgg("char_field", delimiter=";")
        )
        self.assertEqual(values, {"stringagg": "Foo1;Foo2;Foo4;Foo3"})

    def test_string_agg_default_output_field(self):
        values = AggregateTestModel.objects.aggregate(
            stringagg=StringAgg("text_field", delimiter=";"),
        )
        self.assertEqual(values, {"stringagg": "Text1;Text2;Text4;Text3"})

    def test_string_agg_charfield_ordering(self):
        ordering_test_cases = (
            (F("char_field").desc(), "Foo4;Foo3;Foo2;Foo1"),
            (F("char_field").asc(), "Foo1;Foo2;Foo3;Foo4"),
            (F("char_field"), "Foo1;Foo2;Foo3;Foo4"),
            ("char_field", "Foo1;Foo2;Foo3;Foo4"),
            ("-char_field", "Foo4;Foo3;Foo2;Foo1"),
            (Concat("char_field", Value("@")), "Foo1;Foo2;Foo3;Foo4"),
            (Concat("char_field", Value("@")).desc(), "Foo4;Foo3;Foo2;Foo1"),
        )
        for ordering, expected_output in ordering_test_cases:
            with self.subTest(ordering=ordering, expected_output=expected_output):
                values = AggregateTestModel.objects.aggregate(
                    stringagg=StringAgg("char_field", delimiter=";", ordering=ordering)
                )
                self.assertEqual(values, {"stringagg": expected_output})

    def test_string_agg_jsonfield_ordering(self):
        values = AggregateTestModel.objects.aggregate(
            stringagg=StringAgg(
                KeyTextTransform("lang", "json_field"),
                delimiter=";",
                ordering=KeyTextTransform("lang", "json_field"),
                output_field=CharField(),
            ),
        )
        self.assertEqual(values, {"stringagg": "en;pl"})

    def test_string_agg_filter(self):
        values = AggregateTestModel.objects.aggregate(
            stringagg=StringAgg(
                "char_field",
                delimiter=";",
                filter=Q(char_field__endswith="3") | Q(char_field__endswith="1"),
            )
        )
        self.assertEqual(values, {"stringagg": "Foo1;Foo3"})

    def test_orderable_agg_alternative_fields(self):
        values = AggregateTestModel.objects.aggregate(
            arrayagg=ArrayAgg("integer_field", ordering=F("char_field").asc())
        )
        self.assertEqual(values, {"arrayagg": [0, 1, 0, 2]})

    def test_jsonb_agg(self):
        values = AggregateTestModel.objects.aggregate(jsonbagg=JSONBAgg("char_field"))
        self.assertEqual(values, {"jsonbagg": ["Foo1", "Foo2", "Foo4", "Foo3"]})

    def test_jsonb_agg_charfield_ordering(self):
        ordering_test_cases = (
            (F("char_field").desc(), ["Foo4", "Foo3", "Foo2", "Foo1"]),
            (F("char_field").asc(), ["Foo1", "Foo2", "Foo3", "Foo4"]),
            (F("char_field"), ["Foo1", "Foo2", "Foo3", "Foo4"]),
            ("char_field", ["Foo1", "Foo2", "Foo3", "Foo4"]),
            ("-char_field", ["Foo4", "Foo3", "Foo2", "Foo1"]),
            (Concat("char_field", Value("@")), ["Foo1", "Foo2", "Foo3", "Foo4"]),
            (Concat("char_field", Value("@")).desc(), ["Foo4", "Foo3", "Foo2", "Foo1"]),
        )
        for ordering, expected_output in ordering_test_cases:
            with self.subTest(ordering=ordering, expected_output=expected_output):
                values = AggregateTestModel.objects.aggregate(
                    jsonbagg=JSONBAgg("char_field", ordering=ordering),
                )
                self.assertEqual(values, {"jsonbagg": expected_output})

    def test_jsonb_agg_integerfield_ordering(self):
        values = AggregateTestModel.objects.aggregate(
            jsonbagg=JSONBAgg("integer_field", ordering=F("integer_field").desc()),
        )
        self.assertEqual(values, {"jsonbagg": [2, 1, 0, 0]})

    def test_jsonb_agg_booleanfield_ordering(self):
        ordering_test_cases = (
            (F("boolean_field").asc(), [False, False, True, True]),
            (F("boolean_field").desc(), [True, True, False, False]),
            (F("boolean_field"), [False, False, True, True]),
        )
        for ordering, expected_output in ordering_test_cases:
            with self.subTest(ordering=ordering, expected_output=expected_output):
                values = AggregateTestModel.objects.aggregate(
                    jsonbagg=JSONBAgg("boolean_field", ordering=ordering),
                )
                self.assertEqual(values, {"jsonbagg": expected_output})

    def test_jsonb_agg_jsonfield_ordering(self):
        values = AggregateTestModel.objects.aggregate(
            jsonbagg=JSONBAgg(
                KeyTransform("lang", "json_field"),
                filter=Q(json_field__lang__isnull=False),
                ordering=KeyTransform("lang", "json_field"),
            ),
        )
        self.assertEqual(values, {"jsonbagg": ["en", "pl"]})

    def test_jsonb_agg_key_index_transforms(self):
        room101 = Room.objects.create(number=101)
        room102 = Room.objects.create(number=102)
        datetimes = [
            timezone.datetime(2018, 6, 20),
            timezone.datetime(2018, 6, 24),
            timezone.datetime(2018, 6, 28),
        ]
        HotelReservation.objects.create(
            datespan=(datetimes[0].date(), datetimes[1].date()),
            start=datetimes[0],
            end=datetimes[1],
            room=room102,
            requirements={"double_bed": True, "parking": True},
        )
        HotelReservation.objects.create(
            datespan=(datetimes[1].date(), datetimes[2].date()),
            start=datetimes[1],
            end=datetimes[2],
            room=room102,
            requirements={"double_bed": False, "sea_view": True, "parking": False},
        )
        HotelReservation.objects.create(
            datespan=(datetimes[0].date(), datetimes[2].date()),
            start=datetimes[0],
            end=datetimes[2],
            room=room101,
            requirements={"sea_view": False},
        )
        values = (
            Room.objects.annotate(
                requirements=JSONBAgg(
                    "hotelreservation__requirements",
                    ordering="-hotelreservation__start",
                )
            )
            .filter(requirements__0__sea_view=True)
            .values("number", "requirements")
        )
        self.assertSequenceEqual(
            values,
            [
                {
                    "number": 102,
                    "requirements": [
                        {"double_bed": False, "sea_view": True, "parking": False},
                        {"double_bed": True, "parking": True},
                    ],
                },
            ],
        )

    def test_string_agg_array_agg_ordering_in_subquery(self):
        stats = []
        for i, agg in enumerate(AggregateTestModel.objects.order_by("char_field")):
            stats.append(StatTestModel(related_field=agg, int1=i, int2=i + 1))
            stats.append(StatTestModel(related_field=agg, int1=i + 1, int2=i))
        StatTestModel.objects.bulk_create(stats)

        for aggregate, expected_result in (
            (
                ArrayAgg("stattestmodel__int1", ordering="-stattestmodel__int2"),
                [
                    ("Foo1", [0, 1]),
                    ("Foo2", [1, 2]),
                    ("Foo3", [2, 3]),
                    ("Foo4", [3, 4]),
                ],
            ),
            (
                StringAgg(
                    Cast("stattestmodel__int1", CharField()),
                    delimiter=";",
                    ordering="-stattestmodel__int2",
                ),
                [("Foo1", "0;1"), ("Foo2", "1;2"), ("Foo3", "2;3"), ("Foo4", "3;4")],
            ),
        ):
            with self.subTest(aggregate=aggregate.__class__.__name__):
                subquery = (
                    AggregateTestModel.objects.filter(
                        pk=OuterRef("pk"),
                    )
                    .annotate(agg=aggregate)
                    .values("agg")
                )
                values = (
                    AggregateTestModel.objects.annotate(
                        agg=Subquery(subquery),
                    )
                    .order_by("char_field")
                    .values_list("char_field", "agg")
                )
                self.assertEqual(list(values), expected_result)

    def test_string_agg_array_agg_filter_in_subquery(self):
        StatTestModel.objects.bulk_create(
            [
                StatTestModel(related_field=self.aggs[0], int1=0, int2=5),
                StatTestModel(related_field=self.aggs[0], int1=1, int2=4),
                StatTestModel(related_field=self.aggs[0], int1=2, int2=3),
            ]
        )
        for aggregate, expected_result in (
            (
                ArrayAgg("stattestmodel__int1", filter=Q(stattestmodel__int2__gt=3)),
                [("Foo1", [0, 1]), ("Foo2", None)],
            ),
            (
                StringAgg(
                    Cast("stattestmodel__int2", CharField()),
                    delimiter=";",
                    filter=Q(stattestmodel__int1__lt=2),
                ),
                [("Foo1", "5;4"), ("Foo2", None)],
            ),
        ):
            with self.subTest(aggregate=aggregate.__class__.__name__):
                subquery = (
                    AggregateTestModel.objects.filter(
                        pk=OuterRef("pk"),
                    )
                    .annotate(agg=aggregate)
                    .values("agg")
                )
                values = (
                    AggregateTestModel.objects.annotate(
                        agg=Subquery(subquery),
                    )
                    .filter(
                        char_field__in=["Foo1", "Foo2"],
                    )
                    .order_by("char_field")
                    .values_list("char_field", "agg")
                )
                self.assertEqual(list(values), expected_result)

    def test_string_agg_filter_in_subquery_with_exclude(self):
        subquery = (
            AggregateTestModel.objects.annotate(
                stringagg=StringAgg(
                    "char_field",
                    delimiter=";",
                    filter=Q(char_field__endswith="1"),
                )
            )
            .exclude(stringagg="")
            .values("id")
        )
        self.assertSequenceEqual(
            AggregateTestModel.objects.filter(id__in=Subquery(subquery)),
            [self.aggs[0]],
        )

    def test_ordering_isnt_cleared_for_array_subquery(self):
        inner_qs = AggregateTestModel.objects.order_by("-integer_field")
        qs = AggregateTestModel.objects.annotate(
            integers=Func(
                Subquery(inner_qs.values("integer_field")),
                function="ARRAY",
                output_field=ArrayField(base_field=IntegerField()),
            ),
        )
        self.assertSequenceEqual(
            qs.first().integers,
            inner_qs.values_list("integer_field", flat=True),
        )

    def test_window(self):
        self.assertCountEqual(
            AggregateTestModel.objects.annotate(
                integers=Window(
                    expression=ArrayAgg("char_field"),
                    partition_by=F("integer_field"),
                )
            ).values("integers", "char_field"),
            [
                {"integers": ["Foo1", "Foo3"], "char_field": "Foo1"},
                {"integers": ["Foo1", "Foo3"], "char_field": "Foo3"},
                {"integers": ["Foo2"], "char_field": "Foo2"},
                {"integers": ["Foo4"], "char_field": "Foo4"},
            ],
        )

    def test_values_list(self):
        tests = [ArrayAgg("integer_field"), JSONBAgg("integer_field")]
        for aggregation in tests:
            with self.subTest(aggregation=aggregation):
                self.assertCountEqual(
                    AggregateTestModel.objects.values_list(aggregation),
                    [([0],), ([1],), ([2],), ([0],)],
                )


class TestAggregateDistinct(PostgreSQLTestCase):
    @classmethod
    def setUpTestData(cls):
        AggregateTestModel.objects.create(char_field="Foo")
        AggregateTestModel.objects.create(char_field="Foo")
        AggregateTestModel.objects.create(char_field="Bar")

    def test_string_agg_distinct_false(self):
        values = AggregateTestModel.objects.aggregate(
            stringagg=StringAgg("char_field", delimiter=" ", distinct=False)
        )
        self.assertEqual(values["stringagg"].count("Foo"), 2)
        self.assertEqual(values["stringagg"].count("Bar"), 1)

    def test_string_agg_distinct_true(self):
        values = AggregateTestModel.objects.aggregate(
            stringagg=StringAgg("char_field", delimiter=" ", distinct=True)
        )
        self.assertEqual(values["stringagg"].count("Foo"), 1)
        self.assertEqual(values["stringagg"].count("Bar"), 1)

    def test_array_agg_distinct_false(self):
        values = AggregateTestModel.objects.aggregate(
            arrayagg=ArrayAgg("char_field", distinct=False)
        )
        self.assertEqual(sorted(values["arrayagg"]), ["Bar", "Foo", "Foo"])

    def test_array_agg_distinct_true(self):
        values = AggregateTestModel.objects.aggregate(
            arrayagg=ArrayAgg("char_field", distinct=True)
        )
        self.assertEqual(sorted(values["arrayagg"]), ["Bar", "Foo"])

    def test_jsonb_agg_distinct_false(self):
        values = AggregateTestModel.objects.aggregate(
            jsonbagg=JSONBAgg("char_field", distinct=False),
        )
        self.assertEqual(sorted(values["jsonbagg"]), ["Bar", "Foo", "Foo"])

    def test_jsonb_agg_distinct_true(self):
        values = AggregateTestModel.objects.aggregate(
            jsonbagg=JSONBAgg("char_field", distinct=True),
        )
        self.assertEqual(sorted(values["jsonbagg"]), ["Bar", "Foo"])


class TestStatisticsAggregate(PostgreSQLTestCase):
    @classmethod
    def setUpTestData(cls):
        StatTestModel.objects.create(
            int1=1,
            int2=3,
            related_field=AggregateTestModel.objects.create(integer_field=0),
        )
        StatTestModel.objects.create(
            int1=2,
            int2=2,
            related_field=AggregateTestModel.objects.create(integer_field=1),
        )
        StatTestModel.objects.create(
            int1=3,
            int2=1,
            related_field=AggregateTestModel.objects.create(integer_field=2),
        )

    # Tests for base class (StatAggregate)

    def test_missing_arguments_raises_exception(self):
        with self.assertRaisesMessage(ValueError, "Both y and x must be provided."):
            StatAggregate(x=None, y=None)

    def test_correct_source_expressions(self):
        func = StatAggregate(x="test", y=13)
        self.assertIsInstance(func.source_expressions[0], Value)
        self.assertIsInstance(func.source_expressions[1], F)

    def test_alias_is_required(self):
        class SomeFunc(StatAggregate):
            function = "TEST"

        with self.assertRaisesMessage(TypeError, "Complex aggregates require an alias"):
            StatTestModel.objects.aggregate(SomeFunc(y="int2", x="int1"))

    # Test aggregates

    def test_empty_result_set(self):
        StatTestModel.objects.all().delete()
        tests = [
            (Corr(y="int2", x="int1"), None),
            (CovarPop(y="int2", x="int1"), None),
            (CovarPop(y="int2", x="int1", sample=True), None),
            (RegrAvgX(y="int2", x="int1"), None),
            (RegrAvgY(y="int2", x="int1"), None),
            (RegrCount(y="int2", x="int1"), 0),
            (RegrIntercept(y="int2", x="int1"), None),
            (RegrR2(y="int2", x="int1"), None),
            (RegrSlope(y="int2", x="int1"), None),
            (RegrSXX(y="int2", x="int1"), None),
            (RegrSXY(y="int2", x="int1"), None),
            (RegrSYY(y="int2", x="int1"), None),
        ]
        for aggregation, expected_result in tests:
            with self.subTest(aggregation=aggregation):
                # Empty result with non-execution optimization.
                with self.assertNumQueries(0):
                    values = StatTestModel.objects.none().aggregate(
                        aggregation=aggregation,
                    )
                    self.assertEqual(values, {"aggregation": expected_result})
                # Empty result when query must be executed.
                with self.assertNumQueries(1):
                    values = StatTestModel.objects.aggregate(
                        aggregation=aggregation,
                    )
                    self.assertEqual(values, {"aggregation": expected_result})

    def test_default_argument(self):
        StatTestModel.objects.all().delete()
        tests = [
            (Corr(y="int2", x="int1", default=0), 0),
            (CovarPop(y="int2", x="int1", default=0), 0),
            (CovarPop(y="int2", x="int1", sample=True, default=0), 0),
            (RegrAvgX(y="int2", x="int1", default=0), 0),
            (RegrAvgY(y="int2", x="int1", default=0), 0),
            # RegrCount() doesn't support the default argument.
            (RegrIntercept(y="int2", x="int1", default=0), 0),
            (RegrR2(y="int2", x="int1", default=0), 0),
            (RegrSlope(y="int2", x="int1", default=0), 0),
            (RegrSXX(y="int2", x="int1", default=0), 0),
            (RegrSXY(y="int2", x="int1", default=0), 0),
            (RegrSYY(y="int2", x="int1", default=0), 0),
        ]
        for aggregation, expected_result in tests:
            with self.subTest(aggregation=aggregation):
                # Empty result with non-execution optimization.
                with self.assertNumQueries(0):
                    values = StatTestModel.objects.none().aggregate(
                        aggregation=aggregation,
                    )
                    self.assertEqual(values, {"aggregation": expected_result})
                # Empty result when query must be executed.
                with self.assertNumQueries(1):
                    values = StatTestModel.objects.aggregate(
                        aggregation=aggregation,
                    )
                    self.assertEqual(values, {"aggregation": expected_result})

    def test_corr_general(self):
        values = StatTestModel.objects.aggregate(corr=Corr(y="int2", x="int1"))
        self.assertEqual(values, {"corr": -1.0})

    def test_covar_pop_general(self):
        values = StatTestModel.objects.aggregate(covarpop=CovarPop(y="int2", x="int1"))
        self.assertEqual(values, {"covarpop": Approximate(-0.66, places=1)})

    def test_covar_pop_sample(self):
        values = StatTestModel.objects.aggregate(
            covarpop=CovarPop(y="int2", x="int1", sample=True)
        )
        self.assertEqual(values, {"covarpop": -1.0})

    def test_regr_avgx_general(self):
        values = StatTestModel.objects.aggregate(regravgx=RegrAvgX(y="int2", x="int1"))
        self.assertEqual(values, {"regravgx": 2.0})

    def test_regr_avgy_general(self):
        values = StatTestModel.objects.aggregate(regravgy=RegrAvgY(y="int2", x="int1"))
        self.assertEqual(values, {"regravgy": 2.0})

    def test_regr_count_general(self):
        values = StatTestModel.objects.aggregate(
            regrcount=RegrCount(y="int2", x="int1")
        )
        self.assertEqual(values, {"regrcount": 3})

    def test_regr_count_default(self):
        msg = "RegrCount does not allow default."
        with self.assertRaisesMessage(TypeError, msg):
            RegrCount(y="int2", x="int1", default=0)

    def test_regr_intercept_general(self):
        values = StatTestModel.objects.aggregate(
            regrintercept=RegrIntercept(y="int2", x="int1")
        )
        self.assertEqual(values, {"regrintercept": 4})

    def test_regr_r2_general(self):
        values = StatTestModel.objects.aggregate(regrr2=RegrR2(y="int2", x="int1"))
        self.assertEqual(values, {"regrr2": 1})

    def test_regr_slope_general(self):
        values = StatTestModel.objects.aggregate(
            regrslope=RegrSlope(y="int2", x="int1")
        )
        self.assertEqual(values, {"regrslope": -1})

    def test_regr_sxx_general(self):
        values = StatTestModel.objects.aggregate(regrsxx=RegrSXX(y="int2", x="int1"))
        self.assertEqual(values, {"regrsxx": 2.0})

    def test_regr_sxy_general(self):
        values = StatTestModel.objects.aggregate(regrsxy=RegrSXY(y="int2", x="int1"))
        self.assertEqual(values, {"regrsxy": -2.0})

    def test_regr_syy_general(self):
        values = StatTestModel.objects.aggregate(regrsyy=RegrSYY(y="int2", x="int1"))
        self.assertEqual(values, {"regrsyy": 2.0})

    def test_regr_avgx_with_related_obj_and_number_as_argument(self):
        """
        This is more complex test to check if JOIN on field and
        number as argument works as expected.
        """
        values = StatTestModel.objects.aggregate(
            complex_regravgx=RegrAvgX(y=5, x="related_field__integer_field")
        )
        self.assertEqual(values, {"complex_regravgx": 1.0})
