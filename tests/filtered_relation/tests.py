import unittest

from django.db import connection
from django.db.models import Case, Count, F, Q, When
from django.test import TestCase

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
            author=cls.author1)

        cls.book2 = Book.objects.create(
            title='The book by Jane A',
            editor=cls.editor_b,
            author=cls.author2)

        cls.book3 = Book.objects.create(
            title='The book by Jane B',
            editor=cls.editor_b,
            author=cls.author2)

        cls.book4 = Book.objects.create(
            title='The book by Alice',
            editor=cls.editor_a,
            author=cls.author1)
        cls.author1.favourite_books.add(cls.book2)
        cls.author1.favourite_books.add(cls.book3)

    def test_filtered_relation_select_related(self):
        qs = Author.objects.filtered_relation(
            'book', 'book_join', condition=Q()
        ).select_related(
            'book_join__editor',
        ).order_by('pk', 'book_join__pk')
        with self.assertNumQueries(1):
            expected = [
                (self.author1, self.book1, self.editor_a, self.author1),
                (self.author1, self.book4, self.editor_a, self.author1),
                (self.author2, self.book2, self.editor_b, self.author2),
                (self.author2, self.book3, self.editor_b, self.author2)
            ]
            self.assertQuerysetEqual(
                qs, expected, lambda x: (x, x.book_join, x.book_join.editor, x.book_join.author)
            )

    def test_filtered_relation_select_related_foreign_key(self):
        # this doesn't make much sense, but let's have it anyways...
        qs = Book.objects.filtered_relation(
            'author', 'author_join', condition=Q()
        ).select_related(
            'author_join'
        ).order_by('pk')
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
        self.assertQuerysetEqual(
            Author.objects.filtered_relation(
                'book', alias='book_alice',
                condition=Q(book__title__iexact='poem by alice')),
            ["<Author: Alice>", "<Author: Jane>"])

    def test_filered_relation_with_join(self):
        self.assertQuerysetEqual(
            Author.objects.filtered_relation(
                'book', alias='book_alice',
                condition=Q(book__title__iexact='poem by alice')
            ).filter(book_alice__isnull=False),
            ["<Author: Alice>"])

    @unittest.skipUnless(connection.vendor != 'mysql', 'Non MySQL specific test.')
    def test_filtered_relation_alias_mapping_other(self):
        queryset = Author.objects.filtered_relation(
            'book', alias='book_alice',
            condition=Q(book__title__iexact='poem by alice')
        ).filter(book_alice__isnull=False)
        self.assertIn('INNER JOIN "filtered_relation_book" book_alice ON', str(queryset.query))

    @unittest.skipUnless(connection.vendor == 'mysql', 'MySQL specific test.')
    def test_filtered_relation_alias_mapping_mysql(self):
        queryset = (Author.objects
                    .filtered_relation(
                        'book', alias='book_alice',
                        condition=Q(book__title__iexact='poem by alice'))
                    .filter(book_alice__isnull=False))
        self.assertIn('INNER JOIN `filtered_relation_book` book_alice ON', str(queryset.query))

    def test_filtered_relation_with_multiple_filter(self):
        self.assertQuerysetEqual(
            Author.objects.filtered_relation('book', alias='book_editor_a',
                                             condition=Q(book__title__icontains='book',
                                                         book__editor_id=self.editor_a.pk)
                                             ).filter(book_editor_a__isnull=False),
            ["<Author: Alice>"])

    def test_filtered_relation_multiple_times(self):
        self.assertQuerysetEqual(
            Author.objects.filtered_relation('book', alias='book_title_alice',
                                             condition=Q(book__title__icontains='alice')
                                             ).filter(book_title_alice__isnull=False).filter(
                                                 book_title_alice__isnull=False).distinct(),
            ["<Author: Alice>"])

    def test_exclude_relation_with_join(self):
        self.assertQuerysetEqual(
            Author.objects.filtered_relation(
                'book', alias='book_alice',
                condition=~Q(book__title__icontains='alice')
            ).filter(book_alice__isnull=False).distinct(),
            ["<Author: Jane>"])

    def test_filtered_relation_with_m2m(self):
        qs = Author.objects.filtered_relation(
            'favourite_books', alias='favourite_books_written_by_jane',
            condition=Q(favourite_books__in=[self.book2])).filter(favourite_books_written_by_jane__isnull=False)
        self.assertQuerysetEqual(qs, ["<Author: Alice>"])

    def test_filtered_relation_with_m2m_deep(self):
        qs = Author.objects.filtered_relation(
            'favourite_books', alias='favourite_books_written_by_jane',
            condition=Q(favourite_books__author=self.author2)
        ).filter(favourite_books_written_by_jane__title='The book by Jane B')
        self.assertQuerysetEqual(qs, ["<Author: Alice>"])

    def test_filtered_relation_with_m2m_multijoin(self):
        qs = Author.objects.filtered_relation(
            'favourite_books', alias='favourite_books_written_by_jane',
            condition=Q(favourite_books__author=self.author2)
        ).filter(favourite_books_written_by_jane__editor__name='b').distinct()
        self.assertQuerysetEqual(qs, ["<Author: Alice>"])

    def test_filtered_relation_values_list(self):
        self.assertQuerysetEqual(Author.objects.filtered_relation(
            'book', alias='book_alice',
            condition=Q(book__title__iexact='poem by alice')
        ).values_list('book_alice__title', flat=True).order_by('-book_alice__title'),
            ["Poem by Alice", None], lambda x: x)

    def test_filtered_relation_values(self):
        self.assertQuerysetEqual(Author.objects.filtered_relation(
            'book', alias='book_alice',
            condition=Q(book__title__iexact='poem by alice')
        ).values().order_by('-book_alice__id'),
            [{'id': 1, 'name': 'Alice'},
             {'id': 2, 'name': 'Jane'}],
            lambda x: x)

    def test_filtered_relation_extra(self):
        self.assertQuerysetEqual(Author.objects.filtered_relation(
            'book', alias='book_alice',
            condition=Q(book__title__iexact='poem by alice')
        ).extra(where=["1 = 1"]).order_by('-book_alice__id'),
            ["<Author: Alice>", "<Author: Jane>"])

    @skipUnlessDBFeature('supports_select_union')
    def test_filtered_relation_union(self):
        qs1 = Author.objects.filtered_relation(
            'book', alias='book_alice',
            condition=Q(book__title__iexact='poem by alice')
        ).filter(book_alice__isnull=False).order_by()
        qs2 = Author.objects.filtered_relation(
            'book', alias='book_jane',
            condition=Q(book__title__iexact='the book by jane a')
        ).filter(book_jane__isnull=False).order_by()
        self.assertQuerysetEqual(qs1.union(qs2).order_by('id'), ["<Author: Alice>", "<Author: Jane>"])

    @skipUnlessDBFeature('supports_select_intersection')
    def test_filtered_relation_intersection(self):
        qs1 = Author.objects.filtered_relation(
            'book', alias='book_alice',
            condition=Q(book__title__iexact='poem by alice')
        ).filter(book_alice__isnull=False).order_by()
        qs2 = Author.objects.filtered_relation(
            'book', alias='book_jane',
            condition=Q(book__title__iexact='the book by jane a')
        ).filter(book_jane__isnull=False).order_by()
        self.assertQuerysetEqual(qs1.intersection(qs2).order_by('id'), [])

    def test_filtered_relation_difference(self):
        qs1 = Author.objects.filtered_relation(
            'book', alias='book_alice',
            condition=Q(book__title__iexact='poem by alice')
        ).filter(book_alice__isnull=False).order_by()
        qs2 = Author.objects.filtered_relation(
            'book', alias='book_jane',
            condition=Q(book__title__iexact='the book by jane a')
        ).filter(book_jane__isnull=False).order_by()
        self.assertQuerysetEqual(qs1.difference(qs2).order_by('id'), ["<Author: Alice>"])

    def test_filtered_relation_defer(self):
        # One query for the list, and one query to fetch the
        # deferred title.
        with self.assertNumQueries(2):
            self.assertQuerysetEqual(Author.objects.filtered_relation(
                'book', alias='book_alice',
                condition=Q(book__title__iexact='poem by alice')
            ).select_related('book_alice').defer('book_alice__title').order_by('-book_alice__title'),
                ["Poem by Alice", None], lambda author: getattr(author.book_alice, 'title', None))

    def test_filtered_relation_only(self):
        # One query for the list, and one query to fetch the
        # deffered state.
        with self.assertNumQueries(2):
            self.assertQuerysetEqual(Author.objects.filtered_relation(
                'book', alias='book_alice',
                condition=Q(book__title__iexact='poem by alice')
            ).select_related('book_alice').only('book_alice__title').order_by('-book_alice__title'),
                ["available", None], lambda author: getattr(author.book_alice, 'state', None))

    def test_filtered_relation_as_subquery(self):
        inner_qs = Author.objects.filtered_relation('book', alias='book_alice',
                                                    condition=Q(book__title__iexact='poem by alice')
                                                    ).filter(book_alice__isnull=False)
        qs = Author.objects.filter(id__in=inner_qs)
        self.assertQuerysetEqual(qs, ["<Author: Alice>"])

    def test_filtered_relation_with_foreign_key_error(self):
        with self.assertRaisesMessage(ValueError, "Filtered relation 'alice_favourite_books'"
                                      " cannot operate on foreign key 'author__favourite_books__author'."):
            list(Book.objects.filtered_relation('author__favourite_books',
                                                alias='alice_favourite_books',
                                                condition=Q(author__favourite_books__author=self.author1)
                                                ).filter(alice_favourite_books__title__icontains='poem'))

    def test_filtered_relation_with_foreign_key_on_condition_error(self):
        with self.assertRaisesMessage(ValueError, "Filtered relation 'book_edited_by_b'"
                                      " cannot operate on foreign key 'book__editor__name__icontains'."):
            list(Author.objects.filtered_relation(
                'book',
                alias='book_edited_by_b',
                condition=Q(book__editor__name__icontains='b')
            ).filter(book_edited_by_b__isnull=False))

    def test_filtered_relation_with_empty_relation_name_error(self):
        with self.assertRaisesMessage(ValueError, 'relation_name cannot be empty'):
            Book.objects.filtered_relation('', alias='blank', condition=Q(blank=''))

    def test_filtered_relation_with_empty_alias_error(self):
        with self.assertRaisesMessage(ValueError, 'alias cannot be empty'):
            Book.objects.filtered_relation('favourite_books', alias='', condition=Q(blank=''))


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
        Test case that shows how filtered_relation not only improves performance,
        but also ensure correctness of results when aggregation and multiple LEFT JOIN are involved.

        Use Case:

            Books can be reserved then rented by a borrower.
            Each reservation and rental_session are recorded with Reservation and RentalSession models.
            Every time a reservation or a rental session is over, their state change to 'stopped'.

        Goal: Count number of books that are either currently reserved or rented by borrower1 or available.
        """
        qs = Book.objects.annotate(
            is_reserved_or_rented_by=Case(
                When(reservation__state=Reservation.NEW, then=F('reservation__borrower__pk')),
                When(rental_session__state=RentalSession.NEW, then=F('rental_session__borrower__pk')),
                default=None)
        ).filter(Q(is_reserved_or_rented_by=self.borrower1.pk) | Q(state=Book.AVAILABLE)
                 ).distinct().order_by()  # disable implicit grouping
        self.assertEqual(qs.count(), 1)
        # If count is equal to 1 we expect also the same aggregation to return the same result
        # but it fails by returning 4.
        self.assertQuerysetEqual(qs.annotate(total=Count('pk')).values('total'), ["{'total': 4}"])

        qs = Book.objects.filtered_relation(
            'reservation',
            alias='active_reservations',
            condition=Q(reservation__state=Reservation.NEW, reservation__borrower=self.borrower1)
        ).filtered_relation('rental_session',
                            alias='active_rental_sessions',
                            condition=Q(rental_session__state=RentalSession.NEW,
                                        rental_session__borrower=self.borrower1)
                            ).filter(
                                (Q(active_reservations__isnull=False) |
                                 Q(active_rental_sessions__isnull=False)) |
                                Q(state=Book.AVAILABLE)).distinct().order_by()  # disable implicit grouping
        self.assertEqual(qs.count(), 1)
        # Thanks to filtered_relation the aggregation is now correct
        self.assertQuerysetEqual(qs.annotate(total=Count('pk')).values('total'), ["{'total': 1}"])
