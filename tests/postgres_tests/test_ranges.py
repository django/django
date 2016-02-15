import datetime
import json
import unittest

from django import forms
from django.core import exceptions, serializers
from django.db import connection
from django.db.models import F
from django.test import TestCase, override_settings
from django.utils import timezone

from . import PostgreSQLTestCase
from .models import RangeLookupsModel, RangesModel

try:
    from psycopg2.extras import DateRange, DateTimeTZRange, NumericRange
    from django.contrib.postgres import fields as pg_fields, forms as pg_forms
    from django.contrib.postgres.validators import (
        RangeMaxValueValidator, RangeMinValueValidator,
    )
except ImportError:
    pass


def skipUnlessPG92(test):
    try:
        PG_VERSION = connection.pg_version
    except AttributeError:
        PG_VERSION = 0
    if PG_VERSION < 90200:
        return unittest.skip('PostgreSQL >= 9.2 required')(test)
    return test


@skipUnlessPG92
class TestSaveLoad(TestCase):

    def test_all_fields(self):
        now = timezone.now()
        instance = RangesModel(
            ints=NumericRange(0, 10),
            bigints=NumericRange(10, 20),
            floats=NumericRange(20, 30),
            timestamps=DateTimeTZRange(now - datetime.timedelta(hours=1), now),
            dates=DateRange(now.date() - datetime.timedelta(days=1), now.date()),
        )
        instance.save()
        loaded = RangesModel.objects.get()
        self.assertEqual(instance.ints, loaded.ints)
        self.assertEqual(instance.bigints, loaded.bigints)
        self.assertEqual(instance.floats, loaded.floats)
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

    def test_range_object_boundaries(self):
        r = NumericRange(0, 10, '[]')
        instance = RangesModel(floats=r)
        instance.save()
        loaded = RangesModel.objects.get()
        self.assertEqual(r, loaded.floats)
        self.assertTrue(10 in loaded.floats)

    def test_unbounded(self):
        r = NumericRange(None, None, '()')
        instance = RangesModel(floats=r)
        instance.save()
        loaded = RangesModel.objects.get()
        self.assertEqual(r, loaded.floats)

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


@skipUnlessPG92
class TestQuerying(TestCase):

    @classmethod
    def setUpTestData(cls):
        cls.objs = [
            RangesModel.objects.create(ints=NumericRange(0, 10)),
            RangesModel.objects.create(ints=NumericRange(5, 15)),
            RangesModel.objects.create(ints=NumericRange(None, 0)),
            RangesModel.objects.create(ints=NumericRange(empty=True)),
            RangesModel.objects.create(ints=None),
        ]

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


@skipUnlessPG92
class TestQueryingWithRanges(TestCase):
    def test_date_range(self):
        objs = [
            RangeLookupsModel.objects.create(date='2015-01-01'),
            RangeLookupsModel.objects.create(date='2015-05-05'),
        ]
        self.assertSequenceEqual(
            RangeLookupsModel.objects.filter(date__contained_by=DateRange('2015-01-01', '2015-05-04')),
            [objs[0]],
        )

    def test_date_range_datetime_field(self):
        objs = [
            RangeLookupsModel.objects.create(timestamp='2015-01-01'),
            RangeLookupsModel.objects.create(timestamp='2015-05-05'),
        ]
        self.assertSequenceEqual(
            RangeLookupsModel.objects.filter(timestamp__date__contained_by=DateRange('2015-01-01', '2015-05-04')),
            [objs[0]],
        )

    def test_datetime_range(self):
        objs = [
            RangeLookupsModel.objects.create(timestamp='2015-01-01T09:00:00'),
            RangeLookupsModel.objects.create(timestamp='2015-05-05T17:00:00'),
        ]
        self.assertSequenceEqual(
            RangeLookupsModel.objects.filter(
                timestamp__contained_by=DateTimeTZRange('2015-01-01T09:00', '2015-05-04T23:55')
            ),
            [objs[0]],
        )

    def test_integer_range(self):
        objs = [
            RangeLookupsModel.objects.create(integer=5),
            RangeLookupsModel.objects.create(integer=99),
            RangeLookupsModel.objects.create(integer=-1),
        ]
        self.assertSequenceEqual(
            RangeLookupsModel.objects.filter(integer__contained_by=NumericRange(1, 98)),
            [objs[0]]
        )

    def test_biginteger_range(self):
        objs = [
            RangeLookupsModel.objects.create(big_integer=5),
            RangeLookupsModel.objects.create(big_integer=99),
            RangeLookupsModel.objects.create(big_integer=-1),
        ]
        self.assertSequenceEqual(
            RangeLookupsModel.objects.filter(big_integer__contained_by=NumericRange(1, 98)),
            [objs[0]]
        )

    def test_float_range(self):
        objs = [
            RangeLookupsModel.objects.create(float=5),
            RangeLookupsModel.objects.create(float=99),
            RangeLookupsModel.objects.create(float=-1),
        ]
        self.assertSequenceEqual(
            RangeLookupsModel.objects.filter(float__contained_by=NumericRange(1, 98)),
            [objs[0]]
        )

    def test_f_ranges(self):
        parent = RangesModel.objects.create(floats=NumericRange(0, 10))
        objs = [
            RangeLookupsModel.objects.create(float=5, parent=parent),
            RangeLookupsModel.objects.create(float=99, parent=parent),
        ]
        self.assertSequenceEqual(
            RangeLookupsModel.objects.filter(float__contained_by=F('parent__floats')),
            [objs[0]]
        )

    def test_exclude(self):
        objs = [
            RangeLookupsModel.objects.create(float=5),
            RangeLookupsModel.objects.create(float=99),
            RangeLookupsModel.objects.create(float=-1),
        ]
        self.assertSequenceEqual(
            RangeLookupsModel.objects.exclude(float__contained_by=NumericRange(0, 100)),
            [objs[2]]
        )


@skipUnlessPG92
class TestSerialization(TestCase):
    test_data = (
        '[{"fields": {"ints": "{\\"upper\\": \\"10\\", \\"lower\\": \\"0\\", '
        '\\"bounds\\": \\"[)\\"}", "floats": "{\\"empty\\": true}", '
        '"bigints": null, "timestamps": "{\\"upper\\": \\"2014-02-02T12:12:12+00:00\\", '
        '\\"lower\\": \\"2014-01-01T00:00:00+00:00\\", \\"bounds\\": \\"[)\\"}", '
        '"dates": "{\\"upper\\": \\"2014-02-02\\", \\"lower\\": \\"2014-01-01\\", \\"bounds\\": \\"[)\\"}" }, '
        '"model": "postgres_tests.rangesmodel", "pk": null}]'
    )

    lower_date = datetime.date(2014, 1, 1)
    upper_date = datetime.date(2014, 2, 2)
    lower_dt = datetime.datetime(2014, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
    upper_dt = datetime.datetime(2014, 2, 2, 12, 12, 12, tzinfo=timezone.utc)

    def test_dumping(self):
        instance = RangesModel(ints=NumericRange(0, 10), floats=NumericRange(empty=True),
            timestamps=DateTimeTZRange(self.lower_dt, self.upper_dt),
            dates=DateRange(self.lower_date, self.upper_date))
        data = serializers.serialize('json', [instance])
        dumped = json.loads(data)
        for field in ('ints', 'dates', 'timestamps'):
            dumped[0]['fields'][field] = json.loads(dumped[0]['fields'][field])
        check = json.loads(self.test_data)
        for field in ('ints', 'dates', 'timestamps'):
            check[0]['fields'][field] = json.loads(check[0]['fields'][field])
        self.assertEqual(dumped, check)

    def test_loading(self):
        instance = list(serializers.deserialize('json', self.test_data))[0].object
        self.assertEqual(instance.ints, NumericRange(0, 10))
        self.assertEqual(instance.floats, NumericRange(empty=True))
        self.assertEqual(instance.bigints, None)

    def test_serialize_range_with_null(self):
        instance = RangesModel(ints=NumericRange(None, 10))
        data = serializers.serialize('json', [instance])
        new_instance = list(serializers.deserialize('json', data))[0].object
        self.assertEqual(new_instance.ints, NumericRange(None, 10))

        instance = RangesModel(ints=NumericRange(10, None))
        data = serializers.serialize('json', [instance])
        new_instance = list(serializers.deserialize('json', data))[0].object
        self.assertEqual(new_instance.ints, NumericRange(10, None))


class TestValidators(PostgreSQLTestCase):

    def test_max(self):
        validator = RangeMaxValueValidator(5)
        validator(NumericRange(0, 5))
        with self.assertRaises(exceptions.ValidationError) as cm:
            validator(NumericRange(0, 10))
        self.assertEqual(cm.exception.messages[0], 'Ensure that this range is completely less than or equal to 5.')
        self.assertEqual(cm.exception.code, 'max_value')

    def test_min(self):
        validator = RangeMinValueValidator(5)
        validator(NumericRange(10, 15))
        with self.assertRaises(exceptions.ValidationError) as cm:
            validator(NumericRange(0, 10))
        self.assertEqual(cm.exception.messages[0], 'Ensure that this range is completely greater than or equal to 5.')
        self.assertEqual(cm.exception.code, 'min_value')


class TestFormField(PostgreSQLTestCase):

    def test_valid_integer(self):
        field = pg_forms.IntegerRangeField()
        value = field.clean(['1', '2'])
        self.assertEqual(value, NumericRange(1, 2))

    def test_valid_floats(self):
        field = pg_forms.FloatRangeField()
        value = field.clean(['1.12345', '2.001'])
        self.assertEqual(value, NumericRange(1.12345, 2.001))

    def test_valid_timestamps(self):
        field = pg_forms.DateTimeRangeField()
        value = field.clean(['01/01/2014 00:00:00', '02/02/2014 12:12:12'])
        lower = datetime.datetime(2014, 1, 1, 0, 0, 0)
        upper = datetime.datetime(2014, 2, 2, 12, 12, 12)
        self.assertEqual(value, DateTimeTZRange(lower, upper))

    def test_valid_dates(self):
        field = pg_forms.DateRangeField()
        value = field.clean(['01/01/2014', '02/02/2014'])
        lower = datetime.date(2014, 1, 1)
        upper = datetime.date(2014, 2, 2)
        self.assertEqual(value, DateRange(lower, upper))

    def test_using_split_datetime_widget(self):
        class SplitDateTimeRangeField(pg_forms.DateTimeRangeField):
            base_field = forms.SplitDateTimeField

        class SplitForm(forms.Form):
            field = SplitDateTimeRangeField()

        form = SplitForm()
        self.assertHTMLEqual(str(form), '''
            <tr>
                <th>
                <label for="id_field_0">Field:</label>
                </th>
                <td>
                    <input id="id_field_0_0" name="field_0_0" type="text" />
                    <input id="id_field_0_1" name="field_0_1" type="text" />
                    <input id="id_field_1_0" name="field_1_0" type="text" />
                    <input id="id_field_1_1" name="field_1_1" type="text" />
                </td>
            </tr>
        ''')
        form = SplitForm({
            'field_0_0': '01/01/2014',
            'field_0_1': '00:00:00',
            'field_1_0': '02/02/2014',
            'field_1_1': '12:12:12',
        })
        self.assertTrue(form.is_valid())
        lower = datetime.datetime(2014, 1, 1, 0, 0, 0)
        upper = datetime.datetime(2014, 2, 2, 12, 12, 12)
        self.assertEqual(form.cleaned_data['field'], DateTimeTZRange(lower, upper))

    def test_none(self):
        field = pg_forms.IntegerRangeField(required=False)
        value = field.clean(['', ''])
        self.assertEqual(value, None)

    def test_rendering(self):
        class RangeForm(forms.Form):
            ints = pg_forms.IntegerRangeField()

        self.assertHTMLEqual(str(RangeForm()), '''
        <tr>
            <th><label for="id_ints_0">Ints:</label></th>
            <td>
                <input id="id_ints_0" name="ints_0" type="number" />
                <input id="id_ints_1" name="ints_1" type="number" />
            </td>
        </tr>
        ''')

    def test_integer_lower_bound_higher(self):
        field = pg_forms.IntegerRangeField()
        with self.assertRaises(exceptions.ValidationError) as cm:
            field.clean(['10', '2'])
        self.assertEqual(cm.exception.messages[0], 'The start of the range must not exceed the end of the range.')
        self.assertEqual(cm.exception.code, 'bound_ordering')

    def test_integer_open(self):
        field = pg_forms.IntegerRangeField()
        value = field.clean(['', '0'])
        self.assertEqual(value, NumericRange(None, 0))

    def test_integer_incorrect_data_type(self):
        field = pg_forms.IntegerRangeField()
        with self.assertRaises(exceptions.ValidationError) as cm:
            field.clean('1')
        self.assertEqual(cm.exception.messages[0], 'Enter two whole numbers.')
        self.assertEqual(cm.exception.code, 'invalid')

    def test_integer_invalid_lower(self):
        field = pg_forms.IntegerRangeField()
        with self.assertRaises(exceptions.ValidationError) as cm:
            field.clean(['a', '2'])
        self.assertEqual(cm.exception.messages[0], 'Enter a whole number.')

    def test_integer_invalid_upper(self):
        field = pg_forms.IntegerRangeField()
        with self.assertRaises(exceptions.ValidationError) as cm:
            field.clean(['1', 'b'])
        self.assertEqual(cm.exception.messages[0], 'Enter a whole number.')

    def test_integer_required(self):
        field = pg_forms.IntegerRangeField(required=True)
        with self.assertRaises(exceptions.ValidationError) as cm:
            field.clean(['', ''])
        self.assertEqual(cm.exception.messages[0], 'This field is required.')
        value = field.clean([1, ''])
        self.assertEqual(value, NumericRange(1, None))

    def test_float_lower_bound_higher(self):
        field = pg_forms.FloatRangeField()
        with self.assertRaises(exceptions.ValidationError) as cm:
            field.clean(['1.8', '1.6'])
        self.assertEqual(cm.exception.messages[0], 'The start of the range must not exceed the end of the range.')
        self.assertEqual(cm.exception.code, 'bound_ordering')

    def test_float_open(self):
        field = pg_forms.FloatRangeField()
        value = field.clean(['', '3.1415926'])
        self.assertEqual(value, NumericRange(None, 3.1415926))

    def test_float_incorrect_data_type(self):
        field = pg_forms.FloatRangeField()
        with self.assertRaises(exceptions.ValidationError) as cm:
            field.clean('1.6')
        self.assertEqual(cm.exception.messages[0], 'Enter two numbers.')
        self.assertEqual(cm.exception.code, 'invalid')

    def test_float_invalid_lower(self):
        field = pg_forms.FloatRangeField()
        with self.assertRaises(exceptions.ValidationError) as cm:
            field.clean(['a', '3.1415926'])
        self.assertEqual(cm.exception.messages[0], 'Enter a number.')

    def test_float_invalid_upper(self):
        field = pg_forms.FloatRangeField()
        with self.assertRaises(exceptions.ValidationError) as cm:
            field.clean(['1.61803399', 'b'])
        self.assertEqual(cm.exception.messages[0], 'Enter a number.')

    def test_float_required(self):
        field = pg_forms.FloatRangeField(required=True)
        with self.assertRaises(exceptions.ValidationError) as cm:
            field.clean(['', ''])
        self.assertEqual(cm.exception.messages[0], 'This field is required.')
        value = field.clean(['1.61803399', ''])
        self.assertEqual(value, NumericRange(1.61803399, None))

    def test_date_lower_bound_higher(self):
        field = pg_forms.DateRangeField()
        with self.assertRaises(exceptions.ValidationError) as cm:
            field.clean(['2013-04-09', '1976-04-16'])
        self.assertEqual(cm.exception.messages[0], 'The start of the range must not exceed the end of the range.')
        self.assertEqual(cm.exception.code, 'bound_ordering')

    def test_date_open(self):
        field = pg_forms.DateRangeField()
        value = field.clean(['', '2013-04-09'])
        self.assertEqual(value, DateRange(None, datetime.date(2013, 4, 9)))

    def test_date_incorrect_data_type(self):
        field = pg_forms.DateRangeField()
        with self.assertRaises(exceptions.ValidationError) as cm:
            field.clean('1')
        self.assertEqual(cm.exception.messages[0], 'Enter two valid dates.')
        self.assertEqual(cm.exception.code, 'invalid')

    def test_date_invalid_lower(self):
        field = pg_forms.DateRangeField()
        with self.assertRaises(exceptions.ValidationError) as cm:
            field.clean(['a', '2013-04-09'])
        self.assertEqual(cm.exception.messages[0], 'Enter a valid date.')

    def test_date_invalid_upper(self):
        field = pg_forms.DateRangeField()
        with self.assertRaises(exceptions.ValidationError) as cm:
            field.clean(['2013-04-09', 'b'])
        self.assertEqual(cm.exception.messages[0], 'Enter a valid date.')

    def test_date_required(self):
        field = pg_forms.DateRangeField(required=True)
        with self.assertRaises(exceptions.ValidationError) as cm:
            field.clean(['', ''])
        self.assertEqual(cm.exception.messages[0], 'This field is required.')
        value = field.clean(['1976-04-16', ''])
        self.assertEqual(value, DateRange(datetime.date(1976, 4, 16), None))

    def test_datetime_lower_bound_higher(self):
        field = pg_forms.DateTimeRangeField()
        with self.assertRaises(exceptions.ValidationError) as cm:
            field.clean(['2006-10-25 14:59', '2006-10-25 14:58'])
        self.assertEqual(cm.exception.messages[0], 'The start of the range must not exceed the end of the range.')
        self.assertEqual(cm.exception.code, 'bound_ordering')

    def test_datetime_open(self):
        field = pg_forms.DateTimeRangeField()
        value = field.clean(['', '2013-04-09 11:45'])
        self.assertEqual(value, DateTimeTZRange(None, datetime.datetime(2013, 4, 9, 11, 45)))

    def test_datetime_incorrect_data_type(self):
        field = pg_forms.DateTimeRangeField()
        with self.assertRaises(exceptions.ValidationError) as cm:
            field.clean('2013-04-09 11:45')
        self.assertEqual(cm.exception.messages[0], 'Enter two valid date/times.')
        self.assertEqual(cm.exception.code, 'invalid')

    def test_datetime_invalid_lower(self):
        field = pg_forms.DateTimeRangeField()
        with self.assertRaises(exceptions.ValidationError) as cm:
            field.clean(['45', '2013-04-09 11:45'])
        self.assertEqual(cm.exception.messages[0], 'Enter a valid date/time.')

    def test_datetime_invalid_upper(self):
        field = pg_forms.DateTimeRangeField()
        with self.assertRaises(exceptions.ValidationError) as cm:
            field.clean(['2013-04-09 11:45', 'sweet pickles'])
        self.assertEqual(cm.exception.messages[0], 'Enter a valid date/time.')

    def test_datetime_required(self):
        field = pg_forms.DateTimeRangeField(required=True)
        with self.assertRaises(exceptions.ValidationError) as cm:
            field.clean(['', ''])
        self.assertEqual(cm.exception.messages[0], 'This field is required.')
        value = field.clean(['2013-04-09 11:45', ''])
        self.assertEqual(value, DateTimeTZRange(datetime.datetime(2013, 4, 9, 11, 45), None))

    @override_settings(USE_TZ=True, TIME_ZONE='Africa/Johannesburg')
    def test_datetime_prepare_value(self):
        field = pg_forms.DateTimeRangeField()
        value = field.prepare_value(
            DateTimeTZRange(datetime.datetime(2015, 5, 22, 16, 6, 33, tzinfo=timezone.utc), None)
        )
        self.assertEqual(value, [datetime.datetime(2015, 5, 22, 18, 6, 33), None])

    def test_model_field_formfield_integer(self):
        model_field = pg_fields.IntegerRangeField()
        form_field = model_field.formfield()
        self.assertIsInstance(form_field, pg_forms.IntegerRangeField)

    def test_model_field_formfield_biginteger(self):
        model_field = pg_fields.BigIntegerRangeField()
        form_field = model_field.formfield()
        self.assertIsInstance(form_field, pg_forms.IntegerRangeField)

    def test_model_field_formfield_float(self):
        model_field = pg_fields.FloatRangeField()
        form_field = model_field.formfield()
        self.assertIsInstance(form_field, pg_forms.FloatRangeField)

    def test_model_field_formfield_date(self):
        model_field = pg_fields.DateRangeField()
        form_field = model_field.formfield()
        self.assertIsInstance(form_field, pg_forms.DateRangeField)

    def test_model_field_formfield_datetime(self):
        model_field = pg_fields.DateTimeRangeField()
        form_field = model_field.formfield()
        self.assertIsInstance(form_field, pg_forms.DateTimeRangeField)


class TestWidget(PostgreSQLTestCase):
    def test_range_widget(self):
        f = pg_forms.ranges.DateTimeRangeField()
        self.assertHTMLEqual(
            f.widget.render('datetimerange', ''),
            '<input type="text" name="datetimerange_0" /><input type="text" name="datetimerange_1" />'
        )
        self.assertHTMLEqual(
            f.widget.render('datetimerange', None),
            '<input type="text" name="datetimerange_0" /><input type="text" name="datetimerange_1" />'
        )
        dt_range = DateTimeTZRange(
            datetime.datetime(2006, 1, 10, 7, 30),
            datetime.datetime(2006, 2, 12, 9, 50)
        )
        self.assertHTMLEqual(
            f.widget.render('datetimerange', dt_range),
            '<input type="text" name="datetimerange_0" value="2006-01-10 07:30:00" />'
            '<input type="text" name="datetimerange_1" value="2006-02-12 09:50:00" />'
        )
