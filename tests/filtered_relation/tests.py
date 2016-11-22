import unittest

from django.core.exceptions import FieldError
from django.db import connection
from django.db.models import Q
from django.test import TestCase

from .models import Author, Book, Editor


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

    def test_filtered_relation_wo_join(self):
        self.assertQuerysetEqual(
            Author.objects
            .filtered_relation(
                'book', alias='book_alice',
                condition=Q(book__title__iexact='poem by alice')),
            ["<Author: Alice>", "<Author: Jane>"])

    def test_filered_relation_with_join(self):
        self.assertQuerysetEqual(
            Author.objects
            .filtered_relation(
                'book', alias='book_alice',
                condition=Q(book__title__iexact='poem by alice'))
            .filter(book_alice__isnull=False),
            ["<Author: Alice>"])

    @unittest.skipUnless(connection.vendor != 'mysql', 'Non MySQL specific test.')
    def test_filtered_relation_alias_mapping_other(self):
        queryset = (Author.objects
                    .filtered_relation(
                        'book', alias='book_alice',
                        condition=Q(book__title__iexact='poem by alice'))
                    .filter(book_alice__isnull=False))
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
            Author.objects
            .filtered_relation('book', alias='book_editor_a',
                               condition=Q(book__title__icontains='book',
                                           book__editor_id=self.editor_a.pk))
            .filter(book_editor_a__isnull=False),
            ["<Author: Alice>"])

    def test_filtered_relation_multiple_times(self):
        self.assertQuerysetEqual(
            Author.objects
            .filtered_relation('book', alias='book_title_alice',
                               condition=Q(book__title__icontains='alice'))
            .filter(book_title_alice__isnull=False)
            .filter(book_title_alice__isnull=False)
            .distinct(),
            ["<Author: Alice>"])

    def test_exclude_relation_with_join(self):
        self.assertQuerysetEqual(
            Author.objects
            .filtered_relation(
                'book', alias='book_alice',
                condition=~Q(book__title__icontains='alice'))
            .filter(book_alice__isnull=False)
            .distinct(),
            ["<Author: Jane>"])

    def test_filtered_relation_with_m2m(self):
        self.assertQuerysetEqual(
            Author.objects
            .filtered_relation('favourite_books', alias='favourite_books_written_by_jane',
                               condition=Q(favourite_books__in=[self.book2]))
            .filter(favourite_books_written_by_jane__isnull=False),
            ["<Author: Alice>"])

    def test_filtered_relation_with_foreign_key_error(self):
        with self.assertRaises(FieldError):
            list(Book.objects.filtered_relation('author__favourite_books',
                                                alias='alice_favourite_books',
                                                condition=Q(author__favourite_books__author=self.author1))
                 .filter(alice_favourite_books__title__icontains='poem'))

    def test_filtered_relation_with_foreign_key_on_condition_error(self):
        with self.assertRaises(FieldError):
            list(Author.objects
                 .filtered_relation(
                     'book',
                     alias='book_edited_by_b',
                     condition=Q(book__editor__name__icontains='b'))
                 .filter(book_edited_by_b__isnull=False))

    def test_filtered_relation_with_empty_relation_name_error(self):
        with self.assertRaises(FieldError):
            Book.objects.filtered_relation('', alias='blank', condition=Q(blank=''))

    def test_filtered_relation_with_empty_alias_error(self):
        with self.assertRaises(FieldError):
            Book.objects.filtered_relation('favourite_books', alias='', condition=Q(blank=''))
