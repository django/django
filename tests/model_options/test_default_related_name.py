from django.test import TestCase

from .models.default_related_name import Author, Book, Editor


class DefaultRelatedNameTests(TestCase):

    def setUp(self):
        self.author = Author.objects.create(first_name="Dave", last_name="Loper")
        self.editor = Editor.objects.create(name="Test Editions",
                                            bestselling_author=self.author)
        self.book = Book.objects.create(title="Test Book", editor=self.editor)
        self.book.authors.add(self.author)
        self.book.save()

    def test_no_default_related_name(self):
        try:
            self.author.editor_set
        except AttributeError:
            self.fail("Author should have an editor_set relation.")

    def test_default_related_name(self):
        try:
            self.author.books
        except AttributeError:
            self.fail("Author should have a books relation.")

    def test_related_name_overrides_default_related_name(self):
        try:
            self.editor.edited_books
        except AttributeError:
            self.fail("Editor should have a edited_books relation.")

    def test_inheritance(self):
        try:
            # Here model_options corresponds to the name of the application used
            # in this test
            self.book.model_options_bookstores
        except AttributeError:
            self.fail("Book should have a model_options_bookstores relation.")

    def test_inheritance_with_overridden_default_related_name(self):
        try:
            self.book.editor_stores
        except AttributeError:
            self.fail("Book should have a editor_stores relation.")
