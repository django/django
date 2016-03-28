from __future__ import unicode_literals

import datetime
from decimal import Decimal

from django.core.exceptions import FieldDoesNotExist, FieldError
from django.db.models import (
    BooleanField, CharField, Count, DateTimeField, ExpressionWrapper, F, Func,
    IntegerField, Sum, Value,
)
from django.test import TestCase
from django.utils import six

from .models import (
    Author, Book, Company, DepartmentStore, Employee, Store, Ticket,
)


def cxOracle_py3_bug(func):
    """
    There's a bug in Django/cx_Oracle with respect to string handling under
    Python 3 (essentially, they treat Python 3 strings as Python 2 strings
    rather than unicode). This makes some tests here fail under Python 3, so
    we mark them as expected failures until someone fixes them in #23843.
    """
    from unittest import expectedFailure
    from django.db import connection
    return expectedFailure(func) if connection.vendor == 'oracle' and six.PY3 else func


class NonAggregateAnnotationTestCase(TestCase):
    fixtures = ["annotations.json"]

    def test_basic_annotation(self):
        books = Book.objects.annotate(
            is_book=Value(1, output_field=IntegerField()))
        for book in books:
            self.assertEqual(book.is_book, 1)

    def test_basic_f_annotation(self):
        books = Book.objects.annotate(another_rating=F('rating'))
        for book in books:
            self.assertEqual(book.another_rating, book.rating)

    def test_joined_annotation(self):
        books = Book.objects.select_related('publisher').annotate(
            num_awards=F('publisher__num_awards'))
        for book in books:
            self.assertEqual(book.num_awards, book.publisher.num_awards)

    def test_mixed_type_annotation_date_interval(self):
        active = datetime.datetime(2015, 3, 20, 14, 0, 0)
        duration = datetime.timedelta(hours=1)
        expires = datetime.datetime(2015, 3, 20, 14, 0, 0) + duration
        Ticket.objects.create(active_at=active, duration=duration)
        t = Ticket.objects.annotate(
            expires=ExpressionWrapper(F('active_at') + F('duration'), output_field=DateTimeField())
        ).first()
        self.assertEqual(t.expires, expires)

    def test_mixed_type_annotation_numbers(self):
        test = Book.objects.get(isbn='159059725')
        b = Book.objects.annotate(
            combined=ExpressionWrapper(F('pages') + F('rating'), output_field=IntegerField())
        ).get(isbn=test.isbn)
        combined = int(test.pages + test.rating)
        self.assertEqual(b.combined, combined)

    def test_annotate_with_aggregation(self):
        books = Book.objects.annotate(
            is_book=Value(1, output_field=IntegerField()),
            rating_count=Count('rating'))
        for book in books:
            self.assertEqual(book.is_book, 1)
            self.assertEqual(book.rating_count, 1)

    def test_aggregate_over_annotation(self):
        agg = Author.objects.annotate(other_age=F('age')).aggregate(otherage_sum=Sum('other_age'))
        other_agg = Author.objects.aggregate(age_sum=Sum('age'))
        self.assertEqual(agg['otherage_sum'], other_agg['age_sum'])

    def test_filter_annotation(self):
        books = Book.objects.annotate(
            is_book=Value(1, output_field=IntegerField())
        ).filter(is_book=1)
        for book in books:
            self.assertEqual(book.is_book, 1)

    def test_filter_annotation_with_f(self):
        books = Book.objects.annotate(
            other_rating=F('rating')
        ).filter(other_rating=3.5)
        for book in books:
            self.assertEqual(book.other_rating, 3.5)

    def test_filter_annotation_with_double_f(self):
        books = Book.objects.annotate(
            other_rating=F('rating')
        ).filter(other_rating=F('rating'))
        for book in books:
            self.assertEqual(book.other_rating, book.rating)

    def test_filter_agg_with_double_f(self):
        books = Book.objects.annotate(
            sum_rating=Sum('rating')
        ).filter(sum_rating=F('sum_rating'))
        for book in books:
            self.assertEqual(book.sum_rating, book.rating)

    def test_filter_wrong_annotation(self):
        with six.assertRaisesRegex(self, FieldError, "Cannot resolve keyword .*"):
            list(Book.objects.annotate(
                sum_rating=Sum('rating')
            ).filter(sum_rating=F('nope')))

    def test_combined_annotation_commutative(self):
        b1 = Book.objects.get(isbn='159059725')
        book1 = Book.objects.annotate(adjusted_rating=F('rating') + 2).get(pk=b1.pk)
        book2 = Book.objects.annotate(adjusted_rating=2 + F('rating')).get(pk=b1.pk)
        self.assertEqual(book1.adjusted_rating, book2.adjusted_rating)
        book1 = Book.objects.annotate(adjusted_rating=F('rating') + None).get(pk=b1.pk)
        book2 = Book.objects.annotate(adjusted_rating=None + F('rating')).get(pk=b1.pk)
        self.assertEqual(book1.adjusted_rating, book2.adjusted_rating)

    def test_update_with_annotation(self):
        book_preupdate = Book.objects.get(pk=2)
        Book.objects.annotate(other_rating=F('rating') - 1).update(rating=F('other_rating'))
        book_postupdate = Book.objects.get(pk=2)
        self.assertEqual(book_preupdate.rating - 1, book_postupdate.rating)

    def test_annotation_with_m2m(self):
        books = Book.objects.annotate(author_age=F('authors__age')).filter(pk=1).order_by('author_age')
        self.assertEqual(books[0].author_age, 34)
        self.assertEqual(books[1].author_age, 35)

    def test_annotation_reverse_m2m(self):
        books = Book.objects.annotate(
            store_name=F('store__name')).filter(
            name='Practical Django Projects').order_by(
            'store_name')

        self.assertQuerysetEqual(
            books, [
                'Amazon.com',
                'Books.com',
                'Mamma and Pappa\'s Books'
            ],
            lambda b: b.store_name
        )

    def test_values_annotation(self):
        """
        Annotations can reference fields in a values clause,
        and contribute to an existing values clause.
        """
        # annotate references a field in values()
        qs = Book.objects.values('rating').annotate(other_rating=F('rating') - 1)
        book = qs.get(pk=1)
        self.assertEqual(book['rating'] - 1, book['other_rating'])

        # filter refs the annotated value
        book = qs.get(other_rating=4)
        self.assertEqual(book['other_rating'], 4)

        # can annotate an existing values with a new field
        book = qs.annotate(other_isbn=F('isbn')).get(other_rating=4)
        self.assertEqual(book['other_rating'], 4)
        self.assertEqual(book['other_isbn'], '155860191')

    def test_defer_annotation(self):
        """
        Deferred attributes can be referenced by an annotation,
        but they are not themselves deferred, and cannot be deferred.
        """
        qs = Book.objects.defer('rating').annotate(other_rating=F('rating') - 1)

        with self.assertNumQueries(2):
            book = qs.get(other_rating=4)
            self.assertEqual(book.rating, 5)
            self.assertEqual(book.other_rating, 4)

        with six.assertRaisesRegex(self, FieldDoesNotExist, "\w has no field named u?'other_rating'"):
            book = qs.defer('other_rating').get(other_rating=4)

    def test_mti_annotations(self):
        """
        Fields on an inherited model can be referenced by an
        annotated field.
        """
        d = DepartmentStore.objects.create(
            name='Angus & Robinson',
            original_opening=datetime.date(2014, 3, 8),
            friday_night_closing=datetime.time(21, 00, 00),
            chain='Westfield'
        )

        books = Book.objects.filter(rating__gt=4)
        for b in books:
            d.books.add(b)

        qs = DepartmentStore.objects.annotate(
            other_name=F('name'),
            other_chain=F('chain'),
            is_open=Value(True, BooleanField()),
            book_isbn=F('books__isbn')
        ).order_by('book_isbn').filter(chain='Westfield')

        self.assertQuerysetEqual(
            qs, [
                ('Angus & Robinson', 'Westfield', True, '155860191'),
                ('Angus & Robinson', 'Westfield', True, '159059725')
            ],
            lambda d: (d.other_name, d.other_chain, d.is_open, d.book_isbn)
        )

    def test_null_annotation(self):
        """
        Test that annotating None onto a model round-trips
        """
        book = Book.objects.annotate(no_value=Value(None, output_field=IntegerField())).first()
        self.assertIsNone(book.no_value)

    def test_order_by_annotation(self):
        authors = Author.objects.annotate(other_age=F('age')).order_by('other_age')
        self.assertQuerysetEqual(
            authors, [
                25, 29, 29, 34, 35, 37, 45, 46, 57,
            ],
            lambda a: a.other_age
        )

    def test_order_by_aggregate(self):
        authors = Author.objects.values('age').annotate(age_count=Count('age')).order_by('age_count', 'age')
        self.assertQuerysetEqual(
            authors, [
                (25, 1), (34, 1), (35, 1), (37, 1), (45, 1), (46, 1), (57, 1), (29, 2),
            ],
            lambda a: (a['age'], a['age_count'])
        )

    def test_annotate_exists(self):
        authors = Author.objects.annotate(c=Count('id')).filter(c__gt=1)
        self.assertFalse(authors.exists())

    def test_column_field_ordering(self):
        """
        Test that columns are aligned in the correct order for
        resolve_columns. This test will fail on mysql if column
        ordering is out. Column fields should be aligned as:
        1. extra_select
        2. model_fields
        3. annotation_fields
        4. model_related_fields
        """
        store = Store.objects.first()
        Employee.objects.create(id=1, first_name='Max', manager=True, last_name='Paine',
                                store=store, age=23, salary=Decimal(50000.00))
        Employee.objects.create(id=2, first_name='Buffy', manager=False, last_name='Summers',
                                store=store, age=18, salary=Decimal(40000.00))

        qs = Employee.objects.extra(
            select={'random_value': '42'}
        ).select_related('store').annotate(
            annotated_value=Value(17, output_field=IntegerField())
        )

        rows = [
            (1, 'Max', True, 42, 'Paine', 23, Decimal(50000.00), store.name, 17),
            (2, 'Buffy', False, 42, 'Summers', 18, Decimal(40000.00), store.name, 17)
        ]

        self.assertQuerysetEqual(
            qs.order_by('id'), rows,
            lambda e: (
                e.id, e.first_name, e.manager, e.random_value, e.last_name, e.age,
                e.salary, e.store.name, e.annotated_value))

    def test_column_field_ordering_with_deferred(self):
        store = Store.objects.first()
        Employee.objects.create(id=1, first_name='Max', manager=True, last_name='Paine',
                                store=store, age=23, salary=Decimal(50000.00))
        Employee.objects.create(id=2, first_name='Buffy', manager=False, last_name='Summers',
                                store=store, age=18, salary=Decimal(40000.00))

        qs = Employee.objects.extra(
            select={'random_value': '42'}
        ).select_related('store').annotate(
            annotated_value=Value(17, output_field=IntegerField())
        )

        rows = [
            (1, 'Max', True, 42, 'Paine', 23, Decimal(50000.00), store.name, 17),
            (2, 'Buffy', False, 42, 'Summers', 18, Decimal(40000.00), store.name, 17)
        ]

        # and we respect deferred columns!
        self.assertQuerysetEqual(
            qs.defer('age').order_by('id'), rows,
            lambda e: (
                e.id, e.first_name, e.manager, e.random_value, e.last_name, e.age,
                e.salary, e.store.name, e.annotated_value))

    @cxOracle_py3_bug
    def test_custom_functions(self):
        Company(name='Apple', motto=None, ticker_name='APPL', description='Beautiful Devices').save()
        Company(name='Django Software Foundation', motto=None, ticker_name=None, description=None).save()
        Company(name='Google', motto='Do No Evil', ticker_name='GOOG', description='Internet Company').save()
        Company(name='Yahoo', motto=None, ticker_name=None, description='Internet Company').save()

        qs = Company.objects.annotate(
            tagline=Func(
                F('motto'),
                F('ticker_name'),
                F('description'),
                Value('No Tag'),
                function='COALESCE')
            ).order_by('name')

        self.assertQuerysetEqual(
            qs, [
                ('Apple', 'APPL'),
                ('Django Software Foundation', 'No Tag'),
                ('Google', 'Do No Evil'),
                ('Yahoo', 'Internet Company')
            ],
            lambda c: (c.name, c.tagline)
        )

    @cxOracle_py3_bug
    def test_custom_functions_can_ref_other_functions(self):
        Company(name='Apple', motto=None, ticker_name='APPL', description='Beautiful Devices').save()
        Company(name='Django Software Foundation', motto=None, ticker_name=None, description=None).save()
        Company(name='Google', motto='Do No Evil', ticker_name='GOOG', description='Internet Company').save()
        Company(name='Yahoo', motto=None, ticker_name=None, description='Internet Company').save()

        class Lower(Func):
            function = 'LOWER'

        qs = Company.objects.annotate(
            tagline=Func(
                F('motto'),
                F('ticker_name'),
                F('description'),
                Value('No Tag'),
                function='COALESCE')
        ).annotate(
            tagline_lower=Lower(F('tagline'), output_field=CharField())
        ).order_by('name')

        # LOWER function supported by:
        # oracle, postgres, mysql, sqlite, sqlserver

        self.assertQuerysetEqual(
            qs, [
                ('Apple', 'APPL'.lower()),
                ('Django Software Foundation', 'No Tag'.lower()),
                ('Google', 'Do No Evil'.lower()),
                ('Yahoo', 'Internet Company'.lower())
            ],
            lambda c: (c.name, c.tagline_lower)
        )
