import unittest

from django.db import NotSupportedError, connection, transaction
from django.db.models import Count
from django.test import TestCase, skipIfDBFeature, skipUnlessDBFeature
from django.test.utils import CaptureQueriesContext

from .models import Tag


@skipUnlessDBFeature('supports_explaining_query_execution')
class ExplainTests(TestCase):

    def test_basic(self):
        querysets = [
            Tag.objects.filter(name='test'),
            Tag.objects.filter(name='test').select_related('parent'),
            Tag.objects.filter(name='test').prefetch_related('children'),
            Tag.objects.filter(name='test').annotate(Count('children')),
            Tag.objects.filter(name='test').values_list('name'),
            Tag.objects.order_by().union(Tag.objects.order_by().filter(name='test')),
            Tag.objects.all().select_for_update().filter(name='test'),
        ]
        supported_formats = connection.features.supported_explain_formats
        all_formats = (None,) + tuple(supported_formats) + tuple(f.lower() for f in supported_formats)
        for idx, queryset in enumerate(querysets):
            for format in all_formats:
                with self.subTest(format=format, queryset=idx):
                    if connection.vendor == 'mysql':
                        # This does a query and caches the result.
                        connection.features.needs_explain_extended
                    with self.assertNumQueries(1), CaptureQueriesContext(connection) as captured_queries:
                        result = queryset.explain(format=format)
                        self.assertTrue(captured_queries[0]['sql'].startswith(connection.ops.explain_prefix))
                        self.assertIsInstance(result, str)
                        self.assertTrue(result)

    @skipUnlessDBFeature('validates_explain_options')
    def test_unknown_options(self):
        with self.assertRaisesMessage(ValueError, 'Unknown options: test, test2'):
            Tag.objects.all().explain(test=1, test2=1)

    def test_unknown_format(self):
        msg = 'DOES NOT EXIST is not a recognized format.'
        if connection.features.supported_explain_formats:
            msg += ' Allowed formats: %s' % ', '.join(sorted(connection.features.supported_explain_formats))
        with self.assertRaisesMessage(ValueError, msg):
            Tag.objects.all().explain(format='does not exist')

    @unittest.skipUnless(connection.vendor == 'postgresql', 'PostgreSQL specific')
    def test_postgres_options(self):
        qs = Tag.objects.filter(name='test')
        test_options = [
            {'COSTS': False, 'BUFFERS': True, 'ANALYZE': True},
            {'costs': False, 'buffers': True, 'analyze': True},
            {'verbose': True, 'timing': True, 'analyze': True},
            {'verbose': False, 'timing': False, 'analyze': True},
        ]
        if connection.pg_version >= 100000:
            test_options.append({'summary': True})
        for options in test_options:
            with self.subTest(**options), transaction.atomic():
                with CaptureQueriesContext(connection) as captured_queries:
                    qs.explain(format='text', **options)
                self.assertEqual(len(captured_queries), 1)
                for name, value in options.items():
                    option = '{} {}'.format(name.upper(), 'true' if value else 'false')
                    self.assertIn(option, captured_queries[0]['sql'])

    @unittest.skipUnless(connection.vendor == 'mysql', 'MySQL specific')
    def test_mysql_text_to_traditional(self):
        with CaptureQueriesContext(connection) as captured_queries:
            Tag.objects.filter(name='test').explain(format='text')
        self.assertEqual(len(captured_queries), 1)
        self.assertIn('FORMAT=TRADITIONAL', captured_queries[0]['sql'])

    @unittest.skipUnless(connection.vendor == 'mysql', 'MySQL < 5.7 specific')
    def test_mysql_extended(self):
        # Inner skip to avoid module level query for MySQL version.
        if not connection.features.needs_explain_extended:
            raise unittest.SkipTest('MySQL < 5.7 specific')
        qs = Tag.objects.filter(name='test')
        with CaptureQueriesContext(connection) as captured_queries:
            qs.explain(format='json')
        self.assertEqual(len(captured_queries), 1)
        self.assertNotIn('EXTENDED', captured_queries[0]['sql'])
        with CaptureQueriesContext(connection) as captured_queries:
            qs.explain(format='text')
        self.assertEqual(len(captured_queries), 1)
        self.assertNotIn('EXTENDED', captured_queries[0]['sql'])


@skipIfDBFeature('supports_explaining_query_execution')
class ExplainUnsupportedTests(TestCase):

    def test_message(self):
        msg = 'This backend does not support explaining query execution.'
        with self.assertRaisesMessage(NotSupportedError, msg):
            Tag.objects.filter(name='test').explain()
