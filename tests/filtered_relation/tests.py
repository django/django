from django.db import connection
from django.db.models import Case, Count, F, FilteredRelation, Q, When
from django.test import TestCase
from django.test.testcases import skipUnlessDBFeature

from .models import Author, Book, Borrower, Editor, RentalSession, Reservation


class FilteredRelationTests(TestCase):

    @classmethod
    def setUpTestData(cls):
        cls.author1 = Author.objects.create(name='Alice')
        cls.author2 = Author.objects.create(name='Jane')

        cls.editor_a = Editor.objects.create(name='a')
        cls.editor_b = Editor.objects.create(name='b')

        cls.book1 = Book.objects.create(
            title='Poem by Alice',
            editor=cls.editor_a,
            author=cls.author1,
        )

        cls.book2 = Book.objects.create(
            title='The book by Jane A',
            editor=cls.editor_b,
            author=cls.author2,
        )

        cls.book3 = Book.objects.create(
            title='The book by Jane B',
            editor=cls.editor_b,
            author=cls.author2,
        )

        cls.book4 = Book.objects.create(
            title='The book by Alice',
            editor=cls.editor_a,
            author=cls.author1,
        )
        cls.author1.favourite_books.add(cls.book2)
        cls.author1.favourite_books.add(cls.book3)

    def test_filtered_relation_select_related(self):
        qs = Author.objects.annotate(
            book_join=FilteredRelation('book', condition=Q())
        ).select_related('book_join__editor').order_by('pk', 'book_join__pk')
        with self.assertNumQueries(1):
            expected = [
                (self.author1, self.book1, self.editor_a, self.author1),
                (self.author1, self.book4, self.editor_a, self.author1),
                (self.author2, self.book2, self.editor_b, self.author2),
                (self.author2, self.book3, self.editor_b, self.author2),
            ]
            self.assertQuerysetEqual(
                qs, expected, lambda x: (x, x.book_join, x.book_join.editor, x.book_join.author)
            )

    def test_filtered_relation_select_related_foreign_key(self):
        # this doesn't make much sense, but let's have it anyways...
        qs = Book.objects.annotate(
            author_join=FilteredRelation('author', condition=Q())
        ).select_related('author_join').order_by('pk')
        with self.assertNumQueries(1):
            expected = [
                (self.book1, self.author1),
                (self.book2, self.author2),
                (self.book3, self.author2),
                (self.book4, self.author1),
            ]
            self.assertQuerysetEqual(
                qs, expected, lambda x: (x, x.author_join)
            )

    def test_filtered_relation_wo_join(self):
        self.assertSequenceEqual(
            Author.objects.annotate(
                book_alice=FilteredRelation(
                    'book', condition=Q(book__title__iexact='poem by alice'),
                )), [self.author1, self.author2])

    def test_filered_relation_with_join(self):
        self.assertQuerysetEqual(
            Author.objects.annotate(
                book_alice=FilteredRelation(
                    'book', condition=Q(book__title__iexact='poem by alice'),
                )).filter(book_alice__isnull=False), ["<Author: Alice>"])

    def test_filtered_relation_alias_mapping_other(self):
        queryset = Author.objects.annotate(
            book_alice=FilteredRelation(
                'book', condition=Q(book__title__iexact='poem by alice'),
            )).filter(book_alice__isnull=False)
        self.assertIn(
            'INNER JOIN {} book_alice ON'.format(
                connection.ops.quote_name('filtered_relation_book'),
            ),
            str(queryset.query))

    def test_filtered_relation_with_multiple_filter(self):
        self.assertQuerysetEqual(
            Author.objects.annotate(
                book_editor_a=FilteredRelation(
                    'book', condition=Q(book__title__icontains='book',
                                        book__editor_id=self.editor_a.pk),
                )).filter(book_editor_a__isnull=False), ["<Author: Alice>"])

    def test_filtered_relation_multiple_times(self):
        self.assertQuerysetEqual(
            Author.objects.annotate(
                book_title_alice=FilteredRelation(
                    'book', condition=Q(book__title__icontains='alice'),
                )).filter(book_title_alice__isnull=False).filter(book_title_alice__isnull=False).distinct(),
            ["<Author: Alice>"])

    def test_exclude_relation_with_join(self):
        self.assertQuerysetEqual(
            Author.objects.annotate(
                book_alice=FilteredRelation(
                    'book', condition=~Q(book__title__icontains='alice'),
                )).filter(book_alice__isnull=False).distinct(),
            ["<Author: Jane>"])

    def test_filtered_relation_with_m2m(self):
        qs = Author.objects.annotate(
            favourite_books_written_by_jane=FilteredRelation(
                'favourite_books', condition=Q(favourite_books__in=[self.book2]),
            )).filter(favourite_books_written_by_jane__isnull=False)
        self.assertQuerysetEqual(qs, ["<Author: Alice>"])

    def test_filtered_relation_with_m2m_deep(self):
        qs = Author.objects.annotate(
            favourite_books_written_by_jane=FilteredRelation(
                'favourite_books', condition=Q(favourite_books__author=self.author2),
            )).filter(favourite_books_written_by_jane__title='The book by Jane B')
        self.assertQuerysetEqual(qs, ["<Author: Alice>"])

    def test_filtered_relation_with_m2m_multijoin(self):
        qs = Author.objects.annotate(
            favourite_books_written_by_jane=FilteredRelation(
                'favourite_books', condition=Q(favourite_books__author=self.author2),
            )).filter(favourite_books_written_by_jane__editor__name='b').distinct()
        self.assertQuerysetEqual(qs, ["<Author: Alice>"])

    def test_filtered_relation_values_list(self):
        self.assertSequenceEqual(
            Author.objects.annotate(
                book_alice=FilteredRelation(
                    'book', condition=Q(book__title__iexact='poem by alice'),
                )).filter(book_alice__isnull=False).values_list(
                    'book_alice__title', flat=True),
            ["Poem by Alice"])

    def test_filtered_relation_values(self):
        self.assertSequenceEqual(Author.objects.annotate(
            book_alice=FilteredRelation(
                'book', condition=Q(book__title__iexact='poem by alice'),
            )).filter(book_alice__isnull=False).values(),
            [{'id': 1, 'name': 'Alice'}])

    def test_filtered_relation_extra(self):
        self.assertSequenceEqual(Author.objects.annotate(
            book_alice=FilteredRelation(
                'book', condition=Q(book__title__iexact='poem by alice'),
            )).filter(book_alice__isnull=False).extra(
                where=["1 = 1"]),
            [self.author1])

    @skipUnlessDBFeature('supports_select_union')
    def test_filtered_relation_union(self):
        qs1 = Author.objects.annotate(
            book_alice=FilteredRelation(
                'book', condition=Q(book__title__iexact='poem by alice'),
            )).filter(book_alice__isnull=False)
        qs2 = Author.objects.annotate(
            book_jane=FilteredRelation(
                'book', condition=Q(book__title__iexact='the book by jane a'),
            )).filter(book_jane__isnull=False)
        self.assertSequenceEqual(qs1.union(qs2), [self.author1, self.author2])

    @skipUnlessDBFeature('supports_select_intersection')
    def test_filtered_relation_intersection(self):
        qs1 = Author.objects.annotate(
            book_alice=FilteredRelation(
                'book', condition=Q(book__title__iexact='poem by alice'),
            )).filter(book_alice__isnull=False)
        qs2 = Author.objects.annotate(
            book_jane=FilteredRelation(
                'book', condition=Q(book__title__iexact='the book by jane a'),
            )).filter(book_jane__isnull=False)
        self.assertQuerysetEqual(qs1.intersection(qs2), [])

    @skipUnlessDBFeature('supports_select_difference')
    def test_filtered_relation_difference(self):
        qs1 = Author.objects.annotate(
            book_alice=FilteredRelation(
                'book', condition=Q(book__title__iexact='poem by alice'),
            )).filter(book_alice__isnull=False)
        qs2 = Author.objects.annotate(
            book_jane=FilteredRelation(
                'book', condition=Q(book__title__iexact='the book by jane a'),
            )).filter(book_jane__isnull=False)
        self.assertSequenceEqual(qs1.difference(qs2), [self.author1])

    def test_filtered_relation_select_for_update(self):
        self.assertQuerysetEqual(Author.objects.annotate(
            book_jane=FilteredRelation(
                'book', condition=Q(book__title__iexact='the book by jane a'),
            )).filter(book_jane__isnull=False).select_for_update(),
            ['<Author: Jane>'])

    def test_filtered_relation_defer(self):
        # One query for the list, and one query to fetch the
        # deferred title.
        with self.assertNumQueries(2):
            self.assertQuerysetEqual(Author.objects.annotate(
                book_alice=FilteredRelation(
                    'book', condition=Q(book__title__iexact='poem by alice'),
                )).filter(book_alice__isnull=False).select_related(
                    'book_alice').defer('book_alice__title'),
                ["Poem by Alice"], lambda author: author.book_alice.title)

    def test_filtered_relation_only_not_supported(self):
        msg = "only() is not supported with filtered relation 'book_alice'"
        with self.assertRaisesMessage(ValueError, msg):
            Author.objects.annotate(
                book_alice=FilteredRelation(
                    'book', condition=Q(book__title__iexact='poem by alice'),
                )).filter(book_alice__isnull=False).select_related('book_alice').only(
                    'book_alice__state')

    def test_filtered_relation_as_subquery(self):
        inner_qs = Author.objects.annotate(
            book_alice=FilteredRelation(
                'book', condition=Q(book__title__iexact='poem by alice'),
            )).filter(book_alice__isnull=False)
        qs = Author.objects.filter(id__in=inner_qs)
        self.assertQuerysetEqual(qs, ["<Author: Alice>"])

    def test_filtered_relation_with_foreign_key_error(self):
        msg = ("Filtered relation 'alice_favourite_books' cannot operate on foreign key"
               " 'author__favourite_books__author'.")
        with self.assertRaisesMessage(ValueError, msg):
            list(
                Book.objects.annotate(
                    alice_favourite_books=FilteredRelation(
                        'author__favourite_books',
                        condition=Q(author__favourite_books__author=self.author1),
                    )).filter(alice_favourite_books__title__icontains='poem')
            )

    def test_filtered_relation_with_foreign_key_on_condition_error(self):
        msg = ("Filtered relation 'book_edited_by_b' cannot operate on foreign key"
               " 'book__editor__name__icontains'.")
        with self.assertRaisesMessage(ValueError, msg):
            list(
                Author.objects.annotate(
                    book_edited_by_b=FilteredRelation(
                        'book', condition=Q(book__editor__name__icontains='b'),
                    )).filter(book_edited_by_b__isnull=False)
            )

    def test_filtered_relation_with_empty_relation_name_error(self):
        with self.assertRaisesMessage(ValueError, 'relation_name cannot be empty'):
            FilteredRelation('', condition=Q(blank=''))

    def test_filtered_relation_with_prefetch_related(self):
        msg = ("prefetch_related() is not supported with filtered relation 'book_title_contains_b'")
        with self.assertRaisesMessage(ValueError, msg):
            Author.objects.annotate(
                book_title_contains_b=FilteredRelation(
                    'book',
                    condition=Q(book__title__icontains='b'),
                )).filter(
                    book_title_contains_b__isnull=False
            ).prefetch_related('book_title_contains_b')
        with self.assertRaisesMessage(ValueError, msg):
            Author.objects.annotate(
                book_title_contains_b=FilteredRelation(
                    'book',
                    condition=Q(book__title__icontains='b'),
                )).filter(
                    book_title_contains_b__isnull=False
            ).prefetch_related('book_title_contains_b__editor')


class FilteredRelationWithAggregationTests(TestCase):

    @classmethod
    def setUpTestData(cls):
        cls.author1 = Author.objects.create(name='Alice')
        cls.editor_a = Editor.objects.create(name='a')
        cls.book1 = Book.objects.create(
            title='Poem by Alice',
            editor=cls.editor_a,
            author=cls.author1,
        )
        cls.borrower1 = Borrower.objects.create(name='Jenny')
        cls.borrower2 = Borrower.objects.create(name='Kevin')
        # borrower 1 reserve, rent and return book1
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
        # borrower2 reserve, rent and return book1
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

    def test_filtered_relation_enforce_aggregation_correctness(self):
        """
        Test case that shows how filtered_relation not only improves
        performance, but also ensure correctness of results when aggregation
        and multiple LEFT JOIN are involved.

        Use Case:

            Books can be reserved then rented by a borrower.
            Each reservation and rental_session are recorded with
            Reservation and RentalSession models.
            Every time a reservation or a rental session is over,
            their state change to 'stopped'.

        Goal: Count number of books that are either currently reserved or
              rented by borrower1 or available.
        """
        qs = Book.objects.annotate(
            is_reserved_or_rented_by=Case(
                When(reservation__state=Reservation.NEW, then=F('reservation__borrower__pk')),
                When(rental_session__state=RentalSession.NEW, then=F('rental_session__borrower__pk')),
                default=None)
        ).filter(
            Q(is_reserved_or_rented_by=self.borrower1.pk) | Q(state=Book.AVAILABLE)
        ).distinct().order_by()  # disable implicit grouping
        self.assertEqual(qs.count(), 1)
        # If count is equal to 1 we expect also the same aggregation to return the same result
        # but it fails by returning 4.
        self.assertQuerysetEqual(qs.annotate(total=Count('pk')).values('total'), ["{'total': 4}"])

        qs = Book.objects.annotate(
            active_reservations=FilteredRelation(
                'reservation', condition=Q(reservation__state=Reservation.NEW,
                                           reservation__borrower=self.borrower1),
            )).annotate(
                active_rental_sessions=FilteredRelation(
                    'rental_session', condition=Q(rental_session__state=RentalSession.NEW,
                                                  rental_session__borrower=self.borrower1),
                )).filter((Q(active_reservations__isnull=False) |
                           Q(active_rental_sessions__isnull=False)) |
                          Q(state=Book.AVAILABLE)).distinct().order_by()  # disable implicit grouping
        self.assertEqual(qs.count(), 1)
        # Thanks to FilteredRelation the aggregation is now correct
        self.assertQuerysetEqual(qs.annotate(total=Count('pk')).values('total'), ["{'total': 1}"])
