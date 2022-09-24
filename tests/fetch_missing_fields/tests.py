from django.core.exceptions import FetchMissingFieldError
from django.db.models import fetch_missing_fields
from django.test import TestCase

from .models import Author, Bio, Book


class FetchMissingFieldsTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.author1 = Author.objects.create(name="Charlotte")
        cls.author2 = Author.objects.create(name="Anne")
        cls.author3 = Author.objects.create(name="Emily")
        cls.author4 = Author.objects.create(name="Jane")
        cls.author_set = {cls.author1, cls.author2, cls.author3, cls.author4}

        cls.book1 = Book.objects.create(title="Poems", author=cls.author1)
        cls.book2 = Book.objects.create(title="Jane Eyre", author=cls.author2)
        cls.book3 = Book.objects.create(title="Wuthering Heights", author=cls.author3)
        cls.book4 = Book.objects.create(
            title="Sense and Sensibility", author=cls.author4
        )

    def test_defaults(self):
        # Check defaults before entering a block
        self.assertEqual(fetch_missing_fields.get_current_related_strategy(), "peers")
        self.assertEqual(fetch_missing_fields.get_current_deferred_strategy(), "peers")

        with fetch_missing_fields("never"):
            self.assertEqual(
                fetch_missing_fields.get_current_related_strategy(), "never"
            )
            self.assertEqual(
                fetch_missing_fields.get_current_deferred_strategy(), "never"
            )

        # Ensure modes are reset to defaults when the last context is left
        self.assertEqual(fetch_missing_fields.get_current_related_strategy(), "peers")
        self.assertEqual(fetch_missing_fields.get_current_deferred_strategy(), "peers")

    def test_nested_contexts(self):
        with fetch_missing_fields("never"):
            self.assertEqual(
                fetch_missing_fields.get_current_related_strategy(), "never"
            )
            with fetch_missing_fields("on_demand"):
                self.assertEqual(
                    fetch_missing_fields.get_current_related_strategy(), "on_demand"
                )
            self.assertEqual(
                fetch_missing_fields.get_current_related_strategy(), "never"
            )

    @fetch_missing_fields(deferred="never")
    def test_override_single_mode(self):
        self.assertEqual(fetch_missing_fields.get_current_related_strategy(), "peers")
        self.assertEqual(fetch_missing_fields.get_current_deferred_strategy(), "never")

    def test_decorator_single_argument(self):
        @fetch_missing_fields("on_demand")
        def func():
            self.assertEqual(
                fetch_missing_fields.get_current_related_strategy(), "on_demand"
            )

            self.assertEqual(
                fetch_missing_fields.get_current_deferred_strategy(), "on_demand"
            )

        func()

    def test_decorator_kwargs(self):
        @fetch_missing_fields(related="never", deferred="on_demand")
        def func():
            self.assertEqual(
                fetch_missing_fields.get_current_related_strategy(), "never"
            )

            self.assertEqual(
                fetch_missing_fields.get_current_deferred_strategy(), "on_demand"
            )

        func()

    def test_context_bad_arg(self):
        with self.assertRaises(ValueError):
            with fetch_missing_fields("bad_value"):
                pass

    @fetch_missing_fields("never")
    def test_fetch_missing_fields_does_not_raise_exception(self):
        books = list(Book.objects.all())
        with self.assertRaises(FetchMissingFieldError):
            books[0].author

    @fetch_missing_fields("peers")
    def test_auto_chaining(self):
        Bio.objects.bulk_create(
            [
                Bio(author=self.author1, text="bio1"),
                Bio(author=self.author2, text="bio2"),
                Bio(author=self.author3, text="bio3"),
                Bio(author=self.author4, text="bio4"),
            ]
        )
        with self.assertNumQueries(3):
            bio_texts = {book.author.bio.text for book in Book.objects.all()}
            self.assertEqual(bio_texts, {"bio1", "bio2", "bio3", "bio4"})

    def test_set_default_disallow_never(self):
        with self.assertRaises(ValueError):
            fetch_missing_fields.set_default("never")

    def test_set_default_bad_arg(self):
        with self.assertRaises(ValueError):
            fetch_missing_fields.set_default("not_valid")

    def test_set_default_positional_argument(self):
        fetch_missing_fields.set_default("on_demand")
        assert fetch_missing_fields.get_current_related_strategy() == "on_demand"
        assert fetch_missing_fields.get_current_deferred_strategy() == "on_demand"

    def test_set_default_kwarg(self):
        # Try changing both
        fetch_missing_fields.set_default(related="on_demand", deferred="never")
        assert fetch_missing_fields.get_current_related_strategy() == "on_demand"
        assert fetch_missing_fields.get_current_deferred_strategy() == "never"

        # Change just one, make sure the other stays the same.
        fetch_missing_fields.set_default(related="peers")
        assert fetch_missing_fields.get_current_related_strategy() == "peers"
        assert fetch_missing_fields.get_current_deferred_strategy() == "never"

    def test_one_to_one_forward_peers(self):
        Bio.objects.bulk_create(
            [
                Bio(author=self.author1),
                Bio(author=self.author2),
                Bio(author=self.author3),
                Bio(author=self.author4),
            ]
        )
        with self.assertNumQueries(2):
            authors = [b.author for b in Bio.objects.all()]

        normal_authors = [b.author for b in Bio.objects.all()]
        self.assertEqual(authors, normal_authors)

    def test_one_to_one_reverse_peers(self):
        bios_set = {
            Bio(author=self.author1),
            Bio(author=self.author2),
            Bio(author=self.author3),
            Bio(author=self.author4),
        }
        Bio.objects.bulk_create(bios_set)
        with self.assertNumQueries(1):
            authors = list(Author.objects.all())

        with self.assertNumQueries(1):
            bios = {a.bio for a in authors}

        self.assertEqual(bios, bios_set)

    def test_foreignkey_forward_peers(self):
        with self.assertNumQueries(1):
            books = list(Book.objects.all())

        with self.assertNumQueries(1):
            authors = {book.author for book in books}

        self.assertEqual(authors, self.author_set)

    def tearDown(self):
        fetch_missing_fields.set_default("peers")
