import datetime

from tests.postgres_tests import PostgreSQLTestCase

from django.conf import settings
from django.db.models import (
    Count, DateTimeField, Exists, F, Max, Min, OuterRef, Q, Sum,
)
from django.db.models.functions import Cast, Coalesce
from django.test import TestCase

from .models import (
    Author, Bit, Book, BookAuthor, BookEditor, Brand, Cat, Catalog,
    CatalogInfo, Category, Child, Collection, Dog, Item, ItemCollectionM2M,
    Owner, Package, Parent, Product, Publisher, Purchase, Sale, Seller, Store,
)

# Postgres specific import
try:
    from django.contrib.postgres.aggregates import ArrayAgg
except ImportError:
    pass


class TestParentChild(TestCase):

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.p1 = Parent.objects.create(name='John')
        cls.p2 = Parent.objects.create(name='Jane')

        cls.c1 = Child.objects.create(parent=cls.p1, name='Joe', timestamp='2017-06-01', other_timestamp=None),
        cls.c2 = Child.objects.create(parent=cls.p1, name='Jan', timestamp='2017-07-01', other_timestamp=None),
        cls.c3 = Child.objects.create(parent=cls.p1, name='Jan', timestamp='2017-05-01', other_timestamp='2017-08-01')

    def test_subquery_min(self):
        annotation = {
            'oldest_child_timestamp': Min('child__timestamp', output_field=DateTimeField()).as_subquery()
        }

        parents = Parent.objects.filter(name='John').annotate(**annotation)

        oldest_child = Child.objects.filter(parent__name='John').order_by('timestamp')[0]

        self.assertEqual(parents[0].oldest_child_timestamp, oldest_child.timestamp)

    def test_subquery_max(self):
        annotation = {
            'youngest_child_timestamp': Max('child__timestamp', output_field=DateTimeField()).as_subquery()
        }

        parents = Parent.objects.filter(name='John').annotate(**annotation)

        youngest_child = Child.objects.filter(parent__name='John').order_by('-timestamp')[0]

        self.assertEqual(parents[0].youngest_child_timestamp, youngest_child.timestamp)

    def test_subquery_count(self):
        annotation = {
            'child_count': Count('child').as_subquery()
        }

        parents = Parent.objects.annotate(**annotation)

        counts = {parent.name: parent.child_count for parent in parents}

        self.assertEqual(counts, {'John': 3, 'Jane': 0})

    def test_subquery_count_filtered(self):
        annotation = {
            'child_count': Count('child', filter=Q(name='Jan')).as_subquery()
        }

        parents = Parent.objects.annotate(**annotation)

        counts = {parent.name: parent.child_count for parent in parents}

        self.assertEqual(counts, {'John': 2, 'Jane': 0})

    def test_function(self):
        if settings.DATABASES['default']['ENGINE'] == 'django.db.backends.mysql':
            # Explicit cast for MySQL with Coalesce and Datetime
            # https://docs.djangoproject.com/en/2.1/ref/models/database-functions/#coalesce
            annotation = {
                'oldest_child_with_other': Cast(Min(Coalesce('child__other_timestamp', 'child__timestamp'),
                                                    output_field=DateTimeField()).as_subquery(),
                                                DateTimeField())
            }
        else:
            annotation = {
                'oldest_child_with_other': Min(Coalesce('child__other_timestamp', 'child__timestamp'),
                                               output_field=DateTimeField()).as_subquery()
            }

        parents = Parent.objects.filter(name='John').annotate(**annotation)

        oldest_child = Child.objects.filter(
            parent__name='John'
        ).order_by(
            Coalesce('other_timestamp', 'timestamp').asc()
        )[0]

        self.assertEqual(parents[0].oldest_child_with_other, oldest_child.other_timestamp or oldest_child.timestamp)


class TestManyToMany(TestCase):

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()

        cls.p1 = Publisher.objects.create(name='Publisher 1', number=1)
        cls.p2 = Publisher.objects.create(name='Publisher 2', number=2)

        cls.a1 = Author.objects.create(name='Author 1')
        cls.a2 = Author.objects.create(name='Author 2')
        cls.a3 = Author.objects.create(name='Author 3')
        cls.a4 = Author.objects.create(name='Author 4')
        cls.a5 = Author.objects.create(name='Author 5')
        cls.a6 = Author.objects.create(name='Author 6')

        cls.b1 = Book.objects.create(title='Book 1', publisher=cls.p1)
        cls.b2 = Book.objects.create(title='Book 2', publisher=cls.p1)
        cls.b3 = Book.objects.create(title='Book 3', publisher=cls.p2)
        cls.b4 = Book.objects.create(title='Book 4', publisher=cls.p2)

        BookAuthor.objects.create(author=cls.a1, book=cls.b1, id=1)
        BookAuthor.objects.create(author=cls.a2, book=cls.b2, id=2)
        BookAuthor.objects.create(author=cls.a3, book=cls.b2, id=3)
        BookAuthor.objects.create(author=cls.a3, book=cls.b3, id=4)
        BookAuthor.objects.create(author=cls.a4, book=cls.b3, id=5)
        BookAuthor.objects.create(author=cls.a5, book=cls.b4, id=6)

        BookEditor.objects.create(editor=cls.a6, book=cls.b4)
        BookEditor.objects.create(editor=cls.a6, book=cls.b4)

    def test_subquery_count_forward(self):
        annotation = {
            'author_count': Count('authors').as_subquery()
        }
        books = Book.objects.annotate(**annotation).order_by('id')

        counts = {book.title: book.author_count for book in books}
        self.assertEqual(counts, {'Book 1': 1, 'Book 2': 2, 'Book 3': 2, 'Book 4': 1})

    def test_subquery_count_reverse(self):
        annotation = {
            'book_count': Count('authored_books').as_subquery()
        }
        authors = Author.objects.annotate(**annotation).order_by('id')

        counts = {author.name: author.book_count for author in authors}
        self.assertEqual(counts, {'Author 1': 1,
                                  'Author 2': 1,
                                  'Author 3': 2,
                                  'Author 4': 1,
                                  'Author 5': 1,
                                  'Author 6': 0})

    def test_subquery_count_reverse_explicit(self):
        # The two queries are the same, one just passes a long version of joining from author to books,
        # this test verifies that the automatic reverse of the joins handles both cases.
        # The annotation is a bit non-sensical, taking the Max over titles, but that isn't the point
        annotation = {
            'max_book_title': Max('bookauthor__book__title').as_subquery()
        }
        authors = Author.objects.annotate(**annotation).order_by('id')

        titles = {author.name: author.max_book_title for author in authors}
        self.assertEqual(titles, {'Author 1': 'Book 1',
                                  'Author 2': 'Book 2',
                                  'Author 3': 'Book 3',
                                  'Author 4': 'Book 3',
                                  'Author 5': 'Book 4',
                                  'Author 6': None})

        annotation = {
            'max_book_title': Max('authored_books__title').as_subquery()
        }
        authors = Author.objects.annotate(**annotation).order_by('id')

        titles = {author.name: author.max_book_title for author in authors}
        self.assertEqual(titles, {'Author 1': 'Book 1',
                                  'Author 2': 'Book 2',
                                  'Author 3': 'Book 3',
                                  'Author 4': 'Book 3',
                                  'Author 5': 'Book 4',
                                  'Author 6': None})

    def test_subquery_min_through_m2m_and_foreign_key(self):

        annotation = {
            'max_publisher_number': Max('authored_books__publisher__number').as_subquery()
        }
        authors = Author.objects.annotate(**annotation)

        numbers = {author.name: author.max_publisher_number for author in authors}
        self.assertEqual(numbers, {'Author 1': 1,
                                   'Author 2': 1,
                                   'Author 3': 2,
                                   'Author 4': 2,
                                   'Author 5': 2,
                                   'Author 6': None})

    def test_self_join(self):
        annotation = {
            'book_author_count': Count('book__bookauthor').as_subquery()
        }

        book_authors = BookAuthor.objects.annotate(**annotation)

        counts = {ba.id: ba.book_author_count for ba in book_authors}

        self.assertEqual(counts, {1: 1,
                                  2: 2,
                                  3: 2,
                                  4: 2,
                                  5: 2,
                                  6: 1})


class TestForeignKey(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.p1 = Publisher.objects.create(name='Publisher 1', number=1)
        cls.p2 = Publisher.objects.create(name='Publisher 2', number=2)

        cls.a1 = Author.objects.create(name='Author 1')
        cls.a2 = Author.objects.create(name='Author 2')
        cls.a3 = Author.objects.create(name='Author 3')
        cls.a4 = Author.objects.create(name='Author 4')
        cls.a5 = Author.objects.create(name='Author 5')
        cls.a6 = Author.objects.create(name='Author 6')

        cls.b1 = Book.objects.create(title='Book 1', publisher=cls.p1)
        cls.b2 = Book.objects.create(title='Book 2', publisher=cls.p1)
        cls.b3 = Book.objects.create(title='Book 3', publisher=cls.p2)
        cls.b4 = Book.objects.create(title='Book 4', publisher=cls.p2)

        BookAuthor.objects.create(author=cls.a1, book=cls.b1, id=1)
        BookAuthor.objects.create(author=cls.a2, book=cls.b2, id=2)
        BookAuthor.objects.create(author=cls.a3, book=cls.b2, id=3)
        BookAuthor.objects.create(author=cls.a3, book=cls.b3, id=4)
        BookAuthor.objects.create(author=cls.a4, book=cls.b3, id=5)
        BookAuthor.objects.create(author=cls.a5, book=cls.b4, id=6)

    def test_aggregate_foreign_key(self):
        bookauthors = BookAuthor.objects.annotate(min_publisher_id=Min('book__publisher_id').as_subquery())

        bookauthors = {bookauthor.id: bookauthor.min_publisher_id for bookauthor in bookauthors}

        self.assertEqual(bookauthors, {1: 1,
                                       2: 1,
                                       3: 1,
                                       4: 2,
                                       5: 2,
                                       6: 2})


class TestReverseForeignKey(TestCase):

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.c1 = Catalog.objects.create(number='A')
        cls.c2 = Catalog.objects.create(number='B')

        CatalogInfo.objects.create(catalog=cls.c1, info='cat A info', id=3)
        CatalogInfo.objects.create(catalog=cls.c2, info='cat B info', id=4)

        cls.p1 = Package.objects.create(name='Box', quantity=10, catalog=cls.c1)
        cls.p2 = Package.objects.create(name='Case', quantity=24, catalog=cls.c2)

        Purchase.objects.create(price=5, pack=cls.p1)
        Purchase.objects.create(price=6, pack=cls.p1)
        Purchase.objects.create(price=4, pack=cls.p1)
        Purchase.objects.create(price=11, pack=cls.p2)
        Purchase.objects.create(price=12, pack=cls.p2)

    def test_reverse_foreign_key(self):
        annotations = {
            'max_price': Max('package__purchase__price').as_subquery(),
            'min_price': Min('package__purchase__price').as_subquery()
        }
        catalogs = Catalog.objects.annotate(**annotations)

        prices = {catalog.number: (catalog.max_price, catalog.min_price) for catalog in catalogs}

        self.assertEqual(prices, {'A': (6, 4),
                                  'B': (12, 11)})

    def test_forward_and_reverse_foreign_keys(self):
        annotations = {
            'max_price': Max('catalog__package__purchase__price').as_subquery(),
            'min_price': Min('catalog__package__purchase__price').as_subquery()
        }

        catalog_infos = CatalogInfo.objects.annotate(**annotations)

        extremes = {info.info: (info.max_price, info.min_price) for info in catalog_infos}

        self.assertEqual(extremes, {'cat A info': (6, 4),
                                    'cat B info': (12, 11)})


class TestExists(TestCase):

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.p1 = Parent.objects.create(name='John')
        cls.p2 = Parent.objects.create(name='Jane')

        cls.c1 = Child.objects.create(parent=cls.p1, name='Joe', timestamp='2017-06-01', other_timestamp=None),
        cls.c2 = Child.objects.create(parent=cls.p1, name='Jan', timestamp='2017-07-01', other_timestamp=None),
        cls.c3 = Child.objects.create(parent=cls.p1, name='Jan', timestamp='2017-05-01', other_timestamp='2017-08-01')

    def test_original_exists(self):
        ps = Parent.objects.annotate(has_children=Exists(Child.objects.filter(parent=OuterRef('pk')))).order_by('pk')
        ps = list(ps)

        self.assertEqual(ps[0].has_children, True)
        self.assertEqual(ps[1].has_children, False)

    def test_easy_exists(self):
        ps = Parent.objects.annotate(has_children=Exists('child')).order_by('pk')
        ps = list(ps)

        self.assertEqual(ps[0].has_children, True)
        self.assertEqual(ps[1].has_children, False)

    def test_negated_exists(self):
        ps = Parent.objects.annotate(has_children=~Exists(Child.objects.filter(parent=OuterRef('pk')))).order_by('pk')
        ps = list(ps)

        self.assertEqual(ps[0].has_children, False)
        self.assertEqual(ps[1].has_children, True)

    def test_easy_negated_exists(self):
        ps = Parent.objects.annotate(has_children=~Exists('child')).order_by('pk')
        ps = list(ps)

        self.assertEqual(ps[0].has_children, False)
        self.assertEqual(ps[1].has_children, True)


class TestManyToManyExists(TestCase):

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()

        cls.p1 = Publisher.objects.create(name='Publisher 1', number=1)
        cls.p2 = Publisher.objects.create(name='Publisher 2', number=2)

        cls.a1 = Author.objects.create(name='Author 1')
        cls.a2 = Author.objects.create(name='Author 2')
        cls.a3 = Author.objects.create(name='Author 3')
        cls.a4 = Author.objects.create(name='Author 4')
        cls.a5 = Author.objects.create(name='Author 5')
        cls.a6 = Author.objects.create(name='Author 6')

        cls.b1 = Book.objects.create(title='Book 1', publisher=cls.p1)
        cls.b2 = Book.objects.create(title='Book 2', publisher=cls.p1)
        cls.b3 = Book.objects.create(title='Book 3', publisher=cls.p2)
        cls.b4 = Book.objects.create(title='Book 4', publisher=cls.p2)

        BookAuthor.objects.create(author=cls.a1, book=cls.b1, id=1)
        BookAuthor.objects.create(author=cls.a2, book=cls.b2, id=2)
        BookAuthor.objects.create(author=cls.a3, book=cls.b2, id=3)
        BookAuthor.objects.create(author=cls.a3, book=cls.b3, id=4)
        BookAuthor.objects.create(author=cls.a4, book=cls.b3, id=5)
        BookAuthor.objects.create(author=cls.a5, book=cls.b4, id=6)

        BookEditor.objects.create(editor=cls.a6, book=cls.b4)
        BookEditor.objects.create(editor=cls.a6, book=cls.b4)

    def test_forward(self):
        books = Book.objects.annotate(has_authors=Exists('authors')).order_by('id')
        for book in books:
            self.assertTrue(book.has_authors)

        # Only book 4 has editors
        books = Book.objects.annotate(has_editors=Exists('editors')).order_by('id')
        editors = {book.title: book.has_editors for book in books}

        self.assertEqual(editors, {'Book 1': False,
                                   'Book 2': False,
                                   'Book 3': False,
                                   'Book 4': True})

    def test_reverse(self):
        authors = Author.objects.annotate(has_books=Exists('authored_books')).order_by('id')
        books = {author.name: author.has_books for author in authors}

        self.assertEqual(books, {'Author 1': True,
                                 'Author 2': True,
                                 'Author 3': True,
                                 'Author 4': True,
                                 'Author 5': True,
                                 'Author 6': False})

    def test_two_joins(self):
        authors = Author.objects.annotate(has_editors=Exists('authored_books__editors')).order_by('id')

        # Only author 5 has written a book with editors

        editors = {author.name: author.has_editors for author in authors}

        self.assertEqual(editors, {'Author 1': False,
                                   'Author 2': False,
                                   'Author 3': False,
                                   'Author 4': False,
                                   'Author 5': True,
                                   'Author 6': False})

    def test_filter(self):
        publisher_id = Publisher.objects.get(name='Publisher 1').id
        authors = Author.objects.annotate(published_by_1=Exists('authored_books',
                                                                filter=Q(book__publisher_id=publisher_id)))

        authors = {author.name: author.published_by_1 for author in authors}

        self.assertEqual(authors, {'Author 1': True,
                                   'Author 2': True,
                                   'Author 3': True,
                                   'Author 4': False,
                                   'Author 5': False,
                                   'Author 6': False})

    def test_filter_last_join(self):
        publisher_id = Publisher.objects.get(name='Publisher 1').id
        authors = Author.objects.annotate(
            published_by_1=Exists('authored_books__publisher', filter=Q(id=publisher_id)))

        authors = {author.name: author.published_by_1 for author in authors}

        self.assertEqual(authors, {'Author 1': True,
                                   'Author 2': True,
                                   'Author 3': True,
                                   'Author 4': False,
                                   'Author 5': False,
                                   'Author 6': False})


class TestExistsReverseNames(TestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()

        cls.cat1 = Category.objects.create(name='cat one')
        cls.cat2 = Category.objects.create(name='cat two')
        cls.cat3 = Category.objects.create(name='cat three')

        cls.col1 = Collection.objects.create(name='coll one', the_category=cls.cat1)
        cls.col2 = Collection.objects.create(name='coll two', the_category=cls.cat1)
        cls.col3 = Collection.objects.create(name='coll three', the_category=cls.cat2)
        cls.col4 = Collection.objects.create(name='coll four', the_category=cls.cat2)
        cls.col5 = Collection.objects.create(name='coll five', the_category=cls.cat3)

        cls.i1 = Item.objects.create(name='item one')
        cls.i2 = Item.objects.create(name='item two')
        cls.i3 = Item.objects.create(name='item three')
        cls.i4 = Item.objects.create(name='item four')
        cls.i5 = Item.objects.create(name='item five')
        cls.i6 = Item.objects.create(name='item six')

        ItemCollectionM2M.objects.create(thing=cls.i1, collection_key=cls.col1)
        ItemCollectionM2M.objects.create(thing=cls.i2, collection_key=cls.col2)

        cls.b1 = Bit.objects.create(name="bit one")

        cls.col1.bits.add(cls.b1)

    def test_name_doesnt_match(self):
        annotation = {
            'has_category': Exists('collection_key__the_category')
        }

        items = Item.objects.annotate(**annotation)

        items = {item.name: item.has_category for item in items}

        self.assertEqual(items, {'item one': True,
                                 'item two': True,
                                 'item three': False,
                                 'item four': False,
                                 'item five': False,
                                 'item six': False,
                                 })

    def test_name_doesnt_match_m2m(self):
        annotation = {
            'has_bits': Exists('collection_key__bits')
        }

        items = Item.objects.annotate(**annotation)

        items = {item.name: item.has_bits for item in items}

        self.assertEqual(items, {'item one': True,
                                 'item two': False,
                                 'item three': False,
                                 'item four': False,
                                 'item five': False,
                                 'item six': False,
                                 })


class TestGenericForeignKey(TestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()

        cls.d1 = Dog.objects.create(name="Fido")
        cls.d2 = Dog.objects.create(name="Snoopy")
        cls.d3 = Dog.objects.create(name="Otis")

        cls.c1 = Cat.objects.create(name="Muffin")
        cls.c2 = Cat.objects.create(name="Grumpy")
        cls.c3 = Cat.objects.create(name="Garfield")

        Owner.objects.create(name="Jon", pet=cls.c3)

    def test_exists(self):
        annotation = {'has_an_owner': Exists('owner')}

        cats = Cat.objects.annotate(**annotation)

        cats = {cat.name: cat.has_an_owner for cat in cats}

        self.assertEqual(cats, {'Muffin': False,
                                'Grumpy': False,
                                'Garfield': True})


class TestForeignKeyToField(TestCase):

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.b1 = Brand.objects.create(name='Python', company_id=1337)

        Product.objects.create(brand=cls.b1, num_purchases=1)
        Product.objects.create(brand=cls.b1, num_purchases=3)

    def test_foreign_key_to_field(self):
        brands = Brand.objects.annotate(
            purchase_sum=Sum('products__num_purchases').as_subquery()
        )
        self.assertEqual(brands.first().purchase_sum, 4)


class TestAggregateComputedField(TestCase):

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()

        cls.st1 = Store.objects.create(name='Store 1')
        cls.st2 = Store.objects.create(name='Store 2')

        cls.sr1 = Seller.objects.create(name='Seller 1', store=cls.st1)
        cls.sr2 = Seller.objects.create(name='Seller 2', store=cls.st1)
        cls.sr3 = Seller.objects.create(name='Seller 3', store=cls.st2)
        cls.sr4 = Seller.objects.create(name='Seller 4', store=cls.st2)
        cls.sr5 = Seller.objects.create(name='Seller 5', store=cls.st2)

        Sale.objects.create(date='2019-01-01', revenue=100, expenses=50, seller=cls.sr1)
        Sale.objects.create(date='2019-01-02', revenue=101, expenses=52, seller=cls.sr2)
        Sale.objects.create(date='2019-01-01', revenue=102, expenses=54, seller=cls.sr3)
        Sale.objects.create(date='2019-01-01', revenue=103, expenses=56, seller=cls.sr4)
        Sale.objects.create(date='2019-01-01', revenue=104, expenses=58, seller=cls.sr5)
        Sale.objects.create(date='2019-01-01', revenue=105, expenses=60, seller=cls.sr1)
        Sale.objects.create(date='2019-01-01', revenue=106, expenses=62, seller=cls.sr2)
        Sale.objects.create(date='2019-01-01', revenue=107, expenses=64, seller=cls.sr3)
        Sale.objects.create(date='2019-01-01', revenue=108, expenses=66, seller=cls.sr4)
        Sale.objects.create(date='2019-01-01', revenue=109, expenses=68, seller=cls.sr5)
        Sale.objects.create(date='2019-01-01', revenue=110, expenses=70, seller=cls.sr1)
        Sale.objects.create(date='2019-01-01', revenue=111, expenses=72, seller=cls.sr5)

    def test_aggregate_computed_field(self):
        from django.db.models import Sum

        stores = Store.objects.annotate(
            balance=Sum('seller__sale__revenue') - Sum('seller__sale__expenses')
        )

        expected = dict((store.id, store.balance) for store in stores)

        stores = Store.objects.annotate(
            balance=Sum('seller__sale__revenue').as_subquery() - Sum('seller__sale__expenses').as_subquery()
        )

        actual = dict((store.id, store.balance) for store in stores)
        self.assertEqual(expected, actual)

    def test_aggregate_computed_filtered_field(self):
        stores = Store.objects.annotate(
            balance=(Sum('seller__sale__revenue', filter=Q(seller__sale__date='2019-01-02')) -
                     Sum('seller__sale__expenses', filter=Q(seller__sale__date='2019-01-02')))
        )

        expected = dict((store.id, store.balance) for store in stores)

        stores = Store.objects.annotate(
            balance=Sum(F('seller__sale__revenue') - F('seller__sale__expenses'),
                        filter=Q(date='2019-01-02')).as_subquery()
        )

        actual = dict((store.id, store.balance) for store in stores)
        self.assertEqual(expected, actual)


class TestOrderableAggregate(PostgreSQLTestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.p1 = Parent.objects.create(name='John')
        cls.p2 = Parent.objects.create(name='Jane')

        cls.c1 = Child.objects.create(parent=cls.p1, name='Joe', timestamp='2017-06-01', other_timestamp=None),
        cls.c2 = Child.objects.create(parent=cls.p1, name='Jan', timestamp='2017-07-01', other_timestamp=None),
        cls.c3 = Child.objects.create(parent=cls.p1, name='Jen', timestamp='2017-05-01', other_timestamp='2017-08-01')
        cls.c4 = Child.objects.create(parent=cls.p1, name='Bhani', timestamp='2014-05-01',
                                      other_timestamp='2017-06-01')
        cls.c5 = Child.objects.create(parent=cls.p1, name='Carlos', timestamp='2019-05-01',
                                      other_timestamp='2017-09-01')
        cls.c6 = Child.objects.create(parent=cls.p1, name='Anansi', timestamp='2018-05-01',
                                      other_timestamp='2017-05-01')

    def test_arrayagg_subquery_ordering(self):
        parents = Parent.objects.annotate(
            children_by_name=ArrayAgg('child__name', ordering='name').as_subquery(),
            children_by_timestamp=ArrayAgg('child__timestamp', ordering='timestamp').as_subquery()
        )

        parent = parents.get(name='John')

        self.assertEqual(parent.children_by_name, ['Anansi', 'Bhani', 'Carlos', 'Jan', 'Jen', 'Joe'])
        self.assertEqual(parent.children_by_timestamp, [datetime.datetime(2014, 5, 1),
                                                        datetime.datetime(2017, 5, 1),
                                                        datetime.datetime(2017, 6, 1),
                                                        datetime.datetime(2017, 7, 1),
                                                        datetime.datetime(2018, 5, 1),
                                                        datetime.datetime(2019, 5, 1)])
