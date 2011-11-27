from __future__ import absolute_import

import datetime
from decimal import Decimal

from django.db.models import Avg, Sum, Count, Max, Min
from django.test import TestCase, Approximate

from .models import Author, Publisher, Book, Store


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
            u'The Definitive Guide to Django: Web Development Done Right'
        )
        self.assertEqual(b.mean_age, 34.5)

    def test_annotate_m2m(self):
        books = Book.objects.filter(rating__lt=4.5).annotate(Avg("authors__age")).order_by("name")
        self.assertQuerysetEqual(
            books, [
                (u'Artificial Intelligence: A Modern Approach', 51.5),
                (u'Practical Django Projects', 29.0),
                (u'Python Web Development with Django', Approximate(30.3, places=1)),
                (u'Sams Teach Yourself Django in 24 Hours', 45.0)
            ],
            lambda b: (b.name, b.authors__age__avg),
        )

        books = Book.objects.annotate(num_authors=Count("authors")).order_by("name")
        self.assertQuerysetEqual(
            books, [
                (u'Artificial Intelligence: A Modern Approach', 2),
                (u'Paradigms of Artificial Intelligence Programming: Case Studies in Common Lisp', 1),
                (u'Practical Django Projects', 1),
                (u'Python Web Development with Django', 3),
                (u'Sams Teach Yourself Django in 24 Hours', 1),
                (u'The Definitive Guide to Django: Web Development Done Right', 2)
            ],
            lambda b: (b.name, b.num_authors)
        )

    def test_backwards_m2m_annotate(self):
        authors = Author.objects.filter(name__contains="a").annotate(Avg("book__rating")).order_by("name")
        self.assertQuerysetEqual(
            authors, [
                (u'Adrian Holovaty', 4.5),
                (u'Brad Dayley', 3.0),
                (u'Jacob Kaplan-Moss', 4.5),
                (u'James Bennett', 4.0),
                (u'Paul Bissex', 4.0),
                (u'Stuart Russell', 4.0)
            ],
            lambda a: (a.name, a.book__rating__avg)
        )

        authors = Author.objects.annotate(num_books=Count("book")).order_by("name")
        self.assertQuerysetEqual(
            authors, [
                (u'Adrian Holovaty', 1),
                (u'Brad Dayley', 1),
                (u'Jacob Kaplan-Moss', 1),
                (u'James Bennett', 1),
                (u'Jeffrey Forcier', 1),
                (u'Paul Bissex', 1),
                (u'Peter Norvig', 2),
                (u'Stuart Russell', 1),
                (u'Wesley J. Chun', 1)
            ],
            lambda a: (a.name, a.num_books)
        )

    def test_reverse_fkey_annotate(self):
        books = Book.objects.annotate(Sum("publisher__num_awards")).order_by("name")
        self.assertQuerysetEqual(
            books, [
                (u'Artificial Intelligence: A Modern Approach', 7),
                (u'Paradigms of Artificial Intelligence Programming: Case Studies in Common Lisp', 9),
                (u'Practical Django Projects', 3),
                (u'Python Web Development with Django', 7),
                (u'Sams Teach Yourself Django in 24 Hours', 1),
                (u'The Definitive Guide to Django: Web Development Done Right', 3)
            ],
            lambda b: (b.name, b.publisher__num_awards__sum)
        )

        publishers = Publisher.objects.annotate(Sum("book__price")).order_by("name")
        self.assertQuerysetEqual(
            publishers, [
                (u'Apress', Decimal("59.69")),
                (u"Jonno's House of Books", None),
                (u'Morgan Kaufmann', Decimal("75.00")),
                (u'Prentice Hall', Decimal("112.49")),
                (u'Sams', Decimal("23.09"))
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
                (u'Adrian Holovaty', 32.0),
                (u'Brad Dayley', None),
                (u'Jacob Kaplan-Moss', 29.5),
                (u'James Bennett', 34.0),
                (u'Jeffrey Forcier', 27.0),
                (u'Paul Bissex', 31.0),
                (u'Peter Norvig', 46.0),
                (u'Stuart Russell', 57.0),
                (u'Wesley J. Chun', Approximate(33.66, places=1))
            ],
            lambda a: (a.name, a.friends__age__avg)
        )

    def test_count(self):
        vals = Book.objects.aggregate(Count("rating"))
        self.assertEqual(vals, {"rating__count": 6})

        vals = Book.objects.aggregate(Count("rating", distinct=True))
        self.assertEqual(vals, {"rating__count": 4})

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
            pubdate=datetime.date(2008,12,1)
        )
        Book.objects.create(
            name='ExpensiveBook2',
            pages=1,
            isbn='222',
            rating=4.0,
            price=Decimal("1000"),
            publisher=p,
            contact_id=1,
            pubdate=datetime.date(2008,12,2)
        )
        Book.objects.create(
            name='ExpensiveBook3',
            pages=1,
            isbn='333',
            rating=4.5,
            price=Decimal("35"),
            publisher=p,
            contact_id=1,
            pubdate=datetime.date(2008,12,3)
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

        books = Book.objects.annotate(num_authors=Count("authors__name")).filter(num_authors__ge=2).order_by("pk")
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
                    'name': u'Morgan Kaufmann'
                },
                {
                    'earliest_book': datetime.date(1995, 1, 15),
                    'num_awards': 7,
                    'id': 3,
                    'name': u'Prentice Hall'
                },
                {
                    'earliest_book': datetime.date(2007, 12, 6),
                    'num_awards': 3,
                    'id': 1,
                    'name': u'Apress'
                },
                {
                    'earliest_book': datetime.date(2008, 3, 3),
                    'num_awards': 1,
                    'id': 2,
                    'name': u'Sams'
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
