from datetime import date
from decimal import Decimal
from unittest import mock

from django.db import connection, transaction
from django.db.models import (
    BooleanField,
    Case,
    Count,
    DecimalField,
    ExpressionWrapper,
    F,
    FilteredRelation,
    Q,
    Sum,
    Value,
    When,
)
from django.db.models.functions import Concat
from django.db.models.lookups import Exact, IStartsWith
from django.test import TestCase
from django.test.testcases import skipUnlessDBFeature

from .models import (
    Author,
    Book,
    BookDailySales,
    Borrower,
    Currency,
    Editor,
    ExchangeRate,
    RentalSession,
    Reservation,
    Seller,
)


class FilteredRelationTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.author1 = Author.objects.create(name="Alice")
        cls.author2 = Author.objects.create(name="Jane")
        cls.editor_a = Editor.objects.create(name="a")
        cls.editor_b = Editor.objects.create(name="b")
        cls.book1 = Book.objects.create(
            title="Poem by Alice",
            editor=cls.editor_a,
            author=cls.author1,
        )
        cls.book1.generic_author.set([cls.author2])
        cls.book2 = Book.objects.create(
            title="The book by Jane A",
            editor=cls.editor_b,
            author=cls.author2,
        )
        cls.book3 = Book.objects.create(
            title="The book by Jane B",
            editor=cls.editor_b,
            author=cls.author2,
        )
        cls.book4 = Book.objects.create(
            title="The book by Alice",
            editor=cls.editor_a,
            author=cls.author1,
        )
        cls.author1.favorite_books.add(cls.book2)
        cls.author1.favorite_books.add(cls.book3)

    def test_select_related(self):
        qs = (
            Author.objects.annotate(
                book_join=FilteredRelation("book"),
            )
            .select_related("book_join__editor")
            .order_by("pk", "book_join__pk")
        )
        with self.assertNumQueries(1):
            self.assertQuerySetEqual(
                qs,
                [
                    (self.author1, self.book1, self.editor_a, self.author1),
                    (self.author1, self.book4, self.editor_a, self.author1),
                    (self.author2, self.book2, self.editor_b, self.author2),
                    (self.author2, self.book3, self.editor_b, self.author2),
                ],
                lambda x: (x, x.book_join, x.book_join.editor, x.book_join.author),
            )

    def test_select_related_multiple(self):
        qs = (
            Book.objects.annotate(
                author_join=FilteredRelation("author"),
                editor_join=FilteredRelation("editor"),
            )
            .select_related("author_join", "editor_join")
            .order_by("pk")
        )
        self.assertQuerySetEqual(
            qs,
            [
                (self.book1, self.author1, self.editor_a),
                (self.book2, self.author2, self.editor_b),
                (self.book3, self.author2, self.editor_b),
                (self.book4, self.author1, self.editor_a),
            ],
            lambda x: (x, x.author_join, x.editor_join),
        )

    def test_select_related_with_empty_relation(self):
        qs = (
            Author.objects.annotate(
                book_join=FilteredRelation("book", condition=Q(pk=-1)),
            )
            .select_related("book_join")
            .order_by("pk")
        )
        self.assertSequenceEqual(qs, [self.author1, self.author2])

    def test_select_related_foreign_key(self):
        qs = (
            Book.objects.annotate(
                author_join=FilteredRelation("author"),
            )
            .select_related("author_join")
            .order_by("pk")
        )
        with self.assertNumQueries(1):
            self.assertQuerySetEqual(
                qs,
                [
                    (self.book1, self.author1),
                    (self.book2, self.author2),
                    (self.book3, self.author2),
                    (self.book4, self.author1),
                ],
                lambda x: (x, x.author_join),
            )

    @skipUnlessDBFeature("has_select_for_update", "has_select_for_update_of")
    def test_select_related_foreign_key_for_update_of(self):
        with transaction.atomic():
            qs = (
                Book.objects.annotate(
                    author_join=FilteredRelation("author"),
                )
                .select_related("author_join")
                .select_for_update(of=("self",))
                .order_by("pk")
            )
            with self.assertNumQueries(1):
                self.assertQuerySetEqual(
                    qs,
                    [
                        (self.book1, self.author1),
                        (self.book2, self.author2),
                        (self.book3, self.author2),
                        (self.book4, self.author1),
                    ],
                    lambda x: (x, x.author_join),
                )

    def test_without_join(self):
        self.assertCountEqual(
            Author.objects.annotate(
                book_alice=FilteredRelation(
                    "book", condition=Q(book__title__iexact="poem by alice")
                ),
            ),
            [self.author1, self.author2],
        )

    def test_with_join(self):
        self.assertSequenceEqual(
            Author.objects.annotate(
                book_alice=FilteredRelation(
                    "book", condition=Q(book__title__iexact="poem by alice")
                ),
            ).filter(book_alice__isnull=False),
            [self.author1],
        )

    def test_with_exclude(self):
        self.assertSequenceEqual(
            Author.objects.annotate(
                book_alice=FilteredRelation(
                    "book", condition=Q(book__title__iexact="poem by alice")
                ),
            ).exclude(book_alice__isnull=False),
            [self.author2],
        )

    def test_with_join_and_complex_condition(self):
        self.assertSequenceEqual(
            Author.objects.annotate(
                book_alice=FilteredRelation(
                    "book",
                    condition=Q(
                        Q(book__title__iexact="poem by alice")
                        | Q(book__state=Book.RENTED)
                    ),
                ),
            ).filter(book_alice__isnull=False),
            [self.author1],
        )

    def test_internal_queryset_alias_mapping(self):
        queryset = Author.objects.annotate(
            book_alice=FilteredRelation(
                "book", condition=Q(book__title__iexact="poem by alice")
            ),
        ).filter(book_alice__isnull=False)
        self.assertIn(
            "INNER JOIN {} book_alice ON".format(
                connection.ops.quote_name("filtered_relation_book")
            ),
            str(queryset.query),
        )

    def test_multiple(self):
        qs = (
            Author.objects.annotate(
                book_title_alice=FilteredRelation(
                    "book", condition=Q(book__title__contains="Alice")
                ),
                book_title_jane=FilteredRelation(
                    "book", condition=Q(book__title__icontains="Jane")
                ),
            )
            .filter(name="Jane")
            .values("book_title_alice__title", "book_title_jane__title")
        )
        empty = "" if connection.features.interprets_empty_strings_as_nulls else None
        self.assertCountEqual(
            qs,
            [
                {
                    "book_title_alice__title": empty,
                    "book_title_jane__title": "The book by Jane A",
                },
                {
                    "book_title_alice__title": empty,
                    "book_title_jane__title": "The book by Jane B",
                },
            ],
        )

    def test_with_multiple_filter(self):
        self.assertSequenceEqual(
            Author.objects.annotate(
                book_editor_a=FilteredRelation(
                    "book",
                    condition=Q(
                        book__title__icontains="book", book__editor_id=self.editor_a.pk
                    ),
                ),
            ).filter(book_editor_a__isnull=False),
            [self.author1],
        )

    def test_multiple_times(self):
        self.assertSequenceEqual(
            Author.objects.annotate(
                book_title_alice=FilteredRelation(
                    "book", condition=Q(book__title__icontains="alice")
                ),
            )
            .filter(book_title_alice__isnull=False)
            .filter(book_title_alice__isnull=False)
            .distinct(),
            [self.author1],
        )

    def test_exclude_relation_with_join(self):
        self.assertSequenceEqual(
            Author.objects.annotate(
                book_alice=FilteredRelation(
                    "book", condition=~Q(book__title__icontains="alice")
                ),
            )
            .filter(book_alice__isnull=False)
            .distinct(),
            [self.author2],
        )

    def test_with_m2m(self):
        qs = Author.objects.annotate(
            favorite_books_written_by_jane=FilteredRelation(
                "favorite_books",
                condition=Q(favorite_books__in=[self.book2]),
            ),
        ).filter(favorite_books_written_by_jane__isnull=False)
        self.assertSequenceEqual(qs, [self.author1])

    def test_with_m2m_deep(self):
        qs = Author.objects.annotate(
            favorite_books_written_by_jane=FilteredRelation(
                "favorite_books",
                condition=Q(favorite_books__author=self.author2),
            ),
        ).filter(favorite_books_written_by_jane__title="The book by Jane B")
        self.assertSequenceEqual(qs, [self.author1])

    def test_with_m2m_multijoin(self):
        qs = (
            Author.objects.annotate(
                favorite_books_written_by_jane=FilteredRelation(
                    "favorite_books",
                    condition=Q(favorite_books__author=self.author2),
                )
            )
            .filter(favorite_books_written_by_jane__editor__name="b")
            .distinct()
        )
        self.assertSequenceEqual(qs, [self.author1])

    def test_values_list(self):
        self.assertSequenceEqual(
            Author.objects.annotate(
                book_alice=FilteredRelation(
                    "book", condition=Q(book__title__iexact="poem by alice")
                ),
            )
            .filter(book_alice__isnull=False)
            .values_list("book_alice__title", flat=True),
            ["Poem by Alice"],
        )

    def test_values(self):
        self.assertSequenceEqual(
            Author.objects.annotate(
                book_alice=FilteredRelation(
                    "book", condition=Q(book__title__iexact="poem by alice")
                ),
            )
            .filter(book_alice__isnull=False)
            .values(),
            [
                {
                    "id": self.author1.pk,
                    "name": "Alice",
                    "content_type_id": None,
                    "object_id": None,
                }
            ],
        )

    def test_extra(self):
        self.assertSequenceEqual(
            Author.objects.annotate(
                book_alice=FilteredRelation(
                    "book", condition=Q(book__title__iexact="poem by alice")
                ),
            )
            .filter(book_alice__isnull=False)
            .extra(where=["1 = 1"]),
            [self.author1],
        )

    @skipUnlessDBFeature("supports_select_union")
    def test_union(self):
        qs1 = Author.objects.annotate(
            book_alice=FilteredRelation(
                "book", condition=Q(book__title__iexact="poem by alice")
            ),
        ).filter(book_alice__isnull=False)
        qs2 = Author.objects.annotate(
            book_jane=FilteredRelation(
                "book", condition=Q(book__title__iexact="the book by jane a")
            ),
        ).filter(book_jane__isnull=False)
        self.assertSequenceEqual(qs1.union(qs2), [self.author1, self.author2])

    @skipUnlessDBFeature("supports_select_intersection")
    def test_intersection(self):
        qs1 = Author.objects.annotate(
            book_alice=FilteredRelation(
                "book", condition=Q(book__title__iexact="poem by alice")
            ),
        ).filter(book_alice__isnull=False)
        qs2 = Author.objects.annotate(
            book_jane=FilteredRelation(
                "book", condition=Q(book__title__iexact="the book by jane a")
            ),
        ).filter(book_jane__isnull=False)
        self.assertSequenceEqual(qs1.intersection(qs2), [])

    @skipUnlessDBFeature("supports_select_difference")
    def test_difference(self):
        qs1 = Author.objects.annotate(
            book_alice=FilteredRelation(
                "book", condition=Q(book__title__iexact="poem by alice")
            ),
        ).filter(book_alice__isnull=False)
        qs2 = Author.objects.annotate(
            book_jane=FilteredRelation(
                "book", condition=Q(book__title__iexact="the book by jane a")
            ),
        ).filter(book_jane__isnull=False)
        self.assertSequenceEqual(qs1.difference(qs2), [self.author1])

    def test_select_for_update(self):
        self.assertSequenceEqual(
            Author.objects.annotate(
                book_jane=FilteredRelation(
                    "book", condition=Q(book__title__iexact="the book by jane a")
                ),
            )
            .filter(book_jane__isnull=False)
            .select_for_update(),
            [self.author2],
        )

    def test_defer(self):
        # One query for the list and one query for the deferred title.
        with self.assertNumQueries(2):
            self.assertQuerySetEqual(
                Author.objects.annotate(
                    book_alice=FilteredRelation(
                        "book", condition=Q(book__title__iexact="poem by alice")
                    ),
                )
                .filter(book_alice__isnull=False)
                .select_related("book_alice")
                .defer("book_alice__title"),
                ["Poem by Alice"],
                lambda author: author.book_alice.title,
            )

    def test_only_not_supported(self):
        msg = "only() is not supported with FilteredRelation."
        with self.assertRaisesMessage(ValueError, msg):
            Author.objects.annotate(
                book_alice=FilteredRelation(
                    "book", condition=Q(book__title__iexact="poem by alice")
                ),
            ).filter(book_alice__isnull=False).select_related("book_alice").only(
                "book_alice__state"
            )

    def test_as_subquery(self):
        inner_qs = Author.objects.annotate(
            book_alice=FilteredRelation(
                "book", condition=Q(book__title__iexact="poem by alice")
            ),
        ).filter(book_alice__isnull=False)
        qs = Author.objects.filter(id__in=inner_qs)
        self.assertSequenceEqual(qs, [self.author1])

    def test_nested_foreign_key(self):
        qs = (
            Author.objects.annotate(
                book_editor_worked_with=FilteredRelation(
                    "book__editor",
                    condition=Q(book__title__icontains="book by"),
                ),
            )
            .filter(
                book_editor_worked_with__isnull=False,
            )
            .select_related(
                "book_editor_worked_with",
            )
            .order_by("pk", "book_editor_worked_with__pk")
        )
        with self.assertNumQueries(1):
            self.assertQuerySetEqual(
                qs,
                [
                    (self.author1, self.editor_a),
                    (self.author2, self.editor_b),
                    (self.author2, self.editor_b),
                ],
                lambda x: (x, x.book_editor_worked_with),
            )

    def test_nested_foreign_key_nested_field(self):
        qs = (
            Author.objects.annotate(
                book_editor_worked_with=FilteredRelation(
                    "book__editor", condition=Q(book__title__icontains="book by")
                ),
            )
            .filter(
                book_editor_worked_with__isnull=False,
            )
            .values(
                "name",
                "book_editor_worked_with__name",
            )
            .order_by("name", "book_editor_worked_with__name")
            .distinct()
        )
        self.assertSequenceEqual(
            qs,
            [
                {
                    "name": self.author1.name,
                    "book_editor_worked_with__name": self.editor_a.name,
                },
                {
                    "name": self.author2.name,
                    "book_editor_worked_with__name": self.editor_b.name,
                },
            ],
        )

    def test_nested_foreign_key_filtered_base_object(self):
        qs = (
            Author.objects.annotate(
                alice_editors=FilteredRelation(
                    "book__editor",
                    condition=Q(name="Alice"),
                ),
            )
            .values(
                "name",
                "alice_editors__pk",
            )
            .order_by("name", "alice_editors__name")
            .distinct()
        )
        self.assertSequenceEqual(
            qs,
            [
                {"name": self.author1.name, "alice_editors__pk": self.editor_a.pk},
                {"name": self.author2.name, "alice_editors__pk": None},
            ],
        )

    def test_nested_m2m_filtered(self):
        qs = (
            Book.objects.annotate(
                favorite_book=FilteredRelation(
                    "author__favorite_books",
                    condition=Q(author__favorite_books__title__icontains="book by"),
                ),
            )
            .values(
                "title",
                "favorite_book__pk",
            )
            .order_by("title", "favorite_book__title")
        )
        self.assertSequenceEqual(
            qs,
            [
                {"title": self.book1.title, "favorite_book__pk": self.book2.pk},
                {"title": self.book1.title, "favorite_book__pk": self.book3.pk},
                {"title": self.book4.title, "favorite_book__pk": self.book2.pk},
                {"title": self.book4.title, "favorite_book__pk": self.book3.pk},
                {"title": self.book2.title, "favorite_book__pk": None},
                {"title": self.book3.title, "favorite_book__pk": None},
            ],
        )

    def test_nested_chained_relations(self):
        qs = (
            Author.objects.annotate(
                my_books=FilteredRelation(
                    "book",
                    condition=Q(book__title__icontains="book by"),
                ),
                preferred_by_authors=FilteredRelation(
                    "my_books__preferred_by_authors",
                    condition=Q(my_books__preferred_by_authors__name="Alice"),
                ),
            )
            .annotate(
                author=F("name"),
                book_title=F("my_books__title"),
                preferred_by_author_pk=F("preferred_by_authors"),
            )
            .order_by("author", "book_title", "preferred_by_author_pk")
        )
        self.assertQuerySetEqual(
            qs,
            [
                ("Alice", "The book by Alice", None),
                ("Jane", "The book by Jane A", self.author1.pk),
                ("Jane", "The book by Jane B", self.author1.pk),
            ],
            lambda x: (x.author, x.book_title, x.preferred_by_author_pk),
        )

    def test_three_level_nested_chained_relations(self):
        borrower = Borrower.objects.create(name="Jenny")
        Reservation.objects.create(
            borrower=borrower,
            book=self.book1,
            state=Reservation.STOPPED,
        )
        qs = Author.objects.annotate(
            my_books=FilteredRelation("book"),
            my_reserved_books=FilteredRelation(
                "my_books__reservation",
                condition=Q(my_books__reservation__state=Reservation.STOPPED),
            ),
            my_readers=FilteredRelation(
                "my_reserved_books__borrower",
                condition=Q(my_reserved_books__borrower=borrower),
            ),
        )
        self.assertSequenceEqual(
            qs.filter(my_readers=borrower).values_list("name", flat=True), ["Alice"]
        )

    def test_deep_nested_foreign_key(self):
        qs = (
            Book.objects.annotate(
                author_favorite_book_editor=FilteredRelation(
                    "author__favorite_books__editor",
                    condition=Q(author__favorite_books__title__icontains="Jane A"),
                ),
            )
            .filter(
                author_favorite_book_editor__isnull=False,
            )
            .select_related(
                "author_favorite_book_editor",
            )
            .order_by("pk", "author_favorite_book_editor__pk")
        )
        with self.assertNumQueries(1):
            self.assertQuerySetEqual(
                qs,
                [
                    (self.book1, self.editor_b),
                    (self.book4, self.editor_b),
                ],
                lambda x: (x, x.author_favorite_book_editor),
            )

    def test_relation_name_lookup(self):
        msg = (
            "FilteredRelation's relation_name cannot contain lookups (got "
            "'book__title__icontains')."
        )
        with self.assertRaisesMessage(ValueError, msg):
            Author.objects.annotate(
                book_title=FilteredRelation(
                    "book__title__icontains",
                    condition=Q(book__title="Poem by Alice"),
                ),
            )

    def test_condition_outside_relation_name(self):
        msg = (
            "FilteredRelation's condition doesn't support relations outside "
            "the 'book__editor' (got 'book__author__name__icontains')."
        )
        with self.assertRaisesMessage(ValueError, msg):
            Author.objects.annotate(
                book_editor=FilteredRelation(
                    "book__editor",
                    condition=Q(book__author__name__icontains="book"),
                ),
            )

    def test_condition_with_exact_lookup_outside_relation_name(self):
        qs = Author.objects.annotate(
            book_editor=FilteredRelation(
                "book__editor",
                condition=Q(book__author__name="book"),
            ),
        ).filter(book_editor__isnull=True)
        self.assertEqual(qs.count(), 4)

    def test_condition_with_func_and_lookup_outside_relation_name(self):
        qs = Author.objects.annotate(
            book_editor=FilteredRelation(
                "book__editor",
                condition=Q(
                    book__title=Concat(Value("The book by "), F("book__author__name"))
                ),
            ),
        ).filter(book_editor__isnull=False)
        self.assertEqual(qs.count(), 1)

    def test_condition_deeper_relation_name(self):
        msg = (
            "FilteredRelation's condition doesn't support nested relations "
            "deeper than the relation_name (got "
            "'book__editor__name__icontains' for 'book')."
        )
        with self.assertRaisesMessage(ValueError, msg):
            Author.objects.annotate(
                book_editor=FilteredRelation(
                    "book",
                    condition=Q(book__editor__name__icontains="b"),
                ),
            )

    def test_condition_deeper_relation_name_implicit_exact(self):
        msg = (
            "FilteredRelation's condition doesn't support nested relations "
            "deeper than the relation_name (got 'book__editor__name' for 'book')."
        )
        with self.assertRaisesMessage(ValueError, msg):
            Author.objects.annotate(
                book_editor=FilteredRelation(
                    "book",
                    condition=Q(book__editor__name="b"),
                ),
            )

    def test_with_empty_relation_name_error(self):
        with self.assertRaisesMessage(ValueError, "relation_name cannot be empty."):
            FilteredRelation("", condition=Q(blank=""))

    def test_with_condition_as_expression_error(self):
        msg = "condition argument must be a Q() instance."
        expression = Case(
            When(book__title__iexact="poem by alice", then=True),
            default=False,
        )
        with self.assertRaisesMessage(ValueError, msg):
            FilteredRelation("book", condition=expression)

    def test_with_prefetch_related(self):
        msg = "prefetch_related() is not supported with FilteredRelation."
        qs = Author.objects.annotate(
            book_title_contains_b=FilteredRelation(
                "book", condition=Q(book__title__icontains="b")
            ),
        ).filter(
            book_title_contains_b__isnull=False,
        )
        with self.assertRaisesMessage(ValueError, msg):
            qs.prefetch_related("book_title_contains_b")
        with self.assertRaisesMessage(ValueError, msg):
            qs.prefetch_related("book_title_contains_b__editor")

    def test_with_generic_foreign_key(self):
        self.assertSequenceEqual(
            Book.objects.annotate(
                generic_authored_book=FilteredRelation(
                    "generic_author", condition=Q(generic_author__isnull=False)
                ),
            ).filter(generic_authored_book__isnull=False),
            [self.book1],
        )

    def test_eq(self):
        self.assertEqual(
            FilteredRelation("book", condition=Q(book__title="b")), mock.ANY
        )

    def test_conditional_expression(self):
        qs = Author.objects.annotate(
            the_book=FilteredRelation("book", condition=Q(Value(False))),
        ).filter(the_book__isnull=False)
        self.assertSequenceEqual(qs, [])

    def test_expression_outside_relation_name(self):
        qs = Author.objects.annotate(
            book_editor=FilteredRelation(
                "book__editor",
                condition=Q(
                    Exact(F("book__author__name"), "Alice"),
                    Value(True),
                    book__title__startswith="Poem",
                ),
            ),
        ).filter(book_editor__isnull=False)
        self.assertSequenceEqual(qs, [self.author1])

    def test_conditional_expression_with_case(self):
        qs = Book.objects.annotate(
            alice_author=FilteredRelation(
                "author",
                condition=Q(
                    Case(When(author__name="Alice", then=True), default=False),
                ),
            ),
        ).filter(alice_author__isnull=False)
        self.assertCountEqual(qs, [self.book1, self.book4])

    def test_conditional_expression_outside_relation_name(self):
        tests = [
            Q(Case(When(book__author__name="Alice", then=True), default=False)),
            Q(
                ExpressionWrapper(
                    Q(Value(True), Exact(F("book__author__name"), "Alice")),
                    output_field=BooleanField(),
                ),
            ),
        ]
        for condition in tests:
            with self.subTest(condition=condition):
                qs = Author.objects.annotate(
                    book_editor=FilteredRelation("book__editor", condition=condition),
                ).filter(book_editor__isnull=True)
                self.assertSequenceEqual(qs, [self.author2, self.author2])

    def test_conditional_expression_with_lookup(self):
        lookups = [
            Q(book__title__istartswith="poem"),
            Q(IStartsWith(F("book__title"), "poem")),
        ]
        for condition in lookups:
            with self.subTest(condition=condition):
                qs = Author.objects.annotate(
                    poem_book=FilteredRelation("book", condition=condition)
                ).filter(poem_book__isnull=False)
                self.assertSequenceEqual(qs, [self.author1])

    def test_conditional_expression_with_expressionwrapper(self):
        qs = Author.objects.annotate(
            poem_book=FilteredRelation(
                "book",
                condition=Q(
                    ExpressionWrapper(
                        Q(Exact(F("book__title"), "Poem by Alice")),
                        output_field=BooleanField(),
                    ),
                ),
            ),
        ).filter(poem_book__isnull=False)
        self.assertSequenceEqual(qs, [self.author1])

    def test_conditional_expression_with_multiple_fields(self):
        qs = Author.objects.annotate(
            my_books=FilteredRelation(
                "book__author",
                condition=Q(Exact(F("book__author__name"), F("book__author__name"))),
            ),
        ).filter(my_books__isnull=True)
        self.assertSequenceEqual(qs, [])

    def test_conditional_expression_rhs_contains_relation_name(self):
        qs = Book.objects.annotate(
            rel=FilteredRelation(
                "editor",
                condition=Q(id=1 * F("number_editor")),
            )
        ).filter(rel__isnull=True)
        self.assertSequenceEqual(qs, [])

    def test_conditional_expression_rhs_startswith_relation_name(self):
        qs = Book.objects.annotate(
            rel=FilteredRelation(
                "editor",
                condition=Q(id=1 * F("editor_number")),
            )
        ).filter(rel__isnull=True)
        self.assertSequenceEqual(qs, [])

    def test_conditional_expression_lhs_startswith_relation_name(self):
        qs = Book.objects.annotate(
            rel=FilteredRelation(
                "editor",
                condition=Q(editor_number__gt=1),
            )
        ).filter(rel__isnull=True)
        self.assertSequenceEqual(qs, [])

    def test_conditional_expression_lhs_contains_relation_name(self):
        qs = Book.objects.annotate(
            rel=FilteredRelation(
                "editor",
                condition=Q(number_editor__gt=1),
            )
        ).filter(rel__isnull=True)
        self.assertSequenceEqual(qs, [])

    def test_conditional_expression_does_not_support_queryset(self):
        msg = "Passing a QuerySet within a FilteredRelation is not supported."
        with self.assertRaisesMessage(ValueError, msg):
            Author.objects.annotate(
                poem_book=FilteredRelation(
                    "book",
                    condition=Q(book__in=Book.objects.filter(title__istartswith="a")),
                ),
            ).filter(poem_book__isnull=False)


class FilteredRelationAggregationTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.author1 = Author.objects.create(name="Alice")
        cls.editor_a = Editor.objects.create(name="a")
        cls.book1 = Book.objects.create(
            title="Poem by Alice",
            editor=cls.editor_a,
            author=cls.author1,
        )
        cls.borrower1 = Borrower.objects.create(name="Jenny")
        cls.borrower2 = Borrower.objects.create(name="Kevin")
        # borrower 1 reserves, rents, and returns book1.
        Reservation.objects.create(
            borrower=cls.borrower1,
            book=cls.book1,
            state=Reservation.STOPPED,
        )
        RentalSession.objects.create(
            borrower=cls.borrower1,
            book=cls.book1,
            state=RentalSession.STOPPED,
        )
        # borrower2 reserves, rents, and returns book1.
        Reservation.objects.create(
            borrower=cls.borrower2,
            book=cls.book1,
            state=Reservation.STOPPED,
        )
        RentalSession.objects.create(
            borrower=cls.borrower2,
            book=cls.book1,
            state=RentalSession.STOPPED,
        )

    def test_aggregate(self):
        """
        filtered_relation() not only improves performance but also creates
        correct results when aggregating with multiple LEFT JOINs.

        Books can be reserved then rented by a borrower. Each reservation and
        rental session are recorded with Reservation and RentalSession models.
        Every time a reservation or a rental session is over, their state is
        changed to 'stopped'.

        Goal: Count number of books that are either currently reserved or
        rented by borrower1 or available.
        """
        qs = (
            Book.objects.annotate(
                is_reserved_or_rented_by=Case(
                    When(
                        reservation__state=Reservation.NEW,
                        then=F("reservation__borrower__pk"),
                    ),
                    When(
                        rental_session__state=RentalSession.NEW,
                        then=F("rental_session__borrower__pk"),
                    ),
                    default=None,
                )
            )
            .filter(
                Q(is_reserved_or_rented_by=self.borrower1.pk) | Q(state=Book.AVAILABLE)
            )
            .distinct()
        )
        self.assertEqual(qs.count(), 1)
        # If count is equal to 1, the same aggregation should return in the
        # same result but it returns 4.
        self.assertSequenceEqual(
            qs.annotate(total=Count("pk")).values("total"), [{"total": 4}]
        )
        # With FilteredRelation, the result is as expected (1).
        qs = (
            Book.objects.annotate(
                active_reservations=FilteredRelation(
                    "reservation",
                    condition=Q(
                        reservation__state=Reservation.NEW,
                        reservation__borrower=self.borrower1,
                    ),
                ),
            )
            .annotate(
                active_rental_sessions=FilteredRelation(
                    "rental_session",
                    condition=Q(
                        rental_session__state=RentalSession.NEW,
                        rental_session__borrower=self.borrower1,
                    ),
                ),
            )
            .filter(
                (
                    Q(active_reservations__isnull=False)
                    | Q(active_rental_sessions__isnull=False)
                )
                | Q(state=Book.AVAILABLE)
            )
            .distinct()
        )
        self.assertEqual(qs.count(), 1)
        self.assertSequenceEqual(
            qs.annotate(total=Count("pk")).values("total"), [{"total": 1}]
        )

    def test_condition_spans_join(self):
        self.assertSequenceEqual(
            Book.objects.annotate(
                contains_editor_author=FilteredRelation(
                    "author", condition=Q(author__name__icontains=F("editor__name"))
                )
            ).filter(
                contains_editor_author__isnull=False,
            ),
            [self.book1],
        )

    def test_condition_spans_join_chained(self):
        self.assertSequenceEqual(
            Book.objects.annotate(
                contains_editor_author=FilteredRelation(
                    "author", condition=Q(author__name__icontains=F("editor__name"))
                ),
                contains_editor_author_ref=FilteredRelation(
                    "author",
                    condition=Q(author__name=F("contains_editor_author__name")),
                ),
            ).filter(
                contains_editor_author_ref__isnull=False,
            ),
            [self.book1],
        )

    def test_condition_self_ref(self):
        self.assertSequenceEqual(
            Book.objects.annotate(
                contains_author=FilteredRelation(
                    "author",
                    condition=Q(title__icontains=F("author__name")),
                )
            ).filter(
                contains_author__isnull=False,
            ),
            [self.book1],
        )


class FilteredRelationAnalyticalAggregationTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        author = Author.objects.create(name="Author")
        editor = Editor.objects.create(name="Editor")
        cls.book1 = Book.objects.create(
            title="Poem by Alice",
            editor=editor,
            author=author,
        )
        cls.book2 = Book.objects.create(
            title="The book by Jane A",
            editor=editor,
            author=author,
        )
        cls.book3 = Book.objects.create(
            title="The book by Jane B",
            editor=editor,
            author=author,
        )
        cls.seller1 = Seller.objects.create(name="Seller 1")
        cls.seller2 = Seller.objects.create(name="Seller 2")
        cls.usd = Currency.objects.create(currency="USD")
        cls.eur = Currency.objects.create(currency="EUR")
        cls.sales_date1 = date(2020, 7, 6)
        cls.sales_date2 = date(2020, 7, 7)
        ExchangeRate.objects.bulk_create(
            [
                ExchangeRate(
                    rate_date=cls.sales_date1,
                    from_currency=cls.usd,
                    to_currency=cls.eur,
                    rate=0.40,
                ),
                ExchangeRate(
                    rate_date=cls.sales_date1,
                    from_currency=cls.eur,
                    to_currency=cls.usd,
                    rate=1.60,
                ),
                ExchangeRate(
                    rate_date=cls.sales_date2,
                    from_currency=cls.usd,
                    to_currency=cls.eur,
                    rate=0.50,
                ),
                ExchangeRate(
                    rate_date=cls.sales_date2,
                    from_currency=cls.eur,
                    to_currency=cls.usd,
                    rate=1.50,
                ),
                ExchangeRate(
                    rate_date=cls.sales_date2,
                    from_currency=cls.usd,
                    to_currency=cls.usd,
                    rate=1.00,
                ),
            ]
        )
        BookDailySales.objects.bulk_create(
            [
                BookDailySales(
                    book=cls.book1,
                    sale_date=cls.sales_date1,
                    currency=cls.usd,
                    sales=100.00,
                    seller=cls.seller1,
                ),
                BookDailySales(
                    book=cls.book2,
                    sale_date=cls.sales_date1,
                    currency=cls.eur,
                    sales=200.00,
                    seller=cls.seller1,
                ),
                BookDailySales(
                    book=cls.book1,
                    sale_date=cls.sales_date2,
                    currency=cls.usd,
                    sales=50.00,
                    seller=cls.seller2,
                ),
                BookDailySales(
                    book=cls.book2,
                    sale_date=cls.sales_date2,
                    currency=cls.eur,
                    sales=100.00,
                    seller=cls.seller2,
                ),
            ]
        )

    def test_aggregate(self):
        tests = [
            Q(daily_sales__sale_date__gte=self.sales_date2),
            ~Q(daily_sales__seller=self.seller1),
        ]
        for condition in tests:
            with self.subTest(condition=condition):
                qs = (
                    Book.objects.annotate(
                        recent_sales=FilteredRelation(
                            "daily_sales", condition=condition
                        ),
                        recent_sales_rates=FilteredRelation(
                            "recent_sales__currency__rates_from",
                            condition=Q(
                                recent_sales__currency__rates_from__rate_date=F(
                                    "recent_sales__sale_date"
                                ),
                                recent_sales__currency__rates_from__to_currency=(
                                    self.usd
                                ),
                            ),
                        ),
                    )
                    .annotate(
                        sales_sum=Sum(
                            F("recent_sales__sales") * F("recent_sales_rates__rate"),
                            output_field=DecimalField(),
                        ),
                    )
                    .values("title", "sales_sum")
                    .order_by(
                        F("sales_sum").desc(nulls_last=True),
                    )
                )
                self.assertSequenceEqual(
                    qs,
                    [
                        {"title": self.book2.title, "sales_sum": Decimal(150.00)},
                        {"title": self.book1.title, "sales_sum": Decimal(50.00)},
                        {"title": self.book3.title, "sales_sum": None},
                    ],
                )
