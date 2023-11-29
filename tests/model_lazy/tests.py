from django.db.models import (
    FETCH_ONE,
    FETCH_PEERS,
    RAISE,
    lazy_mode,
    set_default_lazy_mode,
)
from django.db.models.lazy import LazyFieldAccess, get_lazy_mode
from django.test import TestCase

from .models import Author, Bio, Book


class LazyModeTests(TestCase):
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

    def test_set_default(self):
        try:
            set_default_lazy_mode(RAISE)
            self.assertIs(get_lazy_mode(), RAISE)
        finally:
            set_default_lazy_mode(FETCH_ONE)

    def test_set_default_bad_argument(self):
        with self.assertRaises(TypeError):
            set_default_lazy_mode("RAISE")
        # TODO: assert on message

    def test_lazy_mode_context_manager(self):
        self.assertIs(get_lazy_mode(), FETCH_ONE)

        with lazy_mode(RAISE):
            self.assertIs(get_lazy_mode(), RAISE)

        self.assertIs(get_lazy_mode(), FETCH_ONE)

    def test_nested_contexts(self):
        with lazy_mode(RAISE):
            self.assertIs(get_lazy_mode(), RAISE)
            with lazy_mode(FETCH_PEERS):
                self.assertIs(get_lazy_mode(), FETCH_PEERS)
            self.assertIs(get_lazy_mode(), RAISE)

    @lazy_mode(RAISE)
    def test_decorator(self):
        self.assertIs(get_lazy_mode(), RAISE)

    def test_bad_argument(self):
        with self.assertRaises(TypeError):
            with lazy_mode("RAISE"):
                pass
        # TODO: assert on message

    @lazy_mode(RAISE)
    def test_raise_mode(self):
        books = list(Book.objects.all())
        with self.assertRaises(LazyFieldAccess):
            books[0].author

    @lazy_mode(FETCH_PEERS)
    def test_fetch_peers_chained(self):
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

    @lazy_mode(FETCH_ONE)
    def test_deferred_fields_fetch_one(self):
        with self.assertNumQueries(5):
            names = {a.name for a in Author.objects.defer("name")}
            self.assertEqual(names, {"Charlotte", "Anne", "Emily", "Jane"})

    @lazy_mode(FETCH_PEERS)
    def test_deferred_fields_fetch_peers(self):
        with self.assertNumQueries(2):
            names = {a.name for a in Author.objects.defer("name")}
            self.assertEqual(names, {"Charlotte", "Anne", "Emily", "Jane"})

    @lazy_mode(FETCH_PEERS)
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

    @lazy_mode(FETCH_PEERS)
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

    @lazy_mode(FETCH_PEERS)
    def test_foreignkey_forward_peers(self):
        with self.assertNumQueries(1):
            books = list(Book.objects.all())

        with self.assertNumQueries(1):
            authors = {book.author for book in books}

        self.assertEqual(authors, self.author_set)
