import datetime
from decimal import Decimal
from unittest import skipIf

from django.core.exceptions import FieldDoesNotExist, FieldError
from django.db import connection
from django.db.models import (
    BooleanField, Case, CharField, Count, DateTimeField, Exists,
    ExpressionWrapper, F, Func, IntegerField, Max, NullBooleanField, OuterRef,
    Q, Subquery, Sum, Value, When,
)
from django.db.models.expressions import RawSQL
from django.db.models.functions import ExtractYear, Length, Lower
from django.test import TestCase, skipUnlessDBFeature

from .models import (
    Author, Book, Company, DepartmentStore, Employee, Publisher, Store, Ticket,
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
    return expectedFailure(func) if connection.vendor == 'oracle' else func


class NonAggregateAnnotationTestCase(TestCase):

    @classmethod
    def setUpTestData(cls):
        cls.a1 = Author.objects.create(name='Adrian Holovaty', age=34)
        cls.a2 = Author.objects.create(name='Jacob Kaplan-Moss', age=35)
        cls.a3 = Author.objects.create(name='Brad Dayley', age=45)
        cls.a4 = Author.objects.create(name='James Bennett', age=29)
        cls.a5 = Author.objects.create(name='Jeffrey Forcier', age=37)
        cls.a6 = Author.objects.create(name='Paul Bissex', age=29)
        cls.a7 = Author.objects.create(name='Wesley J. Chun', age=25)
        cls.a8 = Author.objects.create(name='Peter Norvig', age=57)
        cls.a9 = Author.objects.create(name='Stuart Russell', age=46)
        cls.a1.friends.add(cls.a2, cls.a4)
        cls.a2.friends.add(cls.a1, cls.a7)
        cls.a4.friends.add(cls.a1)
        cls.a5.friends.add(cls.a6, cls.a7)
        cls.a6.friends.add(cls.a5, cls.a7)
        cls.a7.friends.add(cls.a2, cls.a5, cls.a6)
        cls.a8.friends.add(cls.a9)
        cls.a9.friends.add(cls.a8)

        cls.p1 = Publisher.objects.create(name='Apress', num_awards=3)
        cls.p2 = Publisher.objects.create(name='Sams', num_awards=1)
        cls.p3 = Publisher.objects.create(name='Prentice Hall', num_awards=7)
        cls.p4 = Publisher.objects.create(name='Morgan Kaufmann', num_awards=9)
        cls.p5 = Publisher.objects.create(name="Jonno's House of Books", num_awards=0)

        cls.b1 = Book.objects.create(
            isbn='159059725', name='The Definitive Guide to Django: Web Development Done Right',
            pages=447, rating=4.5, price=Decimal('30.00'), contact=cls.a1, publisher=cls.p1,
            pubdate=datetime.date(2007, 12, 6)
        )
        cls.b2 = Book.objects.create(
            isbn='067232959', name='Sams Teach Yourself Django in 24 Hours',
            pages=528, rating=3.0, price=Decimal('23.09'), contact=cls.a3, publisher=cls.p2,
            pubdate=datetime.date(2008, 3, 3)
        )
        cls.b3 = Book.objects.create(
            isbn='159059996', name='Practical Django Projects',
            pages=300, rating=4.0, price=Decimal('29.69'), contact=cls.a4, publisher=cls.p1,
            pubdate=datetime.date(2008, 6, 23)
        )
        cls.b4 = Book.objects.create(
            isbn='013235613', name='Python Web Development with Django',
            pages=350, rating=4.0, price=Decimal('29.69'), contact=cls.a5, publisher=cls.p3,
            pubdate=datetime.date(2008, 11, 3)
        )
        cls.b5 = Book.objects.create(
            isbn='013790395', name='Artificial Intelligence: A Modern Approach',
            pages=1132, rating=4.0, price=Decimal('82.80'), contact=cls.a8, publisher=cls.p3,
            pubdate=datetime.date(1995, 1, 15)
        )
        cls.b6 = Book.objects.create(
            isbn='155860191', name='Paradigms of Artificial Intelligence Programming: Case Studies in Common Lisp',
            pages=946, rating=5.0, price=Decimal('75.00'), contact=cls.a8, publisher=cls.p4,
            pubdate=datetime.date(1991, 10, 15)
        )
        cls.b1.authors.add(cls.a1, cls.a2)
        cls.b2.authors.add(cls.a3)
        cls.b3.authors.add(cls.a4)
        cls.b4.authors.add(cls.a5, cls.a6, cls.a7)
        cls.b5.authors.add(cls.a8, cls.a9)
        cls.b6.authors.add(cls.a8)

        s1 = Store.objects.create(
            name='Amazon.com',
            original_opening=datetime.datetime(1994, 4, 23, 9, 17, 42),
            friday_night_closing=datetime.time(23, 59, 59)
        )
        s2 = Store.objects.create(
            name='Books.com',
            original_opening=datetime.datetime(2001, 3, 15, 11, 23, 37),
            friday_night_closing=datetime.time(23, 59, 59)
        )
        s3 = Store.objects.create(
            name="Mamma and Pappa's Books",
            original_opening=datetime.datetime(1945, 4, 25, 16, 24, 14),
            friday_night_closing=datetime.time(21, 30)
        )
        s1.books.add(cls.b1, cls.b2, cls.b3, cls.b4, cls.b5, cls.b6)
        s2.books.add(cls.b1, cls.b3, cls.b5, cls.b6)
        s3.books.add(cls.b3, cls.b4, cls.b6)

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
        test = self.b1
        b = Book.objects.annotate(
            combined=ExpressionWrapper(F('pages') + F('rating'), output_field=IntegerField())
        ).get(isbn=test.isbn)
        combined = int(test.pages + test.rating)
        self.assertEqual(b.combined, combined)

    def test_empty_expression_annotation(self):
        books = Book.objects.annotate(
            selected=ExpressionWrapper(Q(pk__in=[]), output_field=BooleanField())
        )
        self.assertEqual(len(books), Book.objects.count())
        self.assertTrue(all(not book.selected for book in books))

        books = Book.objects.annotate(
            selected=ExpressionWrapper(Q(pk__in=Book.objects.none()), output_field=BooleanField())
        )
        self.assertEqual(len(books), Book.objects.count())
        self.assertTrue(all(not book.selected for book in books))

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

    @skipUnlessDBFeature('can_distinct_on_fields')
    def test_distinct_on_with_annotation(self):
        store = Store.objects.create(
            name='test store',
            original_opening=datetime.datetime.now(),
            friday_night_closing=datetime.time(21, 00, 00),
        )
        names = [
            'Theodore Roosevelt',
            'Eleanor Roosevelt',
            'Franklin Roosevelt',
            'Ned Stark',
            'Catelyn Stark',
        ]
        for name in names:
            Employee.objects.create(
                store=store,
                first_name=name.split()[0],
                last_name=name.split()[1],
                age=30, salary=2000,
            )

        people = Employee.objects.annotate(
            name_lower=Lower('last_name'),
        ).distinct('name_lower')

        self.assertEqual({p.last_name for p in people}, {'Stark', 'Roosevelt'})
        self.assertEqual(len(people), 2)

        people2 = Employee.objects.annotate(
            test_alias=F('store__name'),
        ).distinct('test_alias')
        self.assertEqual(len(people2), 1)

        lengths = Employee.objects.annotate(
            name_len=Length('first_name'),
        ).distinct('name_len').values_list('name_len', flat=True)
        self.assertSequenceEqual(lengths, [3, 7, 8])

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
        with self.assertRaisesMessage(FieldError, "Cannot resolve keyword 'nope' into field."):
            list(Book.objects.annotate(
                sum_rating=Sum('rating')
            ).filter(sum_rating=F('nope')))

    def test_decimal_annotation(self):
        salary = Decimal(10) ** -Employee._meta.get_field('salary').decimal_places
        Employee.objects.create(
            first_name='Max',
            last_name='Paine',
            store=Store.objects.first(),
            age=23,
            salary=salary,
        )
        self.assertEqual(
            Employee.objects.annotate(new_salary=F('salary') / 10).get().new_salary,
            salary / 10,
        )

    def test_filter_decimal_annotation(self):
        qs = Book.objects.annotate(new_price=F('price') + 1).filter(new_price=Decimal(31)).values_list('new_price')
        self.assertEqual(qs.get(), (Decimal(31),))

    def test_combined_annotation_commutative(self):
        book1 = Book.objects.annotate(adjusted_rating=F('rating') + 2).get(pk=self.b1.pk)
        book2 = Book.objects.annotate(adjusted_rating=2 + F('rating')).get(pk=self.b1.pk)
        self.assertEqual(book1.adjusted_rating, book2.adjusted_rating)
        book1 = Book.objects.annotate(adjusted_rating=F('rating') + None).get(pk=self.b1.pk)
        book2 = Book.objects.annotate(adjusted_rating=None + F('rating')).get(pk=self.b1.pk)
        self.assertEqual(book1.adjusted_rating, book2.adjusted_rating)

    def test_update_with_annotation(self):
        book_preupdate = Book.objects.get(pk=self.b2.pk)
        Book.objects.annotate(other_rating=F('rating') - 1).update(rating=F('other_rating'))
        book_postupdate = Book.objects.get(pk=self.b2.pk)
        self.assertEqual(book_preupdate.rating - 1, book_postupdate.rating)

    def test_annotation_with_m2m(self):
        books = Book.objects.annotate(author_age=F('authors__age')).filter(pk=self.b1.pk).order_by('author_age')
        self.assertEqual(books[0].author_age, 34)
        self.assertEqual(books[1].author_age, 35)

    def test_annotation_reverse_m2m(self):
        books = Book.objects.annotate(
            store_name=F('store__name'),
        ).filter(
            name='Practical Django Projects',
        ).order_by('store_name')

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
        book = qs.get(pk=self.b1.pk)
        self.assertEqual(book['rating'] - 1, book['other_rating'])

        # filter refs the annotated value
        book = qs.get(other_rating=4)
        self.assertEqual(book['other_rating'], 4)

        # can annotate an existing values with a new field
        book = qs.annotate(other_isbn=F('isbn')).get(other_rating=4)
        self.assertEqual(book['other_rating'], 4)
        self.assertEqual(book['other_isbn'], '155860191')

    def test_values_with_pk_annotation(self):
        # annotate references a field in values() with pk
        publishers = Publisher.objects.values('id', 'book__rating').annotate(total=Sum('book__rating'))
        for publisher in publishers.filter(pk=self.p1.pk):
            self.assertEqual(publisher['book__rating'], publisher['total'])

    @skipUnlessDBFeature('allows_group_by_pk')
    def test_rawsql_group_by_collapse(self):
        raw = RawSQL('SELECT MIN(id) FROM annotations_book', [])
        qs = Author.objects.values('id').annotate(
            min_book_id=raw,
            count_friends=Count('friends'),
        ).order_by()
        _, _, group_by = qs.query.get_compiler(using='default').pre_sql_setup()
        self.assertEqual(len(group_by), 1)
        self.assertNotEqual(raw, group_by[0])

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

        with self.assertRaisesMessage(FieldDoesNotExist, "Book has no field named 'other_rating'"):
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
        Annotating None onto a model round-trips
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

    def test_raw_sql_with_inherited_field(self):
        DepartmentStore.objects.create(
            name='Angus & Robinson',
            original_opening=datetime.date(2014, 3, 8),
            friday_night_closing=datetime.time(21),
            chain='Westfield',
            area=123,
        )
        tests = (
            ('name', 'Angus & Robinson'),
            ('surface', 123),
            ("case when name='Angus & Robinson' then chain else name end", 'Westfield'),
        )
        for sql, expected_result in tests:
            with self.subTest(sql=sql):
                self.assertSequenceEqual(
                    DepartmentStore.objects.annotate(
                        annotation=RawSQL(sql, ()),
                    ).values_list('annotation', flat=True),
                    [expected_result],
                )

    def test_annotate_exists(self):
        authors = Author.objects.annotate(c=Count('id')).filter(c__gt=1)
        self.assertFalse(authors.exists())

    def test_column_field_ordering(self):
        """
        Columns are aligned in the correct order for resolve_columns. This test
        will fail on MySQL if column ordering is out. Column fields should be
        aligned as:
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
                function='COALESCE'
            )
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
                function='COALESCE',
            )
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

    def test_boolean_value_annotation(self):
        books = Book.objects.annotate(
            is_book=Value(True, output_field=BooleanField()),
            is_pony=Value(False, output_field=BooleanField()),
            is_none=Value(None, output_field=BooleanField(null=True)),
            is_none_old=Value(None, output_field=NullBooleanField()),
        )
        self.assertGreater(len(books), 0)
        for book in books:
            self.assertIs(book.is_book, True)
            self.assertIs(book.is_pony, False)
            self.assertIsNone(book.is_none)
            self.assertIsNone(book.is_none_old)

    def test_annotation_in_f_grouped_by_annotation(self):
        qs = (
            Publisher.objects.annotate(multiplier=Value(3))
            # group by option => sum of value * multiplier
            .values('name')
            .annotate(multiplied_value_sum=Sum(F('multiplier') * F('num_awards')))
            .order_by()
        )
        self.assertCountEqual(
            qs, [
                {'multiplied_value_sum': 9, 'name': 'Apress'},
                {'multiplied_value_sum': 0, 'name': "Jonno's House of Books"},
                {'multiplied_value_sum': 27, 'name': 'Morgan Kaufmann'},
                {'multiplied_value_sum': 21, 'name': 'Prentice Hall'},
                {'multiplied_value_sum': 3, 'name': 'Sams'},
            ]
        )

    def test_arguments_must_be_expressions(self):
        msg = 'QuerySet.annotate() received non-expression(s): %s.'
        with self.assertRaisesMessage(TypeError, msg % BooleanField()):
            Book.objects.annotate(BooleanField())
        with self.assertRaisesMessage(TypeError, msg % True):
            Book.objects.annotate(is_book=True)
        with self.assertRaisesMessage(TypeError, msg % ', '.join([str(BooleanField()), 'True'])):
            Book.objects.annotate(BooleanField(), Value(False), is_book=True)

    def test_chaining_annotation_filter_with_m2m(self):
        qs = Author.objects.filter(
            name='Adrian Holovaty',
            friends__age=35,
        ).annotate(
            jacob_name=F('friends__name'),
        ).filter(
            friends__age=29,
        ).annotate(
            james_name=F('friends__name'),
        ).values('jacob_name', 'james_name')
        self.assertCountEqual(
            qs,
            [{'jacob_name': 'Jacob Kaplan-Moss', 'james_name': 'James Bennett'}],
        )

    def test_annotation_filter_with_subquery(self):
        long_books_qs = Book.objects.filter(
            publisher=OuterRef('pk'),
            pages__gt=400,
        ).values('publisher').annotate(count=Count('pk')).values('count')
        publisher_books_qs = Publisher.objects.annotate(
            total_books=Count('book'),
        ).filter(
            total_books=Subquery(long_books_qs, output_field=IntegerField()),
        ).values('name')
        self.assertCountEqual(publisher_books_qs, [{'name': 'Sams'}, {'name': 'Morgan Kaufmann'}])

    def test_annotation_exists_aggregate_values_chaining(self):
        qs = Book.objects.values('publisher').annotate(
            has_authors=Exists(Book.authors.through.objects.filter(book=OuterRef('pk'))),
            max_pubdate=Max('pubdate'),
        ).values_list('max_pubdate', flat=True).order_by('max_pubdate')
        self.assertCountEqual(qs, [
            datetime.date(1991, 10, 15),
            datetime.date(2008, 3, 3),
            datetime.date(2008, 6, 23),
            datetime.date(2008, 11, 3),
        ])

    @skipUnlessDBFeature('supports_subqueries_in_group_by')
    def test_annotation_subquery_and_aggregate_values_chaining(self):
        qs = Book.objects.annotate(
            pub_year=ExtractYear('pubdate')
        ).values('pub_year').annotate(
            top_rating=Subquery(
                Book.objects.filter(
                    pubdate__year=OuterRef('pub_year')
                ).order_by('-rating').values('rating')[:1]
            ),
            total_pages=Sum('pages'),
        ).values('pub_year', 'total_pages', 'top_rating')
        self.assertCountEqual(qs, [
            {'pub_year': 1991, 'top_rating': 5.0, 'total_pages': 946},
            {'pub_year': 1995, 'top_rating': 4.0, 'total_pages': 1132},
            {'pub_year': 2007, 'top_rating': 4.5, 'total_pages': 447},
            {'pub_year': 2008, 'top_rating': 4.0, 'total_pages': 1178},
        ])

    @skipIf(
        connection.vendor == 'mysql',
        'GROUP BY optimization does not work properly when ONLY_FULL_GROUP_BY '
        'mode is enabled on MySQL, see #31331.',
    )
    def test_annotation_aggregate_with_m2o(self):
        qs = Author.objects.filter(age__lt=30).annotate(
            max_pages=Case(
                When(book_contact_set__isnull=True, then=Value(0)),
                default=Max(F('book__pages')),
                output_field=IntegerField(),
            ),
        ).values('name', 'max_pages')
        self.assertCountEqual(qs, [
            {'name': 'James Bennett', 'max_pages': 300},
            {'name': 'Paul Bissex', 'max_pages': 0},
            {'name': 'Wesley J. Chun', 'max_pages': 0},
        ])
