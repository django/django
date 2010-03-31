from django.conf import settings
from django.test import TestCase
from django.db import DEFAULT_DB_ALIAS
from django.db.models import Count, Max

from regressiontests.aggregation_regress.models import *


class AggregationTests(TestCase):

    def test_aggregates_in_where_clause(self):
        """
        Regression test for #12822: DatabaseError: aggregates not allowed in
        WHERE clause

        Tests that the subselect works and returns results equivalent to a
        query with the IDs listed.

        Before the corresponding fix for this bug, this test passed in 1.1 and
        failed in 1.2-beta (trunk).
        """
        qs = Book.objects.values('contact').annotate(Max('id'))
        qs = qs.order_by('contact').values_list('id__max', flat=True)
        # don't do anything with the queryset (qs) before including it as a
        # subquery
        books = Book.objects.order_by('id')
        qs1 = books.filter(id__in=qs)
        qs2 = books.filter(id__in=list(qs))
        self.assertEqual(list(qs1), list(qs2))

    def test_aggregates_in_where_clause_pre_eval(self):
        """
        Regression test for #12822: DatabaseError: aggregates not allowed in
        WHERE clause

        Same as the above test, but evaluates the queryset for the subquery
        before it's used as a subquery.

        Before the corresponding fix for this bug, this test failed in both
        1.1 and 1.2-beta (trunk).
        """
        qs = Book.objects.values('contact').annotate(Max('id'))
        qs = qs.order_by('contact').values_list('id__max', flat=True)
        # force the queryset (qs) for the subquery to be evaluated in its
        # current state
        list(qs)
        books = Book.objects.order_by('id')
        qs1 = books.filter(id__in=qs)
        qs2 = books.filter(id__in=list(qs))
        self.assertEqual(list(qs1), list(qs2))

    if settings.DATABASES[DEFAULT_DB_ALIAS]['ENGINE'] != 'django.db.backends.oracle':
        def test_annotate_with_extra(self):
            """
            Regression test for #11916: Extra params + aggregation creates
            incorrect SQL.
            """
            #oracle doesn't support subqueries in group by clause
            shortest_book_sql = """
            SELECT name
            FROM aggregation_regress_book b
            WHERE b.publisher_id = aggregation_regress_publisher.id
            ORDER BY b.pages
            LIMIT 1
            """
            # tests that this query does not raise a DatabaseError due to the full
            # subselect being (erroneously) added to the GROUP BY parameters
            qs = Publisher.objects.extra(select={
                'name_of_shortest_book': shortest_book_sql,
            }).annotate(total_books=Count('book'))
            # force execution of the query
            list(qs)
