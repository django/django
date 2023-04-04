import datetime
import json
from decimal import Decimal

from django import forms
from django.core import exceptions, serializers
from django.db.models import DateField, DateTimeField, F, Func, Value
from django.http import QueryDict
from django.test import override_settings
from django.test.utils import isolate_apps
from django.utils import timezone

from . import PostgreSQLSimpleTestCase, PostgreSQLTestCase
from .models import (
    BigAutoFieldModel,
    PostgreSQLModel,
    RangeLookupsModel,
    RangesModel,
    SmallAutoFieldModel,
)

try:
    from django.contrib.postgres import fields as pg_fields
    from django.contrib.postgres import forms as pg_forms
    from django.contrib.postgres.validators import (
        RangeMaxValueValidator,
        RangeMinValueValidator,
    )
    from django.db.backends.postgresql.psycopg_any import (
        DateRange,
        DateTimeTZRange,
        NumericRange,
    )
except ImportError:
    pass


@isolate_apps("postgres_tests")
class BasicTests(PostgreSQLSimpleTestCase):
    def test_get_field_display(self):
        class Model(PostgreSQLModel):
            field = pg_fields.IntegerRangeField(
                choices=[
                    ["1-50", [((1, 25), "1-25"), ([26, 50], "26-50")]],
                    ((51, 100), "51-100"),
                ],
            )

        tests = (
            ((1, 25), "1-25"),
            ([26, 50], "26-50"),
            ((51, 100), "51-100"),
            ((1, 2), "(1, 2)"),
            ([1, 2], "[1, 2]"),
        )
        for value, display in tests:
            with self.subTest(value=value, display=display):
                instance = Model(field=value)
                self.assertEqual(instance.get_field_display(), display)

    def test_discrete_range_fields_unsupported_default_bounds(self):
        discrete_range_types = [
            pg_fields.BigIntegerRangeField,
            pg_fields.IntegerRangeField,
            pg_fields.DateRangeField,
        ]
        for field_type in discrete_range_types:
            msg = f"Cannot use 'default_bounds' with {field_type.__name__}."
            with self.assertRaisesMessage(TypeError, msg):
                field_type(choices=[((51, 100), "51-100")], default_bounds="[]")

    def test_continuous_range_fields_default_bounds(self):
        continuous_range_types = [
            pg_fields.DecimalRangeField,
            pg_fields.DateTimeRangeField,
        ]
        for field_type in continuous_range_types:
            field = field_type(choices=[((51, 100), "51-100")], default_bounds="[]")
            self.assertEqual(field.default_bounds, "[]")

    def test_invalid_default_bounds(self):
        tests = [")]", ")[", "](", "])", "([", "[(", "x", "", None]
        msg = "default_bounds must be one of '[)', '(]', '()', or '[]'."
        for invalid_bounds in tests:
            with self.assertRaisesMessage(ValueError, msg):
                pg_fields.DecimalRangeField(default_bounds=invalid_bounds)

    def test_deconstruct(self):
        field = pg_fields.DecimalRangeField()
        *_, kwargs = field.deconstruct()
        self.assertEqual(kwargs, {})
        field = pg_fields.DecimalRangeField(default_bounds="[]")
        *_, kwargs = field.deconstruct()
        self.assertEqual(kwargs, {"default_bounds": "[]"})


class TestSaveLoad(PostgreSQLTestCase):
    def test_all_fields(self):
        now = timezone.now()
        instance = RangesModel(
            ints=NumericRange(0, 10),
            bigints=NumericRange(10, 20),
            decimals=NumericRange(20, 30),
            timestamps=DateTimeTZRange(now - datetime.timedelta(hours=1), now),
            dates=DateRange(now.date() - datetime.timedelta(days=1), now.date()),
        )
        instance.save()
        loaded = RangesModel.objects.get()
        self.assertEqual(instance.ints, loaded.ints)
        self.assertEqual(instance.bigints, loaded.bigints)
        self.assertEqual(instance.decimals, loaded.decimals)
        self.assertEqual(instance.timestamps, loaded.timestamps)
        self.assertEqual(instance.dates, loaded.dates)

    def test_range_object(self):
        r = NumericRange(0, 10)
        instance = RangesModel(ints=r)
        instance.save()
        loaded = RangesModel.objects.get()
        self.assertEqual(r, loaded.ints)

    def test_tuple(self):
        instance = RangesModel(ints=(0, 10))
        instance.save()
        loaded = RangesModel.objects.get()
        self.assertEqual(NumericRange(0, 10), loaded.ints)

    def test_tuple_range_with_default_bounds(self):
        range_ = (timezone.now(), timezone.now() + datetime.timedelta(hours=1))
        RangesModel.objects.create(timestamps_closed_bounds=range_, timestamps=range_)
        loaded = RangesModel.objects.get()
        self.assertEqual(
            loaded.timestamps_closed_bounds,
            DateTimeTZRange(range_[0], range_[1], "[]"),
        )
        self.assertEqual(
            loaded.timestamps,
            DateTimeTZRange(range_[0], range_[1], "[)"),
        )

    def test_range_object_boundaries(self):
        r = NumericRange(0, 10, "[]")
        instance = RangesModel(decimals=r)
        instance.save()
        loaded = RangesModel.objects.get()
        self.assertEqual(r, loaded.decimals)
        self.assertIn(10, loaded.decimals)

    def test_range_object_boundaries_range_with_default_bounds(self):
        range_ = DateTimeTZRange(
            timezone.now(),
            timezone.now() + datetime.timedelta(hours=1),
            bounds="()",
        )
        RangesModel.objects.create(timestamps_closed_bounds=range_)
        loaded = RangesModel.objects.get()
        self.assertEqual(loaded.timestamps_closed_bounds, range_)

    def test_unbounded(self):
        r = NumericRange(None, None, "()")
        instance = RangesModel(decimals=r)
        instance.save()
        loaded = RangesModel.objects.get()
        self.assertEqual(r, loaded.decimals)

    def test_empty(self):
        r = NumericRange(empty=True)
        instance = RangesModel(ints=r)
        instance.save()
        loaded = RangesModel.objects.get()
        self.assertEqual(r, loaded.ints)

    def test_null(self):
        instance = RangesModel(ints=None)
        instance.save()
        loaded = RangesModel.objects.get()
        self.assertIsNone(loaded.ints)

    def test_model_set_on_base_field(self):
        instance = RangesModel()
        field = instance._meta.get_field("ints")
        self.assertEqual(field.model, RangesModel)
        self.assertEqual(field.base_field.model, RangesModel)


class TestRangeContainsLookup(PostgreSQLTestCase):
    @classmethod
    def setUpTestData(cls):
        cls.timestamps = [
            datetime.datetime(year=2016, month=1, day=1),
            datetime.datetime(year=2016, month=1, day=2, hour=1),
            datetime.datetime(year=2016, month=1, day=2, hour=12),
            datetime.datetime(year=2016, month=1, day=3),
            datetime.datetime(year=2016, month=1, day=3, hour=1),
            datetime.datetime(year=2016, month=2, day=2),
        ]
        cls.aware_timestamps = [
            timezone.make_aware(timestamp) for timestamp in cls.timestamps
        ]
        cls.dates = [
            datetime.date(year=2016, month=1, day=1),
            datetime.date(year=2016, month=1, day=2),
            datetime.date(year=2016, month=1, day=3),
            datetime.date(year=2016, month=1, day=4),
            datetime.date(year=2016, month=2, day=2),
            datetime.date(year=2016, month=2, day=3),
        ]
        cls.obj = RangesModel.objects.create(
            dates=(cls.dates[0], cls.dates[3]),
            dates_inner=(cls.dates[1], cls.dates[2]),
            timestamps=(cls.timestamps[0], cls.timestamps[3]),
            timestamps_inner=(cls.timestamps[1], cls.timestamps[2]),
        )
        cls.aware_obj = RangesModel.objects.create(
            dates=(cls.dates[0], cls.dates[3]),
            dates_inner=(cls.dates[1], cls.dates[2]),
            timestamps=(cls.aware_timestamps[0], cls.aware_timestamps[3]),
            timestamps_inner=(cls.timestamps[1], cls.timestamps[2]),
        )
        # Objects that don't match any queries.
        for i in range(3, 4):
            RangesModel.objects.create(
                dates=(cls.dates[i], cls.dates[i + 1]),
                timestamps=(cls.timestamps[i], cls.timestamps[i + 1]),
            )
            RangesModel.objects.create(
                dates=(cls.dates[i], cls.dates[i + 1]),
                timestamps=(cls.aware_timestamps[i], cls.aware_timestamps[i + 1]),
            )

    def test_datetime_range_contains(self):
        filter_args = (
            self.timestamps[1],
            self.aware_timestamps[1],
            (self.timestamps[1], self.timestamps[2]),
            (self.aware_timestamps[1], self.aware_timestamps[2]),
            Value(self.dates[0]),
            Func(F("dates"), function="lower", output_field=DateTimeField()),
            F("timestamps_inner"),
        )
        for filter_arg in filter_args:
            with self.subTest(filter_arg=filter_arg):
                self.assertCountEqual(
                    RangesModel.objects.filter(**{"timestamps__contains": filter_arg}),
                    [self.obj, self.aware_obj],
                )

    def test_date_range_contains(self):
        filter_args = (
            self.timestamps[1],
            (self.dates[1], self.dates[2]),
            Value(self.dates[0], output_field=DateField()),
            Func(F("timestamps"), function="lower", output_field=DateField()),
            F("dates_inner"),
        )
        for filter_arg in filter_args:
            with self.subTest(filter_arg=filter_arg):
                self.assertCountEqual(
                    RangesModel.objects.filter(**{"dates__contains": filter_arg}),
                    [self.obj, self.aware_obj],
                )


class TestQuerying(PostgreSQLTestCase):
    @classmethod
    def setUpTestData(cls):
        cls.objs = RangesModel.objects.bulk_create(
            [
                RangesModel(ints=NumericRange(0, 10)),
                RangesModel(ints=NumericRange(5, 15)),
                RangesModel(ints=NumericRange(None, 0)),
                RangesModel(ints=NumericRange(empty=True)),
                RangesModel(ints=None),
            ]
        )

    def test_exact(self):
        self.assertSequenceEqual(
            RangesModel.objects.filter(ints__exact=NumericRange(0, 10)),
            [self.objs[0]],
        )

    def test_isnull(self):
        self.assertSequenceEqual(
            RangesModel.objects.filter(ints__isnull=True),
            [self.objs[4]],
        )

    def test_isempty(self):
        self.assertSequenceEqual(
            RangesModel.objects.filter(ints__isempty=True),
            [self.objs[3]],
        )

    def test_contains(self):
        self.assertSequenceEqual(
            RangesModel.objects.filter(ints__contains=8),
            [self.objs[0], self.objs[1]],
        )

    def test_contains_range(self):
        self.assertSequenceEqual(
            RangesModel.objects.filter(ints__contains=NumericRange(3, 8)),
            [self.objs[0]],
        )

    def test_contained_by(self):
        self.assertSequenceEqual(
            RangesModel.objects.filter(ints__contained_by=NumericRange(0, 20)),
            [self.objs[0], self.objs[1], self.objs[3]],
        )

    def test_overlap(self):
        self.assertSequenceEqual(
            RangesModel.objects.filter(ints__overlap=NumericRange(3, 8)),
            [self.objs[0], self.objs[1]],
        )

    def test_fully_lt(self):
        self.assertSequenceEqual(
            RangesModel.objects.filter(ints__fully_lt=NumericRange(5, 10)),
            [self.objs[2]],
        )

    def test_fully_gt(self):
        self.assertSequenceEqual(
            RangesModel.objects.filter(ints__fully_gt=NumericRange(5, 10)),
            [],
        )

    def test_not_lt(self):
        self.assertSequenceEqual(
            RangesModel.objects.filter(ints__not_lt=NumericRange(5, 10)),
            [self.objs[1]],
        )

    def test_not_gt(self):
        self.assertSequenceEqual(
            RangesModel.objects.filter(ints__not_gt=NumericRange(5, 10)),
            [self.objs[0], self.objs[2]],
        )

    def test_adjacent_to(self):
        self.assertSequenceEqual(
            RangesModel.objects.filter(ints__adjacent_to=NumericRange(0, 5)),
            [self.objs[1], self.objs[2]],
        )

    def test_startswith(self):
        self.assertSequenceEqual(
            RangesModel.objects.filter(ints__startswith=0),
            [self.objs[0]],
        )

    def test_endswith(self):
        self.assertSequenceEqual(
            RangesModel.objects.filter(ints__endswith=0),
            [self.objs[2]],
        )

    def test_startswith_chaining(self):
        self.assertSequenceEqual(
            RangesModel.objects.filter(ints__startswith__gte=0),
            [self.objs[0], self.objs[1]],
        )

    def test_bound_type(self):
        decimals = RangesModel.objects.bulk_create(
            [
                RangesModel(decimals=NumericRange(None, 10)),
                RangesModel(decimals=NumericRange(10, None)),
                RangesModel(decimals=NumericRange(5, 15)),
                RangesModel(decimals=NumericRange(5, 15, "(]")),
            ]
        )
        tests = [
            ("lower_inc", True, [decimals[1], decimals[2]]),
            ("lower_inc", False, [decimals[0], decimals[3]]),
            ("lower_inf", True, [decimals[0]]),
            ("lower_inf", False, [decimals[1], decimals[2], decimals[3]]),
            ("upper_inc", True, [decimals[3]]),
            ("upper_inc", False, [decimals[0], decimals[1], decimals[2]]),
            ("upper_inf", True, [decimals[1]]),
            ("upper_inf", False, [decimals[0], decimals[2], decimals[3]]),
        ]
        for lookup, filter_arg, excepted_result in tests:
            with self.subTest(lookup=lookup, filter_arg=filter_arg):
                self.assertSequenceEqual(
                    RangesModel.objects.filter(**{"decimals__%s" % lookup: filter_arg}),
                    excepted_result,
                )


class TestQueryingWithRanges(PostgreSQLTestCase):
    def test_date_range(self):
        objs = [
            RangeLookupsModel.objects.create(date="2015-01-01"),
            RangeLookupsModel.objects.create(date="2015-05-05"),
        ]
        self.assertSequenceEqual(
            RangeLookupsModel.objects.filter(
                date__contained_by=DateRange("2015-01-01", "2015-05-04")
            ),
            [objs[0]],
        )

    def test_date_range_datetime_field(self):
        objs = [
            RangeLookupsModel.objects.create(timestamp="2015-01-01"),
            RangeLookupsModel.objects.create(timestamp="2015-05-05"),
        ]
        self.assertSequenceEqual(
            RangeLookupsModel.objects.filter(
                timestamp__date__contained_by=DateRange("2015-01-01", "2015-05-04")
            ),
            [objs[0]],
        )

    def test_datetime_range(self):
        objs = [
            RangeLookupsModel.objects.create(timestamp="2015-01-01T09:00:00"),
            RangeLookupsModel.objects.create(timestamp="2015-05-05T17:00:00"),
        ]
        self.assertSequenceEqual(
            RangeLookupsModel.objects.filter(
                timestamp__contained_by=DateTimeTZRange(
                    "2015-01-01T09:00", "2015-05-04T23:55"
                )
            ),
            [objs[0]],
        )

    def test_small_integer_field_contained_by(self):
        objs = [
            RangeLookupsModel.objects.create(small_integer=8),
            RangeLookupsModel.objects.create(small_integer=4),
            RangeLookupsModel.objects.create(small_integer=-1),
        ]
        self.assertSequenceEqual(
            RangeLookupsModel.objects.filter(
                small_integer__contained_by=NumericRange(4, 6)
            ),
            [objs[1]],
        )

    def test_integer_range(self):
        objs = [
            RangeLookupsModel.objects.create(integer=5),
            RangeLookupsModel.objects.create(integer=99),
            RangeLookupsModel.objects.create(integer=-1),
        ]
        self.assertSequenceEqual(
            RangeLookupsModel.objects.filter(integer__contained_by=NumericRange(1, 98)),
            [objs[0]],
        )

    def test_biginteger_range(self):
        objs = [
            RangeLookupsModel.objects.create(big_integer=5),
            RangeLookupsModel.objects.create(big_integer=99),
            RangeLookupsModel.objects.create(big_integer=-1),
        ]
        self.assertSequenceEqual(
            RangeLookupsModel.objects.filter(
                big_integer__contained_by=NumericRange(1, 98)
            ),
            [objs[0]],
        )

    def test_decimal_field_contained_by(self):
        objs = [
            RangeLookupsModel.objects.create(decimal_field=Decimal("1.33")),
            RangeLookupsModel.objects.create(decimal_field=Decimal("2.88")),
            RangeLookupsModel.objects.create(decimal_field=Decimal("99.17")),
        ]
        self.assertSequenceEqual(
            RangeLookupsModel.objects.filter(
                decimal_field__contained_by=NumericRange(
                    Decimal("1.89"), Decimal("7.91")
                ),
            ),
            [objs[1]],
        )

    def test_float_range(self):
        objs = [
            RangeLookupsModel.objects.create(float=5),
            RangeLookupsModel.objects.create(float=99),
            RangeLookupsModel.objects.create(float=-1),
        ]
        self.assertSequenceEqual(
            RangeLookupsModel.objects.filter(float__contained_by=NumericRange(1, 98)),
            [objs[0]],
        )

    def test_small_auto_field_contained_by(self):
        objs = SmallAutoFieldModel.objects.bulk_create(
            [SmallAutoFieldModel() for i in range(1, 5)]
        )
        self.assertSequenceEqual(
            SmallAutoFieldModel.objects.filter(
                id__contained_by=NumericRange(objs[1].pk, objs[3].pk),
            ),
            objs[1:3],
        )

    def test_auto_field_contained_by(self):
        objs = RangeLookupsModel.objects.bulk_create(
            [RangeLookupsModel() for i in range(1, 5)]
        )
        self.assertSequenceEqual(
            RangeLookupsModel.objects.filter(
                id__contained_by=NumericRange(objs[1].pk, objs[3].pk),
            ),
            objs[1:3],
        )

    def test_big_auto_field_contained_by(self):
        objs = BigAutoFieldModel.objects.bulk_create(
            [BigAutoFieldModel() for i in range(1, 5)]
        )
        self.assertSequenceEqual(
            BigAutoFieldModel.objects.filter(
                id__contained_by=NumericRange(objs[1].pk, objs[3].pk),
            ),
            objs[1:3],
        )

    def test_f_ranges(self):
        parent = RangesModel.objects.create(decimals=NumericRange(0, 10))
        objs = [
            RangeLookupsModel.objects.create(float=5, parent=parent),
            RangeLookupsModel.objects.create(float=99, parent=parent),
        ]
        self.assertSequenceEqual(
            RangeLookupsModel.objects.filter(float__contained_by=F("parent__decimals")),
            [objs[0]],
        )

    def test_exclude(self):
        objs = [
            RangeLookupsModel.objects.create(float=5),
            RangeLookupsModel.objects.create(float=99),
            RangeLookupsModel.objects.create(float=-1),
        ]
        self.assertSequenceEqual(
            RangeLookupsModel.objects.exclude(float__contained_by=NumericRange(0, 100)),
            [objs[2]],
        )


class TestSerialization(PostgreSQLSimpleTestCase):
    test_data = (
        '[{"fields": {"ints": "{\\"upper\\": \\"10\\", \\"lower\\": \\"0\\", '
        '\\"bounds\\": \\"[)\\"}", "decimals": "{\\"empty\\": true}", '
        '"bigints": null, "timestamps": '
        '"{\\"upper\\": \\"2014-02-02T12:12:12+00:00\\", '
        '\\"lower\\": \\"2014-01-01T00:00:00+00:00\\", \\"bounds\\": \\"[)\\"}", '
        '"timestamps_inner": null, '
        '"timestamps_closed_bounds": "{\\"upper\\": \\"2014-02-02T12:12:12+00:00\\", '
        '\\"lower\\": \\"2014-01-01T00:00:00+00:00\\", \\"bounds\\": \\"()\\"}", '
        '"dates": "{\\"upper\\": \\"2014-02-02\\", \\"lower\\": \\"2014-01-01\\", '
        '\\"bounds\\": \\"[)\\"}", "dates_inner": null }, '
        '"model": "postgres_tests.rangesmodel", "pk": null}]'
    )

    lower_date = datetime.date(2014, 1, 1)
    upper_date = datetime.date(2014, 2, 2)
    lower_dt = datetime.datetime(2014, 1, 1, 0, 0, 0, tzinfo=datetime.timezone.utc)
    upper_dt = datetime.datetime(2014, 2, 2, 12, 12, 12, tzinfo=datetime.timezone.utc)

    def test_dumping(self):
        instance = RangesModel(
            ints=NumericRange(0, 10),
            decimals=NumericRange(empty=True),
            timestamps=DateTimeTZRange(self.lower_dt, self.upper_dt),
            timestamps_closed_bounds=DateTimeTZRange(
                self.lower_dt,
                self.upper_dt,
                bounds="()",
            ),
            dates=DateRange(self.lower_date, self.upper_date),
        )
        data = serializers.serialize("json", [instance])
        dumped = json.loads(data)
        for field in ("ints", "dates", "timestamps", "timestamps_closed_bounds"):
            dumped[0]["fields"][field] = json.loads(dumped[0]["fields"][field])
        check = json.loads(self.test_data)
        for field in ("ints", "dates", "timestamps", "timestamps_closed_bounds"):
            check[0]["fields"][field] = json.loads(check[0]["fields"][field])

        self.assertEqual(dumped, check)

    def test_loading(self):
        instance = list(serializers.deserialize("json", self.test_data))[0].object
        self.assertEqual(instance.ints, NumericRange(0, 10))
        self.assertEqual(instance.decimals, NumericRange(empty=True))
        self.assertIsNone(instance.bigints)
        self.assertEqual(instance.dates, DateRange(self.lower_date, self.upper_date))
        self.assertEqual(
            instance.timestamps, DateTimeTZRange(self.lower_dt, self.upper_dt)
        )
        self.assertEqual(
            instance.timestamps_closed_bounds,
            DateTimeTZRange(self.lower_dt, self.upper_dt, bounds="()"),
        )

    def test_serialize_range_with_null(self):
        instance = RangesModel(ints=NumericRange(None, 10))
        data = serializers.serialize("json", [instance])
        new_instance = list(serializers.deserialize("json", data))[0].object
        self.assertEqual(new_instance.ints, NumericRange(None, 10))

        instance = RangesModel(ints=NumericRange(10, None))
        data = serializers.serialize("json", [instance])
        new_instance = list(serializers.deserialize("json", data))[0].object
        self.assertEqual(new_instance.ints, NumericRange(10, None))


class TestChecks(PostgreSQLSimpleTestCase):
    def test_choices_tuple_list(self):
        class Model(PostgreSQLModel):
            field = pg_fields.IntegerRangeField(
                choices=[
                    ["1-50", [((1, 25), "1-25"), ([26, 50], "26-50")]],
                    ((51, 100), "51-100"),
                ],
            )

        self.assertEqual(Model._meta.get_field("field").check(), [])


class TestValidators(PostgreSQLSimpleTestCase):
    def test_max(self):
        validator = RangeMaxValueValidator(5)
        validator(NumericRange(0, 5))
        msg = "Ensure that the upper bound of the range is not greater than 5."
        with self.assertRaises(exceptions.ValidationError) as cm:
            validator(NumericRange(0, 10))
        self.assertEqual(cm.exception.messages[0], msg)
        self.assertEqual(cm.exception.code, "max_value")
        with self.assertRaisesMessage(exceptions.ValidationError, msg):
            validator(NumericRange(0, None))  # an unbound range

    def test_min(self):
        validator = RangeMinValueValidator(5)
        validator(NumericRange(10, 15))
        msg = "Ensure that the lower bound of the range is not less than 5."
        with self.assertRaises(exceptions.ValidationError) as cm:
            validator(NumericRange(0, 10))
        self.assertEqual(cm.exception.messages[0], msg)
        self.assertEqual(cm.exception.code, "min_value")
        with self.assertRaisesMessage(exceptions.ValidationError, msg):
            validator(NumericRange(None, 10))  # an unbound range


class TestFormField(PostgreSQLSimpleTestCase):
    def test_valid_integer(self):
        field = pg_forms.IntegerRangeField()
        value = field.clean(["1", "2"])
        self.assertEqual(value, NumericRange(1, 2))

    def test_valid_decimal(self):
        field = pg_forms.DecimalRangeField()
        value = field.clean(["1.12345", "2.001"])
        self.assertEqual(value, NumericRange(Decimal("1.12345"), Decimal("2.001")))

    def test_valid_timestamps(self):
        field = pg_forms.DateTimeRangeField()
        value = field.clean(["01/01/2014 00:00:00", "02/02/2014 12:12:12"])
        lower = datetime.datetime(2014, 1, 1, 0, 0, 0)
        upper = datetime.datetime(2014, 2, 2, 12, 12, 12)
        self.assertEqual(value, DateTimeTZRange(lower, upper))

    def test_valid_dates(self):
        field = pg_forms.DateRangeField()
        value = field.clean(["01/01/2014", "02/02/2014"])
        lower = datetime.date(2014, 1, 1)
        upper = datetime.date(2014, 2, 2)
        self.assertEqual(value, DateRange(lower, upper))

    def test_using_split_datetime_widget(self):
        class SplitDateTimeRangeField(pg_forms.DateTimeRangeField):
            base_field = forms.SplitDateTimeField

        class SplitForm(forms.Form):
            field = SplitDateTimeRangeField()

        form = SplitForm()
        self.assertHTMLEqual(
            str(form),
            """
            <div>
                <fieldset>
                    <legend>Field:</legend>
                    <input id="id_field_0_0" name="field_0_0" type="text">
                    <input id="id_field_0_1" name="field_0_1" type="text">
                    <input id="id_field_1_0" name="field_1_0" type="text">
                    <input id="id_field_1_1" name="field_1_1" type="text">
                </fieldset>
            </div>
        """,
        )
        form = SplitForm(
            {
                "field_0_0": "01/01/2014",
                "field_0_1": "00:00:00",
                "field_1_0": "02/02/2014",
                "field_1_1": "12:12:12",
            }
        )
        self.assertTrue(form.is_valid())
        lower = datetime.datetime(2014, 1, 1, 0, 0, 0)
        upper = datetime.datetime(2014, 2, 2, 12, 12, 12)
        self.assertEqual(form.cleaned_data["field"], DateTimeTZRange(lower, upper))

    def test_none(self):
        field = pg_forms.IntegerRangeField(required=False)
        value = field.clean(["", ""])
        self.assertIsNone(value)

    def test_datetime_form_as_table(self):
        class DateTimeRangeForm(forms.Form):
            datetime_field = pg_forms.DateTimeRangeField(show_hidden_initial=True)

        form = DateTimeRangeForm()
        self.assertHTMLEqual(
            form.as_table(),
            """
            <tr><th>
            <label>Datetime field:</label>
            </th><td>
            <input type="text" name="datetime_field_0" id="id_datetime_field_0">
            <input type="text" name="datetime_field_1" id="id_datetime_field_1">
            <input type="hidden" name="initial-datetime_field_0"
            id="initial-id_datetime_field_0">
            <input type="hidden" name="initial-datetime_field_1"
            id="initial-id_datetime_field_1">
            </td></tr>
            """,
        )
        form = DateTimeRangeForm(
            {
                "datetime_field_0": "2010-01-01 11:13:00",
                "datetime_field_1": "2020-12-12 16:59:00",
            }
        )
        self.assertHTMLEqual(
            form.as_table(),
            """
            <tr><th>
            <label>Datetime field:</label>
            </th><td>
            <input type="text" name="datetime_field_0"
            value="2010-01-01 11:13:00" id="id_datetime_field_0">
            <input type="text" name="datetime_field_1"
            value="2020-12-12 16:59:00" id="id_datetime_field_1">
            <input type="hidden" name="initial-datetime_field_0"
            value="2010-01-01 11:13:00" id="initial-id_datetime_field_0">
            <input type="hidden" name="initial-datetime_field_1"
            value="2020-12-12 16:59:00" id="initial-id_datetime_field_1"></td></tr>
            """,
        )

    def test_datetime_form_initial_data(self):
        class DateTimeRangeForm(forms.Form):
            datetime_field = pg_forms.DateTimeRangeField(show_hidden_initial=True)

        data = QueryDict(mutable=True)
        data.update(
            {
                "datetime_field_0": "2010-01-01 11:13:00",
                "datetime_field_1": "",
                "initial-datetime_field_0": "2010-01-01 10:12:00",
                "initial-datetime_field_1": "",
            }
        )
        form = DateTimeRangeForm(data=data)
        self.assertTrue(form.has_changed())

        data["initial-datetime_field_0"] = "2010-01-01 11:13:00"
        form = DateTimeRangeForm(data=data)
        self.assertFalse(form.has_changed())

    def test_rendering(self):
        class RangeForm(forms.Form):
            ints = pg_forms.IntegerRangeField()

        self.assertHTMLEqual(
            str(RangeForm()),
            """
        <div>
            <fieldset>
                <legend>Ints:</legend>
                <input id="id_ints_0" name="ints_0" type="number">
                <input id="id_ints_1" name="ints_1" type="number">
            </fieldset>
        </div>
        """,
        )

    def test_integer_lower_bound_higher(self):
        field = pg_forms.IntegerRangeField()
        with self.assertRaises(exceptions.ValidationError) as cm:
            field.clean(["10", "2"])
        self.assertEqual(
            cm.exception.messages[0],
            "The start of the range must not exceed the end of the range.",
        )
        self.assertEqual(cm.exception.code, "bound_ordering")

    def test_integer_open(self):
        field = pg_forms.IntegerRangeField()
        value = field.clean(["", "0"])
        self.assertEqual(value, NumericRange(None, 0))

    def test_integer_incorrect_data_type(self):
        field = pg_forms.IntegerRangeField()
        with self.assertRaises(exceptions.ValidationError) as cm:
            field.clean("1")
        self.assertEqual(cm.exception.messages[0], "Enter two whole numbers.")
        self.assertEqual(cm.exception.code, "invalid")

    def test_integer_invalid_lower(self):
        field = pg_forms.IntegerRangeField()
        with self.assertRaises(exceptions.ValidationError) as cm:
            field.clean(["a", "2"])
        self.assertEqual(cm.exception.messages[0], "Enter a whole number.")

    def test_integer_invalid_upper(self):
        field = pg_forms.IntegerRangeField()
        with self.assertRaises(exceptions.ValidationError) as cm:
            field.clean(["1", "b"])
        self.assertEqual(cm.exception.messages[0], "Enter a whole number.")

    def test_integer_required(self):
        field = pg_forms.IntegerRangeField(required=True)
        with self.assertRaises(exceptions.ValidationError) as cm:
            field.clean(["", ""])
        self.assertEqual(cm.exception.messages[0], "This field is required.")
        value = field.clean([1, ""])
        self.assertEqual(value, NumericRange(1, None))

    def test_decimal_lower_bound_higher(self):
        field = pg_forms.DecimalRangeField()
        with self.assertRaises(exceptions.ValidationError) as cm:
            field.clean(["1.8", "1.6"])
        self.assertEqual(
            cm.exception.messages[0],
            "The start of the range must not exceed the end of the range.",
        )
        self.assertEqual(cm.exception.code, "bound_ordering")

    def test_decimal_open(self):
        field = pg_forms.DecimalRangeField()
        value = field.clean(["", "3.1415926"])
        self.assertEqual(value, NumericRange(None, Decimal("3.1415926")))

    def test_decimal_incorrect_data_type(self):
        field = pg_forms.DecimalRangeField()
        with self.assertRaises(exceptions.ValidationError) as cm:
            field.clean("1.6")
        self.assertEqual(cm.exception.messages[0], "Enter two numbers.")
        self.assertEqual(cm.exception.code, "invalid")

    def test_decimal_invalid_lower(self):
        field = pg_forms.DecimalRangeField()
        with self.assertRaises(exceptions.ValidationError) as cm:
            field.clean(["a", "3.1415926"])
        self.assertEqual(cm.exception.messages[0], "Enter a number.")

    def test_decimal_invalid_upper(self):
        field = pg_forms.DecimalRangeField()
        with self.assertRaises(exceptions.ValidationError) as cm:
            field.clean(["1.61803399", "b"])
        self.assertEqual(cm.exception.messages[0], "Enter a number.")

    def test_decimal_required(self):
        field = pg_forms.DecimalRangeField(required=True)
        with self.assertRaises(exceptions.ValidationError) as cm:
            field.clean(["", ""])
        self.assertEqual(cm.exception.messages[0], "This field is required.")
        value = field.clean(["1.61803399", ""])
        self.assertEqual(value, NumericRange(Decimal("1.61803399"), None))

    def test_date_lower_bound_higher(self):
        field = pg_forms.DateRangeField()
        with self.assertRaises(exceptions.ValidationError) as cm:
            field.clean(["2013-04-09", "1976-04-16"])
        self.assertEqual(
            cm.exception.messages[0],
            "The start of the range must not exceed the end of the range.",
        )
        self.assertEqual(cm.exception.code, "bound_ordering")

    def test_date_open(self):
        field = pg_forms.DateRangeField()
        value = field.clean(["", "2013-04-09"])
        self.assertEqual(value, DateRange(None, datetime.date(2013, 4, 9)))

    def test_date_incorrect_data_type(self):
        field = pg_forms.DateRangeField()
        with self.assertRaises(exceptions.ValidationError) as cm:
            field.clean("1")
        self.assertEqual(cm.exception.messages[0], "Enter two valid dates.")
        self.assertEqual(cm.exception.code, "invalid")

    def test_date_invalid_lower(self):
        field = pg_forms.DateRangeField()
        with self.assertRaises(exceptions.ValidationError) as cm:
            field.clean(["a", "2013-04-09"])
        self.assertEqual(cm.exception.messages[0], "Enter a valid date.")

    def test_date_invalid_upper(self):
        field = pg_forms.DateRangeField()
        with self.assertRaises(exceptions.ValidationError) as cm:
            field.clean(["2013-04-09", "b"])
        self.assertEqual(cm.exception.messages[0], "Enter a valid date.")

    def test_date_required(self):
        field = pg_forms.DateRangeField(required=True)
        with self.assertRaises(exceptions.ValidationError) as cm:
            field.clean(["", ""])
        self.assertEqual(cm.exception.messages[0], "This field is required.")
        value = field.clean(["1976-04-16", ""])
        self.assertEqual(value, DateRange(datetime.date(1976, 4, 16), None))

    def test_date_has_changed_first(self):
        self.assertTrue(
            pg_forms.DateRangeField().has_changed(
                ["2010-01-01", "2020-12-12"],
                ["2010-01-31", "2020-12-12"],
            )
        )

    def test_date_has_changed_last(self):
        self.assertTrue(
            pg_forms.DateRangeField().has_changed(
                ["2010-01-01", "2020-12-12"],
                ["2010-01-01", "2020-12-31"],
            )
        )

    def test_datetime_lower_bound_higher(self):
        field = pg_forms.DateTimeRangeField()
        with self.assertRaises(exceptions.ValidationError) as cm:
            field.clean(["2006-10-25 14:59", "2006-10-25 14:58"])
        self.assertEqual(
            cm.exception.messages[0],
            "The start of the range must not exceed the end of the range.",
        )
        self.assertEqual(cm.exception.code, "bound_ordering")

    def test_datetime_open(self):
        field = pg_forms.DateTimeRangeField()
        value = field.clean(["", "2013-04-09 11:45"])
        self.assertEqual(
            value, DateTimeTZRange(None, datetime.datetime(2013, 4, 9, 11, 45))
        )

    def test_datetime_incorrect_data_type(self):
        field = pg_forms.DateTimeRangeField()
        with self.assertRaises(exceptions.ValidationError) as cm:
            field.clean("2013-04-09 11:45")
        self.assertEqual(cm.exception.messages[0], "Enter two valid date/times.")
        self.assertEqual(cm.exception.code, "invalid")

    def test_datetime_invalid_lower(self):
        field = pg_forms.DateTimeRangeField()
        with self.assertRaises(exceptions.ValidationError) as cm:
            field.clean(["45", "2013-04-09 11:45"])
        self.assertEqual(cm.exception.messages[0], "Enter a valid date/time.")

    def test_datetime_invalid_upper(self):
        field = pg_forms.DateTimeRangeField()
        with self.assertRaises(exceptions.ValidationError) as cm:
            field.clean(["2013-04-09 11:45", "sweet pickles"])
        self.assertEqual(cm.exception.messages[0], "Enter a valid date/time.")

    def test_datetime_required(self):
        field = pg_forms.DateTimeRangeField(required=True)
        with self.assertRaises(exceptions.ValidationError) as cm:
            field.clean(["", ""])
        self.assertEqual(cm.exception.messages[0], "This field is required.")
        value = field.clean(["2013-04-09 11:45", ""])
        self.assertEqual(
            value, DateTimeTZRange(datetime.datetime(2013, 4, 9, 11, 45), None)
        )

    @override_settings(USE_TZ=True, TIME_ZONE="Africa/Johannesburg")
    def test_datetime_prepare_value(self):
        field = pg_forms.DateTimeRangeField()
        value = field.prepare_value(
            DateTimeTZRange(
                datetime.datetime(2015, 5, 22, 16, 6, 33, tzinfo=datetime.timezone.utc),
                None,
            )
        )
        self.assertEqual(value, [datetime.datetime(2015, 5, 22, 18, 6, 33), None])

    def test_datetime_has_changed_first(self):
        self.assertTrue(
            pg_forms.DateTimeRangeField().has_changed(
                ["2010-01-01 00:00", "2020-12-12 00:00"],
                ["2010-01-31 23:00", "2020-12-12 00:00"],
            )
        )

    def test_datetime_has_changed_last(self):
        self.assertTrue(
            pg_forms.DateTimeRangeField().has_changed(
                ["2010-01-01 00:00", "2020-12-12 00:00"],
                ["2010-01-01 00:00", "2020-12-31 23:00"],
            )
        )

    def test_model_field_formfield_integer(self):
        model_field = pg_fields.IntegerRangeField()
        form_field = model_field.formfield()
        self.assertIsInstance(form_field, pg_forms.IntegerRangeField)
        self.assertEqual(form_field.range_kwargs, {})

    def test_model_field_formfield_biginteger(self):
        model_field = pg_fields.BigIntegerRangeField()
        form_field = model_field.formfield()
        self.assertIsInstance(form_field, pg_forms.IntegerRangeField)
        self.assertEqual(form_field.range_kwargs, {})

    def test_model_field_formfield_float(self):
        model_field = pg_fields.DecimalRangeField(default_bounds="()")
        form_field = model_field.formfield()
        self.assertIsInstance(form_field, pg_forms.DecimalRangeField)
        self.assertEqual(form_field.range_kwargs, {"bounds": "()"})

    def test_model_field_formfield_date(self):
        model_field = pg_fields.DateRangeField()
        form_field = model_field.formfield()
        self.assertIsInstance(form_field, pg_forms.DateRangeField)
        self.assertEqual(form_field.range_kwargs, {})

    def test_model_field_formfield_datetime(self):
        model_field = pg_fields.DateTimeRangeField()
        form_field = model_field.formfield()
        self.assertIsInstance(form_field, pg_forms.DateTimeRangeField)
        self.assertEqual(
            form_field.range_kwargs,
            {"bounds": pg_fields.ranges.CANONICAL_RANGE_BOUNDS},
        )

    def test_model_field_formfield_datetime_default_bounds(self):
        model_field = pg_fields.DateTimeRangeField(default_bounds="[]")
        form_field = model_field.formfield()
        self.assertIsInstance(form_field, pg_forms.DateTimeRangeField)
        self.assertEqual(form_field.range_kwargs, {"bounds": "[]"})

    def test_model_field_with_default_bounds(self):
        field = pg_forms.DateTimeRangeField(default_bounds="[]")
        value = field.clean(["2014-01-01 00:00:00", "2014-02-03 12:13:14"])
        lower = datetime.datetime(2014, 1, 1, 0, 0, 0)
        upper = datetime.datetime(2014, 2, 3, 12, 13, 14)
        self.assertEqual(value, DateTimeTZRange(lower, upper, "[]"))

    def test_has_changed(self):
        for field, value in (
            (pg_forms.DateRangeField(), ["2010-01-01", "2020-12-12"]),
            (pg_forms.DateTimeRangeField(), ["2010-01-01 11:13", "2020-12-12 14:52"]),
            (pg_forms.IntegerRangeField(), [1, 2]),
            (pg_forms.DecimalRangeField(), ["1.12345", "2.001"]),
        ):
            with self.subTest(field=field.__class__.__name__):
                self.assertTrue(field.has_changed(None, value))
                self.assertTrue(field.has_changed([value[0], ""], value))
                self.assertTrue(field.has_changed(["", value[1]], value))
                self.assertFalse(field.has_changed(value, value))


class TestWidget(PostgreSQLSimpleTestCase):
    def test_range_widget(self):
        f = pg_forms.ranges.DateTimeRangeField()
        self.assertHTMLEqual(
            f.widget.render("datetimerange", ""),
            '<input type="text" name="datetimerange_0">'
            '<input type="text" name="datetimerange_1">',
        )
        self.assertHTMLEqual(
            f.widget.render("datetimerange", None),
            '<input type="text" name="datetimerange_0">'
            '<input type="text" name="datetimerange_1">',
        )
        dt_range = DateTimeTZRange(
            datetime.datetime(2006, 1, 10, 7, 30), datetime.datetime(2006, 2, 12, 9, 50)
        )
        self.assertHTMLEqual(
            f.widget.render("datetimerange", dt_range),
            '<input type="text" name="datetimerange_0" value="2006-01-10 07:30:00">'
            '<input type="text" name="datetimerange_1" value="2006-02-12 09:50:00">',
        )

    def test_range_widget_render_tuple_value(self):
        field = pg_forms.ranges.DateTimeRangeField()
        dt_range_tuple = (
            datetime.datetime(2022, 4, 22, 10, 24),
            datetime.datetime(2022, 5, 12, 9, 25),
        )
        self.assertHTMLEqual(
            field.widget.render("datetimerange", dt_range_tuple),
            '<input type="text" name="datetimerange_0" value="2022-04-22 10:24:00">'
            '<input type="text" name="datetimerange_1" value="2022-05-12 09:25:00">',
        )
