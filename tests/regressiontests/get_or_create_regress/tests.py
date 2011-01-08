from django.test import TestCase

from models import Author, Publisher


class GetOrCreateTests(TestCase):
    def test_related(self):
        p = Publisher.objects.create(name="Acme Publishing")
        # Create a book through the publisher.
        book, created = p.books.get_or_create(name="The Book of Ed & Fred")
        self.assertTrue(created)
        # The publisher should have one book.
        self.assertEqual(p.books.count(), 1)

        # Try get_or_create again, this time nothing should be created.
        book, created = p.books.get_or_create(name="The Book of Ed & Fred")
        self.assertFalse(created)
        # And the publisher should still have one book.
        self.assertEqual(p.books.count(), 1)

        # Add an author to the book.
        ed, created = book.authors.get_or_create(name="Ed")
        self.assertTrue(created)
        # The book should have one author.
        self.assertEqual(book.authors.count(), 1)

        # Try get_or_create again, this time nothing should be created.
        ed, created = book.authors.get_or_create(name="Ed")
        self.assertFalse(created)
        # And the book should still have one author.
        self.assertEqual(book.authors.count(), 1)

        # Add a second author to the book.
        fred, created = book.authors.get_or_create(name="Fred")
        self.assertTrue(created)

        # The book should have two authors now.
        self.assertEqual(book.authors.count(), 2)

        # Create an Author not tied to any books.
        Author.objects.create(name="Ted")

        # There should be three Authors in total. The book object should have two.
        self.assertEqual(Author.objects.count(), 3)
        self.assertEqual(book.authors.count(), 2)

        # Try creating a book through an author.
        _, created = ed.books.get_or_create(name="Ed's Recipes", publisher=p)
        self.assertTrue(created)

        # Now Ed has two Books, Fred just one.
        self.assertEqual(ed.books.count(), 2)
        self.assertEqual(fred.books.count(), 1)

        # Use the publisher's primary key value instead of a model instance.
        _, created = ed.books.get_or_create(name='The Great Book of Ed', publisher_id=p.id)
        self.assertTrue(created)
        # Try get_or_create again, this time nothing should be created.
        _, created = ed.books.get_or_create(name='The Great Book of Ed', publisher_id=p.id)
        self.assertFalse(created)
        # The publisher should have three books.
        self.assertEqual(p.books.count(), 3)
