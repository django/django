from __future__ import absolute_import, unicode_literals

from datetime import datetime
from operator import attrgetter

from django.core.exceptions import FieldError
from django.test import TestCase, skipUnlessDBFeature
from django.utils import six

from shared_models.models import Author, Book

from .models import Tag, Game, Season, Player


class LookupTests(TestCase):

    def setUp(self):
        # Create a few Authors.
        self.au1 = Author(name='Author 1')
        self.au1.save()
        self.au2 = Author(name='Author 2')
        self.au2.save()
        # Create a couple of Books.
        self.b1 = Book(title='Book 1', pubdate=datetime(2005, 7, 26), author=self.au1)
        self.b1.save()
        self.b2 = Book(title='Book 2', pubdate=datetime(2005, 7, 27), author=self.au1)
        self.b2.save()
        self.b3 = Book(title='Book 3', pubdate=datetime(2005, 7, 27), author=self.au1)
        self.b3.save()
        self.b4 = Book(title='Book 4', pubdate=datetime(2005, 7, 28), author=self.au1)
        self.b4.save()
        self.b5 = Book(title='Book 5', pubdate=datetime(2005, 8, 1, 9, 0), author=self.au2)
        self.b5.save()
        self.b6 = Book(title='Book 6', pubdate=datetime(2005, 8, 1, 8, 0), author=self.au2)
        self.b6.save()
        self.b7 = Book(title='Book 7', pubdate=datetime(2005, 7, 27), author=self.au2)
        self.b7.save()
        # Create a few Tags.
        self.t1 = Tag(name='Tag 1')
        self.t1.save()
        self.t1.articles.add(self.b1, self.b2, self.b3)
        self.t2 = Tag(name='Tag 2')
        self.t2.save()
        self.t2.articles.add(self.b3, self.b4, self.b5)
        self.t3 = Tag(name='Tag 3')
        self.t3.save()
        self.t3.articles.add(self.b5, self.b6, self.b7)

    def test_exists(self):
        # We can use .exists() to check that there are some
        self.assertTrue(Book.objects.exists())
        for a in Book.objects.all():
            a.delete()
        # There should be none now!
        self.assertFalse(Book.objects.exists())

    def test_lookup_int_as_str(self):
        # Integer value can be queried using string
        self.assertQuerysetEqual(Book.objects.filter(id__iexact=str(self.b1.id)),
                                 ['<Book: Book 1>'])

    @skipUnlessDBFeature('supports_date_lookup_using_string')
    def test_lookup_date_as_str(self):
        # A date lookup can be performed using a string search
        self.assertQuerysetEqual(Book.objects.filter(pubdate__startswith='2005'),
            [
                '<Book: Book 5>',
                '<Book: Book 6>',
                '<Book: Book 4>',
                '<Book: Book 2>',
                '<Book: Book 3>',
                '<Book: Book 7>',
                '<Book: Book 1>',
            ])

    def test_iterator(self):
        # Each QuerySet gets iterator(), which is a generator that "lazily"
        # returns results using database-level iteration.
        self.assertQuerysetEqual(Book.objects.iterator(),
            [
                'Book 5',
                'Book 6',
                'Book 4',
                'Book 2',
                'Book 3',
                'Book 7',
                'Book 1',
            ],
            transform=attrgetter('title'))
        # iterator() can be used on any QuerySet.
        self.assertQuerysetEqual(
            Book.objects.filter(title__endswith='4').iterator(),
            ['Book 4'],
            transform=attrgetter('title'))

    def test_count(self):
        # count() returns the number of objects matching search criteria.
        self.assertEqual(Book.objects.count(), 7)
        self.assertEqual(Book.objects.filter(pubdate__exact=datetime(2005, 7, 27)).count(), 3)
        self.assertEqual(Book.objects.filter(title__startswith='Blah blah').count(), 0)

        # count() should respect sliced query sets.
        articles = Book.objects.all()
        self.assertEqual(articles.count(), 7)
        self.assertEqual(articles[:4].count(), 4)
        self.assertEqual(articles[1:100].count(), 6)
        self.assertEqual(articles[10:100].count(), 0)

        # Date and date/time lookups can also be done with strings.
        self.assertEqual(Book.objects.filter(pubdate__exact='2005-07-27').count(), 3)

    def test_in_bulk(self):
        # in_bulk() takes a list of IDs and returns a dictionary mapping IDs to objects.
        arts = Book.objects.in_bulk([self.b1.id, self.b2.id])
        self.assertEqual(arts[self.b1.id], self.b1)
        self.assertEqual(arts[self.b2.id], self.b2)
        self.assertEqual(Book.objects.in_bulk([self.b3.id]), {self.b3.id: self.b3})
        self.assertEqual(Book.objects.in_bulk(set([self.b3.id])), {self.b3.id: self.b3})
        self.assertEqual(Book.objects.in_bulk(frozenset([self.b3.id])), {self.b3.id: self.b3})
        self.assertEqual(Book.objects.in_bulk((self.b3.id,)), {self.b3.id: self.b3})
        self.assertEqual(Book.objects.in_bulk([1000]), {})
        self.assertEqual(Book.objects.in_bulk([]), {})
        self.assertEqual(Book.objects.in_bulk(iter([self.b1.id])), {self.b1.id: self.b1})
        self.assertEqual(Book.objects.in_bulk(iter([])), {})
        self.assertRaises(TypeError, Book.objects.in_bulk)
        self.assertRaises(TypeError, Book.objects.in_bulk, name__startswith='Blah')

    def test_values(self):
        # values() returns a list of dictionaries instead of object instances --
        # and you can specify which fields you want to retrieve.
        identity = lambda x:x
        self.assertQuerysetEqual(Book.objects.values('title'),
            [
                {'title': 'Book 5'},
                {'title': 'Book 6'},
                {'title': 'Book 4'},
                {'title': 'Book 2'},
                {'title': 'Book 3'},
                {'title': 'Book 7'},
                {'title': 'Book 1'},
            ],
            transform=identity)
        self.assertQuerysetEqual(
            Book.objects.filter(pubdate__exact=datetime(2005, 7, 27)).values('id'),
            [{'id': self.b2.id}, {'id': self.b3.id}, {'id': self.b7.id}],
            transform=identity)
        self.assertQuerysetEqual(Book.objects.values('id', 'title'),
            [
                {'id': self.b5.id, 'title': 'Book 5'},
                {'id': self.b6.id, 'title': 'Book 6'},
                {'id': self.b4.id, 'title': 'Book 4'},
                {'id': self.b2.id, 'title': 'Book 2'},
                {'id': self.b3.id, 'title': 'Book 3'},
                {'id': self.b7.id, 'title': 'Book 7'},
                {'id': self.b1.id, 'title': 'Book 1'},
            ],
            transform=identity)
        # You can use values() with iterator() for memory savings,
        # because iterator() uses database-level iteration.
        self.assertQuerysetEqual(Book.objects.values('id', 'title').iterator(),
            [
                {'title': 'Book 5', 'id': self.b5.id},
                {'title': 'Book 6', 'id': self.b6.id},
                {'title': 'Book 4', 'id': self.b4.id},
                {'title': 'Book 2', 'id': self.b2.id},
                {'title': 'Book 3', 'id': self.b3.id},
                {'title': 'Book 7', 'id': self.b7.id},
                {'title': 'Book 1', 'id': self.b1.id},
            ],
            transform=identity)
        # The values() method works with "extra" fields specified in extra(select).
        self.assertQuerysetEqual(
            Book.objects.extra(select={'id_plus_one': 'id + 1'}).values('id', 'id_plus_one'),
            [
                {'id': self.b5.id, 'id_plus_one': self.b5.id + 1},
                {'id': self.b6.id, 'id_plus_one': self.b6.id + 1},
                {'id': self.b4.id, 'id_plus_one': self.b4.id + 1},
                {'id': self.b2.id, 'id_plus_one': self.b2.id + 1},
                {'id': self.b3.id, 'id_plus_one': self.b3.id + 1},
                {'id': self.b7.id, 'id_plus_one': self.b7.id + 1},
                {'id': self.b1.id, 'id_plus_one': self.b1.id + 1},
            ],
            transform=identity)
        data = {
            'id_plus_one': 'id+1',
            'id_plus_two': 'id+2',
            'id_plus_three': 'id+3',
            'id_plus_four': 'id+4',
            'id_plus_five': 'id+5',
            'id_plus_six': 'id+6',
            'id_plus_seven': 'id+7',
            'id_plus_eight': 'id+8',
        }
        self.assertQuerysetEqual(
            Book.objects.filter(id=self.b1.id).extra(select=data).values(*data.keys()),
            [{
                'id_plus_one': self.b1.id + 1,
                'id_plus_two': self.b1.id + 2,
                'id_plus_three': self.b1.id + 3,
                'id_plus_four': self.b1.id + 4,
                'id_plus_five': self.b1.id + 5,
                'id_plus_six': self.b1.id + 6,
                'id_plus_seven': self.b1.id + 7,
                'id_plus_eight': self.b1.id + 8,
            }], transform=identity)
        # You can specify fields from forward and reverse relations, just like filter().
        self.assertQuerysetEqual(
            Book.objects.values('title', 'author__name'),
            [
                {'title': self.b5.title, 'author__name': self.au2.name},
                {'title': self.b6.title, 'author__name': self.au2.name},
                {'title': self.b4.title, 'author__name': self.au1.name},
                {'title': self.b2.title, 'author__name': self.au1.name},
                {'title': self.b3.title, 'author__name': self.au1.name},
                {'title': self.b7.title, 'author__name': self.au2.name},
                {'title': self.b1.title, 'author__name': self.au1.name},
            ], transform=identity)
        self.assertQuerysetEqual(
            Author.objects.values('name', 'book__title').order_by('name', 'book__title'),
            [
                {'name': self.au1.name, 'book__title': self.b1.title},
                {'name': self.au1.name, 'book__title': self.b2.title},
                {'name': self.au1.name, 'book__title': self.b3.title},
                {'name': self.au1.name, 'book__title': self.b4.title},
                {'name': self.au2.name, 'book__title': self.b5.title},
                {'name': self.au2.name, 'book__title': self.b6.title},
                {'name': self.au2.name, 'book__title': self.b7.title},
            ], transform=identity)
        self.assertQuerysetEqual(
            Author.objects.values('name', 'book__title', 'book__tag__name').order_by('name', 'book__title', 'book__tag__name'),
            [
                {'name': self.au1.name, 'book__title': self.b1.title, 'book__tag__name': self.t1.name},
                {'name': self.au1.name, 'book__title': self.b2.title, 'book__tag__name': self.t1.name},
                {'name': self.au1.name, 'book__title': self.b3.title, 'book__tag__name': self.t1.name},
                {'name': self.au1.name, 'book__title': self.b3.title, 'book__tag__name': self.t2.name},
                {'name': self.au1.name, 'book__title': self.b4.title, 'book__tag__name': self.t2.name},
                {'name': self.au2.name, 'book__title': self.b5.title, 'book__tag__name': self.t2.name},
                {'name': self.au2.name, 'book__title': self.b5.title, 'book__tag__name': self.t3.name},
                {'name': self.au2.name, 'book__title': self.b6.title, 'book__tag__name': self.t3.name},
                {'name': self.au2.name, 'book__title': self.b7.title, 'book__tag__name': self.t3.name},
            ], transform=identity)
        # However, an exception FieldDoesNotExist will be thrown if you specify
        # a non-existent field name in values() (a field that is neither in the
        # model nor in extra(select)).
        self.assertRaises(FieldError,
            Book.objects.extra(select={'id_plus_one': 'id + 1'}).values,
            'id', 'id_plus_two')
        # If you don't specify field names to values(), all are returned.
        self.assertQuerysetEqual(Book.objects.filter(id=self.b5.id).values(),
            [{
                'id': self.b5.id,
                'author_id': self.au2.id,
                'title': 'Book 5',
                'pages': 0,
                'pubdate': datetime(2005, 8, 1, 9, 0)
            }], transform=identity)

    def test_values_list(self):
        # values_list() is similar to values(), except that the results are
        # returned as a list of tuples, rather than a list of dictionaries.
        # Within each tuple, the order of the elements is the same as the order
        # of fields in the values_list() call.
        identity = lambda x:x
        self.assertQuerysetEqual(Book.objects.values_list('title'),
            [
                ('Book 5',),
                ('Book 6',),
                ('Book 4',),
                ('Book 2',),
                ('Book 3',),
                ('Book 7',),
                ('Book 1',),
            ], transform=identity)
        self.assertQuerysetEqual(Book.objects.values_list('id').order_by('id'),
            [(self.b1.id,), (self.b2.id,), (self.b3.id,), (self.b4.id,), (self.b5.id,), (self.b6.id,), (self.b7.id,)],
            transform=identity)
        self.assertQuerysetEqual(
            Book.objects.values_list('id', flat=True).order_by('id'),
            [self.b1.id, self.b2.id, self.b3.id, self.b4.id, self.b5.id, self.b6.id, self.b7.id],
            transform=identity)
        self.assertQuerysetEqual(
            Book.objects.extra(select={'id_plus_one': 'id+1'})
                           .order_by('id').values_list('id'),
            [(self.b1.id,), (self.b2.id,), (self.b3.id,), (self.b4.id,), (self.b5.id,), (self.b6.id,), (self.b7.id,)],
            transform=identity)
        self.assertQuerysetEqual(
            Book.objects.extra(select={'id_plus_one': 'id+1'})
                           .order_by('id').values_list('id_plus_one', 'id'),
            [
                (self.b1.id+1, self.b1.id),
                (self.b2.id+1, self.b2.id),
                (self.b3.id+1, self.b3.id),
                (self.b4.id+1, self.b4.id),
                (self.b5.id+1, self.b5.id),
                (self.b6.id+1, self.b6.id),
                (self.b7.id+1, self.b7.id)
            ],
            transform=identity)
        self.assertQuerysetEqual(
            Book.objects.extra(select={'id_plus_one': 'id+1'})
                           .order_by('id').values_list('id', 'id_plus_one'),
            [
                (self.b1.id, self.b1.id+1),
                (self.b2.id, self.b2.id+1),
                (self.b3.id, self.b3.id+1),
                (self.b4.id, self.b4.id+1),
                (self.b5.id, self.b5.id+1),
                (self.b6.id, self.b6.id+1),
                (self.b7.id, self.b7.id+1)
            ],
            transform=identity)
        self.assertQuerysetEqual(
            Author.objects.values_list('name', 'book__title', 'book__tag__name').order_by('name', 'book__title', 'book__tag__name'),
            [
                (self.au1.name, self.b1.title, self.t1.name),
                (self.au1.name, self.b2.title, self.t1.name),
                (self.au1.name, self.b3.title, self.t1.name),
                (self.au1.name, self.b3.title, self.t2.name),
                (self.au1.name, self.b4.title, self.t2.name),
                (self.au2.name, self.b5.title, self.t2.name),
                (self.au2.name, self.b5.title, self.t3.name),
                (self.au2.name, self.b6.title, self.t3.name),
                (self.au2.name, self.b7.title, self.t3.name),
            ], transform=identity)
        self.assertRaises(TypeError, Book.objects.values_list, 'id', 'title', flat=True)

    def test_get_next_previous_by(self):
        # Every DateField and DateTimeField creates get_next_by_FOO() and
        # get_previous_by_FOO() methods. In the case of identical date values,
        # these methods will use the ID as a fallback check. This guarantees
        # that no records are skipped or duplicated.
        self.assertEqual(repr(self.b1.get_next_by_pubdate()),
                         '<Book: Book 2>')
        self.assertEqual(repr(self.b2.get_next_by_pubdate()),
                         '<Book: Book 3>')
        self.assertEqual(repr(self.b2.get_next_by_pubdate(title__endswith='6')),
                         '<Book: Book 6>')
        self.assertEqual(repr(self.b3.get_next_by_pubdate()),
                         '<Book: Book 7>')
        self.assertEqual(repr(self.b4.get_next_by_pubdate()),
                         '<Book: Book 6>')
        self.assertRaises(Book.DoesNotExist, self.b5.get_next_by_pubdate)
        self.assertEqual(repr(self.b6.get_next_by_pubdate()),
                         '<Book: Book 5>')
        self.assertEqual(repr(self.b7.get_next_by_pubdate()),
                         '<Book: Book 4>')

        self.assertEqual(repr(self.b7.get_previous_by_pubdate()),
                         '<Book: Book 3>')
        self.assertEqual(repr(self.b6.get_previous_by_pubdate()),
                         '<Book: Book 4>')
        self.assertEqual(repr(self.b5.get_previous_by_pubdate()),
                         '<Book: Book 6>')
        self.assertEqual(repr(self.b4.get_previous_by_pubdate()),
                         '<Book: Book 7>')
        self.assertEqual(repr(self.b3.get_previous_by_pubdate()),
                         '<Book: Book 2>')
        self.assertEqual(repr(self.b2.get_previous_by_pubdate()),
                         '<Book: Book 1>')

    def test_escaping(self):
        # Underscores, percent signs and backslashes have special meaning in the
        # underlying SQL code, but Django handles the quoting of them automatically.
        b8 = Book(title='Book_ with underscore', pubdate=datetime(2005, 11, 20))
        b8.save()
        self.assertQuerysetEqual(Book.objects.filter(title__startswith='Book'),
            [
                '<Book: Book_ with underscore>',
                '<Book: Book 5>',
                '<Book: Book 6>',
                '<Book: Book 4>',
                '<Book: Book 2>',
                '<Book: Book 3>',
                '<Book: Book 7>',
                '<Book: Book 1>',
            ])
        self.assertQuerysetEqual(Book.objects.filter(title__startswith='Book_'),
                                 ['<Book: Book_ with underscore>'])
        b9 = Book(title='Book% with percent sign', pubdate=datetime(2005, 11, 21))
        b9.save()
        self.assertQuerysetEqual(Book.objects.filter(title__startswith='Book'),
            [
                '<Book: Book% with percent sign>',
                '<Book: Book_ with underscore>',
                '<Book: Book 5>',
                '<Book: Book 6>',
                '<Book: Book 4>',
                '<Book: Book 2>',
                '<Book: Book 3>',
                '<Book: Book 7>',
                '<Book: Book 1>',
            ])
        self.assertQuerysetEqual(Book.objects.filter(title__startswith='Book%'),
                                 ['<Book: Book% with percent sign>'])
        b10 = Book(title='Book with \\ backslash', pubdate=datetime(2005, 11, 22))
        b10.save()
        self.assertQuerysetEqual(Book.objects.filter(title__contains='\\'),
                                 ['<Book: Book with \ backslash>'])

    def test_exclude(self):
        b8 = Book.objects.create(title='Book_ with underscore', pubdate=datetime(2005, 11, 20))
        b9 = Book.objects.create(title='Book% with percent sign', pubdate=datetime(2005, 11, 21))
        b10 = Book.objects.create(title='Book with \\ backslash', pubdate=datetime(2005, 11, 22))

        # exclude() is the opposite of filter() when doing lookups:
        self.assertQuerysetEqual(
            Book.objects.filter(title__contains='Book').exclude(title__contains='with'),
            [
                '<Book: Book 5>',
                '<Book: Book 6>',
                '<Book: Book 4>',
                '<Book: Book 2>',
                '<Book: Book 3>',
                '<Book: Book 7>',
                '<Book: Book 1>',
            ])
        self.assertQuerysetEqual(Book.objects.exclude(title__startswith="Book_"),
            [
                '<Book: Book with \\ backslash>',
                '<Book: Book% with percent sign>',
                '<Book: Book 5>',
                '<Book: Book 6>',
                '<Book: Book 4>',
                '<Book: Book 2>',
                '<Book: Book 3>',
                '<Book: Book 7>',
                '<Book: Book 1>',
            ])
        self.assertQuerysetEqual(Book.objects.exclude(title="Book 7"),
            [
                '<Book: Book with \\ backslash>',
                '<Book: Book% with percent sign>',
                '<Book: Book_ with underscore>',
                '<Book: Book 5>',
                '<Book: Book 6>',
                '<Book: Book 4>',
                '<Book: Book 2>',
                '<Book: Book 3>',
                '<Book: Book 1>',
            ])

    def test_none(self):
       # none() returns a QuerySet that behaves like any other QuerySet object
        self.assertQuerysetEqual(Book.objects.none(), [])
        self.assertQuerysetEqual(
            Book.objects.none().filter(title__startswith='Book'), [])
        self.assertQuerysetEqual(
            Book.objects.filter(title__startswith='Book').none(), [])
        self.assertEqual(Book.objects.none().count(), 0)
        self.assertEqual(
            Book.objects.none().update(title="This should not take effect"), 0)
        self.assertQuerysetEqual(
            [article for article in Book.objects.none().iterator()],
            [])

    def test_in(self):
        # using __in with an empty list should return an empty query set
        self.assertQuerysetEqual(Book.objects.filter(id__in=[]), [])
        self.assertQuerysetEqual(Book.objects.exclude(id__in=[]),
            [
                '<Book: Book 5>',
                '<Book: Book 6>',
                '<Book: Book 4>',
                '<Book: Book 2>',
                '<Book: Book 3>',
                '<Book: Book 7>',
                '<Book: Book 1>',
            ])

    def test_error_messages(self):
        # Programming errors are pointed out with nice error messages
        with six.assertRaisesRegex(self, FieldError, "Cannot resolve keyword 'pubdate_year' "
             "into field. Choices are: .+"):
                Book.objects.filter(pubdate_year='2005').count()

        with self.assertRaises(FieldError, msg="Join on field 'title' not permitted. "
             "Did you misspell 'starts' for the lookup type?"):
                Book.objects.filter(title__starts='Book')

    def test_regex(self):
        # Create some articles with a bit more interesting names for testing field lookups:
        for a in Book.objects.all():
            a.delete()
        now = datetime.now()
        b1 = Book(pubdate=now, title='f')
        b1.save()
        b2 = Book(pubdate=now, title='fo')
        b2.save()
        b3 = Book(pubdate=now, title='foo')
        b3.save()
        b4 = Book(pubdate=now, title='fooo')
        b4.save()
        b5 = Book(pubdate=now, title='hey-Foo')
        b5.save()
        b6 = Book(pubdate=now, title='bar')
        b6.save()
        b7 = Book(pubdate=now, title='AbBa')
        b7.save()
        b8 = Book(pubdate=now, title='baz')
        b8.save()
        b9 = Book(pubdate=now, title='baxZ')
        b9.save()
        # zero-or-more
        self.assertQuerysetEqual(Book.objects.filter(title__regex=r'fo*'),
            ['<Book: f>', '<Book: fo>', '<Book: foo>', '<Book: fooo>'])
        self.assertQuerysetEqual(Book.objects.filter(title__iregex=r'fo*'),
            [
                '<Book: f>',
                '<Book: fo>',
                '<Book: foo>',
                '<Book: fooo>',
                '<Book: hey-Foo>',
            ])
        # one-or-more
        self.assertQuerysetEqual(Book.objects.filter(title__regex=r'fo+'),
            ['<Book: fo>', '<Book: foo>', '<Book: fooo>'])
        # wildcard
        self.assertQuerysetEqual(Book.objects.filter(title__regex=r'fooo?'),
            ['<Book: foo>', '<Book: fooo>'])
        # leading anchor
        self.assertQuerysetEqual(Book.objects.filter(title__regex=r'^b'),
            ['<Book: bar>', '<Book: baxZ>', '<Book: baz>'])
        self.assertQuerysetEqual(Book.objects.filter(title__iregex=r'^a'),
            ['<Book: AbBa>'])
        # trailing anchor
        self.assertQuerysetEqual(Book.objects.filter(title__regex=r'z$'),
            ['<Book: baz>'])
        self.assertQuerysetEqual(Book.objects.filter(title__iregex=r'z$'),
            ['<Book: baxZ>', '<Book: baz>'])
        # character sets
        self.assertQuerysetEqual(Book.objects.filter(title__regex=r'ba[rz]'),
            ['<Book: bar>', '<Book: baz>'])
        self.assertQuerysetEqual(Book.objects.filter(title__regex=r'ba.[RxZ]'),
            ['<Book: baxZ>'])
        self.assertQuerysetEqual(Book.objects.filter(title__iregex=r'ba[RxZ]'),
            ['<Book: bar>', '<Book: baxZ>', '<Book: baz>'])

        # and more articles:
        b10 = Book(pubdate=now, title='foobar')
        b10.save()
        b11 = Book(pubdate=now, title='foobaz')
        b11.save()
        b12 = Book(pubdate=now, title='ooF')
        b12.save()
        b13 = Book(pubdate=now, title='foobarbaz')
        b13.save()
        b14 = Book(pubdate=now, title='zoocarfaz')
        b14.save()
        b15 = Book(pubdate=now, title='barfoobaz')
        b15.save()
        b16 = Book(pubdate=now, title='bazbaRFOO')
        b16.save()

        # alternation
        self.assertQuerysetEqual(Book.objects.filter(title__regex=r'oo(f|b)'),
            [
                '<Book: barfoobaz>',
                '<Book: foobar>',
                '<Book: foobarbaz>',
                '<Book: foobaz>',
            ])
        self.assertQuerysetEqual(Book.objects.filter(title__iregex=r'oo(f|b)'),
            [
                '<Book: barfoobaz>',
                '<Book: foobar>',
                '<Book: foobarbaz>',
                '<Book: foobaz>',
                '<Book: ooF>',
            ])
        self.assertQuerysetEqual(Book.objects.filter(title__regex=r'^foo(f|b)'),
            ['<Book: foobar>', '<Book: foobarbaz>', '<Book: foobaz>'])

        # greedy matching
        self.assertQuerysetEqual(Book.objects.filter(title__regex=r'b.*az'),
            [
                '<Book: barfoobaz>',
                '<Book: baz>',
                '<Book: bazbaRFOO>',
                '<Book: foobarbaz>',
                '<Book: foobaz>',
            ])
        self.assertQuerysetEqual(Book.objects.filter(title__iregex=r'b.*ar'),
            [
                '<Book: bar>',
                '<Book: barfoobaz>',
                '<Book: bazbaRFOO>',
                '<Book: foobar>',
                '<Book: foobarbaz>',
            ])

    @skipUnlessDBFeature('supports_regex_backreferencing')
    def test_regex_backreferencing(self):
        # grouping and backreferences
        now = datetime.now()
        b10 = Book(pubdate=now, title='foobar')
        b10.save()
        b11 = Book(pubdate=now, title='foobaz')
        b11.save()
        b12 = Book(pubdate=now, title='ooF')
        b12.save()
        b13 = Book(pubdate=now, title='foobarbaz')
        b13.save()
        b14 = Book(pubdate=now, title='zoocarfaz')
        b14.save()
        b15 = Book(pubdate=now, title='barfoobaz')
        b15.save()
        b16 = Book(pubdate=now, title='bazbaRFOO')
        b16.save()
        self.assertQuerysetEqual(Book.objects.filter(title__regex=r'b(.).*b\1'),
            ['<Book: barfoobaz>', '<Book: bazbaRFOO>', '<Book: foobarbaz>'])

    def test_nonfield_lookups(self):
        """
        Ensure that a lookup query containing non-fields raises the proper
        exception.
        """
        with self.assertRaises(FieldError):
            Book.objects.filter(name__blahblah=99)
        with self.assertRaises(FieldError):
            Book.objects.filter(name__blahblah__exact=99)
        with self.assertRaises(FieldError):
            Book.objects.filter(blahblah=99)

    def test_lookup_collision(self):
        """
        Ensure that genuine field names don't collide with built-in lookup
        types ('year', 'gt', 'range', 'in' etc.).
        Refs #11670.
        """

        # Here we're using 'gt' as a code number for the year, e.g. 111=>2009.
        season_2009 = Season.objects.create(year=2009, gt=111)
        season_2009.games.create(home="Houston Astros", away="St. Louis Cardinals")
        season_2010 = Season.objects.create(year=2010, gt=222)
        season_2010.games.create(home="Houston Astros", away="Chicago Cubs")
        season_2010.games.create(home="Houston Astros", away="Milwaukee Brewers")
        season_2010.games.create(home="Houston Astros", away="St. Louis Cardinals")
        season_2011 = Season.objects.create(year=2011, gt=333)
        season_2011.games.create(home="Houston Astros", away="St. Louis Cardinals")
        season_2011.games.create(home="Houston Astros", away="Milwaukee Brewers")
        hunter_pence = Player.objects.create(name="Hunter Pence")
        hunter_pence.games = Game.objects.filter(season__year__in=[2009, 2010])
        pudge = Player.objects.create(name="Ivan Rodriquez")
        pudge.games = Game.objects.filter(season__year=2009)
        pedro_feliz = Player.objects.create(name="Pedro Feliz")
        pedro_feliz.games = Game.objects.filter(season__year__in=[2011])
        johnson = Player.objects.create(name="Johnson")
        johnson.games = Game.objects.filter(season__year__in=[2011])

        # Games in 2010
        self.assertEqual(Game.objects.filter(season__year=2010).count(), 3)
        self.assertEqual(Game.objects.filter(season__year__exact=2010).count(), 3)
        self.assertEqual(Game.objects.filter(season__gt=222).count(), 3)
        self.assertEqual(Game.objects.filter(season__gt__exact=222).count(), 3)

        # Games in 2011
        self.assertEqual(Game.objects.filter(season__year=2011).count(), 2)
        self.assertEqual(Game.objects.filter(season__year__exact=2011).count(), 2)
        self.assertEqual(Game.objects.filter(season__gt=333).count(), 2)
        self.assertEqual(Game.objects.filter(season__gt__exact=333).count(), 2)
        self.assertEqual(Game.objects.filter(season__year__gt=2010).count(), 2)
        self.assertEqual(Game.objects.filter(season__gt__gt=222).count(), 2)

        # Games played in 2010 and 2011
        self.assertEqual(Game.objects.filter(season__year__in=[2010, 2011]).count(), 5)
        self.assertEqual(Game.objects.filter(season__year__gt=2009).count(), 5)
        self.assertEqual(Game.objects.filter(season__gt__in=[222, 333]).count(), 5)
        self.assertEqual(Game.objects.filter(season__gt__gt=111).count(), 5)

        # Players who played in 2009
        self.assertEqual(Player.objects.filter(games__season__year=2009).distinct().count(), 2)
        self.assertEqual(Player.objects.filter(games__season__year__exact=2009).distinct().count(), 2)
        self.assertEqual(Player.objects.filter(games__season__gt=111).distinct().count(), 2)
        self.assertEqual(Player.objects.filter(games__season__gt__exact=111).distinct().count(), 2)

        # Players who played in 2010
        self.assertEqual(Player.objects.filter(games__season__year=2010).distinct().count(), 1)
        self.assertEqual(Player.objects.filter(games__season__year__exact=2010).distinct().count(), 1)
        self.assertEqual(Player.objects.filter(games__season__gt=222).distinct().count(), 1)
        self.assertEqual(Player.objects.filter(games__season__gt__exact=222).distinct().count(), 1)

        # Players who played in 2011
        self.assertEqual(Player.objects.filter(games__season__year=2011).distinct().count(), 2)
        self.assertEqual(Player.objects.filter(games__season__year__exact=2011).distinct().count(), 2)
        self.assertEqual(Player.objects.filter(games__season__gt=333).distinct().count(), 2)
        self.assertEqual(Player.objects.filter(games__season__year__gt=2010).distinct().count(), 2)
        self.assertEqual(Player.objects.filter(games__season__gt__gt=222).distinct().count(), 2)
