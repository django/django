from __future__ import unicode_literals

import datetime
import re
from decimal import Decimal

from django.core.exceptions import FieldError
from django.db import connection
from django.db.models import (
    F, Aggregate, Avg, Count, DecimalField, FloatField, Func, IntegerField,
    Max, Min, Sum, Value,
)
from django.test import TestCase, ignore_warnings
from django.test.utils import Approximate, CaptureQueriesContext
from django.utils import six, timezone
from django.utils.deprecation import RemovedInDjango110Warning

from .models import Author, Book, Publisher, Store


class BaseAggregateTestCase(TestCase):
    fixtures = ["aggregation.json"]

    def test_empty_aggregate(self):
        self.assertEqual(Author.objects.all().aggregate(), {})

    def test_single_aggregate(self):
        vals = Author.objects.aggregate(Avg("age"))
        self.assertEqual(vals, {"age__avg": Approximate(37.4, places=1)})

    def test_multiple_aggregates(self):
        vals = Author.objects.aggregate(Sum("age"), Avg("age"))
        self.assertEqual(vals, {"age__sum": 337, "age__avg": Approximate(37.4, places=1)})

    def test_filter_aggregate(self):
        vals = Author.objects.filter(age__gt=29).aggregate(Sum("age"))
        self.assertEqual(len(vals), 1)
        self.assertEqual(vals["age__sum"], 254)

    def test_related_aggregate(self):
        vals = Author.objects.aggregate(Avg("friends__age"))
        self.assertEqual(len(vals), 1)
        self.assertAlmostEqual(vals["friends__age__avg"], 34.07, places=2)

        vals = Book.objects.filter(rating__lt=4.5).aggregate(Avg("authors__age"))
        self.assertEqual(len(vals), 1)
        self.assertAlmostEqual(vals["authors__age__avg"], 38.2857, places=2)

        vals = Author.objects.all().filter(name__contains="a").aggregate(Avg("book__rating"))
        self.assertEqual(len(vals), 1)
        self.assertEqual(vals["book__rating__avg"], 4.0)

        vals = Book.objects.aggregate(Sum("publisher__num_awards"))
        self.assertEqual(len(vals), 1)
        self.assertEqual(vals["publisher__num_awards__sum"], 30)

        vals = Publisher.objects.aggregate(Sum("book__price"))
        self.assertEqual(len(vals), 1)
        self.assertEqual(vals["book__price__sum"], Decimal("270.27"))

    def test_aggregate_multi_join(self):
        vals = Store.objects.aggregate(Max("books__authors__age"))
        self.assertEqual(len(vals), 1)
        self.assertEqual(vals["books__authors__age__max"], 57)

        vals = Author.objects.aggregate(Min("book__publisher__num_awards"))
        self.assertEqual(len(vals), 1)
        self.assertEqual(vals["book__publisher__num_awards__min"], 1)

    def test_aggregate_alias(self):
        vals = Store.objects.filter(name="Amazon.com").aggregate(amazon_mean=Avg("books__rating"))
        self.assertEqual(len(vals), 1)
        self.assertAlmostEqual(vals["amazon_mean"], 4.08, places=2)

    def test_annotate_basic(self):
        self.assertQuerysetEqual(
            Book.objects.annotate().order_by('pk'), [
                "The Definitive Guide to Django: Web Development Done Right",
                "Sams Teach Yourself Django in 24 Hours",
                "Practical Django Projects",
                "Python Web Development with Django",
                "Artificial Intelligence: A Modern Approach",
                "Paradigms of Artificial Intelligence Programming: Case Studies in Common Lisp"
            ],
            lambda b: b.name
        )

        books = Book.objects.annotate(mean_age=Avg("authors__age"))
        b = books.get(pk=1)
        self.assertEqual(
            b.name,
            'The Definitive Guide to Django: Web Development Done Right'
        )
        self.assertEqual(b.mean_age, 34.5)

    def test_annotate_defer(self):
        qs = Book.objects.annotate(
            page_sum=Sum("pages")).defer('name').filter(pk=1)

        rows = [
            (1, "159059725", 447, "The Definitive Guide to Django: Web Development Done Right")
        ]
        self.assertQuerysetEqual(
            qs.order_by('pk'), rows,
            lambda r: (r.id, r.isbn, r.page_sum, r.name)
        )

    def test_annotate_defer_select_related(self):
        qs = Book.objects.select_related('contact').annotate(
            page_sum=Sum("pages")).defer('name').filter(pk=1)

        rows = [
            (1, "159059725", 447, "Adrian Holovaty",
             "The Definitive Guide to Django: Web Development Done Right")
        ]
        self.assertQuerysetEqual(
            qs.order_by('pk'), rows,
            lambda r: (r.id, r.isbn, r.page_sum, r.contact.name, r.name)
        )

    def test_annotate_m2m(self):
        books = Book.objects.filter(rating__lt=4.5).annotate(Avg("authors__age")).order_by("name")
        self.assertQuerysetEqual(
            books, [
                ('Artificial Intelligence: A Modern Approach', 51.5),
                ('Practical Django Projects', 29.0),
                ('Python Web Development with Django', Approximate(30.3, places=1)),
                ('Sams Teach Yourself Django in 24 Hours', 45.0)
            ],
            lambda b: (b.name, b.authors__age__avg),
        )

        books = Book.objects.annotate(num_authors=Count("authors")).order_by("name")
        self.assertQuerysetEqual(
            books, [
                ('Artificial Intelligence: A Modern Approach', 2),
                ('Paradigms of Artificial Intelligence Programming: Case Studies in Common Lisp', 1),
                ('Practical Django Projects', 1),
                ('Python Web Development with Django', 3),
                ('Sams Teach Yourself Django in 24 Hours', 1),
                ('The Definitive Guide to Django: Web Development Done Right', 2)
            ],
            lambda b: (b.name, b.num_authors)
        )

    def test_backwards_m2m_annotate(self):
        authors = Author.objects.filter(name__contains="a").annotate(Avg("book__rating")).order_by("name")
        self.assertQuerysetEqual(
            authors, [
                ('Adrian Holovaty', 4.5),
                ('Brad Dayley', 3.0),
                ('Jacob Kaplan-Moss', 4.5),
                ('James Bennett', 4.0),
                ('Paul Bissex', 4.0),
                ('Stuart Russell', 4.0)
            ],
            lambda a: (a.name, a.book__rating__avg)
        )

        authors = Author.objects.annotate(num_books=Count("book")).order_by("name")
        self.assertQuerysetEqual(
            authors, [
                ('Adrian Holovaty', 1),
                ('Brad Dayley', 1),
                ('Jacob Kaplan-Moss', 1),
                ('James Bennett', 1),
                ('Jeffrey Forcier', 1),
                ('Paul Bissex', 1),
                ('Peter Norvig', 2),
                ('Stuart Russell', 1),
                ('Wesley J. Chun', 1)
            ],
            lambda a: (a.name, a.num_books)
        )

    def test_reverse_fkey_annotate(self):
        books = Book.objects.annotate(Sum("publisher__num_awards")).order_by("name")
        self.assertQuerysetEqual(
            books, [
                ('Artificial Intelligence: A Modern Approach', 7),
                ('Paradigms of Artificial Intelligence Programming: Case Studies in Common Lisp', 9),
                ('Practical Django Projects', 3),
                ('Python Web Development with Django', 7),
                ('Sams Teach Yourself Django in 24 Hours', 1),
                ('The Definitive Guide to Django: Web Development Done Right', 3)
            ],
            lambda b: (b.name, b.publisher__num_awards__sum)
        )

        publishers = Publisher.objects.annotate(Sum("book__price")).order_by("name")
        self.assertQuerysetEqual(
            publishers, [
                ('Apress', Decimal("59.69")),
                ("Jonno's House of Books", None),
                ('Morgan Kaufmann', Decimal("75.00")),
                ('Prentice Hall', Decimal("112.49")),
                ('Sams', Decimal("23.09"))
            ],
            lambda p: (p.name, p.book__price__sum)
        )

    def test_annotate_values(self):
        books = list(Book.objects.filter(pk=1).annotate(mean_age=Avg("authors__age")).values())
        self.assertEqual(
            books, [
                {
                    "contact_id": 1,
                    "id": 1,
                    "isbn": "159059725",
                    "mean_age": 34.5,
                    "name": "The Definitive Guide to Django: Web Development Done Right",
                    "pages": 447,
                    "price": Approximate(Decimal("30")),
                    "pubdate": datetime.date(2007, 12, 6),
                    "publisher_id": 1,
                    "rating": 4.5,
                }
            ]
        )

        books = Book.objects.filter(pk=1).annotate(mean_age=Avg('authors__age')).values('pk', 'isbn', 'mean_age')
        self.assertEqual(
            list(books), [
                {
                    "pk": 1,
                    "isbn": "159059725",
                    "mean_age": 34.5,
                }
            ]
        )

        books = Book.objects.filter(pk=1).annotate(mean_age=Avg("authors__age")).values("name")
        self.assertEqual(
            list(books), [
                {
                    "name": "The Definitive Guide to Django: Web Development Done Right"
                }
            ]
        )

        books = Book.objects.filter(pk=1).values().annotate(mean_age=Avg('authors__age'))
        self.assertEqual(
            list(books), [
                {
                    "contact_id": 1,
                    "id": 1,
                    "isbn": "159059725",
                    "mean_age": 34.5,
                    "name": "The Definitive Guide to Django: Web Development Done Right",
                    "pages": 447,
                    "price": Approximate(Decimal("30")),
                    "pubdate": datetime.date(2007, 12, 6),
                    "publisher_id": 1,
                    "rating": 4.5,
                }
            ]
        )

        books = Book.objects.values("rating").annotate(n_authors=Count("authors__id"), mean_age=Avg("authors__age")).order_by("rating")
        self.assertEqual(
            list(books), [
                {
                    "rating": 3.0,
                    "n_authors": 1,
                    "mean_age": 45.0,
                },
                {
                    "rating": 4.0,
                    "n_authors": 6,
                    "mean_age": Approximate(37.16, places=1)
                },
                {
                    "rating": 4.5,
                    "n_authors": 2,
                    "mean_age": 34.5,
                },
                {
                    "rating": 5.0,
                    "n_authors": 1,
                    "mean_age": 57.0,
                }
            ]
        )

        authors = Author.objects.annotate(Avg("friends__age")).order_by("name")
        self.assertEqual(len(authors), 9)
        self.assertQuerysetEqual(
            authors, [
                ('Adrian Holovaty', 32.0),
                ('Brad Dayley', None),
                ('Jacob Kaplan-Moss', 29.5),
                ('James Bennett', 34.0),
                ('Jeffrey Forcier', 27.0),
                ('Paul Bissex', 31.0),
                ('Peter Norvig', 46.0),
                ('Stuart Russell', 57.0),
                ('Wesley J. Chun', Approximate(33.66, places=1))
            ],
            lambda a: (a.name, a.friends__age__avg)
        )

    def test_count(self):
        vals = Book.objects.aggregate(Count("rating"))
        self.assertEqual(vals, {"rating__count": 6})

        vals = Book.objects.aggregate(Count("rating", distinct=True))
        self.assertEqual(vals, {"rating__count": 4})

    def test_count_star(self):
        with self.assertNumQueries(1) as ctx:
            Book.objects.aggregate(n=Count("*"))
        sql = ctx.captured_queries[0]['sql']
        self.assertIn('SELECT COUNT(*) ', sql)

    def test_fkey_aggregate(self):
        explicit = list(Author.objects.annotate(Count('book__id')))
        implicit = list(Author.objects.annotate(Count('book')))
        self.assertEqual(explicit, implicit)

    def test_annotate_ordering(self):
        books = Book.objects.values('rating').annotate(oldest=Max('authors__age')).order_by('oldest', 'rating')
        self.assertEqual(
            list(books), [
                {
                    "rating": 4.5,
                    "oldest": 35,
                },
                {
                    "rating": 3.0,
                    "oldest": 45
                },
                {
                    "rating": 4.0,
                    "oldest": 57,
                },
                {
                    "rating": 5.0,
                    "oldest": 57,
                }
            ]
        )

        books = Book.objects.values("rating").annotate(oldest=Max("authors__age")).order_by("-oldest", "-rating")
        self.assertEqual(
            list(books), [
                {
                    "rating": 5.0,
                    "oldest": 57,
                },
                {
                    "rating": 4.0,
                    "oldest": 57,
                },
                {
                    "rating": 3.0,
                    "oldest": 45,
                },
                {
                    "rating": 4.5,
                    "oldest": 35,
                }
            ]
        )

    def test_aggregate_annotation(self):
        vals = Book.objects.annotate(num_authors=Count("authors__id")).aggregate(Avg("num_authors"))
        self.assertEqual(vals, {"num_authors__avg": Approximate(1.66, places=1)})

    def test_filtering(self):
        p = Publisher.objects.create(name='Expensive Publisher', num_awards=0)
        Book.objects.create(
            name='ExpensiveBook1',
            pages=1,
            isbn='111',
            rating=3.5,
            price=Decimal("1000"),
            publisher=p,
            contact_id=1,
            pubdate=datetime.date(2008, 12, 1)
        )
        Book.objects.create(
            name='ExpensiveBook2',
            pages=1,
            isbn='222',
            rating=4.0,
            price=Decimal("1000"),
            publisher=p,
            contact_id=1,
            pubdate=datetime.date(2008, 12, 2)
        )
        Book.objects.create(
            name='ExpensiveBook3',
            pages=1,
            isbn='333',
            rating=4.5,
            price=Decimal("35"),
            publisher=p,
            contact_id=1,
            pubdate=datetime.date(2008, 12, 3)
        )

        publishers = Publisher.objects.annotate(num_books=Count("book__id")).filter(num_books__gt=1).order_by("pk")
        self.assertQuerysetEqual(
            publishers, [
                "Apress",
                "Prentice Hall",
                "Expensive Publisher",
            ],
            lambda p: p.name,
        )

        publishers = Publisher.objects.filter(book__price__lt=Decimal("40.0")).order_by("pk")
        self.assertQuerysetEqual(
            publishers, [
                "Apress",
                "Apress",
                "Sams",
                "Prentice Hall",
                "Expensive Publisher",
            ],
            lambda p: p.name
        )

        publishers = Publisher.objects.annotate(num_books=Count("book__id")).filter(num_books__gt=1, book__price__lt=Decimal("40.0")).order_by("pk")
        self.assertQuerysetEqual(
            publishers, [
                "Apress",
                "Prentice Hall",
                "Expensive Publisher",
            ],
            lambda p: p.name,
        )

        publishers = Publisher.objects.filter(book__price__lt=Decimal("40.0")).annotate(num_books=Count("book__id")).filter(num_books__gt=1).order_by("pk")
        self.assertQuerysetEqual(
            publishers, [
                "Apress",
            ],
            lambda p: p.name
        )

        publishers = Publisher.objects.annotate(num_books=Count("book")).filter(num_books__range=[1, 3]).order_by("pk")
        self.assertQuerysetEqual(
            publishers, [
                "Apress",
                "Sams",
                "Prentice Hall",
                "Morgan Kaufmann",
                "Expensive Publisher",
            ],
            lambda p: p.name
        )

        publishers = Publisher.objects.annotate(num_books=Count("book")).filter(num_books__range=[1, 2]).order_by("pk")
        self.assertQuerysetEqual(
            publishers, [
                "Apress",
                "Sams",
                "Prentice Hall",
                "Morgan Kaufmann",
            ],
            lambda p: p.name
        )

        publishers = Publisher.objects.annotate(num_books=Count("book")).filter(num_books__in=[1, 3]).order_by("pk")
        self.assertQuerysetEqual(
            publishers, [
                "Sams",
                "Morgan Kaufmann",
                "Expensive Publisher",
            ],
            lambda p: p.name,
        )

        publishers = Publisher.objects.annotate(num_books=Count("book")).filter(num_books__isnull=True)
        self.assertEqual(len(publishers), 0)

    def test_annotation(self):
        vals = Author.objects.filter(pk=1).aggregate(Count("friends__id"))
        self.assertEqual(vals, {"friends__id__count": 2})

        books = Book.objects.annotate(num_authors=Count("authors__name")).filter(num_authors__exact=2).order_by("pk")
        self.assertQuerysetEqual(
            books, [
                "The Definitive Guide to Django: Web Development Done Right",
                "Artificial Intelligence: A Modern Approach",
            ],
            lambda b: b.name
        )

        authors = Author.objects.annotate(num_friends=Count("friends__id", distinct=True)).filter(num_friends=0).order_by("pk")
        self.assertQuerysetEqual(
            authors, [
                "Brad Dayley",
            ],
            lambda a: a.name
        )

        publishers = Publisher.objects.annotate(num_books=Count("book__id")).filter(num_books__gt=1).order_by("pk")
        self.assertQuerysetEqual(
            publishers, [
                "Apress",
                "Prentice Hall",
            ],
            lambda p: p.name
        )

        publishers = Publisher.objects.filter(book__price__lt=Decimal("40.0")).annotate(num_books=Count("book__id")).filter(num_books__gt=1)
        self.assertQuerysetEqual(
            publishers, [
                "Apress",
            ],
            lambda p: p.name
        )

        books = Book.objects.annotate(num_authors=Count("authors__id")).filter(authors__name__contains="Norvig", num_authors__gt=1)
        self.assertQuerysetEqual(
            books, [
                "Artificial Intelligence: A Modern Approach",
            ],
            lambda b: b.name
        )

    def test_more_aggregation(self):
        a = Author.objects.get(name__contains='Norvig')
        b = Book.objects.get(name__contains='Done Right')
        b.authors.add(a)
        b.save()

        vals = Book.objects.annotate(num_authors=Count("authors__id")).filter(authors__name__contains="Norvig", num_authors__gt=1).aggregate(Avg("rating"))
        self.assertEqual(vals, {"rating__avg": 4.25})

    def test_even_more_aggregate(self):
        publishers = Publisher.objects.annotate(earliest_book=Min("book__pubdate")).exclude(earliest_book=None).order_by("earliest_book").values()
        self.assertEqual(
            list(publishers), [
                {
                    'earliest_book': datetime.date(1991, 10, 15),
                    'num_awards': 9,
                    'id': 4,
                    'name': 'Morgan Kaufmann'
                },
                {
                    'earliest_book': datetime.date(1995, 1, 15),
                    'num_awards': 7,
                    'id': 3,
                    'name': 'Prentice Hall'
                },
                {
                    'earliest_book': datetime.date(2007, 12, 6),
                    'num_awards': 3,
                    'id': 1,
                    'name': 'Apress'
                },
                {
                    'earliest_book': datetime.date(2008, 3, 3),
                    'num_awards': 1,
                    'id': 2,
                    'name': 'Sams'
                }
            ]
        )

        vals = Store.objects.aggregate(Max("friday_night_closing"), Min("original_opening"))
        self.assertEqual(
            vals,
            {
                "friday_night_closing__max": datetime.time(23, 59, 59),
                "original_opening__min": datetime.datetime(1945, 4, 25, 16, 24, 14),
            }
        )

    def test_annotate_values_list(self):
        books = Book.objects.filter(pk=1).annotate(mean_age=Avg("authors__age")).values_list("pk", "isbn", "mean_age")
        self.assertEqual(
            list(books), [
                (1, "159059725", 34.5),
            ]
        )

        books = Book.objects.filter(pk=1).annotate(mean_age=Avg("authors__age")).values_list("isbn")
        self.assertEqual(
            list(books), [
                ('159059725',)
            ]
        )

        books = Book.objects.filter(pk=1).annotate(mean_age=Avg("authors__age")).values_list("mean_age")
        self.assertEqual(
            list(books), [
                (34.5,)
            ]
        )

        books = Book.objects.filter(pk=1).annotate(mean_age=Avg("authors__age")).values_list("mean_age", flat=True)
        self.assertEqual(list(books), [34.5])

        books = Book.objects.values_list("price").annotate(count=Count("price")).order_by("-count", "price")
        self.assertEqual(
            list(books), [
                (Decimal("29.69"), 2),
                (Decimal('23.09'), 1),
                (Decimal('30'), 1),
                (Decimal('75'), 1),
                (Decimal('82.8'), 1),
            ]
        )

    def test_dates_with_aggregation(self):
        """
        Test that .dates() returns a distinct set of dates when applied to a
        QuerySet with aggregation.

        Refs #18056. Previously, .dates() would return distinct (date_kind,
        aggregation) sets, in this case (year, num_authors), so 2008 would be
        returned twice because there are books from 2008 with a different
        number of authors.
        """
        dates = Book.objects.annotate(num_authors=Count("authors")).dates('pubdate', 'year')
        self.assertQuerysetEqual(
            dates, [
                "datetime.date(1991, 1, 1)",
                "datetime.date(1995, 1, 1)",
                "datetime.date(2007, 1, 1)",
                "datetime.date(2008, 1, 1)"
            ]
        )

    def test_values_aggregation(self):
        # Refs #20782
        max_rating = Book.objects.values('rating').aggregate(max_rating=Max('rating'))
        self.assertEqual(max_rating['max_rating'], 5)
        max_books_per_rating = Book.objects.values('rating').annotate(
            books_per_rating=Count('id')
        ).aggregate(Max('books_per_rating'))
        self.assertEqual(
            max_books_per_rating,
            {'books_per_rating__max': 3})

    def test_ticket17424(self):
        """
        Check that doing exclude() on a foreign model after annotate()
        doesn't crash.
        """
        all_books = list(Book.objects.values_list('pk', flat=True).order_by('pk'))
        annotated_books = Book.objects.order_by('pk').annotate(one=Count("id"))

        # The value doesn't matter, we just need any negative
        # constraint on a related model that's a noop.
        excluded_books = annotated_books.exclude(publisher__name="__UNLIKELY_VALUE__")

        # Try to generate query tree
        str(excluded_books.query)

        self.assertQuerysetEqual(excluded_books, all_books, lambda x: x.pk)

        # Check internal state
        self.assertIsNone(annotated_books.query.alias_map["aggregation_book"].join_type)
        self.assertIsNone(excluded_books.query.alias_map["aggregation_book"].join_type)

    def test_ticket12886(self):
        """
        Check that aggregation over sliced queryset works correctly.
        """
        qs = Book.objects.all().order_by('-rating')[0:3]
        vals = qs.aggregate(average_top3_rating=Avg('rating'))['average_top3_rating']
        self.assertAlmostEqual(vals, 4.5, places=2)

    def test_ticket11881(self):
        """
        Check that subqueries do not needlessly contain ORDER BY, SELECT FOR UPDATE
        or select_related() stuff.
        """
        qs = Book.objects.all().select_for_update().order_by(
            'pk').select_related('publisher').annotate(max_pk=Max('pk'))
        with CaptureQueriesContext(connection) as captured_queries:
            qs.aggregate(avg_pk=Avg('max_pk'))
            self.assertEqual(len(captured_queries), 1)
            qstr = captured_queries[0]['sql'].lower()
            self.assertNotIn('for update', qstr)
            forced_ordering = connection.ops.force_no_ordering()
            if forced_ordering:
                # If the backend needs to force an ordering we make sure it's
                # the only "ORDER BY" clause present in the query.
                self.assertEqual(
                    re.findall(r'order by (\w+)', qstr),
                    [', '.join(f[1][0] for f in forced_ordering).lower()]
                )
            else:
                self.assertNotIn('order by', qstr)
            self.assertEqual(qstr.count(' join '), 0)

    def test_decimal_max_digits_has_no_effect(self):
        Book.objects.all().delete()
        a1 = Author.objects.first()
        p1 = Publisher.objects.first()
        thedate = timezone.now()
        for i in range(10):
            Book.objects.create(
                isbn="abcde{}".format(i), name="none", pages=10, rating=4.0,
                price=9999.98, contact=a1, publisher=p1, pubdate=thedate)

        book = Book.objects.aggregate(price_sum=Sum('price'))
        self.assertEqual(book['price_sum'], Decimal("99999.80"))


class ComplexAggregateTestCase(TestCase):
    fixtures = ["aggregation.json"]

    def test_nonaggregate_aggregation_throws(self):
        with six.assertRaisesRegex(self, TypeError, 'fail is not an aggregate expression'):
            Book.objects.aggregate(fail=F('price'))

    def test_nonfield_annotation(self):
        book = Book.objects.annotate(val=Max(Value(2, output_field=IntegerField())))[0]
        self.assertEqual(book.val, 2)
        book = Book.objects.annotate(val=Max(Value(2), output_field=IntegerField()))[0]
        self.assertEqual(book.val, 2)
        book = Book.objects.annotate(val=Max(2, output_field=IntegerField()))[0]
        self.assertEqual(book.val, 2)

    def test_missing_output_field_raises_error(self):
        with six.assertRaisesRegex(self, FieldError, 'Cannot resolve expression type, unknown output_field'):
            Book.objects.annotate(val=Max(2))[0]

    def test_annotation_expressions(self):
        authors = Author.objects.annotate(combined_ages=Sum(F('age') + F('friends__age'))).order_by('name')
        authors2 = Author.objects.annotate(combined_ages=Sum('age') + Sum('friends__age')).order_by('name')
        for qs in (authors, authors2):
            self.assertEqual(len(qs), 9)
            self.assertQuerysetEqual(
                qs, [
                    ('Adrian Holovaty', 132),
                    ('Brad Dayley', None),
                    ('Jacob Kaplan-Moss', 129),
                    ('James Bennett', 63),
                    ('Jeffrey Forcier', 128),
                    ('Paul Bissex', 120),
                    ('Peter Norvig', 103),
                    ('Stuart Russell', 103),
                    ('Wesley J. Chun', 176)
                ],
                lambda a: (a.name, a.combined_ages)
            )

    def test_aggregation_expressions(self):
        a1 = Author.objects.aggregate(av_age=Sum('age') / Count('*'))
        a2 = Author.objects.aggregate(av_age=Sum('age') / Count('age'))
        a3 = Author.objects.aggregate(av_age=Avg('age'))
        self.assertEqual(a1, {'av_age': 37})
        self.assertEqual(a2, {'av_age': 37})
        self.assertEqual(a3, {'av_age': Approximate(37.4, places=1)})

    def test_order_of_precedence(self):
        p1 = Book.objects.filter(rating=4).aggregate(avg_price=(Avg('price') + 2) * 3)
        self.assertEqual(p1, {'avg_price': Approximate(148.18, places=2)})

        p2 = Book.objects.filter(rating=4).aggregate(avg_price=Avg('price') + 2 * 3)
        self.assertEqual(p2, {'avg_price': Approximate(53.39, places=2)})

    def test_combine_different_types(self):
        with six.assertRaisesRegex(self, FieldError, 'Expression contains mixed types. You must set output_field'):
            Book.objects.annotate(sums=Sum('rating') + Sum('pages') + Sum('price')).get(pk=4)

        b1 = Book.objects.annotate(sums=Sum(F('rating') + F('pages') + F('price'),
                                   output_field=IntegerField())).get(pk=4)
        self.assertEqual(b1.sums, 383)

        b2 = Book.objects.annotate(sums=Sum(F('rating') + F('pages') + F('price'),
                                   output_field=FloatField())).get(pk=4)
        self.assertEqual(b2.sums, 383.69)

        b3 = Book.objects.annotate(sums=Sum(F('rating') + F('pages') + F('price'),
                                   output_field=DecimalField())).get(pk=4)
        self.assertEqual(b3.sums, Approximate(Decimal("383.69"), places=2))

    def test_complex_aggregations_require_kwarg(self):
        with six.assertRaisesRegex(self, TypeError, 'Complex annotations require an alias'):
            Author.objects.annotate(Sum(F('age') + F('friends__age')))
        with six.assertRaisesRegex(self, TypeError, 'Complex aggregates require an alias'):
            Author.objects.aggregate(Sum('age') / Count('age'))
        with six.assertRaisesRegex(self, TypeError, 'Complex aggregates require an alias'):
            Author.objects.aggregate(Sum(1))

    def test_aggregate_over_complex_annotation(self):
        qs = Author.objects.annotate(
            combined_ages=Sum(F('age') + F('friends__age')))

        age = qs.aggregate(max_combined_age=Max('combined_ages'))
        self.assertEqual(age['max_combined_age'], 176)

        age = qs.aggregate(max_combined_age_doubled=Max('combined_ages') * 2)
        self.assertEqual(age['max_combined_age_doubled'], 176 * 2)

        age = qs.aggregate(
            max_combined_age_doubled=Max('combined_ages') + Max('combined_ages'))
        self.assertEqual(age['max_combined_age_doubled'], 176 * 2)

        age = qs.aggregate(
            max_combined_age_doubled=Max('combined_ages') + Max('combined_ages'),
            sum_combined_age=Sum('combined_ages'))
        self.assertEqual(age['max_combined_age_doubled'], 176 * 2)
        self.assertEqual(age['sum_combined_age'], 954)

        age = qs.aggregate(
            max_combined_age_doubled=Max('combined_ages') + Max('combined_ages'),
            sum_combined_age_doubled=Sum('combined_ages') + Sum('combined_ages'))
        self.assertEqual(age['max_combined_age_doubled'], 176 * 2)
        self.assertEqual(age['sum_combined_age_doubled'], 954 * 2)

    def test_values_annotation_with_expression(self):
        # ensure the F() is promoted to the group by clause
        qs = Author.objects.values('name').annotate(another_age=Sum('age') + F('age'))
        a = qs.get(pk=1)
        self.assertEqual(a['another_age'], 68)

        qs = qs.annotate(friend_count=Count('friends'))
        a = qs.get(pk=1)
        self.assertEqual(a['friend_count'], 2)

        qs = qs.annotate(combined_age=Sum('age') + F('friends__age')).filter(pk=1).order_by('-combined_age')
        self.assertEqual(
            list(qs), [
                {
                    "name": 'Adrian Holovaty',
                    "another_age": 68,
                    "friend_count": 1,
                    "combined_age": 69
                },
                {
                    "name": 'Adrian Holovaty',
                    "another_age": 68,
                    "friend_count": 1,
                    "combined_age": 63
                }
            ]
        )

        vals = qs.values('name', 'combined_age')
        self.assertEqual(
            list(vals), [
                {
                    "name": 'Adrian Holovaty',
                    "combined_age": 69
                },
                {
                    "name": 'Adrian Holovaty',
                    "combined_age": 63
                }
            ]
        )

    def test_annotate_values_aggregate(self):
        alias_age = Author.objects.annotate(
            age_alias=F('age')
        ).values(
            'age_alias',
        ).aggregate(sum_age=Sum('age_alias'))

        age = Author.objects.values('age').aggregate(sum_age=Sum('age'))

        self.assertEqual(alias_age['sum_age'], age['sum_age'])

    def test_annotate_over_annotate(self):
        author = Author.objects.annotate(
            age_alias=F('age')
        ).annotate(
            sum_age=Sum('age_alias')
        ).get(pk=1)

        other_author = Author.objects.annotate(
            sum_age=Sum('age')
        ).get(pk=1)

        self.assertEqual(author.sum_age, other_author.sum_age)

    def test_annotated_aggregate_over_annotated_aggregate(self):
        with six.assertRaisesRegex(self, FieldError, "Cannot compute Sum\('id__max'\): 'id__max' is an aggregate"):
            Book.objects.annotate(Max('id')).annotate(Sum('id__max'))

    def test_add_implementation(self):
        try:
            # test completely changing how the output is rendered
            def lower_case_function_override(self, compiler, connection):
                sql, params = compiler.compile(self.source_expressions[0])
                substitutions = dict(function=self.function.lower(), expressions=sql)
                substitutions.update(self.extra)
                return self.template % substitutions, params
            setattr(Sum, 'as_' + connection.vendor, lower_case_function_override)

            qs = Book.objects.annotate(sums=Sum(F('rating') + F('pages') + F('price'),
                                       output_field=IntegerField()))
            self.assertEqual(str(qs.query).count('sum('), 1)
            b1 = qs.get(pk=4)
            self.assertEqual(b1.sums, 383)

            # test changing the dict and delegating
            def lower_case_function_super(self, compiler, connection):
                self.extra['function'] = self.function.lower()
                return super(Sum, self).as_sql(compiler, connection)
            setattr(Sum, 'as_' + connection.vendor, lower_case_function_super)

            qs = Book.objects.annotate(sums=Sum(F('rating') + F('pages') + F('price'),
                                       output_field=IntegerField()))
            self.assertEqual(str(qs.query).count('sum('), 1)
            b1 = qs.get(pk=4)
            self.assertEqual(b1.sums, 383)

            # test overriding all parts of the template
            def be_evil(self, compiler, connection):
                substitutions = dict(function='MAX', expressions='2')
                substitutions.update(self.extra)
                return self.template % substitutions, ()
            setattr(Sum, 'as_' + connection.vendor, be_evil)

            qs = Book.objects.annotate(sums=Sum(F('rating') + F('pages') + F('price'),
                                       output_field=IntegerField()))
            self.assertEqual(str(qs.query).count('MAX('), 1)
            b1 = qs.get(pk=4)
            self.assertEqual(b1.sums, 2)
        finally:
            delattr(Sum, 'as_' + connection.vendor)

    def test_complex_values_aggregation(self):
        max_rating = Book.objects.values('rating').aggregate(
            double_max_rating=Max('rating') + Max('rating'))
        self.assertEqual(max_rating['double_max_rating'], 5 * 2)

        max_books_per_rating = Book.objects.values('rating').annotate(
            books_per_rating=Count('id') + 5
        ).aggregate(Max('books_per_rating'))
        self.assertEqual(
            max_books_per_rating,
            {'books_per_rating__max': 3 + 5})

    def test_expression_on_aggregation(self):

        # Create a plain expression
        class Greatest(Func):
            function = 'GREATEST'

            def as_sqlite(self, compiler, connection):
                return super(Greatest, self).as_sql(compiler, connection, function='MAX')

        qs = Publisher.objects.annotate(
            price_or_median=Greatest(Avg('book__rating'), Avg('book__price'))
        ).filter(price_or_median__gte=F('num_awards')).order_by('pk')
        self.assertQuerysetEqual(
            qs, [1, 2, 3, 4], lambda v: v.pk)

        qs2 = Publisher.objects.annotate(
            rating_or_num_awards=Greatest(Avg('book__rating'), F('num_awards'),
                                          output_field=FloatField())
        ).filter(rating_or_num_awards__gt=F('num_awards')).order_by('pk')
        self.assertQuerysetEqual(
            qs2, [1, 2], lambda v: v.pk)

    @ignore_warnings(category=RemovedInDjango110Warning)
    def test_backwards_compatibility(self):
        from django.db.models.sql import aggregates as sql_aggregates

        class SqlNewSum(sql_aggregates.Aggregate):
            sql_function = 'SUM'

        class NewSum(Aggregate):
            name = 'Sum'

            def add_to_query(self, query, alias, col, source, is_summary):
                klass = SqlNewSum
                aggregate = klass(
                    col, source=source, is_summary=is_summary, **self.extra)
                query.annotations[alias] = aggregate

        qs = Author.objects.values('name').annotate(another_age=NewSum('age') + F('age'))
        a = qs.get(pk=1)
        self.assertEqual(a['another_age'], 68)
