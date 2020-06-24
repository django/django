import decimal

from django.core.management.color import no_style
from django.db import NotSupportedError, connection, transaction
from django.db.backends.base.operations import BaseDatabaseOperations
from django.db.models import DurationField
from django.test import (
    SimpleTestCase, TestCase, TransactionTestCase, override_settings,
    skipIfDBFeature,
)
from django.utils import timezone

from ..models import Author, Book


class SimpleDatabaseOperationTests(SimpleTestCase):
    may_require_msg = 'subclasses of BaseDatabaseOperations may require a %s() method'

    def setUp(self):
        self.ops = BaseDatabaseOperations(connection=connection)

    def test_deferrable_sql(self):
        self.assertEqual(self.ops.deferrable_sql(), '')

    def test_end_transaction_rollback(self):
        self.assertEqual(self.ops.end_transaction_sql(success=False), 'ROLLBACK;')

    def test_no_limit_value(self):
        with self.assertRaisesMessage(NotImplementedError, self.may_require_msg % 'no_limit_value'):
            self.ops.no_limit_value()

    def test_quote_name(self):
        with self.assertRaisesMessage(NotImplementedError, self.may_require_msg % 'quote_name'):
            self.ops.quote_name('a')

    def test_regex_lookup(self):
        with self.assertRaisesMessage(NotImplementedError, self.may_require_msg % 'regex_lookup'):
            self.ops.regex_lookup(lookup_type='regex')

    def test_set_time_zone_sql(self):
        self.assertEqual(self.ops.set_time_zone_sql(), '')

    def test_sql_flush(self):
        msg = 'subclasses of BaseDatabaseOperations must provide an sql_flush() method'
        with self.assertRaisesMessage(NotImplementedError, msg):
            self.ops.sql_flush(None, None)

    def test_pk_default_value(self):
        self.assertEqual(self.ops.pk_default_value(), 'DEFAULT')

    def test_tablespace_sql(self):
        self.assertEqual(self.ops.tablespace_sql(None), '')

    def test_sequence_reset_by_name_sql(self):
        self.assertEqual(self.ops.sequence_reset_by_name_sql(None, []), [])

    def test_adapt_unknown_value_decimal(self):
        value = decimal.Decimal('3.14')
        self.assertEqual(
            self.ops.adapt_unknown_value(value),
            self.ops.adapt_decimalfield_value(value)
        )

    def test_adapt_unknown_value_date(self):
        value = timezone.now().date()
        self.assertEqual(self.ops.adapt_unknown_value(value), self.ops.adapt_datefield_value(value))

    def test_adapt_unknown_value_time(self):
        value = timezone.now().time()
        self.assertEqual(self.ops.adapt_unknown_value(value), self.ops.adapt_timefield_value(value))

    def test_adapt_timefield_value_none(self):
        self.assertIsNone(self.ops.adapt_timefield_value(None))

    def test_adapt_datetimefield_value(self):
        self.assertIsNone(self.ops.adapt_datetimefield_value(None))

    def test_adapt_timefield_value(self):
        msg = 'Django does not support timezone-aware times.'
        with self.assertRaisesMessage(ValueError, msg):
            self.ops.adapt_timefield_value(timezone.make_aware(timezone.now()))

    @override_settings(USE_TZ=False)
    def test_adapt_timefield_value_unaware(self):
        now = timezone.now()
        self.assertEqual(self.ops.adapt_timefield_value(now), str(now))

    def test_date_extract_sql(self):
        with self.assertRaisesMessage(NotImplementedError, self.may_require_msg % 'date_extract_sql'):
            self.ops.date_extract_sql(None, None)

    def test_time_extract_sql(self):
        with self.assertRaisesMessage(NotImplementedError, self.may_require_msg % 'date_extract_sql'):
            self.ops.time_extract_sql(None, None)

    def test_date_interval_sql(self):
        with self.assertRaisesMessage(NotImplementedError, self.may_require_msg % 'date_interval_sql'):
            self.ops.date_interval_sql(None)

    def test_date_trunc_sql(self):
        with self.assertRaisesMessage(NotImplementedError, self.may_require_msg % 'date_trunc_sql'):
            self.ops.date_trunc_sql(None, None)

    def test_time_trunc_sql(self):
        with self.assertRaisesMessage(NotImplementedError, self.may_require_msg % 'time_trunc_sql'):
            self.ops.time_trunc_sql(None, None)

    def test_datetime_trunc_sql(self):
        with self.assertRaisesMessage(NotImplementedError, self.may_require_msg % 'datetime_trunc_sql'):
            self.ops.datetime_trunc_sql(None, None, None)

    def test_datetime_cast_date_sql(self):
        with self.assertRaisesMessage(NotImplementedError, self.may_require_msg % 'datetime_cast_date_sql'):
            self.ops.datetime_cast_date_sql(None, None)

    def test_datetime_cast_time_sql(self):
        with self.assertRaisesMessage(NotImplementedError, self.may_require_msg % 'datetime_cast_time_sql'):
            self.ops.datetime_cast_time_sql(None, None)

    def test_datetime_extract_sql(self):
        with self.assertRaisesMessage(NotImplementedError, self.may_require_msg % 'datetime_extract_sql'):
            self.ops.datetime_extract_sql(None, None, None)

    def test_json_cast_text_sql(self):
        msg = self.may_require_msg % 'json_cast_text_sql'
        with self.assertRaisesMessage(NotImplementedError, msg):
            self.ops.json_cast_text_sql(None)


class DatabaseOperationTests(TestCase):
    def setUp(self):
        self.ops = BaseDatabaseOperations(connection=connection)

    @skipIfDBFeature('supports_over_clause')
    def test_window_frame_raise_not_supported_error(self):
        msg = 'This backend does not support window expressions.'
        with self.assertRaisesMessage(NotSupportedError, msg):
            self.ops.window_frame_rows_start_end()

    @skipIfDBFeature('can_distinct_on_fields')
    def test_distinct_on_fields(self):
        msg = 'DISTINCT ON fields is not supported by this database backend'
        with self.assertRaisesMessage(NotSupportedError, msg):
            self.ops.distinct_sql(['a', 'b'], None)

    @skipIfDBFeature('supports_temporal_subtraction')
    def test_subtract_temporals(self):
        duration_field = DurationField()
        duration_field_internal_type = duration_field.get_internal_type()
        msg = (
            'This backend does not support %s subtraction.' %
            duration_field_internal_type
        )
        with self.assertRaisesMessage(NotSupportedError, msg):
            self.ops.subtract_temporals(duration_field_internal_type, None, None)


class SqlFlushTests(TransactionTestCase):
    available_apps = ['backends']

    def test_sql_flush_no_tables(self):
        self.assertEqual(connection.ops.sql_flush(no_style(), []), [])

    def test_execute_sql_flush_statements(self):
        with transaction.atomic():
            author = Author.objects.create(name='George Orwell')
            Book.objects.create(author=author)
            author = Author.objects.create(name='Harper Lee')
            Book.objects.create(author=author)
            Book.objects.create(author=author)
            self.assertIs(Author.objects.exists(), True)
            self.assertIs(Book.objects.exists(), True)

        sql_list = connection.ops.sql_flush(
            no_style(),
            [Author._meta.db_table, Book._meta.db_table],
            reset_sequences=True,
            allow_cascade=True,
        )
        connection.ops.execute_sql_flush(sql_list)

        with transaction.atomic():
            self.assertIs(Author.objects.exists(), False)
            self.assertIs(Book.objects.exists(), False)
            if connection.features.supports_sequence_reset:
                author = Author.objects.create(name='F. Scott Fitzgerald')
                self.assertEqual(author.pk, 1)
                book = Book.objects.create(author=author)
                self.assertEqual(book.pk, 1)
