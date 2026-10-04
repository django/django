import unittest
from datetime import date, datetime, time, timedelta
from decimal import Decimal
from operator import attrgetter, itemgetter
from unittest import mock
from uuid import UUID

from django.core.exceptions import FieldError
from django.db import NotSupportedError, connection
from django.db.models import (
    BinaryField,
    BooleanField,
    Case,
    Count,
    DecimalField,
    ExpressionWrapper,
    F,
    GenericIPAddressField,
    IntegerField,
    Max,
    Min,
    OuterRef,
    Q,
    Subquery,
    Sum,
    TextField,
    Value,
    When,
    Window,
)
from django.db.models.expressions import DatabaseDefault
from django.db.models.functions import Abs, Lag, RowNumber
from django.db.models.lookups import Exact
from django.test import SimpleTestCase, TestCase, skipUnlessDBFeature
from django.test.utils import isolate_apps

from .models import (
    CaseTestModel,
    Client,
    FKCaseTestModel,
    M2MCaseTestModel,
    O2OCaseTestModel,
)

try:
    from PIL import Image
except ImportError:
    Image = None


class CaseExpressionTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        o = CaseTestModel.objects.create(integer=1, integer2=1, string="1")
        O2OCaseTestModel.objects.create(o2o=o, integer=1)
        FKCaseTestModel.objects.create(fk=o, integer=1)

        o = CaseTestModel.objects.create(integer=2, integer2=3, string="2")
        O2OCaseTestModel.objects.create(o2o=o, integer=2)
        FKCaseTestModel.objects.create(fk=o, integer=2)
        FKCaseTestModel.objects.create(fk=o, integer=3)

        o = CaseTestModel.objects.create(integer=3, integer2=4, string="3")
        O2OCaseTestModel.objects.create(o2o=o, integer=3)
        FKCaseTestModel.objects.create(fk=o, integer=3)
        FKCaseTestModel.objects.create(fk=o, integer=4)

        o = CaseTestModel.objects.create(integer=2, integer2=2, string="2")
        O2OCaseTestModel.objects.create(o2o=o, integer=2)
        FKCaseTestModel.objects.create(fk=o, integer=2)
        FKCaseTestModel.objects.create(fk=o, integer=3)

        o = CaseTestModel.objects.create(integer=3, integer2=4, string="3")
        O2OCaseTestModel.objects.create(o2o=o, integer=3)
        FKCaseTestModel.objects.create(fk=o, integer=3)
        FKCaseTestModel.objects.create(fk=o, integer=4)

        o = CaseTestModel.objects.create(integer=3, integer2=3, string="3")
        O2OCaseTestModel.objects.create(o2o=o, integer=3)
        FKCaseTestModel.objects.create(fk=o, integer=3)
        FKCaseTestModel.objects.create(fk=o, integer=4)

        o = CaseTestModel.objects.create(integer=4, integer2=5, string="4")
        O2OCaseTestModel.objects.create(o2o=o, integer=1)
        FKCaseTestModel.objects.create(fk=o, integer=5)

        cls.group_by_fields = [
            f.name
            for f in CaseTestModel._meta.get_fields()
            if not (f.is_relation and f.auto_created)
            and (
                connection.features.allows_group_by_lob
                or not isinstance(f, (BinaryField, TextField))
            )
        ]

    def test_annotate(self):
        self.assertQuerySetEqual(
            CaseTestModel.objects.annotate(
                test=Case(
                    When(integer=1, then=Value("one")),
                    When(integer=2, then=Value("two")),
                    default=Value("other"),
                )
            ).order_by("pk"),
            [
                (1, "one"),
                (2, "two"),
                (3, "other"),
                (2, "two"),
                (3, "other"),
                (3, "other"),
                (4, "other"),
            ],
            transform=attrgetter("integer", "test"),
        )

    def test_annotate_without_default(self):
        self.assertQuerySetEqual(
            CaseTestModel.objects.annotate(
                test=Case(
                    When(integer=1, then=1),
                    When(integer=2, then=2),
                )
            ).order_by("pk"),
            [(1, 1), (2, 2), (3, None), (2, 2), (3, None), (3, None), (4, None)],
            transform=attrgetter("integer", "test"),
        )

    def test_annotate_with_expression_as_value(self):
        self.assertQuerySetEqual(
            CaseTestModel.objects.annotate(
                f_test=Case(
                    When(integer=1, then=F("integer") + 1),
                    When(integer=2, then=F("integer") + 3),
                    default="integer",
                )
            ).order_by("pk"),
            [(1, 2), (2, 5), (3, 3), (2, 5), (3, 3), (3, 3), (4, 4)],
            transform=attrgetter("integer", "f_test"),
        )

    def test_annotate_with_expression_as_condition(self):
        self.assertQuerySetEqual(
            CaseTestModel.objects.annotate(
                f_test=Case(
                    When(integer2=F("integer"), then=Value("equal")),
                    When(integer2=F("integer") + 1, then=Value("+1")),
                )
            ).order_by("pk"),
            [
                (1, "equal"),
                (2, "+1"),
                (3, "+1"),
                (2, "equal"),
                (3, "+1"),
                (3, "equal"),
                (4, "+1"),
            ],
            transform=attrgetter("integer", "f_test"),
        )

    def test_annotate_with_join_in_value(self):
        self.assertQuerySetEqual(
            CaseTestModel.objects.annotate(
                join_test=Case(
                    When(integer=1, then=F("o2o_rel__integer") + 1),
                    When(integer=2, then=F("o2o_rel__integer") + 3),
                    default="o2o_rel__integer",
                )
            ).order_by("pk"),
            [(1, 2), (2, 5), (3, 3), (2, 5), (3, 3), (3, 3), (4, 1)],
            transform=attrgetter("integer", "join_test"),
        )

    def test_annotate_with_in_clause(self):
        fk_rels = FKCaseTestModel.objects.filter(integer__in=[5])
        self.assertQuerySetEqual(
            CaseTestModel.objects.only("pk", "integer")
            .annotate(
                in_test=Sum(
                    Case(
                        When(fk_rel__in=fk_rels, then=F("fk_rel__integer")),
                        default=Value(0),
                    )
                )
            )
            .order_by("pk"),
            [(1, 0), (2, 0), (3, 0), (2, 0), (3, 0), (3, 0), (4, 5)],
            transform=attrgetter("integer", "in_test"),
        )

    def test_annotate_with_join_in_condition(self):
        self.assertQuerySetEqual(
            CaseTestModel.objects.annotate(
                join_test=Case(
                    When(integer2=F("o2o_rel__integer"), then=Value("equal")),
                    When(integer2=F("o2o_rel__integer") + 1, then=Value("+1")),
                    default=Value("other"),
                )
            ).order_by("pk"),
            [
                (1, "equal"),
                (2, "+1"),
                (3, "+1"),
                (2, "equal"),
                (3, "+1"),
                (3, "equal"),
                (4, "other"),
            ],
            transform=attrgetter("integer", "join_test"),
        )

    def test_annotate_with_join_in_predicate(self):
        self.assertQuerySetEqual(
            CaseTestModel.objects.annotate(
                join_test=Case(
                    When(o2o_rel__integer=1, then=Value("one")),
                    When(o2o_rel__integer=2, then=Value("two")),
                    When(o2o_rel__integer=3, then=Value("three")),
                    default=Value("other"),
                )
            ).order_by("pk"),
            [
                (1, "one"),
                (2, "two"),
                (3, "three"),
                (2, "two"),
                (3, "three"),
                (3, "three"),
                (4, "one"),
            ],
            transform=attrgetter("integer", "join_test"),
        )

    def test_annotate_with_annotation_in_value(self):
        self.assertQuerySetEqual(
            CaseTestModel.objects.annotate(
                f_plus_1=F("integer") + 1,
                f_plus_3=F("integer") + 3,
            )
            .annotate(
                f_test=Case(
                    When(integer=1, then="f_plus_1"),
                    When(integer=2, then="f_plus_3"),
                    default="integer",
                ),
            )
            .order_by("pk"),
            [(1, 2), (2, 5), (3, 3), (2, 5), (3, 3), (3, 3), (4, 4)],
            transform=attrgetter("integer", "f_test"),
        )

    def test_annotate_with_annotation_in_condition(self):
        self.assertQuerySetEqual(
            CaseTestModel.objects.annotate(
                f_plus_1=F("integer") + 1,
            )
            .annotate(
                f_test=Case(
                    When(integer2=F("integer"), then=Value("equal")),
                    When(integer2=F("f_plus_1"), then=Value("+1")),
                ),
            )
            .order_by("pk"),
            [
                (1, "equal"),
                (2, "+1"),
                (3, "+1"),
                (2, "equal"),
                (3, "+1"),
                (3, "equal"),
                (4, "+1"),
            ],
            transform=attrgetter("integer", "f_test"),
        )

    def test_annotate_with_annotation_in_predicate(self):
        self.assertQuerySetEqual(
            CaseTestModel.objects.annotate(
                f_minus_2=F("integer") - 2,
            )
            .annotate(
                test=Case(
                    When(f_minus_2=-1, then=Value("negative one")),
                    When(f_minus_2=0, then=Value("zero")),
                    When(f_minus_2=1, then=Value("one")),
                    default=Value("other"),
                ),
            )
            .order_by("pk"),
            [
                (1, "negative one"),
                (2, "zero"),
                (3, "one"),
                (2, "zero"),
                (3, "one"),
                (3, "one"),
                (4, "other"),
            ],
            transform=attrgetter("integer", "test"),
        )

    def test_annotate_with_aggregation_in_value(self):
        self.assertQuerySetEqual(
            CaseTestModel.objects.values(*self.group_by_fields)
            .annotate(
                min=Min("fk_rel__integer"),
                max=Max("fk_rel__integer"),
            )
            .annotate(
                test=Case(
                    When(integer=2, then="min"),
                    When(integer=3, then="max"),
                ),
            )
            .order_by("pk"),
            [
                (1, None, 1, 1),
                (2, 2, 2, 3),
                (3, 4, 3, 4),
                (2, 2, 2, 3),
                (3, 4, 3, 4),
                (3, 4, 3, 4),
                (4, None, 5, 5),
            ],
            transform=itemgetter("integer", "test", "min", "max"),
        )

    def test_annotate_with_aggregation_in_condition(self):
        self.assertQuerySetEqual(
            CaseTestModel.objects.values(*self.group_by_fields)
            .annotate(
                min=Min("fk_rel__integer"),
                max=Max("fk_rel__integer"),
            )
            .annotate(
                test=Case(
                    When(integer2=F("min"), then=Value("min")),
                    When(integer2=F("max"), then=Value("max")),
                ),
            )
            .order_by("pk"),
            [
                (1, 1, "min"),
                (2, 3, "max"),
                (3, 4, "max"),
                (2, 2, "min"),
                (3, 4, "max"),
                (3, 3, "min"),
                (4, 5, "min"),
            ],
            transform=itemgetter("integer", "integer2", "test"),
        )

    def test_annotate_with_aggregation_in_predicate(self):
        self.assertQuerySetEqual(
            CaseTestModel.objects.values(*self.group_by_fields)
            .annotate(
                max=Max("fk_rel__integer"),
            )
            .annotate(
                test=Case(
                    When(max=3, then=Value("max = 3")),
                    When(max=4, then=Value("max = 4")),
                    default=Value(""),
                ),
            )
            .order_by("pk"),
            [
                (1, 1, ""),
                (2, 3, "max = 3"),
                (3, 4, "max = 4"),
                (2, 3, "max = 3"),
                (3, 4, "max = 4"),
                (3, 4, "max = 4"),
                (4, 5, ""),
            ],
            transform=itemgetter("integer", "max", "test"),
        )

    def test_annotate_exclude(self):
        self.assertQuerySetEqual(
            CaseTestModel.objects.annotate(
                test=Case(
                    When(integer=1, then=Value("one")),
                    When(integer=2, then=Value("two")),
                    default=Value("other"),
                )
            )
            .exclude(test="other")
            .order_by("pk"),
            [(1, "one"), (2, "two"), (2, "two")],
            transform=attrgetter("integer", "test"),
        )

    def test_annotate_filter_decimal(self):
        obj = CaseTestModel.objects.create(integer=0, decimal=Decimal("1"))
        qs = CaseTestModel.objects.annotate(
            x=Case(When(integer=0, then=F("decimal"))),
            y=Case(When(integer=0, then=Value(Decimal("1")))),
        )
        self.assertSequenceEqual(qs.filter(Q(x=1) & Q(x=Decimal("1"))), [obj])
        self.assertSequenceEqual(qs.filter(Q(y=1) & Q(y=Decimal("1"))), [obj])

    def test_annotate_values_not_in_order_by(self):
        self.assertEqual(
            list(
                CaseTestModel.objects.annotate(
                    test=Case(
                        When(integer=1, then=Value("one")),
                        When(integer=2, then=Value("two")),
                        When(integer=3, then=Value("three")),
                        default=Value("other"),
                    )
                )
                .order_by("test")
                .values_list("integer", flat=True)
            ),
            [1, 4, 3, 3, 3, 2, 2],
        )

    def test_annotate_with_empty_when(self):
        objects = CaseTestModel.objects.annotate(
            selected=Case(
                When(pk__in=[], then=Value("selected")),
                default=Value("not selected"),
            )
        )
        self.assertEqual(len(objects), CaseTestModel.objects.count())
        self.assertTrue(all(obj.selected == "not selected" for obj in objects))

    def test_annotate_with_full_when(self):
        objects = CaseTestModel.objects.annotate(
            selected=Case(
                When(~Q(pk__in=[]), then=Value("selected")),
                default=Value("not selected"),
            )
        )
        self.assertEqual(len(objects), CaseTestModel.objects.count())
        self.assertTrue(all(obj.selected == "selected" for obj in objects))

    def test_combined_expression(self):
        self.assertQuerySetEqual(
            CaseTestModel.objects.annotate(
                test=Case(
                    When(integer=1, then=2),
                    When(integer=2, then=1),
                    default=3,
                )
                + 1,
            ).order_by("pk"),
            [(1, 3), (2, 2), (3, 4), (2, 2), (3, 4), (3, 4), (4, 4)],
            transform=attrgetter("integer", "test"),
        )

    def test_in_subquery(self):
        self.assertQuerySetEqual(
            CaseTestModel.objects.filter(
                pk__in=CaseTestModel.objects.annotate(
                    test=Case(
                        When(integer=F("integer2"), then="pk"),
                        When(integer=4, then="pk"),
                    ),
                ).values("test")
            ).order_by("pk"),
            [(1, 1), (2, 2), (3, 3), (4, 5)],
            transform=attrgetter("integer", "integer2"),
        )

    def test_condition_with_lookups(self):
        qs = CaseTestModel.objects.annotate(
            test=Case(
                When(Q(integer2=1), string="2", then=Value(False)),
                When(Q(integer2=1), string="1", then=Value(True)),
                default=Value(False),
                output_field=BooleanField(),
            ),
        )
        self.assertIs(qs.get(integer=1).test, True)

    def test_case_reuse(self):
        SOME_CASE = Case(
            When(pk=0, then=Value("0")),
            default=Value("1"),
        )
        self.assertQuerySetEqual(
            CaseTestModel.objects.annotate(somecase=SOME_CASE).order_by("pk"),
            CaseTestModel.objects.annotate(somecase=SOME_CASE)
            .order_by("pk")
            .values_list("pk", "somecase"),
            lambda x: (x.pk, x.somecase),
        )

    def test_aggregate(self):
        self.assertEqual(
            CaseTestModel.objects.aggregate(
                one=Sum(
                    Case(
                        When(integer=1, then=1),
                    )
                ),
                two=Sum(
                    Case(
                        When(integer=2, then=1),
                    )
                ),
                three=Sum(
                    Case(
                        When(integer=3, then=1),
                    )
                ),
                four=Sum(
                    Case(
                        When(integer=4, then=1),
                    )
                ),
            ),
            {"one": 1, "two": 2, "three": 3, "four": 1},
        )

    def test_aggregate_with_expression_as_value(self):
        self.assertEqual(
            CaseTestModel.objects.aggregate(
                one=Sum(Case(When(integer=1, then="integer"))),
                two=Sum(Case(When(integer=2, then=F("integer") - 1))),
                three=Sum(Case(When(integer=3, then=F("integer") + 1))),
            ),
            {"one": 1, "two": 2, "three": 12},
        )

    def test_aggregate_with_expression_as_condition(self):
        self.assertEqual(
            CaseTestModel.objects.aggregate(
                equal=Sum(
                    Case(
                        When(integer2=F("integer"), then=1),
                    )
                ),
                plus_one=Sum(
                    Case(
                        When(integer2=F("integer") + 1, then=1),
                    )
                ),
            ),
            {"equal": 3, "plus_one": 4},
        )

    def test_filter(self):
        self.assertQuerySetEqual(
            CaseTestModel.objects.filter(
                integer2=Case(
                    When(integer=2, then=3),
                    When(integer=3, then=4),
                    default=1,
                )
            ).order_by("pk"),
            [(1, 1), (2, 3), (3, 4), (3, 4)],
            transform=attrgetter("integer", "integer2"),
        )

    def test_filter_without_default(self):
        self.assertQuerySetEqual(
            CaseTestModel.objects.filter(
                integer2=Case(
                    When(integer=2, then=3),
                    When(integer=3, then=4),
                )
            ).order_by("pk"),
            [(2, 3), (3, 4), (3, 4)],
            transform=attrgetter("integer", "integer2"),
        )

    def test_filter_with_expression_as_value(self):
        self.assertQuerySetEqual(
            CaseTestModel.objects.filter(
                integer2=Case(
                    When(integer=2, then=F("integer") + 1),
                    When(integer=3, then=F("integer")),
                    default="integer",
                )
            ).order_by("pk"),
            [(1, 1), (2, 3), (3, 3)],
            transform=attrgetter("integer", "integer2"),
        )

    def test_filter_with_expression_as_condition(self):
        self.assertQuerySetEqual(
            CaseTestModel.objects.filter(
                string=Case(
                    When(integer2=F("integer"), then=Value("2")),
                    When(integer2=F("integer") + 1, then=Value("3")),
                )
            ).order_by("pk"),
            [(3, 4, "3"), (2, 2, "2"), (3, 4, "3")],
            transform=attrgetter("integer", "integer2", "string"),
        )

    def test_filter_with_join_in_value(self):
        self.assertQuerySetEqual(
            CaseTestModel.objects.filter(
                integer2=Case(
                    When(integer=2, then=F("o2o_rel__integer") + 1),
                    When(integer=3, then=F("o2o_rel__integer")),
                    default="o2o_rel__integer",
                )
            ).order_by("pk"),
            [(1, 1), (2, 3), (3, 3)],
            transform=attrgetter("integer", "integer2"),
        )

    def test_filter_with_join_in_condition(self):
        self.assertQuerySetEqual(
            CaseTestModel.objects.filter(
                integer=Case(
                    When(integer2=F("o2o_rel__integer") + 1, then=2),
                    When(integer2=F("o2o_rel__integer"), then=3),
                )
            ).order_by("pk"),
            [(2, 3), (3, 3)],
            transform=attrgetter("integer", "integer2"),
        )

    def test_filter_with_join_in_predicate(self):
        self.assertQuerySetEqual(
            CaseTestModel.objects.filter(
                integer2=Case(
                    When(o2o_rel__integer=1, then=1),
                    When(o2o_rel__integer=2, then=3),
                    When(o2o_rel__integer=3, then=4),
                )
            ).order_by("pk"),
            [(1, 1), (2, 3), (3, 4), (3, 4)],
            transform=attrgetter("integer", "integer2"),
        )

    def test_filter_with_annotation_in_value(self):
        self.assertQuerySetEqual(
            CaseTestModel.objects.annotate(
                f=F("integer"),
                f_plus_1=F("integer") + 1,
            )
            .filter(
                integer2=Case(
                    When(integer=2, then="f_plus_1"),
                    When(integer=3, then="f"),
                ),
            )
            .order_by("pk"),
            [(2, 3), (3, 3)],
            transform=attrgetter("integer", "integer2"),
        )

    def test_filter_with_annotation_in_condition(self):
        self.assertQuerySetEqual(
            CaseTestModel.objects.annotate(
                f_plus_1=F("integer") + 1,
            )
            .filter(
                integer=Case(
                    When(integer2=F("integer"), then=2),
                    When(integer2=F("f_plus_1"), then=3),
                ),
            )
            .order_by("pk"),
            [(3, 4), (2, 2), (3, 4)],
            transform=attrgetter("integer", "integer2"),
        )

    def test_filter_with_annotation_in_predicate(self):
        self.assertQuerySetEqual(
            CaseTestModel.objects.annotate(
                f_plus_1=F("integer") + 1,
            )
            .filter(
                integer2=Case(
                    When(f_plus_1=3, then=3),
                    When(f_plus_1=4, then=4),
                    default=1,
                ),
            )
            .order_by("pk"),
            [(1, 1), (2, 3), (3, 4), (3, 4)],
            transform=attrgetter("integer", "integer2"),
        )

    def test_filter_with_aggregation_in_value(self):
        self.assertQuerySetEqual(
            CaseTestModel.objects.values(*self.group_by_fields)
            .annotate(
                min=Min("fk_rel__integer"),
                max=Max("fk_rel__integer"),
            )
            .filter(
                integer2=Case(
                    When(integer=2, then="min"),
                    When(integer=3, then="max"),
                ),
            )
            .order_by("pk"),
            [(3, 4, 3, 4), (2, 2, 2, 3), (3, 4, 3, 4)],
            transform=itemgetter("integer", "integer2", "min", "max"),
        )

    def test_filter_with_aggregation_in_condition(self):
        self.assertQuerySetEqual(
            CaseTestModel.objects.values(*self.group_by_fields)
            .annotate(
                min=Min("fk_rel__integer"),
                max=Max("fk_rel__integer"),
            )
            .filter(
                integer=Case(
                    When(integer2=F("min"), then=2),
                    When(integer2=F("max"), then=3),
                ),
            )
            .order_by("pk"),
            [(3, 4, 3, 4), (2, 2, 2, 3), (3, 4, 3, 4)],
            transform=itemgetter("integer", "integer2", "min", "max"),
        )

    def test_filter_with_aggregation_in_predicate(self):
        self.assertQuerySetEqual(
            CaseTestModel.objects.values(*self.group_by_fields)
            .annotate(
                max=Max("fk_rel__integer"),
            )
            .filter(
                integer=Case(
                    When(max=3, then=2),
                    When(max=4, then=3),
                ),
            )
            .order_by("pk"),
            [(2, 3, 3), (3, 4, 4), (2, 2, 3), (3, 4, 4), (3, 3, 4)],
            transform=itemgetter("integer", "integer2", "max"),
        )

    def test_update(self):
        CaseTestModel.objects.update(
            string=Case(
                When(integer=1, then=Value("one")),
                When(integer=2, then=Value("two")),
                default=Value("other"),
            ),
        )
        self.assertQuerySetEqual(
            CaseTestModel.objects.order_by("pk"),
            [
                (1, "one"),
                (2, "two"),
                (3, "other"),
                (2, "two"),
                (3, "other"),
                (3, "other"),
                (4, "other"),
            ],
            transform=attrgetter("integer", "string"),
        )

    def test_update_without_default(self):
        CaseTestModel.objects.update(
            integer2=Case(
                When(integer=1, then=1),
                When(integer=2, then=2),
            ),
        )
        self.assertQuerySetEqual(
            CaseTestModel.objects.order_by("pk"),
            [(1, 1), (2, 2), (3, None), (2, 2), (3, None), (3, None), (4, None)],
            transform=attrgetter("integer", "integer2"),
        )

    def test_update_with_expression_as_value(self):
        CaseTestModel.objects.update(
            integer=Case(
                When(integer=1, then=F("integer") + 1),
                When(integer=2, then=F("integer") + 3),
                default="integer",
            ),
        )
        self.assertQuerySetEqual(
            CaseTestModel.objects.order_by("pk"),
            [("1", 2), ("2", 5), ("3", 3), ("2", 5), ("3", 3), ("3", 3), ("4", 4)],
            transform=attrgetter("string", "integer"),
        )

    def test_update_with_expression_as_condition(self):
        CaseTestModel.objects.update(
            string=Case(
                When(integer2=F("integer"), then=Value("equal")),
                When(integer2=F("integer") + 1, then=Value("+1")),
            ),
        )
        self.assertQuerySetEqual(
            CaseTestModel.objects.order_by("pk"),
            [
                (1, "equal"),
                (2, "+1"),
                (3, "+1"),
                (2, "equal"),
                (3, "+1"),
                (3, "equal"),
                (4, "+1"),
            ],
            transform=attrgetter("integer", "string"),
        )

    def test_update_with_join_in_condition_raise_field_error(self):
        with self.assertRaisesMessage(
            FieldError, "Joined field references are not permitted in this query"
        ):
            CaseTestModel.objects.update(
                integer=Case(
                    When(integer2=F("o2o_rel__integer") + 1, then=2),
                    When(integer2=F("o2o_rel__integer"), then=3),
                ),
            )

    def test_update_with_join_in_predicate_raise_field_error(self):
        with self.assertRaisesMessage(
            FieldError, "Joined field references are not permitted in this query"
        ):
            CaseTestModel.objects.update(
                string=Case(
                    When(o2o_rel__integer=1, then=Value("one")),
                    When(o2o_rel__integer=2, then=Value("two")),
                    When(o2o_rel__integer=3, then=Value("three")),
                    default=Value("other"),
                ),
            )

    def test_update_big_integer(self):
        CaseTestModel.objects.update(
            big_integer=Case(
                When(integer=1, then=1),
                When(integer=2, then=2),
            ),
        )
        self.assertQuerySetEqual(
            CaseTestModel.objects.order_by("pk"),
            [(1, 1), (2, 2), (3, None), (2, 2), (3, None), (3, None), (4, None)],
            transform=attrgetter("integer", "big_integer"),
        )

    def test_update_binary(self):
        CaseTestModel.objects.update(
            binary=Case(
                When(integer=1, then=b"one"),
                When(integer=2, then=b"two"),
                default=b"",
            ),
        )
        self.assertQuerySetEqual(
            CaseTestModel.objects.order_by("pk"),
            [
                (1, b"one"),
                (2, b"two"),
                (3, b""),
                (2, b"two"),
                (3, b""),
                (3, b""),
                (4, b""),
            ],
            transform=lambda o: (o.integer, bytes(o.binary)),
        )

    def test_update_boolean(self):
        CaseTestModel.objects.update(
            boolean=Case(
                When(integer=1, then=True),
                When(integer=2, then=True),
                default=False,
            ),
        )
        self.assertQuerySetEqual(
            CaseTestModel.objects.order_by("pk"),
            [
                (1, True),
                (2, True),
                (3, False),
                (2, True),
                (3, False),
                (3, False),
                (4, False),
            ],
            transform=attrgetter("integer", "boolean"),
        )

    def test_update_date(self):
        CaseTestModel.objects.update(
            date=Case(
                When(integer=1, then=date(2015, 1, 1)),
                When(integer=2, then=date(2015, 1, 2)),
            ),
        )
        self.assertQuerySetEqual(
            CaseTestModel.objects.order_by("pk"),
            [
                (1, date(2015, 1, 1)),
                (2, date(2015, 1, 2)),
                (3, None),
                (2, date(2015, 1, 2)),
                (3, None),
                (3, None),
                (4, None),
            ],
            transform=attrgetter("integer", "date"),
        )

    def test_update_date_time(self):
        CaseTestModel.objects.update(
            date_time=Case(
                When(integer=1, then=datetime(2015, 1, 1)),
                When(integer=2, then=datetime(2015, 1, 2)),
            ),
        )
        self.assertQuerySetEqual(
            CaseTestModel.objects.order_by("pk"),
            [
                (1, datetime(2015, 1, 1)),
                (2, datetime(2015, 1, 2)),
                (3, None),
                (2, datetime(2015, 1, 2)),
                (3, None),
                (3, None),
                (4, None),
            ],
            transform=attrgetter("integer", "date_time"),
        )

    def test_update_decimal(self):
        CaseTestModel.objects.update(
            decimal=Case(
                When(integer=1, then=Decimal("1.1")),
                When(
                    integer=2, then=Value(Decimal("2.2"), output_field=DecimalField())
                ),
            ),
        )
        self.assertQuerySetEqual(
            CaseTestModel.objects.order_by("pk"),
            [
                (1, Decimal("1.1")),
                (2, Decimal("2.2")),
                (3, None),
                (2, Decimal("2.2")),
                (3, None),
                (3, None),
                (4, None),
            ],
            transform=attrgetter("integer", "decimal"),
        )

    def test_update_duration(self):
        CaseTestModel.objects.update(
            duration=Case(
                When(integer=1, then=timedelta(1)),
                When(integer=2, then=timedelta(2)),
            ),
        )
        self.assertQuerySetEqual(
            CaseTestModel.objects.order_by("pk"),
            [
                (1, timedelta(1)),
                (2, timedelta(2)),
                (3, None),
                (2, timedelta(2)),
                (3, None),
                (3, None),
                (4, None),
            ],
            transform=attrgetter("integer", "duration"),
        )

    def test_update_email(self):
        CaseTestModel.objects.update(
            email=Case(
                When(integer=1, then=Value("1@example.com")),
                When(integer=2, then=Value("2@example.com")),
                default=Value(""),
            ),
        )
        self.assertQuerySetEqual(
            CaseTestModel.objects.order_by("pk"),
            [
                (1, "1@example.com"),
                (2, "2@example.com"),
                (3, ""),
                (2, "2@example.com"),
                (3, ""),
                (3, ""),
                (4, ""),
            ],
            transform=attrgetter("integer", "email"),
        )

    def test_update_file(self):
        CaseTestModel.objects.update(
            file=Case(
                When(integer=1, then=Value("~/1")),
                When(integer=2, then=Value("~/2")),
            ),
        )
        self.assertQuerySetEqual(
            CaseTestModel.objects.order_by("pk"),
            [(1, "~/1"), (2, "~/2"), (3, ""), (2, "~/2"), (3, ""), (3, ""), (4, "")],
            transform=lambda o: (o.integer, str(o.file)),
        )

    def test_update_file_path(self):
        CaseTestModel.objects.update(
            file_path=Case(
                When(integer=1, then=Value("~/1")),
                When(integer=2, then=Value("~/2")),
                default=Value(""),
            ),
        )
        self.assertQuerySetEqual(
            CaseTestModel.objects.order_by("pk"),
            [(1, "~/1"), (2, "~/2"), (3, ""), (2, "~/2"), (3, ""), (3, ""), (4, "")],
            transform=attrgetter("integer", "file_path"),
        )

    def test_update_float(self):
        CaseTestModel.objects.update(
            float=Case(
                When(integer=1, then=1.1),
                When(integer=2, then=2.2),
            ),
        )
        self.assertQuerySetEqual(
            CaseTestModel.objects.order_by("pk"),
            [(1, 1.1), (2, 2.2), (3, None), (2, 2.2), (3, None), (3, None), (4, None)],
            transform=attrgetter("integer", "float"),
        )

    @unittest.skipUnless(Image, "Pillow not installed")
    def test_update_image(self):
        CaseTestModel.objects.update(
            image=Case(
                When(integer=1, then=Value("~/1")),
                When(integer=2, then=Value("~/2")),
            ),
        )
        self.assertQuerySetEqual(
            CaseTestModel.objects.order_by("pk"),
            [(1, "~/1"), (2, "~/2"), (3, ""), (2, "~/2"), (3, ""), (3, ""), (4, "")],
            transform=lambda o: (o.integer, str(o.image)),
        )

    def test_update_generic_ip_address(self):
        CaseTestModel.objects.update(
            generic_ip_address=Case(
                When(integer=1, then=Value("1.1.1.1")),
                When(integer=2, then=Value("2.2.2.2")),
                output_field=GenericIPAddressField(),
            ),
        )
        self.assertQuerySetEqual(
            CaseTestModel.objects.order_by("pk"),
            [
                (1, "1.1.1.1"),
                (2, "2.2.2.2"),
                (3, None),
                (2, "2.2.2.2"),
                (3, None),
                (3, None),
                (4, None),
            ],
            transform=attrgetter("integer", "generic_ip_address"),
        )

    def test_update_null_boolean(self):
        CaseTestModel.objects.update(
            null_boolean=Case(
                When(integer=1, then=True),
                When(integer=2, then=False),
            ),
        )
        self.assertQuerySetEqual(
            CaseTestModel.objects.order_by("pk"),
            [
                (1, True),
                (2, False),
                (3, None),
                (2, False),
                (3, None),
                (3, None),
                (4, None),
            ],
            transform=attrgetter("integer", "null_boolean"),
        )

    def test_update_positive_big_integer(self):
        CaseTestModel.objects.update(
            positive_big_integer=Case(
                When(integer=1, then=1),
                When(integer=2, then=2),
            ),
        )
        self.assertQuerySetEqual(
            CaseTestModel.objects.order_by("pk"),
            [(1, 1), (2, 2), (3, None), (2, 2), (3, None), (3, None), (4, None)],
            transform=attrgetter("integer", "positive_big_integer"),
        )

    def test_update_positive_integer(self):
        CaseTestModel.objects.update(
            positive_integer=Case(
                When(integer=1, then=1),
                When(integer=2, then=2),
            ),
        )
        self.assertQuerySetEqual(
            CaseTestModel.objects.order_by("pk"),
            [(1, 1), (2, 2), (3, None), (2, 2), (3, None), (3, None), (4, None)],
            transform=attrgetter("integer", "positive_integer"),
        )

    def test_update_positive_small_integer(self):
        CaseTestModel.objects.update(
            positive_small_integer=Case(
                When(integer=1, then=1),
                When(integer=2, then=2),
            ),
        )
        self.assertQuerySetEqual(
            CaseTestModel.objects.order_by("pk"),
            [(1, 1), (2, 2), (3, None), (2, 2), (3, None), (3, None), (4, None)],
            transform=attrgetter("integer", "positive_small_integer"),
        )

    def test_update_slug(self):
        CaseTestModel.objects.update(
            slug=Case(
                When(integer=1, then=Value("1")),
                When(integer=2, then=Value("2")),
                default=Value(""),
            ),
        )
        self.assertQuerySetEqual(
            CaseTestModel.objects.order_by("pk"),
            [(1, "1"), (2, "2"), (3, ""), (2, "2"), (3, ""), (3, ""), (4, "")],
            transform=attrgetter("integer", "slug"),
        )

    def test_update_small_integer(self):
        CaseTestModel.objects.update(
            small_integer=Case(
                When(integer=1, then=1),
                When(integer=2, then=2),
            ),
        )
        self.assertQuerySetEqual(
            CaseTestModel.objects.order_by("pk"),
            [(1, 1), (2, 2), (3, None), (2, 2), (3, None), (3, None), (4, None)],
            transform=attrgetter("integer", "small_integer"),
        )

    def test_update_string(self):
        CaseTestModel.objects.filter(string__in=["1", "2"]).update(
            string=Case(
                When(integer=1, then=Value("1")),
                When(integer=2, then=Value("2")),
            ),
        )
        self.assertQuerySetEqual(
            CaseTestModel.objects.filter(string__in=["1", "2"]).order_by("pk"),
            [(1, "1"), (2, "2"), (2, "2")],
            transform=attrgetter("integer", "string"),
        )

    def test_update_text(self):
        CaseTestModel.objects.update(
            text=Case(
                When(integer=1, then=Value("1")),
                When(integer=2, then=Value("2")),
                default=Value(""),
            ),
        )
        self.assertQuerySetEqual(
            CaseTestModel.objects.order_by("pk"),
            [(1, "1"), (2, "2"), (3, ""), (2, "2"), (3, ""), (3, ""), (4, "")],
            transform=attrgetter("integer", "text"),
        )

    def test_update_time(self):
        CaseTestModel.objects.update(
            time=Case(
                When(integer=1, then=time(1)),
                When(integer=2, then=time(2)),
            ),
        )
        self.assertQuerySetEqual(
            CaseTestModel.objects.order_by("pk"),
            [
                (1, time(1)),
                (2, time(2)),
                (3, None),
                (2, time(2)),
                (3, None),
                (3, None),
                (4, None),
            ],
            transform=attrgetter("integer", "time"),
        )

    def test_update_url(self):
        CaseTestModel.objects.update(
            url=Case(
                When(integer=1, then=Value("http://1.example.com/")),
                When(integer=2, then=Value("http://2.example.com/")),
                default=Value(""),
            ),
        )
        self.assertQuerySetEqual(
            CaseTestModel.objects.order_by("pk"),
            [
                (1, "http://1.example.com/"),
                (2, "http://2.example.com/"),
                (3, ""),
                (2, "http://2.example.com/"),
                (3, ""),
                (3, ""),
                (4, ""),
            ],
            transform=attrgetter("integer", "url"),
        )

    def test_update_uuid(self):
        CaseTestModel.objects.update(
            uuid=Case(
                When(integer=1, then=UUID("11111111111111111111111111111111")),
                When(integer=2, then=UUID("22222222222222222222222222222222")),
            ),
        )
        self.assertQuerySetEqual(
            CaseTestModel.objects.order_by("pk"),
            [
                (1, UUID("11111111111111111111111111111111")),
                (2, UUID("22222222222222222222222222222222")),
                (3, None),
                (2, UUID("22222222222222222222222222222222")),
                (3, None),
                (3, None),
                (4, None),
            ],
            transform=attrgetter("integer", "uuid"),
        )

    def test_update_fk(self):
        obj1, obj2 = CaseTestModel.objects.all()[:2]

        CaseTestModel.objects.update(
            fk=Case(
                When(integer=1, then=obj1.pk),
                When(integer=2, then=obj2.pk),
            ),
        )
        self.assertQuerySetEqual(
            CaseTestModel.objects.order_by("pk"),
            [
                (1, obj1.pk),
                (2, obj2.pk),
                (3, None),
                (2, obj2.pk),
                (3, None),
                (3, None),
                (4, None),
            ],
            transform=attrgetter("integer", "fk_id"),
        )

    def test_lookup_in_condition(self):
        self.assertQuerySetEqual(
            CaseTestModel.objects.annotate(
                test=Case(
                    When(integer__lt=2, then=Value("less than 2")),
                    When(integer__gt=2, then=Value("greater than 2")),
                    default=Value("equal to 2"),
                ),
            ).order_by("pk"),
            [
                (1, "less than 2"),
                (2, "equal to 2"),
                (3, "greater than 2"),
                (2, "equal to 2"),
                (3, "greater than 2"),
                (3, "greater than 2"),
                (4, "greater than 2"),
            ],
            transform=attrgetter("integer", "test"),
        )

    def test_lookup_different_fields(self):
        self.assertQuerySetEqual(
            CaseTestModel.objects.annotate(
                test=Case(
                    When(integer=2, integer2=3, then=Value("when")),
                    default=Value("default"),
                ),
            ).order_by("pk"),
            [
                (1, 1, "default"),
                (2, 3, "when"),
                (3, 4, "default"),
                (2, 2, "default"),
                (3, 4, "default"),
                (3, 3, "default"),
                (4, 5, "default"),
            ],
            transform=attrgetter("integer", "integer2", "test"),
        )

    def test_combined_q_object(self):
        self.assertQuerySetEqual(
            CaseTestModel.objects.annotate(
                test=Case(
                    When(Q(integer=2) | Q(integer2=3), then=Value("when")),
                    default=Value("default"),
                ),
            ).order_by("pk"),
            [
                (1, 1, "default"),
                (2, 3, "when"),
                (3, 4, "default"),
                (2, 2, "when"),
                (3, 4, "default"),
                (3, 3, "when"),
                (4, 5, "default"),
            ],
            transform=attrgetter("integer", "integer2", "test"),
        )

    def test_order_by_conditional_implicit(self):
        self.assertQuerySetEqual(
            CaseTestModel.objects.filter(integer__lte=2)
            .annotate(
                test=Case(
                    When(integer=1, then=2),
                    When(integer=2, then=1),
                    default=3,
                )
            )
            .order_by("test", "pk"),
            [(2, 1), (2, 1), (1, 2)],
            transform=attrgetter("integer", "test"),
        )

    def test_order_by_conditional_explicit(self):
        self.assertQuerySetEqual(
            CaseTestModel.objects.filter(integer__lte=2)
            .annotate(
                test=Case(
                    When(integer=1, then=2),
                    When(integer=2, then=1),
                    default=3,
                )
            )
            .order_by(F("test").asc(), "pk"),
            [(2, 1), (2, 1), (1, 2)],
            transform=attrgetter("integer", "test"),
        )

    def test_join_promotion(self):
        o = CaseTestModel.objects.create(integer=1, integer2=1, string="1")
        # Testing that:
        # 1. There isn't any object on the remote side of the fk_rel
        #    relation. If the query used inner joins, then the join to fk_rel
        #    would remove o from the results. So, in effect we are testing that
        #    we are promoting the fk_rel join to a left outer join here.
        # 2. The default value of 3 is generated for the case expression.
        self.assertQuerySetEqual(
            CaseTestModel.objects.filter(pk=o.pk).annotate(
                foo=Case(
                    When(fk_rel__pk=1, then=2),
                    default=3,
                ),
            ),
            [(o, 3)],
            lambda x: (x, x.foo),
        )
        # Now 2 should be generated, as the fk_rel is null.
        self.assertQuerySetEqual(
            CaseTestModel.objects.filter(pk=o.pk).annotate(
                foo=Case(
                    When(fk_rel__isnull=True, then=2),
                    default=3,
                ),
            ),
            [(o, 2)],
            lambda x: (x, x.foo),
        )

    def test_join_promotion_multiple_annotations(self):
        o = CaseTestModel.objects.create(integer=1, integer2=1, string="1")
        # Testing that:
        # 1. There isn't any object on the remote side of the fk_rel
        #    relation. If the query used inner joins, then the join to fk_rel
        #    would remove o from the results. So, in effect we are testing that
        #    we are promoting the fk_rel join to a left outer join here.
        # 2. The default value of 3 is generated for the case expression.
        self.assertQuerySetEqual(
            CaseTestModel.objects.filter(pk=o.pk).annotate(
                foo=Case(
                    When(fk_rel__pk=1, then=2),
                    default=3,
                ),
                bar=Case(
                    When(fk_rel__pk=1, then=4),
                    default=5,
                ),
            ),
            [(o, 3, 5)],
            lambda x: (x, x.foo, x.bar),
        )
        # Now 2 should be generated, as the fk_rel is null.
        self.assertQuerySetEqual(
            CaseTestModel.objects.filter(pk=o.pk).annotate(
                foo=Case(
                    When(fk_rel__isnull=True, then=2),
                    default=3,
                ),
                bar=Case(
                    When(fk_rel__isnull=True, then=4),
                    default=5,
                ),
            ),
            [(o, 2, 4)],
            lambda x: (x, x.foo, x.bar),
        )

    def test_m2m_exclude(self):
        CaseTestModel.objects.create(integer=10, integer2=1, string="1")
        qs = (
            CaseTestModel.objects.values_list("id", "integer")
            .annotate(
                cnt=Sum(
                    Case(When(~Q(fk_rel__integer=1), then=1), default=2),
                ),
            )
            .order_by("integer")
        )
        # The first o has 2 as its fk_rel__integer=1, thus it hits the
        # default=2 case. The other ones have 2 as the result as they have 2
        # fk_rel objects, except for integer=4 and integer=10 (created above).
        # The integer=4 case has one integer, thus the result is 1, and
        # integer=10 doesn't have any and this too generates 1 (instead of 0)
        # as ~Q() also matches nulls.
        self.assertQuerySetEqual(
            qs,
            [(1, 2), (2, 2), (2, 2), (3, 2), (3, 2), (3, 2), (4, 1), (10, 1)],
            lambda x: x[1:],
        )

    def test_m2m_reuse(self):
        CaseTestModel.objects.create(integer=10, integer2=1, string="1")
        # Need to use values before annotate so that Oracle will not group
        # by fields it isn't capable of grouping by.
        qs = (
            CaseTestModel.objects.values_list("id", "integer")
            .annotate(
                cnt=Sum(
                    Case(When(~Q(fk_rel__integer=1), then=1), default=2),
                ),
            )
            .annotate(
                cnt2=Sum(
                    Case(When(~Q(fk_rel__integer=1), then=1), default=2),
                ),
            )
            .order_by("integer")
        )
        self.assertEqual(str(qs.query).count(" JOIN "), 1)
        self.assertQuerySetEqual(
            qs,
            [
                (1, 2, 2),
                (2, 2, 2),
                (2, 2, 2),
                (3, 2, 2),
                (3, 2, 2),
                (3, 2, 2),
                (4, 1, 1),
                (10, 1, 1),
            ],
            lambda x: x[1:],
        )

    def test_aggregation_empty_cases(self):
        tests = [
            # Empty cases and default.
            (Case(output_field=IntegerField()), None),
            # Empty cases and a constant default.
            (Case(default=Value("empty")), "empty"),
            # Empty cases and column in the default.
            (Case(default=F("url")), ""),
        ]
        for case, value in tests:
            with self.subTest(case=case):
                self.assertQuerySetEqual(
                    CaseTestModel.objects.values("string")
                    .annotate(
                        case=case,
                        integer_sum=Sum("integer"),
                    )
                    .order_by("string"),
                    [
                        ("1", value, 1),
                        ("2", value, 4),
                        ("3", value, 9),
                        ("4", value, 4),
                    ],
                    transform=itemgetter("string", "case", "integer_sum"),
                )


class NegatedQExpressionTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.parents = [
            CaseTestModel.objects.create(integer=value) for value in range(1, 5)
        ]
        for parent, children in zip(cls.parents, ((1, 2), (1,), (2, 3), ())):
            for value in children:
                FKCaseTestModel.objects.create(fk=parent, integer=value)
                M2MCaseTestModel.objects.create(integer=value).related.add(parent)

    def test_negated_reverse_relation_condition(self):
        expression = Case(When(~Q(fk_rel__integer=1), then=True), default=False)
        queryset = CaseTestModel.objects.annotate(flag=expression).order_by("integer")
        self.assertSequenceEqual(
            queryset.values_list("integer", "flag"),
            [(1, False), (2, False), (3, True), (4, True)],
        )
        self.assertSequenceEqual(
            queryset.filter(flag=True).values_list("integer", flat=True), [3, 4]
        )

    def test_negated_q_annotation(self):
        queryset = CaseTestModel.objects.annotate(flag=~Q(fk_rel__integer=1))
        self.assertSequenceEqual(
            queryset.order_by("integer").values_list("integer", "flag"),
            [(1, False), (2, False), (3, True), (4, True)],
        )

    def test_negated_condition_rhs_annotation_expression(self):
        for lookup, rhs in (
            ("fk_rel__integer", F("target")),
            ("fk_rel__integer", F("target") + 0),
            ("fk_rel__integer", Abs(F("target"))),
            ("fk_rel__integer__in", [F("target")]),
            ("fk_rel__integer__range", (F("target"), F("target") + 0)),
            (
                "fk_rel__integer",
                Subquery(
                    FKCaseTestModel.objects.filter(integer=OuterRef("target")).values(
                        "integer"
                    )[:1]
                ),
            ),
        ):
            with self.subTest(lookup=lookup, rhs=rhs):
                queryset = CaseTestModel.objects.annotate(
                    target=F("integer") + 1,
                ).annotate(flag=~Q(**{lookup: rhs}))
                self.assertSequenceEqual(
                    queryset.order_by("integer").values_list("integer", "flag"),
                    [(1, False), (2, True), (3, True), (4, True)],
                )

    def test_composed_conditions(self):
        cases = [
            (~(Q(fk_rel__integer=1) | Q(integer=3)), [False, False, False, True]),
            (~(Q(fk_rel__integer=1) & Q(integer=1)), [False, True, True, True]),
            (~Q(fk_rel__integer=F("integer")), [False, True, False, True]),
            (~Q(fk_rel__fk__integer=1), [False, True, True, True]),
        ]
        for condition, expected in cases:
            with self.subTest(condition=condition):
                queryset = CaseTestModel.objects.annotate(
                    flag=Case(When(condition, then=True), default=False)
                )
                self.assertSequenceEqual(
                    queryset.order_by("integer").values_list("flag", flat=True),
                    expected,
                )

    def test_negated_condition_preserves_outer_reference_scope(self):
        for lookup, rhs in (
            ("fk_rel__integer", OuterRef("integer")),
            ("fk_rel__integer", OuterRef("integer") + 0),
            ("fk_rel__integer__in", [OuterRef("integer")]),
        ):
            with self.subTest(lookup=lookup, rhs=rhs):
                inner = (
                    CaseTestModel.objects.filter(integer=OuterRef("integer") + 1)
                    .annotate(flag=~Q(**{lookup: rhs}))
                    .values("flag")[:1]
                )
                queryset = CaseTestModel.objects.annotate(flag=Subquery(inner))
                self.assertSequenceEqual(
                    queryset.order_by("integer").values_list("integer", "flag"),
                    [(1, False), (2, False), (3, True), (4, None)],
                )

    def test_negated_condition_prepares_queryset_rhs(self):
        cases = (
            (
                "fk_rel__in",
                FKCaseTestModel.objects.filter(integer=1),
                [False, False, True, True],
            ),
            (
                "fk_rel",
                FKCaseTestModel.objects.filter(fk=self.parents[0], integer=1)[:1],
                [False, True, True, True],
            ),
        )
        for lookup, rhs, expected in cases:
            with self.subTest(lookup=lookup):
                queryset = CaseTestModel.objects.annotate(
                    flag=~Q(**{lookup: rhs}),
                )
                self.assertSequenceEqual(
                    queryset.order_by("integer").values_list("flag", flat=True),
                    expected,
                )

    def test_negated_condition_validates_queryset_rhs(self):
        cases = (
            (
                "fk_rel",
                FKCaseTestModel.objects.all(),
                "must be limited to one result",
            ),
            (
                "fk_rel__integer__in",
                FKCaseTestModel.objects.values("integer", "fk"),
                "must have 1 selected fields",
            ),
            (
                "fk_rel__in",
                CaseTestModel.objects.all(),
                "Cannot use QuerySet",
            ),
        )
        for lookup, rhs, message in cases:
            with self.subTest(lookup=lookup):
                with self.assertRaisesMessage(ValueError, message):
                    CaseTestModel.objects.annotate(flag=~Q(**{lookup: rhs}))

    def test_negated_condition_with_aggregate_rhs(self):
        parent = CaseTestModel.objects.create(integer=5)
        FKCaseTestModel.objects.create(fk=parent, integer=2)
        for lookup, rhs in (
            ("fk_rel__integer", F("total")),
            ("fk_rel__integer", F("total") + 0),
            ("fk_rel__integer", Abs(F("total"))),
            ("fk_rel__integer", Count("fk_rel")),
            ("fk_rel__integer__in", [F("total")]),
            ("fk_rel__integer__range", (F("total"), F("total") + 0)),
        ):
            condition = ~Q(**{lookup: rhs})
            for expression in (
                condition,
                Case(When(condition, then=True), default=False),
            ):
                with self.subTest(lookup=lookup, rhs=rhs, expression=expression):
                    queryset = (
                        CaseTestModel.objects.filter(pk=parent.pk)
                        .annotate(total=Count("pk"))
                        .annotate(flag=expression)
                    )
                    self.assertSequenceEqual(
                        queryset.values_list("integer", "total", "flag"),
                        [(5, 1, True)],
                    )
        queryset = (
            CaseTestModel.objects.filter(integer__lte=4)
            .annotate(total=Count("fk_rel"))
            .annotate(flag=~Q(fk_rel__integer=F("total")))
        )
        self.assertSequenceEqual(
            queryset.order_by("integer", "flag").values_list(
                "integer", "total", "flag"
            ),
            [
                (1, 1, False),
                (1, 1, True),
                (2, 1, False),
                (3, 1, True),
                (3, 1, True),
                (4, 0, True),
            ],
        )

    def test_negated_condition_with_outer_aggregate_subquery_rhs(self):
        inner = (
            CaseTestModel.objects.filter(pk=OuterRef("pk"))
            .annotate(value=OuterRef("total"))
            .values("value")[:1]
        )
        for aggregate in (Count("fk_rel"), Count("*"), Count(Value(1))):
            with self.subTest(aggregate=aggregate):
                queryset = (
                    CaseTestModel.objects.filter(pk=self.parents[0].pk)
                    .annotate(total=aggregate)
                    .annotate(flag=~Q(fk_rel__integer=Subquery(inner)))
                )
                self.assertSequenceEqual(
                    queryset.order_by("flag").values_list("total", "flag"),
                    [(1, False), (1, True)],
                )

    def test_negated_sibling_with_unresolved_nested_outer_reference(self):
        for depth in (2, 4):
            with self.subTest(depth=depth):
                reference = "integer"
                for _ in range(depth):
                    reference = OuterRef(reference)
                inner = CaseTestModel.objects.annotate(value=reference).values("value")[
                    :1
                ]
                nested = (
                    CaseTestModel.objects.order_by("pk")
                    .annotate(flag=Q(integer=Subquery(inner)) & ~Q(fk_rel__integer=99))
                    .values("flag")[:1]
                )
                for _ in range(depth - 2):
                    nested = CaseTestModel.objects.annotate(
                        flag=Subquery(nested)
                    ).values("flag")[:1]
                queryset = CaseTestModel.objects.annotate(flag=Subquery(nested))
                self.assertSequenceEqual(
                    queryset.order_by("integer").values_list("integer", "flag"),
                    [(1, True), (2, False), (3, False), (4, False)],
                )

    def test_negated_condition_with_nested_outer_aggregate_rhs(self):
        direct = (
            CaseTestModel.objects.filter(pk=OuterRef("pk"))
            .annotate(value=OuterRef("total"))
            .values("value")[:1]
        )
        deepest = (
            CaseTestModel.objects.filter(pk=OuterRef("pk"))
            .annotate(value=OuterRef(OuterRef("total")))
            .values("value")[:1]
        )
        nested = (
            CaseTestModel.objects.filter(pk=OuterRef("pk"))
            .annotate(value=Subquery(deepest))
            .values("value")[:1]
        )
        copied = (
            CaseTestModel.objects.filter(pk=OuterRef("pk"))
            .annotate(value=OuterRef("copied"))
            .values("value")[:1]
        )
        for rhs in (Subquery(direct) + 0, Subquery(nested), Subquery(copied)):
            for wrap in (False, True):
                with self.subTest(rhs=rhs, wrap=wrap):
                    condition = ~Q(fk_rel__integer=rhs)
                    queryset = (
                        CaseTestModel.objects.filter(pk=self.parents[0].pk)
                        .annotate(total=Count("*"), copied=Subquery(direct))
                        .annotate(
                            flag=(
                                Case(When(condition, then=True), default=False)
                                if wrap
                                else condition
                            )
                        )
                    )
                    self.assertSequenceEqual(
                        queryset.order_by("flag").values_list("total", "flag"),
                        [(1, False), (1, True)],
                    )

    def test_negated_condition_with_local_aggregate_rhs(self):
        for aggregate in (
            Count("pk"),
            Count(F("pk") + OuterRef("pk")),
            Count(Value(1)),
        ):
            with self.subTest(aggregate=aggregate):
                inner = (
                    CaseTestModel.objects.filter(pk=OuterRef("pk"))
                    .annotate(value=aggregate)
                    .values("value")[:1]
                )
                queryset = (
                    CaseTestModel.objects.filter(pk=self.parents[0].pk)
                    .annotate(total=Count("fk_rel"))
                    .annotate(flag=~Q(fk_rel__integer=Subquery(inner)))
                )
                self.assertSequenceEqual(
                    queryset.values_list("total", "flag"), [(2, False)]
                )

    def test_negated_condition_ignores_unused_outer_aggregate(self):
        inner = (
            CaseTestModel.objects.filter(pk=OuterRef("pk"))
            .alias(unused=OuterRef("total"))
            .values("integer")[:1]
        )
        queryset = (
            CaseTestModel.objects.filter(pk=self.parents[0].pk)
            .annotate(total=Count(Value(1)), related=Count("fk_rel"))
            .annotate(flag=~Q(fk_rel__integer=Subquery(inner)))
        )
        self.assertSequenceEqual(queryset.values_list("total", "flag"), [(2, False)])

    def test_negated_condition_with_outer_column_aggregate_subquery_rhs(self):
        inner = (
            CaseTestModel.objects.filter(pk=OuterRef("pk"))
            .annotate(value=Count(OuterRef("pk")))
            .values("value")[:1]
        )
        queryset = (
            CaseTestModel.objects.filter(pk=self.parents[0].pk)
            .annotate(total=Count("fk_rel"))
            .annotate(flag=~Q(fk_rel__integer=Subquery(inner)))
        )
        self.assertSequenceEqual(
            queryset.order_by("flag").values_list("total", "flag"),
            [(1, False), (1, True)],
        )

    def test_negated_condition_with_nonfilterable_rhs(self):
        class NonfilterableValue(Value):
            filterable = False

        condition = ~Q(fk_rel__integer=NonfilterableValue(2))
        for expression in (
            condition,
            Case(When(condition, then=True), default=False),
        ):
            with self.subTest(expression=expression):
                queryset = CaseTestModel.objects.annotate(flag=expression)
                self.assertSequenceEqual(
                    queryset.order_by("integer").values_list("integer", "flag"),
                    [(1, False), (2, True), (3, False), (4, True)],
                )
        queryset = (
            CaseTestModel.objects.filter(pk=self.parents[0].pk)
            .annotate(value=F("fk_rel__integer"))
            .annotate(flag=Q(value=1) & condition)
        )
        self.assertSequenceEqual(
            queryset.order_by("value").values_list("value", "flag"),
            [(1, True), (2, False)],
        )
        msg = "NonfilterableValue is disallowed in the filter clause."
        with self.assertRaisesMessage(NotSupportedError, msg):
            CaseTestModel.objects.filter(condition)

    def test_negated_condition_with_aggregate_subquery_rhs(self):
        inner = (
            FKCaseTestModel.objects.filter(fk=OuterRef("pk"))
            .order_by()
            .values("fk")
            .annotate(total=Count("pk"))
            .values("total")[:1]
        )
        queryset = CaseTestModel.objects.annotate(
            flag=~Q(fk_rel__integer=Subquery(inner)),
        )
        self.assertSequenceEqual(
            queryset.order_by("integer").values_list("integer", "flag"),
            [(1, False), (2, False), (3, False), (4, True)],
        )

    def test_aggregate_comparison_before_negated_sibling(self):
        parent = CaseTestModel.objects.create(integer=2)
        for _ in range(2):
            FKCaseTestModel.objects.create(fk=parent, integer=2)
        for condition in (
            Q(integer__lte=Count("fk_rel")),
            Q(integer__lte=Count("fk_rel") + 0),
            Q(integer__lte=Count("fk_rel", filter=~Q(fk_rel__integer=3))),
            Q(Exact(F("integer"), Count("fk_rel"))),
            Q(Case(When(integer__lte=Count("fk_rel"), then=True), default=False)),
            Q(fk_rel__integer__lte=Count("fk_rel")),
            Q(integer__lte=Count("fk_rel") + F("fk_rel__integer") - 2),
            Q(fk_rel__integer=2) & Q(integer__lte=Count("fk_rel")),
        ):
            with self.subTest(condition=condition):
                queryset = CaseTestModel.objects.filter(pk=parent.pk).annotate(
                    flag=condition & ~Q(fk_rel__integer=1),
                )
                self.assertSequenceEqual(
                    queryset.values_list("integer", "flag"), [(2, True)]
                )
        queryset = (
            CaseTestModel.objects.filter(pk=parent.pk)
            .annotate(total=Count("fk_rel"))
            .annotate(flag=Q(integer__lte=F("total")) & ~Q(fk_rel__integer=1))
        )
        self.assertSequenceEqual(
            queryset.values_list("integer", "total", "flag"), [(2, 2, True)]
        )
        for condition, expected in (
            (
                Q(fk_rel__integer=2)
                & ~Q(~Q(fk_rel__integer=2))
                & Q(integer__lte=Count("fk_rel")),
                True,
            ),
            (
                Q(fk_rel__integer=2)
                & Q(integer__lte=Count("fk_rel"))
                & ~Q(~Q(fk_rel__integer=2)),
                True,
            ),
            (
                Q(fk_rel__integer=2)
                & ~Q(~Q(fk_rel__integer=1))
                & Q(integer__lte=Count("fk_rel")),
                False,
            ),
            (
                Q(fk_rel__integer=2)
                & ~(Q(integer__lte=Count("fk_rel")) & ~Q(fk_rel__integer=2)),
                True,
            ),
        ):
            with self.subTest(condition=condition):
                queryset = CaseTestModel.objects.filter(pk=parent.pk).annotate(
                    flag=condition,
                )
                self.assertSequenceEqual(
                    queryset.values_list("integer", "flag"), [(2, expected)]
                )

    def test_negated_sibling_null_lookup_preparation(self):
        for integer, value in ((100, None), (101, 1), (102, 2)):
            parent = CaseTestModel.objects.create(integer=integer)
            CaseTestModel.objects.create(integer=10, integer2=value, fk=parent)
        CaseTestModel.objects.create(integer=103)
        for lookup, rhs in (
            ("casetestmodel__integer2", None),
            ("casetestmodel__integer2__exact", None),
            ("casetestmodel__integer2__iexact", None),
            ("casetestmodel__integer2__isnull", True),
        ):
            with self.subTest(lookup=lookup):
                condition = Q(casetestmodel__integer=10) & ~Q(**{lookup: rhs})
                queryset = CaseTestModel.objects.filter(integer__gte=100).annotate(
                    flag=condition,
                )
                self.assertSequenceEqual(
                    queryset.order_by("integer").values_list("integer", "flag"),
                    [(100, False), (101, True), (102, True), (103, False)],
                )

    def test_negated_condition_iterable_expression_rhs(self):
        class SequenceOnly:
            def __init__(self, values):
                self.values = values

            def __getitem__(self, index):
                return self.values[index]

        parent = CaseTestModel.objects.create(integer=2)
        for _ in range(2):
            FKCaseTestModel.objects.create(fk=parent, integer=2)
        factories = (
            list,
            tuple,
            set,
            frozenset,
            iter,
            lambda values: (value for value in values),
            lambda values: map(lambda value: value, values),
            dict.fromkeys,
            SequenceOnly,
        )
        for rhs, expected in (
            (Count("fk_rel"), False),
            (F("total"), False),
            (F("target"), True),
        ):
            for factory in factories:
                with self.subTest(rhs=rhs, factory=factory):
                    queryset = (
                        CaseTestModel.objects.filter(pk=parent.pk)
                        .annotate(total=Count("fk_rel"), target=F("integer") + 1)
                        .annotate(flag=~Q(fk_rel__integer__in=factory([rhs])))
                    )
                    self.assertSequenceEqual(
                        queryset.values_list("integer", "total", "flag"),
                        [(2, 2, expected)],
                    )
        queryset = CaseTestModel.objects.filter(pk=parent.pk).annotate(
            flag=~Q(fk_rel__integer__range=iter([Count("fk_rel"), Count("fk_rel")])),
        )
        self.assertSequenceEqual(queryset.values_list("integer", "flag"), [(2, False)])
        queryset = CaseTestModel.objects.filter(pk=parent.pk).annotate(
            flag=~Q(fk_rel__integer__in=iter([])),
        )
        self.assertSequenceEqual(queryset.values_list("integer", "flag"), [(2, True)])

    def test_negated_sibling_with_another_multivalued_path(self):
        queryset = CaseTestModel.objects.annotate(
            flag=Q(fk_rel__integer=2) & ~Q(fk_rel__fk__m2m_rel__integer=1),
        )
        self.assertSequenceEqual(
            queryset.filter(flag=True)
            .order_by("integer")
            .values_list("integer", flat=True),
            [3],
        )

    def test_negated_sibling_with_annotation_columns(self):
        parent = CaseTestModel.objects.create(integer=100)
        for value in (1, 2):
            FKCaseTestModel.objects.create(fk=parent, integer=value)
        for condition in (
            Q(value=2),
            Q(wrapped=2),
            Q(Exact(F("value"), Value(2))),
            Q(Exact(Value(2), F("value"))),
            Q(integer=F("value") + 98),
            Q(integer__in=[F("value") + 98]),
            Q(integer__range=(F("value") + 98, F("value") + 98)),
        ):
            with self.subTest(condition=condition):
                queryset = (
                    CaseTestModel.objects.filter(pk=parent.pk)
                    .annotate(value=F("fk_rel__integer"), wrapped=Abs(F("value")))
                    .annotate(flag=condition & ~Q(fk_rel__integer=1))
                    .order_by("value")
                )
                self.assertSequenceEqual(
                    queryset.values_list("value", "flag"), [(1, False), (2, True)]
                )
        for integer in (10, 20):
            child = CaseTestModel.objects.create(integer=integer, fk=parent)
            FKCaseTestModel.objects.create(fk=child, integer=3)
        queryset = (
            CaseTestModel.objects.filter(pk=parent.pk)
            .annotate(value=F("casetestmodel__fk_rel__integer"))
            .annotate(flag=Q(value=3) & ~Q(casetestmodel__integer=20))
            .order_by("casetestmodel__integer")
        )
        self.assertSequenceEqual(
            queryset.values_list("casetestmodel__integer", "flag"),
            [(10, True), (20, False)],
        )

    def test_negated_sibling_with_subquery_annotation_columns(self):
        parent = CaseTestModel.objects.create(integer=100)
        for value in (1, 2):
            FKCaseTestModel.objects.create(fk=parent, integer=value)
        inner = (
            CaseTestModel.objects.filter(pk=OuterRef("pk"))
            .annotate(copied=OuterRef("value"))
            .values("copied")
        )
        nested = (
            CaseTestModel.objects.filter(pk=OuterRef(OuterRef("pk")))
            .annotate(copied=OuterRef(OuterRef("value")))
            .values("copied")
        )
        middle = (
            CaseTestModel.objects.filter(pk=OuterRef("pk"))
            .annotate(copied=Subquery(nested[:1]))
            .values("copied")
        )
        empty = (
            CaseTestModel.objects.filter(pk=0)
            .annotate(copied=Value(0))
            .values("copied")
        )
        combined = empty.union(inner)
        middle_combined = (
            CaseTestModel.objects.filter(pk=OuterRef("pk"))
            .annotate(copied=Subquery(empty.union(nested)[:1]))
            .values("copied")
        )
        for index, subquery in enumerate((inner, middle, combined, middle_combined)):
            for sibling in (
                Q(copied=2),
                Q(wrapped=2),
                Q(Exact(F("copied"), Value(2))),
                Q(integer=F("copied") + 98),
                Q(integer__in=[F("copied") + 98]),
                Q(integer__range=(F("copied") + 98, F("copied") + 98)),
            ):
                condition = sibling & ~Q(fk_rel__integer=1)
                for expression in (
                    condition,
                    Case(When(condition, then=True), default=False),
                ):
                    with self.subTest(subquery=index, expression=expression):
                        queryset = (
                            CaseTestModel.objects.filter(pk=parent.pk)
                            .annotate(
                                value=F("fk_rel__integer"),
                                copied=Subquery(subquery[:1]),
                            )
                            .annotate(wrapped=Abs(F("copied")), flag=expression)
                            .order_by("value")
                        )
                        self.assertSequenceEqual(
                            queryset.values_list("value", "flag"),
                            [(1, False), (2, True)],
                        )

    def test_negated_sibling_does_not_reuse_subquery_internal_columns(self):
        parent = CaseTestModel.objects.create(integer=100)
        for value in (1, 2):
            FKCaseTestModel.objects.create(fk=parent, integer=value)
        children = FKCaseTestModel.objects.filter(fk=OuterRef("pk"))
        for index, inner in enumerate(
            (
                children.order_by("-integer").values("integer")[:1],
                children.values("fk").annotate(total=Count("pk")).values("total"),
                CaseTestModel.objects.filter(pk=OuterRef("pk"))
                .alias(unused=OuterRef("value"))
                .annotate(copied=Value(2))
                .values("copied"),
                CaseTestModel.objects.filter(pk=OuterRef("pk"))
                .annotate(unused=OuterRef("value"), copied=Value(2))
                .values("copied"),
            )
        ):
            condition = Q(copied=2) & ~Q(fk_rel__integer=1)
            for expression in (
                condition,
                Case(When(condition, then=True), default=False),
            ):
                with self.subTest(subquery=index, expression=expression):
                    queryset = (
                        CaseTestModel.objects.filter(pk=parent.pk)
                        .annotate(value=F("fk_rel__integer"), copied=Subquery(inner))
                        .annotate(flag=expression)
                        .order_by("value")
                    )
                    self.assertSequenceEqual(
                        queryset.values_list("value", "flag"), [(1, False), (2, False)]
                    )

    def test_negated_sibling_with_subquery_ordering_annotation(self):
        parent = CaseTestModel.objects.create(integer=100)
        for value in (-1, 1):
            FKCaseTestModel.objects.create(fk=parent, integer=value)
        for name, ordering, extra_ordering, expected in (
            ("key", "key", None, [(-1, 1, False), (1, -1, True)]),
            ("key", F("key").asc(), None, [(-1, 1, False), (1, -1, True)]),
            ("key", (F("key") + 0).asc(), None, [(-1, 1, False), (1, -1, True)]),
            ("key__alias", "key__alias", None, [(-1, 1, False), (1, -1, True)]),
            (
                "key__alias",
                F("key__alias").asc(),
                None,
                [(-1, 1, False), (1, -1, True)],
            ),
            ("key", "integer", ["key"], [(-1, 1, False), (1, -1, True)]),
            ("key", "key", ["integer"], [(-1, -1, False), (1, -1, False)]),
        ):
            inner = (
                FKCaseTestModel.objects.filter(fk=OuterRef("pk"))
                .alias(**{name: OuterRef("value") * F("integer")})
                .order_by(ordering)
                .values("integer")
            )
            if extra_ordering is not None:
                inner = inner.extra(order_by=extra_ordering)
            inner = inner[:1]
            condition = Q(copied=-1) & ~Q(fk_rel__integer=-1)
            for expression in (
                condition,
                Case(When(condition, then=True), default=False),
            ):
                with self.subTest(
                    ordering=ordering,
                    extra_ordering=extra_ordering,
                    expression=expression,
                ):
                    queryset = (
                        CaseTestModel.objects.filter(pk=parent.pk)
                        .annotate(value=F("fk_rel__integer"), copied=Subquery(inner))
                        .annotate(flag=expression)
                        .order_by("value")
                    )
                    self.assertSequenceEqual(
                        queryset.values_list("value", "copied", "flag"),
                        expected,
                    )

    def test_negated_sibling_with_subquery_ordering_alias_starting_minus(self):
        parent = CaseTestModel.objects.create(integer=100)
        for value in (-1, 1):
            FKCaseTestModel.objects.create(fk=parent, integer=value)
        inner = (
            FKCaseTestModel.objects.filter(fk=OuterRef("pk"))
            .alias(**{"-key": OuterRef("value") * F("integer")})
            .order_by("--key")
            .values("integer")[:1]
        )
        condition = Q(copied=1) & ~Q(fk_rel__integer=-1)
        for expression in (
            condition,
            Case(When(condition, then=True), default=False),
        ):
            with self.subTest(expression=expression):
                queryset = (
                    CaseTestModel.objects.filter(pk=parent.pk)
                    .annotate(value=F("fk_rel__integer"), copied=Subquery(inner))
                    .annotate(flag=expression)
                    .order_by("value")
                )
                self.assertSequenceEqual(
                    queryset.values_list("value", "copied", "flag"),
                    [(-1, -1, False), (1, 1, True)],
                )

    @isolate_apps("expressions_case")
    def test_negated_sibling_with_subquery_default_ordering(self):
        class OrderedFKCaseTestModel(FKCaseTestModel):
            class Meta:
                proxy = True
                ordering = ["fk__integer"]

        parent = CaseTestModel.objects.create(integer=100)
        for value in (-1, 1):
            FKCaseTestModel.objects.create(fk=parent, integer=value)
        inner = (
            OrderedFKCaseTestModel.objects.filter(fk=OuterRef("pk"))
            .alias(**{"fk__integer": OuterRef("value") * F("integer")})
            .values("integer")[:1]
        )
        condition = Q(copied=-1) & ~Q(fk_rel__integer=-1)
        for expression in (
            condition,
            Case(When(condition, then=True), default=False),
        ):
            with self.subTest(expression=expression):
                queryset = (
                    CaseTestModel.objects.filter(pk=parent.pk)
                    .annotate(value=F("fk_rel__integer"), copied=Subquery(inner))
                    .annotate(flag=expression)
                    .order_by("value")
                )
                self.assertSequenceEqual(
                    queryset.values_list("value", "copied", "flag"),
                    [(-1, 1, False), (1, -1, True)],
                )

    def test_mixed_aggregate_comparison_before_negated_sibling(self):
        parent = CaseTestModel.objects.create(integer=100)
        for value in (1, 2):
            FKCaseTestModel.objects.create(fk=parent, integer=value)
        base = (
            CaseTestModel.objects.filter(pk=parent.pk)
            .annotate(total=Count("fk_rel"), value=F("fk_rel__integer"))
            .annotate(combined=F("total") + F("value"))
        )
        for sibling in (
            Q(combined=3),
            Q(Exact(F("combined"), Value(3))),
            Q(integer=F("combined") + 97),
            Q(fk_rel__integer=F("total") + 1),
        ):
            condition = sibling & ~Q(fk_rel__integer=1)
            for expression in (
                condition,
                Case(When(condition, then=True), default=False),
            ):
                with self.subTest(sibling=sibling, expression=expression):
                    queryset = base.annotate(flag=expression).order_by("value")
                    self.assertSequenceEqual(
                        queryset.values_list("total", "value", "combined", "flag"),
                        [(1, 1, 2, False), (1, 2, 3, True)],
                    )

    @skipUnlessDBFeature("supports_over_clause")
    def test_window_aggregate_comparison_before_negated_sibling(self):
        parent = CaseTestModel.objects.create(integer=100)
        for value in (1, 2):
            FKCaseTestModel.objects.create(fk=parent, integer=value)
        base = CaseTestModel.objects.filter(pk=parent.pk).annotate(
            value=F("fk_rel__integer"),
            total=Window(Count("fk_rel"), partition_by=[F("pk")]),
        )
        condition = Q(total=2) & ~Q(fk_rel__integer=1)
        for expression in (
            condition,
            Case(When(condition, then=True), default=False),
        ):
            with self.subTest(expression=expression):
                queryset = base.annotate(flag=expression).order_by("value")
                self.assertSequenceEqual(
                    queryset.values_list("value", "total", "flag"),
                    [(1, 2, False), (2, 2, True)],
                )

    @skipUnlessDBFeature("supports_over_clause")
    def test_window_grouped_argument_before_negated_sibling(self):
        parent = CaseTestModel.objects.create(integer=100)
        for value in (1, 2):
            FKCaseTestModel.objects.create(fk=parent, integer=value)
        base = (
            CaseTestModel.objects.filter(pk=parent.pk)
            .annotate(total=Count("fk_rel"))
            .annotate(previous=Window(Lag("total", default=2), partition_by=[F("pk")]))
        )
        condition = Q(previous=2) & ~Q(fk_rel__integer=1)
        self.assertSequenceEqual(
            base.annotate(flag=condition).values_list("total", "flag"),
            [(2, False)],
        )

    def test_negated_sibling_with_subquery_mixed_aggregate_columns(self):
        parent = CaseTestModel.objects.create(integer=100)
        for value in (1, 2):
            FKCaseTestModel.objects.create(fk=parent, integer=value)
        inner = (
            CaseTestModel.objects.filter(pk=OuterRef("pk"))
            .annotate(v=OuterRef("combined"))
            .values("v")[:1]
        )
        queryset = (
            CaseTestModel.objects.filter(pk=parent.pk)
            .annotate(total=Count("fk_rel"), value=F("fk_rel__integer"))
            .annotate(combined=F("total") + F("value"))
            .annotate(copied=Subquery(inner))
            .annotate(flag=Q(copied=3) & ~Q(fk_rel__integer=1))
            .order_by("value")
        )
        self.assertSequenceEqual(
            queryset.values_list("total", "value", "copied", "flag"),
            [(1, 1, 2, False), (1, 2, 3, True)],
        )

    def test_subquery_sibling_preserves_compound_aggregate_grouping(self):
        parent = CaseTestModel.objects.create(integer=100)
        for value in (1, 2):
            FKCaseTestModel.objects.create(fk=parent, integer=value)
        empty = CaseTestModel.objects.filter(pk=0).annotate(v=Value(0)).values("v")
        inner = (
            CaseTestModel.objects.filter(pk=OuterRef("pk"))
            .annotate(v=OuterRef("total"))
            .values("v")
        )
        queryset = CaseTestModel.objects.filter(pk=parent.pk).annotate(
            total=Count("fk_rel"), copied=Subquery(empty.union(inner)[:1])
        )
        self.assertSequenceEqual(queryset.values_list("total", "copied"), [(2, 2)])
        condition = Q(copied=2) & ~Q(fk_rel__integer=1)
        self.assertSequenceEqual(
            queryset.annotate(flag=condition).values_list("total", "copied", "flag"),
            [(2, 2, False)],
        )

    def test_negated_multihop_sibling_preserves_aggregate(self):
        parent = CaseTestModel.objects.create(integer=2)
        for _ in range(2):
            child = CaseTestModel.objects.create(integer=10, fk=parent)
            FKCaseTestModel.objects.create(fk=child, integer=3)
        for condition, expected in (
            (~Q(casetestmodel__fk_rel__integer=1), True),
            (~Q(casetestmodel__fk_rel__integer=3), False),
            (~Q(~Q(casetestmodel__fk_rel__integer=3)), True),
        ):
            with self.subTest(condition=condition):
                queryset = (
                    CaseTestModel.objects.filter(pk=parent.pk)
                    .values("pk")
                    .annotate(total=Count("casetestmodel"))
                    .annotate(flag=Q(casetestmodel__integer=10) & condition)
                )
                self.assertSequenceEqual(
                    queryset.values_list("total", "flag"), [(2, expected)]
                )
                with mock.patch.object(
                    connection.features, "allows_group_by_select_index", False
                ):
                    _, _, group_by = queryset.query.get_compiler(
                        connection=connection
                    ).pre_sql_setup()
                self.assertFalse(any("SELECT" in sql for sql, params in group_by))

    def test_negated_multihop_null_condition_with_scalar_sibling(self):
        parents = []
        for descendants in ((), ((),), ((3, 4),), ((), (3,))):
            parent = CaseTestModel.objects.create(integer=1)
            parents.append(parent)
            for values in descendants:
                child = CaseTestModel.objects.create(integer=10, fk=parent)
                for value in values:
                    FKCaseTestModel.objects.create(fk=child, integer=value)
        other = CaseTestModel.objects.create(integer=2)
        child = CaseTestModel.objects.create(integer=10, fk=other)
        FKCaseTestModel.objects.create(fk=child, integer=3)
        parents.append(other)

        for lookup, rhs, expected in (
            (
                "casetestmodel__fk_rel__integer__isnull",
                True,
                [False, False, True, False, False],
            ),
            (
                "casetestmodel__fk_rel__integer",
                None,
                [False, False, True, False, False],
            ),
            (
                "casetestmodel__fk_rel__integer__isnull",
                False,
                [True, True, False, False, False],
            ),
        ):
            condition = Q(integer=1) & ~Q(**{lookup: rhs})
            for expression in (
                condition,
                Case(When(condition, then=True), default=False),
            ):
                with self.subTest(lookup=lookup, rhs=rhs, expression=expression):
                    queryset = (
                        CaseTestModel.objects.filter(pk__in=[p.pk for p in parents])
                        .annotate(flag=expression)
                        .order_by("pk")
                    )
                    self.assertSequenceEqual(
                        queryset.values_list("flag", flat=True), expected
                    )

    def test_negated_null_condition_with_scalar_sibling(self):
        parents = []
        for children in ((), (2, 3), (None, 2)):
            parent = CaseTestModel.objects.create(integer=1)
            parents.append(parent)
            for value in children:
                CaseTestModel.objects.create(integer=10, integer2=value, fk=parent)
        for condition in (
            ~Q(casetestmodel__integer2__isnull=True),
            Q(integer=1) & ~Q(casetestmodel__integer2__isnull=True),
            Q(integer=1) & ~Q(casetestmodel__integer2=None),
        ):
            for expression in (
                condition,
                Case(When(condition, then=True), default=False),
            ):
                with self.subTest(expression=expression):
                    queryset = (
                        CaseTestModel.objects.filter(pk__in=[p.pk for p in parents])
                        .annotate(flag=expression)
                        .order_by("pk")
                    )
                    self.assertSequenceEqual(
                        queryset.values_list("flag", flat=True), [False, True, False]
                    )

    def test_negated_sibling_with_different_join_paths(self):
        anchor = CaseTestModel.objects.create(integer=99)
        parent = CaseTestModel.objects.create(integer=1, integer2=5, fk=anchor)
        for value in (1, 2):
            child = CaseTestModel.objects.create(integer=10, integer2=value, fk=parent)
            FKCaseTestModel.objects.create(fk=child, integer=value)
        for sibling in (Q(fk__integer=99), Q(value=99)):
            for lookup in ("casetestmodel__integer2", "casetestmodel__fk_rel__integer"):
                condition = sibling & ~Q(**{lookup: 1})
                for expression in (
                    condition,
                    Case(When(condition, then=True), default=False),
                ):
                    with self.subTest(
                        sibling=sibling, lookup=lookup, expression=expression
                    ):
                        queryset = (
                            CaseTestModel.objects.filter(pk=parent.pk)
                            .alias(value=F("fk__integer"))
                            .annotate(flag=expression)
                        )
                        self.assertSequenceEqual(
                            queryset.values_list("integer", "flag"), [(1, False)]
                        )

    def test_negated_null_condition_with_single_valued_prefix(self):
        anchor = CaseTestModel.objects.create(integer=99)
        parent = CaseTestModel.objects.create(integer=1, integer2=5, fk=anchor)
        CaseTestModel.objects.create(integer=20, integer2=None, fk=anchor)
        for lookup, rhs, expected in (
            ("fk__casetestmodel__integer2__isnull", True, False),
            ("fk__casetestmodel__integer2", None, False),
            ("fk__casetestmodel__integer2__isnull", False, False),
        ):
            condition = Q(fk__integer=99) & ~Q(**{lookup: rhs})
            for expression in (
                condition,
                Case(When(condition, then=True), default=False),
            ):
                with self.subTest(lookup=lookup, rhs=rhs, expression=expression):
                    queryset = CaseTestModel.objects.filter(pk=parent.pk).annotate(
                        flag=expression
                    )
                    self.assertSequenceEqual(
                        queryset.values_list("flag", flat=True), [expected]
                    )

    def test_negated_multihop_sibling_cardinality(self):
        for descendants, expected in (
            (((3, 3), (3, 3)), [(2, True)]),
            (((1, 1), (1, 1)), [(2, False)]),
            (((1, 1), (3, 3)), [(1, False), (1, True)]),
            (((), ()), [(2, True)]),
            ((), [(0, None)]),
        ):
            with self.subTest(descendants=descendants):
                parent = CaseTestModel.objects.create(integer=2)
                for values in descendants:
                    child = CaseTestModel.objects.create(integer=10, fk=parent)
                    for value in values:
                        FKCaseTestModel.objects.create(fk=child, integer=value)
                queryset = (
                    CaseTestModel.objects.filter(pk=parent.pk)
                    .values("pk")
                    .annotate(total=Count("casetestmodel"))
                    .annotate(
                        flag=Q(casetestmodel__integer=10)
                        & ~Q(casetestmodel__fk_rel__integer=1)
                    )
                    .order_by("flag")
                )
                self.assertSequenceEqual(
                    queryset.values_list("total", "flag"), expected
                )

    def test_negated_multihop_sibling_outer_reference(self):
        parent = CaseTestModel.objects.create(integer=2)
        child = CaseTestModel.objects.create(integer=10, fk=parent)
        FKCaseTestModel.objects.create(fk=child, integer=3)
        inner = CaseTestModel.objects.filter(pk=OuterRef("pk")).annotate(
            flag=Q(casetestmodel__integer=10)
            & ~Q(casetestmodel__fk_rel__integer=OuterRef("integer"))
        )
        queryset = CaseTestModel.objects.filter(pk=parent.pk).annotate(
            flag=Subquery(inner.values("flag")[:1])
        )
        self.assertSequenceEqual(queryset.values_list("flag", flat=True), [True])
        # Resolving the subquery must leave its reusable expression intact.
        self.assertSequenceEqual(queryset.all().values_list("flag", flat=True), [True])
        self.assertSequenceEqual(
            CaseTestModel.objects.filter(pk=parent.pk)
            .annotate(flag=Subquery(inner.values("flag")[:1]))
            .values_list("flag", flat=True),
            [True],
        )

    def test_negated_multihop_sibling_outer_annotation_grouping(self):
        parent = CaseTestModel.objects.create(integer=2)
        child = CaseTestModel.objects.create(integer=10, fk=parent)
        FKCaseTestModel.objects.create(fk=child, integer=3)
        for integer in (2, 3):
            FKCaseTestModel.objects.create(fk=parent, integer=integer)
        inner = CaseTestModel.objects.filter(pk=OuterRef("pk")).annotate(
            flag=Q(casetestmodel__integer=10)
            & ~Q(casetestmodel__fk_rel__integer=OuterRef("target"))
        )
        queryset = (
            CaseTestModel.objects.filter(pk=parent.pk)
            .annotate(target=F("fk_rel__integer"))
            .values("pk")
            .annotate(total=Count("casetestmodel"))
            .annotate(flag=Subquery(inner.values("flag")[:1]))
            .order_by("flag")
        )
        self.assertSequenceEqual(
            queryset.values_list("total", "flag"), [(1, False), (1, True)]
        )

    def test_negated_multihop_sibling_combined_queries(self):
        parents = []
        for integer in (1, 3, 4):
            parent = CaseTestModel.objects.create(integer=2)
            parents.append(parent.pk)
            child = CaseTestModel.objects.create(integer=10, fk=parent)
            FKCaseTestModel.objects.create(fk=child, integer=integer)

        def matching(needle):
            return (
                CaseTestModel.objects.filter(pk__in=parents)
                .annotate(
                    flag=Q(casetestmodel__integer=10)
                    & ~Q(casetestmodel__fk_rel__integer=needle)
                )
                .filter(flag=True)
            )

        first, second = matching(1), matching(3)
        self.assertCountEqual((first | second).values_list("pk", flat=True), parents)
        self.assertSequenceEqual(
            (first & second).values_list("pk", flat=True), [parents[2]]
        )

    @skipUnlessDBFeature("supports_over_clause")
    def test_negated_condition_window_rhs(self):
        parent = CaseTestModel.objects.create(integer=2)
        for _ in range(2):
            FKCaseTestModel.objects.create(fk=parent, integer=2)
        for condition, flags in (
            (~Q(fk_rel__integer=F("row")), (True, False)),
            (
                Q(fk_rel__integer=2) & ~Q(fk_rel__integer=F("row")),
                (True, False),
            ),
            (
                Q(fk_rel__integer=2) & ~Q(~Q(fk_rel__integer=F("row"))),
                (False, True),
            ),
            (~Q(fk_rel__integer=F("row") + 0), (True, False)),
            (~Q(fk_rel__integer__in=iter([F("row")])), (True, False)),
        ):
            with self.subTest(condition=condition):
                queryset = (
                    CaseTestModel.objects.filter(pk=parent.pk)
                    .annotate(row=Window(RowNumber(), order_by="pk"))
                    .annotate(flag=condition)
                    .order_by("row")
                )
                self.assertSequenceEqual(
                    queryset.values_list("integer", "row", "flag"),
                    [(2, 1, flags[0]), (2, 2, flags[1])],
                )

    def test_negated_many_to_many_condition(self):
        queryset = CaseTestModel.objects.annotate(
            flag=Case(When(~Q(m2m_rel__integer=1), then=True), default=False)
        )
        self.assertSequenceEqual(
            queryset.order_by("integer").values_list("integer", "flag"),
            [(1, False), (2, False), (3, True), (4, True)],
        )

    def test_condition_with_existing_related_filter(self):
        queryset = CaseTestModel.objects.filter(fk_rel__integer=2).annotate(
            flag=Case(When(~Q(fk_rel__integer=1), then=True), default=False)
        )
        self.assertSequenceEqual(
            queryset.order_by("integer").values_list("integer", "flag"),
            [(1, False), (3, True)],
        )

    def test_negated_nullable_foreign_key_condition(self):
        self.parents[0].fk = self.parents[1]
        self.parents[0].save()
        self.parents[2].fk = self.parents[0]
        self.parents[2].save()
        queryset = CaseTestModel.objects.annotate(
            flag=Case(When(~Q(fk__integer=1), then=True), default=False)
        )
        self.assertSequenceEqual(
            queryset.order_by("integer").values_list("integer", "flag"),
            [(1, True), (2, True), (3, False), (4, True)],
        )

    def test_aggregate_conditions_are_per_related_row(self):
        expression = Case(When(~Q(fk_rel__integer=1), then=1), default=2)
        queryset = CaseTestModel.objects.annotate(
            count=Count("fk_rel", filter=~Q(fk_rel__integer=1)),
            total=Sum(ExpressionWrapper(expression, output_field=IntegerField())),
        )
        self.assertSequenceEqual(
            queryset.order_by("integer").values_list("integer", "count", "total"),
            [(1, 1, 3), (2, 0, 2), (3, 2, 2), (4, 0, 1)],
        )

    def test_aggregate_condition_in_database_default(self):
        expression = Case(When(~Q(fk_rel__integer=1), then=1), default=2)
        queryset = CaseTestModel.objects.annotate(
            total=Sum(DatabaseDefault(expression)),
        )
        self.assertSequenceEqual(
            queryset.order_by("integer").values_list("integer", "total"),
            [(1, 3), (2, 2), (3, 2), (4, 1)],
        )

    def test_condition_after_failed_aggregate_resolution(self):
        queryset = CaseTestModel.objects.all()
        with self.assertRaises(FieldError):
            queryset.query.add_annotation(Sum("missing"), "total")
        queryset = queryset.annotate(flag=~Q(fk_rel__integer=1))
        self.assertSequenceEqual(
            queryset.order_by("integer").values_list("integer", "flag"),
            [(1, False), (2, False), (3, True), (4, True)],
        )

    def test_condition_reused_outside_aggregate(self):
        expression = Case(When(~Q(fk_rel__integer=1), then=1), default=2)
        queryset = CaseTestModel.objects.annotate(total=Sum(expression)).annotate(
            flag=expression,
        )
        self.assertSequenceEqual(
            queryset.order_by("integer").values_list("integer", "total", "flag"),
            [(1, 3, 2), (2, 2, 2), (3, 2, 1), (4, 1, 1)],
        )

    def test_boolean_expression_inside_aggregate_q_condition(self):
        condition = Q(Case(When(~Q(fk_rel__integer=1), then=True), default=False))
        queryset = CaseTestModel.objects.annotate(
            count=Count("fk_rel", filter=condition),
        )
        self.assertSequenceEqual(
            queryset.order_by("integer").values_list("integer", "count"),
            [(1, 1), (2, 0), (3, 2), (4, 0)],
        )

    def test_lookup_expression_inside_aggregate_condition(self):
        expression = Case(When(~Q(fk_rel__integer=1), then=True), default=False)
        for condition in (
            Exact(expression, Value(True)),
            Exact(Value(True), expression),
        ):
            with self.subTest(condition=condition):
                queryset = CaseTestModel.objects.annotate(
                    count=Count("fk_rel", filter=condition),
                )
                self.assertSequenceEqual(
                    queryset.order_by("integer").values_list("integer", "count"),
                    [(1, 1), (2, 0), (3, 2), (4, 0)],
                )

    def test_lookup_rhs_inside_aggregate_q_condition(self):
        expression = Case(When(~Q(fk_rel__integer=1), then=1), default=2)
        for lookup, value in (
            ("fk_rel__integer", expression),
            ("fk_rel__integer__in", [expression]),
        ):
            with self.subTest(lookup=lookup):
                queryset = CaseTestModel.objects.annotate(
                    count=Count("fk_rel", filter=Q(**{lookup: value})),
                )
                self.assertSequenceEqual(
                    queryset.order_by("integer").values_list("integer", "count"),
                    [(1, 0), (2, 0), (3, 0), (4, 0)],
                )

    def test_composed_condition_reuses_sibling_alias(self):
        for condition, expected in (
            (Q(fk_rel__integer=2) & ~Q(fk_rel__integer=1), [1, 3]),
            (
                Q(Exact(F("fk_rel__integer"), Value(2))) & ~Q(fk_rel__integer=1),
                [1, 3],
            ),
            (Q(integer__lt=F("fk_rel__integer")) & ~Q(fk_rel__integer=1), [1]),
            (
                Q(fk_rel__integer=2)
                & Q(Case(When(~Q(fk_rel__integer=1), then=True), default=False)),
                [1, 3],
            ),
            (
                Q(fk_rel__integer=2)
                & Q(
                    Exact(
                        Case(When(~Q(fk_rel__integer=1), then=1), default=0),
                        Value(1),
                    )
                ),
                [1, 3],
            ),
            (
                Q(fk_rel__integer=2)
                & Q(integer=Case(When(~Q(fk_rel__integer=1), then=1), default=0)),
                [1],
            ),
            (
                Q(Exact(F("fk_rel__integer"), Value(2)))
                & Q(Case(When(~Q(fk_rel__integer=1), then=True), default=False)),
                [1, 3],
            ),
            (~Q(fk_rel__integer=1) & Q(fk_rel__integer=2), [3]),
        ):
            with self.subTest(condition=condition):
                queryset = CaseTestModel.objects.annotate(flag=condition)
                self.assertSequenceEqual(
                    queryset.filter(flag=True)
                    .order_by("integer")
                    .values_list("integer", flat=True),
                    expected,
                )

    def test_sibling_aliases_do_not_leak_after_failed_resolution(self):
        query = CaseTestModel.objects.all().query
        condition = Q(fk_rel__integer=2) & Q(
            Case(When(~Q(missing=1), then=True), default=False)
        )
        with self.assertRaises(FieldError):
            query.add_annotation(condition, "broken")
        query.add_annotation(~Q(fk_rel__integer=1), "flag")
        queryset = CaseTestModel.objects.all()
        queryset.query = query
        self.assertSequenceEqual(
            queryset.order_by("integer", "flag").values_list("integer", "flag"),
            [(1, False), (1, False), (2, False), (3, True), (3, True), (4, True)],
        )

    def test_sibling_aliases_do_not_leak_into_subqueries(self):
        inner = (
            CaseTestModel.objects.filter(pk=OuterRef("pk"))
            .annotate(flag=~Q(fk_rel__integer=1))
            .values("flag")
        )
        condition = Q(fk_rel__integer=2) & Q(Exact(Subquery(inner), Value(True)))
        queryset = CaseTestModel.objects.annotate(flag=condition)
        self.assertSequenceEqual(
            queryset.filter(flag=True)
            .order_by("integer")
            .values_list("integer", flat=True),
            [3],
        )

    def test_positive_condition_reuses_existing_annotation_join(self):
        queryset = CaseTestModel.objects.annotate(value=F("fk_rel__integer")).annotate(
            flag=Case(When(fk_rel__integer=1, then=True), default=False),
        )
        self.assertSequenceEqual(
            queryset.order_by("integer", "value").values_list(
                "integer", "value", "flag"
            ),
            [
                (1, 1, True),
                (1, 2, False),
                (2, 1, True),
                (3, 2, False),
                (3, 3, False),
                (4, None, False),
            ],
        )

    def test_nullable_reverse_relation_condition(self):
        for parent, value in (
            (self.parents[0], None),
            (self.parents[0], 1),
            (self.parents[1], None),
            (self.parents[2], 2),
        ):
            CaseTestModel.objects.create(integer=10, integer2=value, fk=parent)
        queryset = CaseTestModel.objects.filter(integer__lte=4).annotate(
            flag=Case(When(~Q(casetestmodel__integer2=1), then=True), default=False)
        )
        self.assertSequenceEqual(
            queryset.order_by("integer").values_list("integer", "flag"),
            [(1, False), (2, True), (3, True), (4, True)],
        )

    def test_condition_in_subquery_of_aggregate(self):
        inner = CaseTestModel.objects.filter(pk=OuterRef("pk")).annotate(
            flag=Case(When(~Q(fk_rel__integer=1), then=1), default=0),
        )
        queryset = CaseTestModel.objects.annotate(
            total=Sum(Subquery(inner.values("flag"))),
        )
        self.assertSequenceEqual(
            queryset.order_by("integer").values_list("integer", "total"),
            [(1, 0), (2, 0), (3, 1), (4, 1)],
        )


class CaseDocumentationExamples(TestCase):
    @classmethod
    def setUpTestData(cls):
        Client.objects.create(
            name="Jane Doe",
            account_type=Client.REGULAR,
            registered_on=date.today() - timedelta(days=36),
        )
        Client.objects.create(
            name="James Smith",
            account_type=Client.GOLD,
            registered_on=date.today() - timedelta(days=5),
        )
        Client.objects.create(
            name="Jack Black",
            account_type=Client.PLATINUM,
            registered_on=date.today() - timedelta(days=10 * 365),
        )

    def test_simple_example(self):
        self.assertQuerySetEqual(
            Client.objects.annotate(
                discount=Case(
                    When(account_type=Client.GOLD, then=Value("5%")),
                    When(account_type=Client.PLATINUM, then=Value("10%")),
                    default=Value("0%"),
                ),
            ).order_by("pk"),
            [("Jane Doe", "0%"), ("James Smith", "5%"), ("Jack Black", "10%")],
            transform=attrgetter("name", "discount"),
        )

    def test_lookup_example(self):
        a_month_ago = date.today() - timedelta(days=30)
        a_year_ago = date.today() - timedelta(days=365)
        self.assertQuerySetEqual(
            Client.objects.annotate(
                discount=Case(
                    When(registered_on__lte=a_year_ago, then=Value("10%")),
                    When(registered_on__lte=a_month_ago, then=Value("5%")),
                    default=Value("0%"),
                ),
            ).order_by("pk"),
            [("Jane Doe", "5%"), ("James Smith", "0%"), ("Jack Black", "10%")],
            transform=attrgetter("name", "discount"),
        )

    def test_conditional_update_example(self):
        a_month_ago = date.today() - timedelta(days=30)
        a_year_ago = date.today() - timedelta(days=365)
        Client.objects.update(
            account_type=Case(
                When(registered_on__lte=a_year_ago, then=Value(Client.PLATINUM)),
                When(registered_on__lte=a_month_ago, then=Value(Client.GOLD)),
                default=Value(Client.REGULAR),
            ),
        )
        self.assertQuerySetEqual(
            Client.objects.order_by("pk"),
            [("Jane Doe", "G"), ("James Smith", "R"), ("Jack Black", "P")],
            transform=attrgetter("name", "account_type"),
        )

    def test_conditional_aggregation_example(self):
        Client.objects.create(
            name="Jean Grey",
            account_type=Client.REGULAR,
            registered_on=date.today(),
        )
        Client.objects.create(
            name="James Bond",
            account_type=Client.PLATINUM,
            registered_on=date.today(),
        )
        Client.objects.create(
            name="Jane Porter",
            account_type=Client.PLATINUM,
            registered_on=date.today(),
        )
        self.assertEqual(
            Client.objects.aggregate(
                regular=Count("pk", filter=Q(account_type=Client.REGULAR)),
                gold=Count("pk", filter=Q(account_type=Client.GOLD)),
                platinum=Count("pk", filter=Q(account_type=Client.PLATINUM)),
            ),
            {"regular": 2, "gold": 1, "platinum": 3},
        )
        # This was the example before the filter argument was added.
        self.assertEqual(
            Client.objects.aggregate(
                regular=Sum(
                    Case(
                        When(account_type=Client.REGULAR, then=1),
                    )
                ),
                gold=Sum(
                    Case(
                        When(account_type=Client.GOLD, then=1),
                    )
                ),
                platinum=Sum(
                    Case(
                        When(account_type=Client.PLATINUM, then=1),
                    )
                ),
            ),
            {"regular": 2, "gold": 1, "platinum": 3},
        )

    def test_filter_example(self):
        a_month_ago = date.today() - timedelta(days=30)
        a_year_ago = date.today() - timedelta(days=365)
        self.assertQuerySetEqual(
            Client.objects.filter(
                registered_on__lte=Case(
                    When(account_type=Client.GOLD, then=a_month_ago),
                    When(account_type=Client.PLATINUM, then=a_year_ago),
                ),
            ),
            [("Jack Black", "P")],
            transform=attrgetter("name", "account_type"),
        )

    def test_hash(self):
        expression_1 = Case(
            When(account_type__in=[Client.REGULAR, Client.GOLD], then=1),
            default=2,
            output_field=IntegerField(),
        )
        expression_2 = Case(
            When(account_type__in=(Client.REGULAR, Client.GOLD), then=1),
            default=2,
            output_field=IntegerField(),
        )
        expression_3 = Case(
            When(account_type__in=[Client.REGULAR, Client.GOLD], then=1), default=2
        )
        expression_4 = Case(
            When(account_type__in=[Client.PLATINUM, Client.GOLD], then=2), default=1
        )
        self.assertEqual(hash(expression_1), hash(expression_2))
        self.assertNotEqual(hash(expression_2), hash(expression_3))
        self.assertNotEqual(hash(expression_1), hash(expression_4))
        self.assertNotEqual(hash(expression_3), hash(expression_4))


class CaseWhenTests(SimpleTestCase):
    def test_only_when_arguments(self):
        msg = "Positional arguments must all be When objects."
        with self.assertRaisesMessage(TypeError, msg):
            Case(When(Q(pk__in=[])), object())

    def test_invalid_when_constructor_args(self):
        msg = (
            "When() supports a Q object, a boolean expression, or lookups as "
            "a condition."
        )
        with self.assertRaisesMessage(TypeError, msg):
            When(condition=object())
        with self.assertRaisesMessage(TypeError, msg):
            When(condition=Value(1))
        with self.assertRaisesMessage(TypeError, msg):
            When(Value(1), string="1")
        with self.assertRaisesMessage(TypeError, msg):
            When()

    def test_when_rejects_invalid_arguments(self):
        msg = "The following kwargs are invalid: '_connector', '_negated'"
        with self.assertRaisesMessage(TypeError, msg):
            When(_negated=True, _connector="evil")

    def test_empty_q_object(self):
        msg = "An empty Q() can't be used as a When() condition."
        with self.assertRaisesMessage(ValueError, msg):
            When(Q(), then=Value(True))
