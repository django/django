import warnings

from django.test import TestCase
from django.utils.deprecation import RemovedInDjango20Warning

from .models.default_related_name import Author, Book, Editor


class DefaultRelatedNameTests(TestCase):

    @classmethod
    def setUpTestData(cls):
        cls.author = Author.objects.create(first_name='Dave', last_name='Loper')
        cls.editor = Editor.objects.create(name='Test Editions', bestselling_author=cls.author)
        cls.book = Book.objects.create(title='Test Book', editor=cls.editor)
        cls.book.authors.add(cls.author)

    def test_no_default_related_name(self):
        self.assertEqual(list(self.author.editor_set.all()), [self.editor])

    def test_default_related_name(self):
        self.assertEqual(list(self.author.books.all()), [self.book])

    def test_default_related_name_in_queryset_lookup(self):
        self.assertEqual(Author.objects.get(books=self.book), self.author)

    def test_show_deprecated_message_when_model_name_in_queryset_lookup(self):
        msg = "Query lookup 'book' is deprecated in favor of Meta.default_related_name 'books'."
        with warnings.catch_warnings(record=True) as warns:
            warnings.simplefilter('once')
            Author.objects.get(book=self.book)
        self.assertEqual(len(warns), 1)
        warning = warns.pop()
        self.assertEqual(warning.category, RemovedInDjango20Warning)
        self.assertEqual(str(warning.message), msg)

    def test_related_name_overrides_default_related_name(self):
        self.assertEqual(list(self.editor.edited_books.all()), [self.book])

    def test_inheritance(self):
        # model_options is the name of the application for this test.
        self.assertEqual(list(self.book.model_options_bookstores.all()), [])

    def test_inheritance_with_overridden_default_related_name(self):
        self.assertEqual(list(self.book.editor_stores.all()), [])
