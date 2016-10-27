from django.db.models import Prefetch, prefetch_related_objects
from django.test import TestCase

from .models import Author, Book, Reader


class PrefetchRelatedObjectsTests(TestCase):
    """
    Since prefetch_related_objects() is just the inner part of
    prefetch_related(), only do basic tests to ensure its API hasn't changed.
    """
    @classmethod
    def setUpTestData(cls):
        cls.book1 = Book.objects.create(title='Poems')
        cls.book2 = Book.objects.create(title='Jane Eyre')
        cls.book3 = Book.objects.create(title='Wuthering Heights')
        cls.book4 = Book.objects.create(title='Sense and Sensibility')

        cls.author1 = Author.objects.create(name='Charlotte', first_book=cls.book1)
        cls.author2 = Author.objects.create(name='Anne', first_book=cls.book1)
        cls.author3 = Author.objects.create(name='Emily', first_book=cls.book1)
        cls.author4 = Author.objects.create(name='Jane', first_book=cls.book4)

        cls.book1.authors.add(cls.author1, cls.author2, cls.author3)
        cls.book2.authors.add(cls.author1)
        cls.book3.authors.add(cls.author3)
        cls.book4.authors.add(cls.author4)

        cls.reader1 = Reader.objects.create(name='Amy')
        cls.reader2 = Reader.objects.create(name='Belinda')

        cls.reader1.books_read.add(cls.book1, cls.book4)
        cls.reader2.books_read.add(cls.book2, cls.book4)

    def test_unknown(self):
        book1 = Book.objects.get(id=self.book1.id)
        with self.assertRaises(AttributeError):
            prefetch_related_objects([book1], 'unknown_attribute')

    def test_m2m_forward(self):
        book1 = Book.objects.get(id=self.book1.id)
        with self.assertNumQueries(1):
            prefetch_related_objects([book1], 'authors')

        with self.assertNumQueries(0):
            self.assertEqual(set(book1.authors.all()), {self.author1, self.author2, self.author3})

    def test_m2m_reverse(self):
        author1 = Author.objects.get(id=self.author1.id)
        with self.assertNumQueries(1):
            prefetch_related_objects([author1], 'books')

        with self.assertNumQueries(0):
            self.assertEqual(set(author1.books.all()), {self.book1, self.book2})

    def test_foreignkey_forward(self):
        authors = list(Author.objects.all())
        with self.assertNumQueries(1):
            prefetch_related_objects(authors, 'first_book')

        with self.assertNumQueries(0):
            [author.first_book for author in authors]

    def test_foreignkey_reverse(self):
        books = list(Book.objects.all())
        with self.assertNumQueries(1):
            prefetch_related_objects(books, 'first_time_authors')

        with self.assertNumQueries(0):
            [list(book.first_time_authors.all()) for book in books]

    def test_m2m_then_m2m(self):
        """A m2m can be followed through another m2m."""
        authors = list(Author.objects.all())
        with self.assertNumQueries(2):
            prefetch_related_objects(authors, 'books__read_by')

        with self.assertNumQueries(0):
            self.assertEqual(
                [
                    [[str(r) for r in b.read_by.all()] for b in a.books.all()]
                    for a in authors
                ],
                [
                    [['Amy'], ['Belinda']],  # Charlotte - Poems, Jane Eyre
                    [['Amy']],               # Anne - Poems
                    [['Amy'], []],           # Emily - Poems, Wuthering Heights
                    [['Amy', 'Belinda']],    # Jane - Sense and Sense
                ]
            )

    def test_prefetch_object(self):
        book1 = Book.objects.get(id=self.book1.id)
        with self.assertNumQueries(1):
            prefetch_related_objects([book1], Prefetch('authors'))

        with self.assertNumQueries(0):
            self.assertEqual(set(book1.authors.all()), {self.author1, self.author2, self.author3})

    def test_prefetch_object_to_attr(self):
        book1 = Book.objects.get(id=self.book1.id)
        with self.assertNumQueries(1):
            prefetch_related_objects([book1], Prefetch('authors', to_attr='the_authors'))

        with self.assertNumQueries(0):
            self.assertEqual(set(book1.the_authors), {self.author1, self.author2, self.author3})

    def test_prefetch_queryset(self):
        book1 = Book.objects.get(id=self.book1.id)
        with self.assertNumQueries(1):
            prefetch_related_objects(
                [book1],
                Prefetch('authors', queryset=Author.objects.filter(id__in=[self.author1.id, self.author2.id]))
            )

        with self.assertNumQueries(0):
            self.assertEqual(set(book1.authors.all()), {self.author1, self.author2})
