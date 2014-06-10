
from django.test import TestCase

from .models.default_related_name import Author, Editor, Book, BookStore, \
  EditorStore, Store


class DefaultRelatedNameTests(TestCase):

    def setUp(self):
        self.author_1 = Author.objects.create(first_name="Dave", last_name="Loper")
        self.author_1.save()
        self.author_2 = Author.objects.create(first_name="John", last_name="Go")
        self.author_1.save()
        self.editor = Editor.objects.create(name="Test Editions",
                                              bestselling_author=self.author_1)
        self.editor.save()
        self.book_1 = Book.objects.create(title="Test Book", editor=self.editor)
        self.book_1.authors.add(self.author_1)
        self.book_1.save()
        self.book_2 = Book.objects.create(title="Another Test Book", editor=self.editor)
        self.book_2.authors.add(self.author_1)
        self.book_2.authors.add(self.author_2)
        self.book_2.save()
        self.bookstore = BookStore.objects.create(name="Books for sale",
                                                  address="12, Main Street, Paris")
        self.bookstore.available_books.add(self.book_1)
        self.bookstore.available_books.add(self.book_2)
        self.bookstore.save()
        self.editorstore = EditorStore.objects.create(name="Test Editions Outlet Center",
                                                      address="34, Main Street, Paris",
                                                      editor=self.editor)
        self.editorstore.available_books.add(self.book_1)
        self.editorstore.available_books.add(self.book_2)
        self.editorstore.save()

    def test_no_default_related_name(self):
        try:
            _ = self.author_1.editor_set.all()
        except AttributeError:
            self.fail("Author 1 should have an editor_set relation.")

    def test_default_related_name(self):
        try:
            _ = self.author_1.books.all()
        except AttributeError:
            self.fail("Author should have a books relation.")

    def test_related_name_overrides_default_related_name(self):
        try:
            _ = self.editor.edited_books.all()
        except AttributeError:
            self.fail("Editor 1 should have a edited_books relation.")

    def test_inheritance(self):
        try:
            # Here model_options corresponds to the name of the application used
            # in this test
            _ = self.book_1.model_options_bookstores.all()
        except AttributeError:
            self.fail("Book 1 should have a default_related_name_bookstores relation.")

    def test_inheritance_with_overrided_default_related_name(self):
        try:
            _ = self.book_1.editor_stores.all()
        except AttributeError:
            self.fail("Book 1 should have a editor_stores relation.")
