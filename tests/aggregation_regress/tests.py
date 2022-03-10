import datetime
import pickle
from decimal import Decimal
from operator import attrgetter
from unittest import mock

from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import FieldError
from django.db import connection
from django.db.models import (
    Aggregate,
    Avg,
    Case,
    Count,
    DecimalField,
    F,
    IntegerField,
    Max,
    Q,
    StdDev,
    Sum,
    Value,
    Variance,
    When,
)
from django.test import TestCase, skipUnlessAnyDBFeature, skipUnlessDBFeature
from django.test.utils import Approximate

from .models import (
    Alfa,
    Author,
    Book,
    Bravo,
    Charlie,
    Clues,
    Entries,
    HardbackBook,
    ItemTag,
    Publisher,
    SelfRefFK,
    Store,
    WithManualPK,
)


class AggregationTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.a1 = Author.objects.create(name="Adrian Holovaty", age=34)
        cls.a2 = Author.objects.create(name="Jacob Kaplan-Moss", age=35)
        cls.a3 = Author.objects.create(name="Brad Dayley", age=45)
        cls.a4 = Author.objects.create(name="James Bennett", age=29)
        cls.a5 = Author.objects.create(name="Jeffrey Forcier", age=37)
        cls.a6 = Author.objects.create(name="Paul Bissex", age=29)
        cls.a7 = Author.objects.create(name="Wesley J. Chun", age=25)
        cls.a8 = Author.objects.create(name="Peter Norvig", age=57)
        cls.a9 = Author.objects.create(name="Stuart Russell", age=46)
        cls.a1.friends.add(cls.a2, cls.a4)
        cls.a2.friends.add(cls.a1, cls.a7)
        cls.a4.friends.add(cls.a1)
        cls.a5.friends.add(cls.a6, cls.a7)
        cls.a6.friends.add(cls.a5, cls.a7)
        cls.a7.friends.add(cls.a2, cls.a5, cls.a6)
        cls.a8.friends.add(cls.a9)
        cls.a9.friends.add(cls.a8)

        cls.p1 = Publisher.objects.create(name="Apress", num_awards=3)
        cls.p2 = Publisher.objects.create(name="Sams", num_awards=1)
        cls.p3 = Publisher.objects.create(name="Prentice Hall", num_awards=7)
        cls.p4 = Publisher.objects.create(name="Morgan Kaufmann", num_awards=9)
        cls.p5 = Publisher.objects.create(name="Jonno's House of Books", num_awards=0)

        cls.b1 = Book.objects.create(
            isbn="159059725",
            name="The Definitive Guide to Django: Web Development Done Right",
            pages=447,
            rating=4.5,
            price=Decimal("30.00"),
            contact=cls.a1,
            publisher=cls.p1,
            pubdate=datetime.date(2007, 12, 6),
        )
        cls.b2 = Book.objects.create(
            isbn="067232959",
            name="Sams Teach Yourself Django in 24 Hours",
            pages=528,
            rating=3.0,
            price=Decimal("23.09"),
            contact=cls.a3,
            publisher=cls.p2,
            pubdate=datetime.date(2008, 3, 3),
        )
        cls.b3 = Book.objects.create(
            isbn="159059996",
            name="Practical Django Projects",
            pages=300,
            rating=4.0,
            price=Decimal("29.69"),
            contact=cls.a4,
            publisher=cls.p1,
            pubdate=datetime.date(2008, 6, 23),
        )
        cls.b4 = Book.objects.create(
            isbn="013235613",
            name="Python Web Development with Django",
            pages=350,
            rating=4.0,
            price=Decimal("29.69"),
            contact=cls.a5,
            publisher=cls.p3,
            pubdate=datetime.date(2008, 11, 3),
        )
        cls.b5 = HardbackBook.objects.create(
            isbn="013790395",
            name="Artificial Intelligence: A Modern Approach",
            pages=1132,
            rating=4.0,
            price=Decimal("82.80"),
            contact=cls.a8,
            publisher=cls.p3,
            pubdate=datetime.date(1995, 1, 15),
            weight=4.5,
        )
        cls.b6 = HardbackBook.objects.create(
            isbn="155860191",
            name=(
                "Paradigms of Artificial Intelligence Programming: Case Studies in "
                "Common Lisp"
            ),
            pages=946,
            rating=5.0,
            price=Decimal("75.00"),
            contact=cls.a8,
            publisher=cls.p4,
            pubdate=datetime.date(1991, 10, 15),
            weight=3.7,
        )
        cls.b1.authors.add(cls.a1, cls.a2)
        cls.b2.authors.add(cls.a3)
        cls.b3.authors.add(cls.a4)
        cls.b4.authors.add(cls.a5, cls.a6, cls.a7)
        cls.b5.authors.add(cls.a8, cls.a9)
        cls.b6.authors.add(cls.a8)

        s1 = Store.objects.create(
            name="Amazon.com",
            original_opening=datetime.datetime(1994, 4, 23, 9, 17, 42),
            friday_night_closing=datetime.time(23, 59, 59),
        )
        s2 = Store.objects.create(
            name="Books.com",
            original_opening=datetime.datetime(2001, 3, 15, 11, 23, 37),
            friday_night_closing=datetime.time(23, 59, 59),
        )
        s3 = Store.objects.create(
            name="Mamma and Pappa's Books",
            original_opening=datetime.datetime(1945, 4, 25, 16, 24, 14),
            friday_night_closing=datetime.time(21, 30),
        )
        s1.books.add(cls.b1, cls.b2, cls.b3, cls.b4, cls.b5, cls.b6)
        s2.books.add(cls.b1, cls.b3, cls.b5, cls.b6)
        s3.books.add(cls.b3, cls.b4, cls.b6)

    def assertObjectAttrs(self, obj, **kwargs):
        for attr, value in kwargs.items():
            self.assertEqual(getattr(obj, attr), value)

    def test_annotation_with_value(self):
        values = (
            Book.objects.filter(
                name="Practical Django Projects",
            )
            .annotate(
                discount_price=F("price") * 2,
            )
            .values(
                "discount_price",
            )
            .annotate(sum_discount=Sum("discount_price"))
        )
        self.assertSequenceEqual(
            values,
            [{"discount_price": Decimal("59.38"), "sum_discount": Decimal("59.38")}],
        )

    def test_aggregates_in_where_clause(self):
        """
        Regression test for #12822: DatabaseError: aggregates not allowed in
        WHERE clause

        The subselect works and returns results equivalent to a
        query with the IDs listed.

        Before the corresponding fix for this bug, this test passed in 1.1 and
        failed in 1.2-beta (trunk).
        """
        qs = Book.objects.values("contact").annotate(Max("id"))
        qs = qs.order_by("contact").values_list("id__max", flat=True)
        # don't do anything with the queryset (qs) before including it as a
        # subquery
        books = Book.objects.order_by("id")
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
        qs = Book.objects.values("contact").annotate(Max("id"))
        qs = qs.order_by("contact").values_list("id__max", flat=True)
        # force the queryset (qs) for the subquery to be evaluated in its
        # current state
        list(qs)
        books = Book.objects.order_by("id")
        qs1 = books.filter(id__in=qs)
        qs2 = books.filter(id__in=list(qs))
        self.assertEqual(list(qs1), list(qs2))

    @skipUnlessDBFeature("supports_subqueries_in_group_by")
    def test_annotate_with_extra(self):
        """
        Regression test for #11916: Extra params + aggregation creates
        incorrect SQL.
        """
        # Oracle doesn't support subqueries in group by clause
        shortest_book_sql = """
        SELECT name
        FROM aggregation_regress_book b
        WHERE b.publisher_id = aggregation_regress_publisher.id
        ORDER BY b.pages
        LIMIT 1
        """
        # tests that this query does not raise a DatabaseError due to the full
        # subselect being (erroneously) added to the GROUP BY parameters
        qs = Publisher.objects.extra(
            select={
                "name_of_shortest_book": shortest_book_sql,
            }
        ).annotate(total_books=Count("book"))
        # force execution of the query
        list(qs)

    def test_aggregate(self):
        # Ordering requests are ignored
        self.assertEqual(
            Author.objects.order_by("name").aggregate(Avg("age")),
            {"age__avg": Approximate(37.444, places=1)},
        )

        # Implicit ordering is also ignored
        self.assertEqual(
            Book.objects.aggregate(Sum("pages")),
            {"pages__sum": 3703},
        )

        # Baseline results
        self.assertEqual(
            Book.objects.aggregate(Sum("pages"), Avg("pages")),
            {"pages__sum": 3703, "pages__avg": Approximate(617.166, places=2)},
        )

        # Empty values query doesn't affect grouping or results
        self.assertEqual(
            Book.objects.values().aggregate(Sum("pages"), Avg("pages")),
            {"pages__sum": 3703, "pages__avg": Approximate(617.166, places=2)},
        )

        # Aggregate overrides extra selected column
        self.assertEqual(
            Book.objects.extra(select={"price_per_page": "price / pages"}).aggregate(
                Sum("pages")
            ),
            {"pages__sum": 3703},
        )

    def test_annotation(self):
        # Annotations get combined with extra select clauses
        obj = (
            Book.objects.annotate(mean_auth_age=Avg("authors__age"))
            .extra(select={"manufacture_cost": "price * .5"})
            .get(pk=self.b2.pk)
        )
        self.assertObjectAttrs(
            obj,
            contact_id=self.a3.id,
            isbn="067232959",
            mean_auth_age=45.0,
            name="Sams Teach Yourself Django in 24 Hours",
            pages=528,
            price=Decimal("23.09"),
            pubdate=datetime.date(2008, 3, 3),
            publisher_id=self.p2.id,
            rating=3.0,
        )
        # Different DB backends return different types for the extra select computation
        self.assertIn(obj.manufacture_cost, (11.545, Decimal("11.545")))

        # Order of the annotate/extra in the query doesn't matter
        obj = (
            Book.objects.extra(select={"manufacture_cost": "price * .5"})
            .annotate(mean_auth_age=Avg("authors__age"))
            .get(pk=self.b2.pk)
        )
        self.assertObjectAttrs(
            obj,
            contact_id=self.a3.id,
            isbn="067232959",
            mean_auth_age=45.0,
            name="Sams Teach Yourself Django in 24 Hours",
            pages=528,
            price=Decimal("23.09"),
            pubdate=datetime.date(2008, 3, 3),
            publisher_id=self.p2.id,
            rating=3.0,
        )
        # Different DB backends return different types for the extra select computation
        self.assertIn(obj.manufacture_cost, (11.545, Decimal("11.545")))

        # Values queries can be combined with annotate and extra
        obj = (
            Book.objects.annotate(mean_auth_age=Avg("authors__age"))
            .extra(select={"manufacture_cost": "price * .5"})
            .values()
            .get(pk=self.b2.pk)
        )
        manufacture_cost = obj["manufacture_cost"]
        self.assertIn(manufacture_cost, (11.545, Decimal("11.545")))
        del obj["manufacture_cost"]
        self.assertEqual(
            obj,
            {
                "id": self.b2.id,
                "contact_id": self.a3.id,
                "isbn": "067232959",
                "mean_auth_age": 45.0,
                "name": "Sams Teach Yourself Django in 24 Hours",
                "pages": 528,
                "price": Decimal("23.09"),
                "pubdate": datetime.date(2008, 3, 3),
                "publisher_id": self.p2.id,
                "rating": 3.0,
            },
        )

        # The order of the (empty) values, annotate and extra clauses doesn't
        # matter
        obj = (
            Book.objects.values()
            .annotate(mean_auth_age=Avg("authors__age"))
            .extra(select={"manufacture_cost": "price * .5"})
            .get(pk=self.b2.pk)
        )
        manufacture_cost = obj["manufacture_cost"]
        self.assertIn(manufacture_cost, (11.545, Decimal("11.545")))
        del obj["manufacture_cost"]
        self.assertEqual(
            obj,
            {
                "id": self.b2.id,
                "contact_id": self.a3.id,
                "isbn": "067232959",
                "mean_auth_age": 45.0,
                "name": "Sams Teach Yourself Django in 24 Hours",
                "pages": 528,
                "price": Decimal("23.09"),
                "pubdate": datetime.date(2008, 3, 3),
                "publisher_id": self.p2.id,
                "rating": 3.0,
            },
        )

        # If the annotation precedes the values clause, it won't be included
        # unless it is explicitly named
        obj = (
            Book.objects.annotate(mean_auth_age=Avg("authors__age"))
            .extra(select={"price_per_page": "price / pages"})
            .values("name")
            .get(pk=self.b1.pk)
        )
        self.assertEqual(
            obj,
            {
                "name": "The Definitive Guide to Django: Web Development Done Right",
            },
        )

        obj = (
            Book.objects.annotate(mean_auth_age=Avg("authors__age"))
            .extra(select={"price_per_page": "price / pages"})
            .values("name", "mean_auth_age")
            .get(pk=self.b1.pk)
        )
        self.assertEqual(
            obj,
            {
                "mean_auth_age": 34.5,
                "name": "The Definitive Guide to Django: Web Development Done Right",
            },
        )

        # If an annotation isn't included in the values, it can still be used
        # in a filter
        qs = (
            Book.objects.annotate(n_authors=Count("authors"))
            .values("name")
            .filter(n_authors__gt=2)
        )
        self.assertSequenceEqual(
            qs,
            [{"name": "Python Web Development with Django"}],
        )

        # The annotations are added to values output if values() precedes
        # annotate()
        obj = (
            Book.objects.values("name")
            .annotate(mean_auth_age=Avg("authors__age"))
            .extra(select={"price_per_page": "price / pages"})
            .get(pk=self.b1.pk)
        )
        self.assertEqual(
            obj,
            {
                "mean_auth_age": 34.5,
                "name": "The Definitive Guide to Django: Web Development Done Right",
            },
        )

        # All of the objects are getting counted (allow_nulls) and that values
        # respects the amount of objects
        self.assertEqual(len(Author.objects.annotate(Avg("friends__age")).values()), 9)

        # Consecutive calls to annotate accumulate in the query
        qs = (
            Book.objects.values("price")
            .annotate(oldest=Max("authors__age"))
            .order_by("oldest", "price")
            .annotate(Max("publisher__num_awards"))
        )
        self.assertSequenceEqual(
            qs,
            [
                {"price": Decimal("30"), "oldest": 35, "publisher__num_awards__max": 3},
                {
                    "price": Decimal("29.69"),
                    "oldest": 37,
                    "publisher__num_awards__max": 7,
                },
                {
                    "price": Decimal("23.09"),
                    "oldest": 45,
                    "publisher__num_awards__max": 1,
                },
                {"price": Decimal("75"), "oldest": 57, "publisher__num_awards__max": 9},
                {
                    "price": Decimal("82.8"),
                    "oldest": 57,
                    "publisher__num_awards__max": 7,
                },
            ],
        )

    def test_aggregate_annotation(self):
        # Aggregates can be composed over annotations.
        # The return type is derived from the composed aggregate
        vals = Book.objects.annotate(num_authors=Count("authors__id")).aggregate(
            Max("pages"), Max("price"), Sum("num_authors"), Avg("num_authors")
        )
        self.assertEqual(
            vals,
            {
                "num_authors__sum": 10,
                "num_authors__avg": Approximate(1.666, places=2),
                "pages__max": 1132,
                "price__max": Decimal("82.80"),
            },
        )

        # Regression for #15624 - Missing SELECT columns when using values, annotate
        # and aggregate in a single query
        self.assertEqual(
            Book.objects.annotate(c=Count("authors")).values("c").aggregate(Max("c")),
            {"c__max": 3},
        )

    def test_conditional_aggregate(self):
        # Conditional aggregation of a grouped queryset.
        self.assertEqual(
            Book.objects.annotate(c=Count("authors"))
            .values("pk")
            .aggregate(test=Sum(Case(When(c__gt=1, then=1))))["test"],
            3,
        )

    def test_sliced_conditional_aggregate(self):
        self.assertEqual(
            Author.objects.all()[:5].aggregate(
                test=Sum(Case(When(age__lte=35, then=1)))
            )["test"],
            3,
        )

    def test_annotated_conditional_aggregate(self):
        annotated_qs = Book.objects.annotate(
            discount_price=F("price") * Decimal("0.75")
        )
        self.assertAlmostEqual(
            annotated_qs.aggregate(
                test=Avg(
                    Case(
                        When(pages__lt=400, then="discount_price"),
                        output_field=DecimalField(),
                    )
                )
            )["test"],
            Decimal("22.27"),
            places=2,
        )

    def test_distinct_conditional_aggregate(self):
        self.assertEqual(
            Book.objects.distinct().aggregate(
                test=Avg(
                    Case(
                        When(price=Decimal("29.69"), then="pages"),
                        output_field=IntegerField(),
                    )
                )
            )["test"],
            325,
        )

    def test_conditional_aggregate_on_complex_condition(self):
        self.assertEqual(
            Book.objects.distinct().aggregate(
                test=Avg(
                    Case(
                        When(
                            Q(price__gte=Decimal("29")) & Q(price__lt=Decimal("30")),
                            then="pages",
                        ),
                        output_field=IntegerField(),
                    )
                )
            )["test"],
            325,
        )

    def test_decimal_aggregate_annotation_filter(self):
        """
        Filtering on an aggregate annotation with Decimal values should work.
        Requires special handling on SQLite (#18247).
        """
        self.assertEqual(
            len(
                Author.objects.annotate(sum=Sum("book_contact_set__price")).filter(
                    sum__gt=Decimal(40)
                )
            ),
            1,
        )
        self.assertEqual(
            len(
                Author.objects.annotate(sum=Sum("book_contact_set__price")).filter(
                    sum__lte=Decimal(40)
                )
            ),
            4,
        )

    def test_field_error(self):
        # Bad field requests in aggregates are caught and reported
        msg = (
            "Cannot resolve keyword 'foo' into field. Choices are: authors, "
            "contact, contact_id, hardbackbook, id, isbn, name, pages, price, "
            "pubdate, publisher, publisher_id, rating, store, tags"
        )
        with self.assertRaisesMessage(FieldError, msg):
            Book.objects.aggregate(num_authors=Count("foo"))

        with self.assertRaisesMessage(FieldError, msg):
            Book.objects.annotate(num_authors=Count("foo"))

        msg = (
            "Cannot resolve keyword 'foo' into field. Choices are: authors, "
            "contact, contact_id, hardbackbook, id, isbn, name, num_authors, "
            "pages, price, pubdate, publisher, publisher_id, rating, store, tags"
        )
        with self.assertRaisesMessage(FieldError, msg):
            Book.objects.annotate(num_authors=Count("authors__id")).aggregate(
                Max("foo")
            )

    def test_more(self):
        # Old-style count aggregations can be mixed with new-style
        self.assertEqual(Book.objects.annotate(num_authors=Count("authors")).count(), 6)

        # Non-ordinal, non-computed Aggregates over annotations correctly
        # inherit the annotation's internal type if the annotation is ordinal
        # or computed
        vals = Book.objects.annotate(num_authors=Count("authors")).aggregate(
            Max("num_authors")
        )
        self.assertEqual(vals, {"num_authors__max": 3})

        vals = Publisher.objects.annotate(avg_price=Avg("book__price")).aggregate(
            Max("avg_price")
        )
        self.assertEqual(vals, {"avg_price__max": 75.0})

        # Aliases are quoted to protected aliases that might be reserved names
        vals = Book.objects.aggregate(number=Max("pages"), select=Max("pages"))
        self.assertEqual(vals, {"number": 1132, "select": 1132})

        # Regression for #10064: select_related() plays nice with aggregates
        obj = (
            Book.objects.select_related("publisher")
            .annotate(num_authors=Count("authors"))
            .values()
            .get(isbn="013790395")
        )
        self.assertEqual(
            obj,
            {
                "contact_id": self.a8.id,
                "id": self.b5.id,
                "isbn": "013790395",
                "name": "Artificial Intelligence: A Modern Approach",
                "num_authors": 2,
                "pages": 1132,
                "price": Decimal("82.8"),
                "pubdate": datetime.date(1995, 1, 15),
                "publisher_id": self.p3.id,
                "rating": 4.0,
            },
        )

        # Regression for #10010: exclude on an aggregate field is correctly
        # negated
        self.assertEqual(len(Book.objects.annotate(num_authors=Count("authors"))), 6)
        self.assertEqual(
            len(
                Book.objects.annotate(num_authors=Count("authors")).filter(
                    num_authors__gt=2
                )
            ),
            1,
        )
        self.assertEqual(
            len(
                Book.objects.annotate(num_authors=Count("authors")).exclude(
                    num_authors__gt=2
                )
            ),
            5,
        )

        self.assertEqual(
            len(
                Book.objects.annotate(num_authors=Count("authors"))
                .filter(num_authors__lt=3)
                .exclude(num_authors__lt=2)
            ),
            2,
        )
        self.assertEqual(
            len(
                Book.objects.annotate(num_authors=Count("authors"))
                .exclude(num_authors__lt=2)
                .filter(num_authors__lt=3)
            ),
            2,
        )

    def test_aggregate_fexpr(self):
        # Aggregates can be used with F() expressions
        # ... where the F() is pushed into the HAVING clause
        qs = (
            Publisher.objects.annotate(num_books=Count("book"))
            .filter(num_books__lt=F("num_awards") / 2)
            .order_by("name")
            .values("name", "num_books", "num_awards")
        )
        self.assertSequenceEqual(
            qs,
            [
                {"num_books": 1, "name": "Morgan Kaufmann", "num_awards": 9},
                {"num_books": 2, "name": "Prentice Hall", "num_awards": 7},
            ],
        )

        qs = (
            Publisher.objects.annotate(num_books=Count("book"))
            .exclude(num_books__lt=F("num_awards") / 2)
            .order_by("name")
            .values("name", "num_books", "num_awards")
        )
        self.assertSequenceEqual(
            qs,
            [
                {"num_books": 2, "name": "Apress", "num_awards": 3},
                {"num_books": 0, "name": "Jonno's House of Books", "num_awards": 0},
                {"num_books": 1, "name": "Sams", "num_awards": 1},
            ],
        )

        # ... and where the F() references an aggregate
        qs = (
            Publisher.objects.annotate(num_books=Count("book"))
            .filter(num_awards__gt=2 * F("num_books"))
            .order_by("name")
            .values("name", "num_books", "num_awards")
        )
        self.assertSequenceEqual(
            qs,
            [
                {"num_books": 1, "name": "Morgan Kaufmann", "num_awards": 9},
                {"num_books": 2, "name": "Prentice Hall", "num_awards": 7},
            ],
        )

        qs = (
            Publisher.objects.annotate(num_books=Count("book"))
            .exclude(num_books__lt=F("num_awards") / 2)
            .order_by("name")
            .values("name", "num_books", "num_awards")
        )
        self.assertSequenceEqual(
            qs,
            [
                {"num_books": 2, "name": "Apress", "num_awards": 3},
                {"num_books": 0, "name": "Jonno's House of Books", "num_awards": 0},
                {"num_books": 1, "name": "Sams", "num_awards": 1},
            ],
        )

    def test_db_col_table(self):
        # Tests on fields with non-default table and column names.
        qs = Clues.objects.values("EntryID__Entry").annotate(
            Appearances=Count("EntryID"), Distinct_Clues=Count("Clue", distinct=True)
        )
        self.assertQuerysetEqual(qs, [])

        qs = Entries.objects.annotate(clue_count=Count("clues__ID"))
        self.assertQuerysetEqual(qs, [])

    def test_boolean_conversion(self):
        # Aggregates mixed up ordering of columns for backend's convert_values
        # method. Refs #21126.
        e = Entries.objects.create(Entry="foo")
        c = Clues.objects.create(EntryID=e, Clue="bar")
        qs = Clues.objects.select_related("EntryID").annotate(Count("ID"))
        self.assertSequenceEqual(qs, [c])
        self.assertEqual(qs[0].EntryID, e)
        self.assertIs(qs[0].EntryID.Exclude, False)

    def test_empty(self):
        # Regression for #10089: Check handling of empty result sets with
        # aggregates
        self.assertEqual(Book.objects.filter(id__in=[]).count(), 0)

        vals = Book.objects.filter(id__in=[]).aggregate(
            num_authors=Count("authors"),
            avg_authors=Avg("authors"),
            max_authors=Max("authors"),
            max_price=Max("price"),
            max_rating=Max("rating"),
        )
        self.assertEqual(
            vals,
            {
                "max_authors": None,
                "max_rating": None,
                "num_authors": 0,
                "avg_authors": None,
                "max_price": None,
            },
        )

        qs = (
            Publisher.objects.filter(name="Jonno's House of Books")
            .annotate(
                num_authors=Count("book__authors"),
                avg_authors=Avg("book__authors"),
                max_authors=Max("book__authors"),
                max_price=Max("book__price"),
                max_rating=Max("book__rating"),
            )
            .values()
        )
        self.assertSequenceEqual(
            qs,
            [
                {
                    "max_authors": None,
                    "name": "Jonno's House of Books",
                    "num_awards": 0,
                    "max_price": None,
                    "num_authors": 0,
                    "max_rating": None,
                    "id": self.p5.id,
                    "avg_authors": None,
                }
            ],
        )

    def test_more_more(self):
        # Regression for #10113 - Fields mentioned in order_by() must be
        # included in the GROUP BY. This only becomes a problem when the
        # order_by introduces a new join.
        self.assertQuerysetEqual(
            Book.objects.annotate(num_authors=Count("authors")).order_by(
                "publisher__name", "name"
            ),
            [
                "Practical Django Projects",
                "The Definitive Guide to Django: Web Development Done Right",
                "Paradigms of Artificial Intelligence Programming: Case Studies in "
                "Common Lisp",
                "Artificial Intelligence: A Modern Approach",
                "Python Web Development with Django",
                "Sams Teach Yourself Django in 24 Hours",
            ],
            lambda b: b.name,
        )

        # Regression for #10127 - Empty select_related() works with annotate
        qs = (
            Book.objects.filter(rating__lt=4.5)
            .select_related()
            .annotate(Avg("authors__age"))
            .order_by("name")
        )
        self.assertQuerysetEqual(
            qs,
            [
                (
                    "Artificial Intelligence: A Modern Approach",
                    51.5,
                    "Prentice Hall",
                    "Peter Norvig",
                ),
                ("Practical Django Projects", 29.0, "Apress", "James Bennett"),
                (
                    "Python Web Development with Django",
                    Approximate(30.333, places=2),
                    "Prentice Hall",
                    "Jeffrey Forcier",
                ),
                ("Sams Teach Yourself Django in 24 Hours", 45.0, "Sams", "Brad Dayley"),
            ],
            lambda b: (b.name, b.authors__age__avg, b.publisher.name, b.contact.name),
        )

        # Regression for #10132 - If the values() clause only mentioned extra
        # (select=) columns, those columns are used for grouping
        qs = (
            Book.objects.extra(select={"pub": "publisher_id"})
            .values("pub")
            .annotate(Count("id"))
            .order_by("pub")
        )
        self.assertSequenceEqual(
            qs,
            [
                {"pub": self.p1.id, "id__count": 2},
                {"pub": self.p2.id, "id__count": 1},
                {"pub": self.p3.id, "id__count": 2},
                {"pub": self.p4.id, "id__count": 1},
            ],
        )

        qs = (
            Book.objects.extra(select={"pub": "publisher_id", "foo": "pages"})
            .values("pub")
            .annotate(Count("id"))
            .order_by("pub")
        )
        self.assertSequenceEqual(
            qs,
            [
                {"pub": self.p1.id, "id__count": 2},
                {"pub": self.p2.id, "id__count": 1},
                {"pub": self.p3.id, "id__count": 2},
                {"pub": self.p4.id, "id__count": 1},
            ],
        )

        # Regression for #10182 - Queries with aggregate calls are correctly
        # realiased when used in a subquery
        ids = (
            Book.objects.filter(pages__gt=100)
            .annotate(n_authors=Count("authors"))
            .filter(n_authors__gt=2)
            .order_by("n_authors")
        )
        self.assertQuerysetEqual(
            Book.objects.filter(id__in=ids),
            [
                "Python Web Development with Django",
            ],
            lambda b: b.name,
        )

        # Regression for #15709 - Ensure each group_by field only exists once
        # per query
        qstr = str(
            Book.objects.values("publisher")
            .annotate(max_pages=Max("pages"))
            .order_by()
            .query
        )
        # There is just one GROUP BY clause (zero commas means at most one clause).
        self.assertEqual(qstr[qstr.index("GROUP BY") :].count(", "), 0)

    def test_duplicate_alias(self):
        # Regression for #11256 - duplicating a default alias raises ValueError.
        msg = (
            "The named annotation 'authors__age__avg' conflicts with "
            "the default name for another annotation."
        )
        with self.assertRaisesMessage(ValueError, msg):
            Book.objects.annotate(
                Avg("authors__age"), authors__age__avg=Avg("authors__age")
            )

    def test_field_name_conflict(self):
        # Regression for #11256 - providing an aggregate name
        # that conflicts with a field name on the model raises ValueError
        msg = "The annotation 'age' conflicts with a field on the model."
        with self.assertRaisesMessage(ValueError, msg):
            Author.objects.annotate(age=Avg("friends__age"))

    def test_m2m_name_conflict(self):
        # Regression for #11256 - providing an aggregate name
        # that conflicts with an m2m name on the model raises ValueError
        msg = "The annotation 'friends' conflicts with a field on the model."
        with self.assertRaisesMessage(ValueError, msg):
            Author.objects.annotate(friends=Count("friends"))

    def test_fk_attname_conflict(self):
        msg = "The annotation 'contact_id' conflicts with a field on the model."
        with self.assertRaisesMessage(ValueError, msg):
            Book.objects.annotate(contact_id=F("publisher_id"))

    def test_values_queryset_non_conflict(self):
        # If you're using a values query set, some potential conflicts are
        # avoided.
        # age is a field on Author, so it shouldn't be allowed as an aggregate.
        # But age isn't included in values(), so it is.
        results = (
            Author.objects.values("name")
            .annotate(age=Count("book_contact_set"))
            .order_by("name")
        )
        self.assertEqual(len(results), 9)
        self.assertEqual(results[0]["name"], "Adrian Holovaty")
        self.assertEqual(results[0]["age"], 1)

        # Same problem, but aggregating over m2m fields
        results = (
            Author.objects.values("name")
            .annotate(age=Avg("friends__age"))
            .order_by("name")
        )
        self.assertEqual(len(results), 9)
        self.assertEqual(results[0]["name"], "Adrian Holovaty")
        self.assertEqual(results[0]["age"], 32.0)

        # Same problem, but colliding with an m2m field
        results = (
            Author.objects.values("name")
            .annotate(friends=Count("friends"))
            .order_by("name")
        )
        self.assertEqual(len(results), 9)
        self.assertEqual(results[0]["name"], "Adrian Holovaty")
        self.assertEqual(results[0]["friends"], 2)

    def test_reverse_relation_name_conflict(self):
        # Regression for #11256 - providing an aggregate name
        # that conflicts with a reverse-related name on the model raises ValueError
        msg = "The annotation 'book_contact_set' conflicts with a field on the model."
        with self.assertRaisesMessage(ValueError, msg):
            Author.objects.annotate(book_contact_set=Avg("friends__age"))

    def test_pickle(self):
        # Regression for #10197 -- Queries with aggregates can be pickled.
        # First check that pickling is possible at all. No crash = success
        qs = Book.objects.annotate(num_authors=Count("authors"))
        pickle.dumps(qs)

        # Then check that the round trip works.
        query = qs.query.get_compiler(qs.db).as_sql()[0]
        qs2 = pickle.loads(pickle.dumps(qs))
        self.assertEqual(
            qs2.query.get_compiler(qs2.db).as_sql()[0],
            query,
        )

    def test_more_more_more(self):
        # Regression for #10199 - Aggregate calls clone the original query so
        # the original query can still be used
        books = Book.objects.all()
        books.aggregate(Avg("authors__age"))
        self.assertQuerysetEqual(
            books.all(),
            [
                "Artificial Intelligence: A Modern Approach",
                "Paradigms of Artificial Intelligence Programming: Case Studies in "
                "Common Lisp",
                "Practical Django Projects",
                "Python Web Development with Django",
                "Sams Teach Yourself Django in 24 Hours",
                "The Definitive Guide to Django: Web Development Done Right",
            ],
            lambda b: b.name,
        )

        # Regression for #10248 - Annotations work with dates()
        qs = (
            Book.objects.annotate(num_authors=Count("authors"))
            .filter(num_authors=2)
            .dates("pubdate", "day")
        )
        self.assertSequenceEqual(
            qs,
            [
                datetime.date(1995, 1, 15),
                datetime.date(2007, 12, 6),
            ],
        )

        # Regression for #10290 - extra selects with parameters can be used for
        # grouping.
        qs = (
            Book.objects.annotate(mean_auth_age=Avg("authors__age"))
            .extra(select={"sheets": "(pages + %s) / %s"}, select_params=[1, 2])
            .order_by("sheets")
            .values("sheets")
        )
        self.assertQuerysetEqual(
            qs, [150, 175, 224, 264, 473, 566], lambda b: int(b["sheets"])
        )

        # Regression for 10425 - annotations don't get in the way of a count()
        # clause
        self.assertEqual(
            Book.objects.values("publisher").annotate(Count("publisher")).count(), 4
        )
        self.assertEqual(
            Book.objects.annotate(Count("publisher")).values("publisher").count(), 6
        )

        # Note: intentionally no order_by(), that case needs tests, too.
        publishers = Publisher.objects.filter(id__in=[self.p1.id, self.p2.id])
        self.assertEqual(sorted(p.name for p in publishers), ["Apress", "Sams"])

        publishers = publishers.annotate(n_books=Count("book"))
        sorted_publishers = sorted(publishers, key=lambda x: x.name)
        self.assertEqual(sorted_publishers[0].n_books, 2)
        self.assertEqual(sorted_publishers[1].n_books, 1)

        self.assertEqual(sorted(p.name for p in publishers), ["Apress", "Sams"])

        books = Book.objects.filter(publisher__in=publishers)
        self.assertQuerysetEqual(
            books,
            [
                "Practical Django Projects",
                "Sams Teach Yourself Django in 24 Hours",
                "The Definitive Guide to Django: Web Development Done Right",
            ],
            lambda b: b.name,
        )
        self.assertEqual(sorted(p.name for p in publishers), ["Apress", "Sams"])

        # Regression for 10666 - inherited fields work with annotations and
        # aggregations
        self.assertEqual(
            HardbackBook.objects.aggregate(n_pages=Sum("book_ptr__pages")),
            {"n_pages": 2078},
        )

        self.assertEqual(
            HardbackBook.objects.aggregate(n_pages=Sum("pages")),
            {"n_pages": 2078},
        )

        qs = (
            HardbackBook.objects.annotate(
                n_authors=Count("book_ptr__authors"),
            )
            .values("name", "n_authors")
            .order_by("name")
        )
        self.assertSequenceEqual(
            qs,
            [
                {"n_authors": 2, "name": "Artificial Intelligence: A Modern Approach"},
                {
                    "n_authors": 1,
                    "name": (
                        "Paradigms of Artificial Intelligence Programming: Case "
                        "Studies in Common Lisp"
                    ),
                },
            ],
        )

        qs = (
            HardbackBook.objects.annotate(n_authors=Count("authors"))
            .values("name", "n_authors")
            .order_by("name")
        )
        self.assertSequenceEqual(
            qs,
            [
                {"n_authors": 2, "name": "Artificial Intelligence: A Modern Approach"},
                {
                    "n_authors": 1,
                    "name": (
                        "Paradigms of Artificial Intelligence Programming: Case "
                        "Studies in Common Lisp"
                    ),
                },
            ],
        )

        # Regression for #10766 - Shouldn't be able to reference an aggregate
        # fields in an aggregate() call.
        msg = "Cannot compute Avg('mean_age'): 'mean_age' is an aggregate"
        with self.assertRaisesMessage(FieldError, msg):
            Book.objects.annotate(mean_age=Avg("authors__age")).annotate(
                Avg("mean_age")
            )

    def test_empty_filter_count(self):
        self.assertEqual(
            Author.objects.filter(id__in=[]).annotate(Count("friends")).count(), 0
        )

    def test_empty_filter_aggregate(self):
        self.assertEqual(
            Author.objects.filter(id__in=[])
            .annotate(Count("friends"))
            .aggregate(Count("pk")),
            {"pk__count": 0},
        )

    def test_none_call_before_aggregate(self):
        # Regression for #11789
        self.assertEqual(
            Author.objects.none().aggregate(Avg("age")), {"age__avg": None}
        )

    def test_annotate_and_join(self):
        self.assertEqual(
            Author.objects.annotate(c=Count("friends__name"))
            .exclude(friends__name="Joe")
            .count(),
            Author.objects.count(),
        )

    def test_f_expression_annotation(self):
        # Books with less than 200 pages per author.
        qs = (
            Book.objects.values("name")
            .annotate(n_authors=Count("authors"))
            .filter(pages__lt=F("n_authors") * 200)
            .values_list("pk")
        )
        self.assertQuerysetEqual(
            Book.objects.filter(pk__in=qs),
            ["Python Web Development with Django"],
            attrgetter("name"),
        )

    def test_values_annotate_values(self):
        qs = (
            Book.objects.values("name")
            .annotate(n_authors=Count("authors"))
            .values_list("pk", flat=True)
            .order_by("name")
        )
        self.assertEqual(list(qs), list(Book.objects.values_list("pk", flat=True)))

    def test_having_group_by(self):
        # When a field occurs on the LHS of a HAVING clause that it
        # appears correctly in the GROUP BY clause
        qs = (
            Book.objects.values_list("name")
            .annotate(n_authors=Count("authors"))
            .filter(pages__gt=F("n_authors"))
            .values_list("name", flat=True)
            .order_by("name")
        )
        # Results should be the same, all Books have more pages than authors
        self.assertEqual(list(qs), list(Book.objects.values_list("name", flat=True)))

    def test_values_list_annotation_args_ordering(self):
        """
        Annotate *args ordering should be preserved in values_list results.
        **kwargs comes after *args.
        Regression test for #23659.
        """
        books = (
            Book.objects.values_list("publisher__name")
            .annotate(
                Count("id"), Avg("price"), Avg("authors__age"), avg_pgs=Avg("pages")
            )
            .order_by("-publisher__name")
        )
        self.assertEqual(books[0], ("Sams", 1, Decimal("23.09"), 45.0, 528.0))

    def test_annotation_disjunction(self):
        qs = (
            Book.objects.annotate(n_authors=Count("authors"))
            .filter(Q(n_authors=2) | Q(name="Python Web Development with Django"))
            .order_by("name")
        )
        self.assertQuerysetEqual(
            qs,
            [
                "Artificial Intelligence: A Modern Approach",
                "Python Web Development with Django",
                "The Definitive Guide to Django: Web Development Done Right",
            ],
            attrgetter("name"),
        )

        qs = (
            Book.objects.annotate(n_authors=Count("authors")).filter(
                Q(name="The Definitive Guide to Django: Web Development Done Right")
                | (
                    Q(name="Artificial Intelligence: A Modern Approach")
                    & Q(n_authors=3)
                )
            )
        ).order_by("name")
        self.assertQuerysetEqual(
            qs,
            [
                "The Definitive Guide to Django: Web Development Done Right",
            ],
            attrgetter("name"),
        )

        qs = (
            Publisher.objects.annotate(
                rating_sum=Sum("book__rating"), book_count=Count("book")
            )
            .filter(Q(rating_sum__gt=5.5) | Q(rating_sum__isnull=True))
            .order_by("pk")
        )
        self.assertQuerysetEqual(
            qs,
            [
                "Apress",
                "Prentice Hall",
                "Jonno's House of Books",
            ],
            attrgetter("name"),
        )

        qs = (
            Publisher.objects.annotate(
                rating_sum=Sum("book__rating"), book_count=Count("book")
            )
            .filter(Q(rating_sum__gt=F("book_count")) | Q(rating_sum=None))
            .order_by("num_awards")
        )
        self.assertQuerysetEqual(
            qs,
            [
                "Jonno's House of Books",
                "Sams",
                "Apress",
                "Prentice Hall",
                "Morgan Kaufmann",
            ],
            attrgetter("name"),
        )

    def test_quoting_aggregate_order_by(self):
        qs = (
            Book.objects.filter(name="Python Web Development with Django")
            .annotate(authorCount=Count("authors"))
            .order_by("authorCount")
        )
        self.assertQuerysetEqual(
            qs,
            [
                ("Python Web Development with Django", 3),
            ],
            lambda b: (b.name, b.authorCount),
        )

    def test_stddev(self):
        self.assertEqual(
            Book.objects.aggregate(StdDev("pages")),
            {"pages__stddev": Approximate(311.46, 1)},
        )

        self.assertEqual(
            Book.objects.aggregate(StdDev("rating")),
            {"rating__stddev": Approximate(0.60, 1)},
        )

        self.assertEqual(
            Book.objects.aggregate(StdDev("price")),
            {"price__stddev": Approximate(Decimal("24.16"), 2)},
        )

        self.assertEqual(
            Book.objects.aggregate(StdDev("pages", sample=True)),
            {"pages__stddev": Approximate(341.19, 2)},
        )

        self.assertEqual(
            Book.objects.aggregate(StdDev("rating", sample=True)),
            {"rating__stddev": Approximate(0.66, 2)},
        )

        self.assertEqual(
            Book.objects.aggregate(StdDev("price", sample=True)),
            {"price__stddev": Approximate(Decimal("26.46"), 1)},
        )

        self.assertEqual(
            Book.objects.aggregate(Variance("pages")),
            {"pages__variance": Approximate(97010.80, 1)},
        )

        self.assertEqual(
            Book.objects.aggregate(Variance("rating")),
            {"rating__variance": Approximate(0.36, 1)},
        )

        self.assertEqual(
            Book.objects.aggregate(Variance("price")),
            {"price__variance": Approximate(Decimal("583.77"), 1)},
        )

        self.assertEqual(
            Book.objects.aggregate(Variance("pages", sample=True)),
            {"pages__variance": Approximate(116412.96, 1)},
        )

        self.assertEqual(
            Book.objects.aggregate(Variance("rating", sample=True)),
            {"rating__variance": Approximate(0.44, 2)},
        )

        self.assertEqual(
            Book.objects.aggregate(Variance("price", sample=True)),
            {"price__variance": Approximate(Decimal("700.53"), 2)},
        )

    def test_filtering_by_annotation_name(self):
        # Regression test for #14476

        # The name of the explicitly provided annotation name in this case
        # poses no problem
        qs = (
            Author.objects.annotate(book_cnt=Count("book"))
            .filter(book_cnt=2)
            .order_by("name")
        )
        self.assertQuerysetEqual(qs, ["Peter Norvig"], lambda b: b.name)
        # Neither in this case
        qs = (
            Author.objects.annotate(book_count=Count("book"))
            .filter(book_count=2)
            .order_by("name")
        )
        self.assertQuerysetEqual(qs, ["Peter Norvig"], lambda b: b.name)
        # This case used to fail because the ORM couldn't resolve the
        # automatically generated annotation name `book__count`
        qs = (
            Author.objects.annotate(Count("book"))
            .filter(book__count=2)
            .order_by("name")
        )
        self.assertQuerysetEqual(qs, ["Peter Norvig"], lambda b: b.name)
        # Referencing the auto-generated name in an aggregate() also works.
        self.assertEqual(
            Author.objects.annotate(Count("book")).aggregate(Max("book__count")),
            {"book__count__max": 2},
        )

    def test_annotate_joins(self):
        """
        The base table's join isn't promoted to LOUTER. This could
        cause the query generation to fail if there is an exclude() for fk-field
        in the query, too. Refs #19087.
        """
        qs = Book.objects.annotate(n=Count("pk"))
        self.assertIs(qs.query.alias_map["aggregation_regress_book"].join_type, None)
        # The query executes without problems.
        self.assertEqual(len(qs.exclude(publisher=-1)), 6)

    @skipUnlessAnyDBFeature("allows_group_by_pk", "allows_group_by_selected_pks")
    def test_aggregate_duplicate_columns(self):
        # Regression test for #17144

        results = Author.objects.annotate(num_contacts=Count("book_contact_set"))

        # There should only be one GROUP BY clause, for the `id` column.
        # `name` and `age` should not be grouped on.
        _, _, group_by = results.query.get_compiler(using="default").pre_sql_setup()
        self.assertEqual(len(group_by), 1)
        self.assertIn("id", group_by[0][0])
        self.assertNotIn("name", group_by[0][0])
        self.assertNotIn("age", group_by[0][0])
        self.assertEqual(
            [(a.name, a.num_contacts) for a in results.order_by("name")],
            [
                ("Adrian Holovaty", 1),
                ("Brad Dayley", 1),
                ("Jacob Kaplan-Moss", 0),
                ("James Bennett", 1),
                ("Jeffrey Forcier", 1),
                ("Paul Bissex", 0),
                ("Peter Norvig", 2),
                ("Stuart Russell", 0),
                ("Wesley J. Chun", 0),
            ],
        )

    @skipUnlessAnyDBFeature("allows_group_by_pk", "allows_group_by_selected_pks")
    def test_aggregate_duplicate_columns_only(self):
        # Works with only() too.
        results = Author.objects.only("id", "name").annotate(
            num_contacts=Count("book_contact_set")
        )
        _, _, grouping = results.query.get_compiler(using="default").pre_sql_setup()
        self.assertEqual(len(grouping), 1)
        self.assertIn("id", grouping[0][0])
        self.assertNotIn("name", grouping[0][0])
        self.assertNotIn("age", grouping[0][0])
        self.assertEqual(
            [(a.name, a.num_contacts) for a in results.order_by("name")],
            [
                ("Adrian Holovaty", 1),
                ("Brad Dayley", 1),
                ("Jacob Kaplan-Moss", 0),
                ("James Bennett", 1),
                ("Jeffrey Forcier", 1),
                ("Paul Bissex", 0),
                ("Peter Norvig", 2),
                ("Stuart Russell", 0),
                ("Wesley J. Chun", 0),
            ],
        )

    @skipUnlessAnyDBFeature("allows_group_by_pk", "allows_group_by_selected_pks")
    def test_aggregate_duplicate_columns_select_related(self):
        # And select_related()
        results = Book.objects.select_related("contact").annotate(
            num_authors=Count("authors")
        )
        _, _, grouping = results.query.get_compiler(using="default").pre_sql_setup()
        # In the case of `group_by_selected_pks` we also group by contact.id
        # because of the select_related.
        self.assertEqual(
            len(grouping), 1 if connection.features.allows_group_by_pk else 2
        )
        self.assertIn("id", grouping[0][0])
        self.assertNotIn("name", grouping[0][0])
        self.assertNotIn("contact", grouping[0][0])
        self.assertEqual(
            [(b.name, b.num_authors) for b in results.order_by("name")],
            [
                ("Artificial Intelligence: A Modern Approach", 2),
                (
                    "Paradigms of Artificial Intelligence Programming: Case Studies in "
                    "Common Lisp",
                    1,
                ),
                ("Practical Django Projects", 1),
                ("Python Web Development with Django", 3),
                ("Sams Teach Yourself Django in 24 Hours", 1),
                ("The Definitive Guide to Django: Web Development Done Right", 2),
            ],
        )

    @skipUnlessDBFeature("allows_group_by_selected_pks")
    def test_aggregate_unmanaged_model_columns(self):
        """
        Unmanaged models are sometimes used to represent database views which
        may not allow grouping by selected primary key.
        """

        def assertQuerysetResults(queryset):
            self.assertEqual(
                [(b.name, b.num_authors) for b in queryset.order_by("name")],
                [
                    ("Artificial Intelligence: A Modern Approach", 2),
                    (
                        "Paradigms of Artificial Intelligence Programming: Case "
                        "Studies in Common Lisp",
                        1,
                    ),
                    ("Practical Django Projects", 1),
                    ("Python Web Development with Django", 3),
                    ("Sams Teach Yourself Django in 24 Hours", 1),
                    ("The Definitive Guide to Django: Web Development Done Right", 2),
                ],
            )

        queryset = Book.objects.select_related("contact").annotate(
            num_authors=Count("authors")
        )
        # Unmanaged origin model.
        with mock.patch.object(Book._meta, "managed", False):
            _, _, grouping = queryset.query.get_compiler(
                using="default"
            ).pre_sql_setup()
            self.assertEqual(len(grouping), len(Book._meta.fields) + 1)
            for index, field in enumerate(Book._meta.fields):
                self.assertIn(field.name, grouping[index][0])
            self.assertIn(Author._meta.pk.name, grouping[-1][0])
            assertQuerysetResults(queryset)
        # Unmanaged related model.
        with mock.patch.object(Author._meta, "managed", False):
            _, _, grouping = queryset.query.get_compiler(
                using="default"
            ).pre_sql_setup()
            self.assertEqual(len(grouping), len(Author._meta.fields) + 1)
            self.assertIn(Book._meta.pk.name, grouping[0][0])
            for index, field in enumerate(Author._meta.fields):
                self.assertIn(field.name, grouping[index + 1][0])
            assertQuerysetResults(queryset)

    @skipUnlessDBFeature("allows_group_by_selected_pks")
    def test_aggregate_unmanaged_model_as_tables(self):
        qs = Book.objects.select_related("contact").annotate(
            num_authors=Count("authors")
        )
        # Force treating unmanaged models as tables.
        with mock.patch(
            "django.db.connection.features.allows_group_by_selected_pks_on_model",
            return_value=True,
        ):
            with mock.patch.object(Book._meta, "managed", False), mock.patch.object(
                Author._meta, "managed", False
            ):
                _, _, grouping = qs.query.get_compiler(using="default").pre_sql_setup()
                self.assertEqual(len(grouping), 2)
                self.assertIn("id", grouping[0][0])
                self.assertIn("id", grouping[1][0])
                self.assertQuerysetEqual(
                    qs.order_by("name"),
                    [
                        ("Artificial Intelligence: A Modern Approach", 2),
                        (
                            "Paradigms of Artificial Intelligence Programming: Case "
                            "Studies in Common Lisp",
                            1,
                        ),
                        ("Practical Django Projects", 1),
                        ("Python Web Development with Django", 3),
                        ("Sams Teach Yourself Django in 24 Hours", 1),
                        (
                            "The Definitive Guide to Django: Web Development Done "
                            "Right",
                            2,
                        ),
                    ],
                    attrgetter("name", "num_authors"),
                )

    def test_reverse_join_trimming(self):
        qs = Author.objects.annotate(Count("book_contact_set__contact"))
        self.assertIn(" JOIN ", str(qs.query))

    def test_aggregation_with_generic_reverse_relation(self):
        """
        Regression test for #10870:  Aggregates with joins ignore extra
        filters provided by setup_joins

        tests aggregations with generic reverse relations
        """
        django_book = Book.objects.get(name="Practical Django Projects")
        ItemTag.objects.create(
            object_id=django_book.id,
            tag="intermediate",
            content_type=ContentType.objects.get_for_model(django_book),
        )
        ItemTag.objects.create(
            object_id=django_book.id,
            tag="django",
            content_type=ContentType.objects.get_for_model(django_book),
        )
        # Assign a tag to model with same PK as the book above. If the JOIN
        # used in aggregation doesn't have content type as part of the
        # condition the annotation will also count the 'hi mom' tag for b.
        wmpk = WithManualPK.objects.create(id=django_book.pk)
        ItemTag.objects.create(
            object_id=wmpk.id,
            tag="hi mom",
            content_type=ContentType.objects.get_for_model(wmpk),
        )
        ai_book = Book.objects.get(
            name__startswith="Paradigms of Artificial Intelligence"
        )
        ItemTag.objects.create(
            object_id=ai_book.id,
            tag="intermediate",
            content_type=ContentType.objects.get_for_model(ai_book),
        )

        self.assertEqual(Book.objects.aggregate(Count("tags")), {"tags__count": 3})
        results = Book.objects.annotate(Count("tags")).order_by("-tags__count", "name")
        self.assertEqual(
            [(b.name, b.tags__count) for b in results],
            [
                ("Practical Django Projects", 2),
                (
                    "Paradigms of Artificial Intelligence Programming: Case Studies in "
                    "Common Lisp",
                    1,
                ),
                ("Artificial Intelligence: A Modern Approach", 0),
                ("Python Web Development with Django", 0),
                ("Sams Teach Yourself Django in 24 Hours", 0),
                ("The Definitive Guide to Django: Web Development Done Right", 0),
            ],
        )

    def test_negated_aggregation(self):
        expected_results = Author.objects.exclude(
            pk__in=Author.objects.annotate(book_cnt=Count("book")).filter(book_cnt=2)
        ).order_by("name")
        expected_results = [a.name for a in expected_results]
        qs = (
            Author.objects.annotate(book_cnt=Count("book"))
            .exclude(Q(book_cnt=2), Q(book_cnt=2))
            .order_by("name")
        )
        self.assertQuerysetEqual(qs, expected_results, lambda b: b.name)
        expected_results = Author.objects.exclude(
            pk__in=Author.objects.annotate(book_cnt=Count("book")).filter(book_cnt=2)
        ).order_by("name")
        expected_results = [a.name for a in expected_results]
        qs = (
            Author.objects.annotate(book_cnt=Count("book"))
            .exclude(Q(book_cnt=2) | Q(book_cnt=2))
            .order_by("name")
        )
        self.assertQuerysetEqual(qs, expected_results, lambda b: b.name)

    def test_name_filters(self):
        qs = (
            Author.objects.annotate(Count("book"))
            .filter(Q(book__count__exact=2) | Q(name="Adrian Holovaty"))
            .order_by("name")
        )
        self.assertQuerysetEqual(
            qs, ["Adrian Holovaty", "Peter Norvig"], lambda b: b.name
        )

    def test_name_expressions(self):
        # Aggregates are spotted correctly from F objects.
        # Note that Adrian's age is 34 in the fixtures, and he has one book
        # so both conditions match one author.
        qs = (
            Author.objects.annotate(Count("book"))
            .filter(Q(name="Peter Norvig") | Q(age=F("book__count") + 33))
            .order_by("name")
        )
        self.assertQuerysetEqual(
            qs, ["Adrian Holovaty", "Peter Norvig"], lambda b: b.name
        )

    def test_filter_aggregates_or_connector(self):
        q1 = Q(price__gt=50)
        q2 = Q(authors__count__gt=1)
        query = Book.objects.annotate(Count("authors")).filter(q1 | q2).order_by("pk")
        self.assertQuerysetEqual(
            query,
            [self.b1.pk, self.b4.pk, self.b5.pk, self.b6.pk],
            attrgetter("pk"),
        )

    def test_filter_aggregates_negated_and_connector(self):
        q1 = Q(price__gt=50)
        q2 = Q(authors__count__gt=1)
        query = (
            Book.objects.annotate(Count("authors")).filter(~(q1 & q2)).order_by("pk")
        )
        self.assertQuerysetEqual(
            query,
            [self.b1.pk, self.b2.pk, self.b3.pk, self.b4.pk, self.b6.pk],
            attrgetter("pk"),
        )

    def test_filter_aggregates_xor_connector(self):
        q1 = Q(price__gt=50)
        q2 = Q(authors__count__gt=1)
        query = Book.objects.annotate(Count("authors")).filter(q1 ^ q2).order_by("pk")
        self.assertQuerysetEqual(
            query,
            [self.b1.pk, self.b4.pk, self.b6.pk],
            attrgetter("pk"),
        )

    def test_filter_aggregates_negated_xor_connector(self):
        q1 = Q(price__gt=50)
        q2 = Q(authors__count__gt=1)
        query = (
            Book.objects.annotate(Count("authors")).filter(~(q1 ^ q2)).order_by("pk")
        )
        self.assertQuerysetEqual(
            query,
            [self.b2.pk, self.b3.pk, self.b5.pk],
            attrgetter("pk"),
        )

    def test_ticket_11293_q_immutable(self):
        """
        Splitting a q object to parts for where/having doesn't alter
        the original q-object.
        """
        q1 = Q(isbn="")
        q2 = Q(authors__count__gt=1)
        query = Book.objects.annotate(Count("authors"))
        query.filter(q1 | q2)
        self.assertEqual(len(q2.children), 1)

    def test_fobj_group_by(self):
        """
        An F() object referring to related column works correctly in group by.
        """
        qs = Book.objects.annotate(account=Count("authors")).filter(
            account=F("publisher__num_awards")
        )
        self.assertQuerysetEqual(
            qs, ["Sams Teach Yourself Django in 24 Hours"], lambda b: b.name
        )

    def test_annotate_reserved_word(self):
        """
        Regression #18333 - Ensure annotated column name is properly quoted.
        """
        vals = Book.objects.annotate(select=Count("authors__id")).aggregate(
            Sum("select"), Avg("select")
        )
        self.assertEqual(
            vals,
            {
                "select__sum": 10,
                "select__avg": Approximate(1.666, places=2),
            },
        )

    def test_annotate_on_relation(self):
        book = Book.objects.annotate(
            avg_price=Avg("price"), publisher_name=F("publisher__name")
        ).get(pk=self.b1.pk)
        self.assertEqual(book.avg_price, 30.00)
        self.assertEqual(book.publisher_name, "Apress")

    def test_aggregate_on_relation(self):
        # A query with an existing annotation aggregation on a relation should
        # succeed.
        qs = Book.objects.annotate(avg_price=Avg("price")).aggregate(
            publisher_awards=Sum("publisher__num_awards")
        )
        self.assertEqual(qs["publisher_awards"], 30)

    def test_annotate_distinct_aggregate(self):
        # There are three books with rating of 4.0 and two of the books have
        # the same price. Hence, the distinct removes one rating of 4.0
        # from the results.
        vals1 = (
            Book.objects.values("rating", "price")
            .distinct()
            .aggregate(result=Sum("rating"))
        )
        vals2 = Book.objects.aggregate(result=Sum("rating") - Value(4.0))
        self.assertEqual(vals1, vals2)

    def test_annotate_values_list_flat(self):
        """Find ages that are shared by at least two authors."""
        qs = (
            Author.objects.values_list("age", flat=True)
            .annotate(age_count=Count("age"))
            .filter(age_count__gt=1)
        )
        self.assertSequenceEqual(qs, [29])

    def test_allow_distinct(self):
        class MyAggregate(Aggregate):
            pass

        with self.assertRaisesMessage(TypeError, "MyAggregate does not allow distinct"):
            MyAggregate("foo", distinct=True)

        class DistinctAggregate(Aggregate):
            allow_distinct = True

        DistinctAggregate("foo", distinct=True)

    @skipUnlessDBFeature("supports_subqueries_in_group_by")
    def test_having_subquery_select(self):
        authors = Author.objects.filter(pk=self.a1.pk)
        books = Book.objects.annotate(Count("authors")).filter(
            Q(authors__in=authors) | Q(authors__count__gt=2)
        )
        self.assertEqual(set(books), {self.b1, self.b4})


class JoinPromotionTests(TestCase):
    def test_ticket_21150(self):
        b = Bravo.objects.create()
        c = Charlie.objects.create(bravo=b)
        qs = Charlie.objects.select_related("alfa").annotate(Count("bravo__charlie"))
        self.assertSequenceEqual(qs, [c])
        self.assertIs(qs[0].alfa, None)
        a = Alfa.objects.create()
        c.alfa = a
        c.save()
        # Force re-evaluation
        qs = qs.all()
        self.assertSequenceEqual(qs, [c])
        self.assertEqual(qs[0].alfa, a)

    def test_existing_join_not_promoted(self):
        # No promotion for existing joins
        qs = Charlie.objects.filter(alfa__name__isnull=False).annotate(
            Count("alfa__name")
        )
        self.assertIn(" INNER JOIN ", str(qs.query))
        # Also, the existing join is unpromoted when doing filtering for already
        # promoted join.
        qs = Charlie.objects.annotate(Count("alfa__name")).filter(
            alfa__name__isnull=False
        )
        self.assertIn(" INNER JOIN ", str(qs.query))
        # But, as the join is nullable first use by annotate will be LOUTER
        qs = Charlie.objects.annotate(Count("alfa__name"))
        self.assertIn(" LEFT OUTER JOIN ", str(qs.query))

    def test_non_nullable_fk_not_promoted(self):
        qs = Book.objects.annotate(Count("contact__name"))
        self.assertIn(" INNER JOIN ", str(qs.query))


class SelfReferentialFKTests(TestCase):
    def test_ticket_24748(self):
        t1 = SelfRefFK.objects.create(name="t1")
        SelfRefFK.objects.create(name="t2", parent=t1)
        SelfRefFK.objects.create(name="t3", parent=t1)
        self.assertQuerysetEqual(
            SelfRefFK.objects.annotate(num_children=Count("children")).order_by("name"),
            [("t1", 2), ("t2", 0), ("t3", 0)],
            lambda x: (x.name, x.num_children),
        )
