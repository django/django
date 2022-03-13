from datetime import date
from decimal import Decimal

from django.core.exceptions import FieldDoesNotExist
from django.db.models.query import RawQuerySet
from django.test import TestCase, skipUnlessDBFeature

from .models import (
    Author,
    Book,
    BookFkAsPk,
    Coffee,
    FriendlyAuthor,
    MixedCaseIDColumn,
    Reviewer,
)


class RawQueryTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.a1 = Author.objects.create(
            first_name="Joe", last_name="Smith", dob=date(1950, 9, 20)
        )
        cls.a2 = Author.objects.create(
            first_name="Jill", last_name="Doe", dob=date(1920, 4, 2)
        )
        cls.a3 = Author.objects.create(
            first_name="Bob", last_name="Smith", dob=date(1986, 1, 25)
        )
        cls.a4 = Author.objects.create(
            first_name="Bill", last_name="Jones", dob=date(1932, 5, 10)
        )
        cls.b1 = Book.objects.create(
            title="The awesome book",
            author=cls.a1,
            paperback=False,
            opening_line=(
                "It was a bright cold day in April and the clocks were striking "
                "thirteen."
            ),
        )
        cls.b2 = Book.objects.create(
            title="The horrible book",
            author=cls.a1,
            paperback=True,
            opening_line=(
                "On an evening in the latter part of May a middle-aged man "
                "was walking homeward from Shaston to the village of Marlott, "
                "in the adjoining Vale of Blakemore, or Blackmoor."
            ),
        )
        cls.b3 = Book.objects.create(
            title="Another awesome book",
            author=cls.a1,
            paperback=False,
            opening_line="A squat gray building of only thirty-four stories.",
        )
        cls.b4 = Book.objects.create(
            title="Some other book",
            author=cls.a3,
            paperback=True,
            opening_line="It was the day my grandmother exploded.",
        )
        cls.c1 = Coffee.objects.create(brand="dunkin doughnuts")
        cls.c2 = Coffee.objects.create(brand="starbucks")
        cls.r1 = Reviewer.objects.create()
        cls.r2 = Reviewer.objects.create()
        cls.r1.reviewed.add(cls.b2, cls.b3, cls.b4)

    def assertSuccessfulRawQuery(
        self,
        model,
        query,
        expected_results,
        expected_annotations=(),
        params=[],
        translations=None,
    ):
        """
        Execute the passed query against the passed model and check the output
        """
        results = list(
            model.objects.raw(query, params=params, translations=translations)
        )
        self.assertProcessed(model, results, expected_results, expected_annotations)
        self.assertAnnotations(results, expected_annotations)

    def assertProcessed(self, model, results, orig, expected_annotations=()):
        """
        Compare the results of a raw query against expected results
        """
        self.assertEqual(len(results), len(orig))
        for index, item in enumerate(results):
            orig_item = orig[index]
            for annotation in expected_annotations:
                setattr(orig_item, *annotation)

            for field in model._meta.fields:
                # All values on the model are equal
                self.assertEqual(
                    getattr(item, field.attname), getattr(orig_item, field.attname)
                )
                # This includes checking that they are the same type
                self.assertEqual(
                    type(getattr(item, field.attname)),
                    type(getattr(orig_item, field.attname)),
                )

    def assertNoAnnotations(self, results):
        """
        The results of a raw query contain no annotations
        """
        self.assertAnnotations(results, ())

    def assertAnnotations(self, results, expected_annotations):
        """
        The passed raw query results contain the expected annotations
        """
        if expected_annotations:
            for index, result in enumerate(results):
                annotation, value = expected_annotations[index]
                self.assertTrue(hasattr(result, annotation))
                self.assertEqual(getattr(result, annotation), value)

    def test_rawqueryset_repr(self):
        queryset = RawQuerySet(raw_query="SELECT * FROM raw_query_author")
        self.assertEqual(
            repr(queryset), "<RawQuerySet: SELECT * FROM raw_query_author>"
        )
        self.assertEqual(
            repr(queryset.query), "<RawQuery: SELECT * FROM raw_query_author>"
        )

    def test_simple_raw_query(self):
        """
        Basic test of raw query with a simple database query
        """
        query = "SELECT * FROM raw_query_author"
        authors = Author.objects.all()
        self.assertSuccessfulRawQuery(Author, query, authors)

    def test_raw_query_lazy(self):
        """
        Raw queries are lazy: they aren't actually executed until they're
        iterated over.
        """
        q = Author.objects.raw("SELECT * FROM raw_query_author")
        self.assertIsNone(q.query.cursor)
        list(q)
        self.assertIsNotNone(q.query.cursor)

    def test_FK_raw_query(self):
        """
        Test of a simple raw query against a model containing a foreign key
        """
        query = "SELECT * FROM raw_query_book"
        books = Book.objects.all()
        self.assertSuccessfulRawQuery(Book, query, books)

    def test_db_column_handler(self):
        """
        Test of a simple raw query against a model containing a field with
        db_column defined.
        """
        query = "SELECT * FROM raw_query_coffee"
        coffees = Coffee.objects.all()
        self.assertSuccessfulRawQuery(Coffee, query, coffees)

    def test_pk_with_mixed_case_db_column(self):
        """
        A raw query with a model that has a pk db_column with mixed case.
        """
        query = "SELECT * FROM raw_query_mixedcaseidcolumn"
        queryset = MixedCaseIDColumn.objects.all()
        self.assertSuccessfulRawQuery(MixedCaseIDColumn, query, queryset)

    def test_order_handler(self):
        """
        Test of raw raw query's tolerance for columns being returned in any
        order
        """
        selects = (
            ("dob, last_name, first_name, id"),
            ("last_name, dob, first_name, id"),
            ("first_name, last_name, dob, id"),
        )

        for select in selects:
            query = "SELECT %s FROM raw_query_author" % select
            authors = Author.objects.all()
            self.assertSuccessfulRawQuery(Author, query, authors)

    def test_translations(self):
        """
        Test of raw query's optional ability to translate unexpected result
        column names to specific model fields
        """
        query = (
            "SELECT first_name AS first, last_name AS last, dob, id "
            "FROM raw_query_author"
        )
        translations = {"first": "first_name", "last": "last_name"}
        authors = Author.objects.all()
        self.assertSuccessfulRawQuery(Author, query, authors, translations=translations)

    def test_params(self):
        """
        Test passing optional query parameters
        """
        query = "SELECT * FROM raw_query_author WHERE first_name = %s"
        author = Author.objects.all()[2]
        params = [author.first_name]
        qset = Author.objects.raw(query, params=params)
        results = list(qset)
        self.assertProcessed(Author, results, [author])
        self.assertNoAnnotations(results)
        self.assertEqual(len(results), 1)
        self.assertIsInstance(repr(qset), str)

    def test_params_none(self):
        query = "SELECT * FROM raw_query_author WHERE first_name like 'J%'"
        qset = Author.objects.raw(query, params=None)
        self.assertEqual(len(qset), 2)

    def test_escaped_percent(self):
        query = "SELECT * FROM raw_query_author WHERE first_name like 'J%%'"
        qset = Author.objects.raw(query)
        self.assertEqual(len(qset), 2)

    @skipUnlessDBFeature("supports_paramstyle_pyformat")
    def test_pyformat_params(self):
        """
        Test passing optional query parameters
        """
        query = "SELECT * FROM raw_query_author WHERE first_name = %(first)s"
        author = Author.objects.all()[2]
        params = {"first": author.first_name}
        qset = Author.objects.raw(query, params=params)
        results = list(qset)
        self.assertProcessed(Author, results, [author])
        self.assertNoAnnotations(results)
        self.assertEqual(len(results), 1)
        self.assertIsInstance(repr(qset), str)

    def test_query_representation(self):
        """
        Test representation of raw query with parameters
        """
        query = "SELECT * FROM raw_query_author WHERE last_name = %(last)s"
        qset = Author.objects.raw(query, {"last": "foo"})
        self.assertEqual(
            repr(qset),
            "<RawQuerySet: SELECT * FROM raw_query_author WHERE last_name = foo>",
        )
        self.assertEqual(
            repr(qset.query),
            "<RawQuery: SELECT * FROM raw_query_author WHERE last_name = foo>",
        )

        query = "SELECT * FROM raw_query_author WHERE last_name = %s"
        qset = Author.objects.raw(query, {"foo"})
        self.assertEqual(
            repr(qset),
            "<RawQuerySet: SELECT * FROM raw_query_author WHERE last_name = foo>",
        )
        self.assertEqual(
            repr(qset.query),
            "<RawQuery: SELECT * FROM raw_query_author WHERE last_name = foo>",
        )

    def test_many_to_many(self):
        """
        Test of a simple raw query against a model containing a m2m field
        """
        query = "SELECT * FROM raw_query_reviewer"
        reviewers = Reviewer.objects.all()
        self.assertSuccessfulRawQuery(Reviewer, query, reviewers)

    def test_extra_conversions(self):
        """Extra translations are ignored."""
        query = "SELECT * FROM raw_query_author"
        translations = {"something": "else"}
        authors = Author.objects.all()
        self.assertSuccessfulRawQuery(Author, query, authors, translations=translations)

    def test_missing_fields(self):
        query = "SELECT id, first_name, dob FROM raw_query_author"
        for author in Author.objects.raw(query):
            self.assertIsNotNone(author.first_name)
            # last_name isn't given, but it will be retrieved on demand
            self.assertIsNotNone(author.last_name)

    def test_missing_fields_without_PK(self):
        query = "SELECT first_name, dob FROM raw_query_author"
        msg = "Raw query must include the primary key"
        with self.assertRaisesMessage(FieldDoesNotExist, msg):
            list(Author.objects.raw(query))

    def test_annotations(self):
        query = (
            "SELECT a.*, count(b.id) as book_count "
            "FROM raw_query_author a "
            "LEFT JOIN raw_query_book b ON a.id = b.author_id "
            "GROUP BY a.id, a.first_name, a.last_name, a.dob ORDER BY a.id"
        )
        expected_annotations = (
            ("book_count", 3),
            ("book_count", 0),
            ("book_count", 1),
            ("book_count", 0),
        )
        authors = Author.objects.all()
        self.assertSuccessfulRawQuery(Author, query, authors, expected_annotations)

    def test_white_space_query(self):
        query = "    SELECT * FROM raw_query_author"
        authors = Author.objects.all()
        self.assertSuccessfulRawQuery(Author, query, authors)

    def test_multiple_iterations(self):
        query = "SELECT * FROM raw_query_author"
        normal_authors = Author.objects.all()
        raw_authors = Author.objects.raw(query)

        # First Iteration
        first_iterations = 0
        for index, raw_author in enumerate(raw_authors):
            self.assertEqual(normal_authors[index], raw_author)
            first_iterations += 1

        # Second Iteration
        second_iterations = 0
        for index, raw_author in enumerate(raw_authors):
            self.assertEqual(normal_authors[index], raw_author)
            second_iterations += 1

        self.assertEqual(first_iterations, second_iterations)

    def test_get_item(self):
        # Indexing on RawQuerySets
        query = "SELECT * FROM raw_query_author ORDER BY id ASC"
        third_author = Author.objects.raw(query)[2]
        self.assertEqual(third_author.first_name, "Bob")

        first_two = Author.objects.raw(query)[0:2]
        self.assertEqual(len(first_two), 2)

        with self.assertRaises(TypeError):
            Author.objects.raw(query)["test"]

    def test_inheritance(self):
        f = FriendlyAuthor.objects.create(
            first_name="Wesley", last_name="Chun", dob=date(1962, 10, 28)
        )
        query = "SELECT * FROM raw_query_friendlyauthor"
        self.assertEqual([o.pk for o in FriendlyAuthor.objects.raw(query)], [f.pk])

    def test_query_count(self):
        self.assertNumQueries(
            1, list, Author.objects.raw("SELECT * FROM raw_query_author")
        )

    def test_subquery_in_raw_sql(self):
        list(
            Book.objects.raw(
                "SELECT id FROM "
                "(SELECT * FROM raw_query_book WHERE paperback IS NOT NULL) sq"
            )
        )

    def test_db_column_name_is_used_in_raw_query(self):
        """
        Regression test that ensures the `column` attribute on the field is
        used to generate the list of fields included in the query, as opposed
        to the `attname`. This is important when the primary key is a
        ForeignKey field because `attname` and `column` are not necessarily the
        same.
        """
        b = BookFkAsPk.objects.create(book=self.b1)
        self.assertEqual(
            list(
                BookFkAsPk.objects.raw(
                    "SELECT not_the_default FROM raw_query_bookfkaspk"
                )
            ),
            [b],
        )

    def test_decimal_parameter(self):
        c = Coffee.objects.create(brand="starbucks", price=20.5)
        qs = Coffee.objects.raw(
            "SELECT * FROM raw_query_coffee WHERE price >= %s", params=[Decimal(20)]
        )
        self.assertEqual(list(qs), [c])

    def test_result_caching(self):
        with self.assertNumQueries(1):
            books = Book.objects.raw("SELECT * FROM raw_query_book")
            list(books)
            list(books)

    def test_iterator(self):
        with self.assertNumQueries(2):
            books = Book.objects.raw("SELECT * FROM raw_query_book")
            list(books.iterator())
            list(books.iterator())

    def test_bool(self):
        self.assertIs(bool(Book.objects.raw("SELECT * FROM raw_query_book")), True)
        self.assertIs(
            bool(Book.objects.raw("SELECT * FROM raw_query_book WHERE id = 0")), False
        )

    def test_len(self):
        self.assertEqual(len(Book.objects.raw("SELECT * FROM raw_query_book")), 4)
        self.assertEqual(
            len(Book.objects.raw("SELECT * FROM raw_query_book WHERE id = 0")), 0
        )
