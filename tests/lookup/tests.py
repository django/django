import collections
from datetime import datetime
from math import ceil
from operator import attrgetter

from django.core.exceptions import FieldError
from django.db import connection
from django.test import TestCase, skipUnlessDBFeature

from .models import Article, Author, Game, Player, Season, Tag


class LookupTests(TestCase):

    def setUp(self):
        # Create a few Authors.
        self.au1 = Author.objects.create(name='Author 1')
        self.au2 = Author.objects.create(name='Author 2')
        # Create a few Articles.
        self.a1 = Article.objects.create(
            headline='Article 1',
            pub_date=datetime(2005, 7, 26),
            author=self.au1,
            slug='a1',
        )
        self.a2 = Article.objects.create(
            headline='Article 2',
            pub_date=datetime(2005, 7, 27),
            author=self.au1,
            slug='a2',
        )
        self.a3 = Article.objects.create(
            headline='Article 3',
            pub_date=datetime(2005, 7, 27),
            author=self.au1,
            slug='a3',
        )
        self.a4 = Article.objects.create(
            headline='Article 4',
            pub_date=datetime(2005, 7, 28),
            author=self.au1,
            slug='a4',
        )
        self.a5 = Article.objects.create(
            headline='Article 5',
            pub_date=datetime(2005, 8, 1, 9, 0),
            author=self.au2,
            slug='a5',
        )
        self.a6 = Article.objects.create(
            headline='Article 6',
            pub_date=datetime(2005, 8, 1, 8, 0),
            author=self.au2,
            slug='a6',
        )
        self.a7 = Article.objects.create(
            headline='Article 7',
            pub_date=datetime(2005, 7, 27),
            author=self.au2,
            slug='a7',
        )
        # Create a few Tags.
        self.t1 = Tag.objects.create(name='Tag 1')
        self.t1.articles.add(self.a1, self.a2, self.a3)
        self.t2 = Tag.objects.create(name='Tag 2')
        self.t2.articles.add(self.a3, self.a4, self.a5)
        self.t3 = Tag.objects.create(name='Tag 3')
        self.t3.articles.add(self.a5, self.a6, self.a7)

    def test_exists(self):
        # We can use .exists() to check that there are some
        self.assertTrue(Article.objects.exists())
        for a in Article.objects.all():
            a.delete()
        # There should be none now!
        self.assertFalse(Article.objects.exists())

    def test_lookup_int_as_str(self):
        # Integer value can be queried using string
        self.assertQuerysetEqual(Article.objects.filter(id__iexact=str(self.a1.id)),
                                 ['<Article: Article 1>'])

    @skipUnlessDBFeature('supports_date_lookup_using_string')
    def test_lookup_date_as_str(self):
        # A date lookup can be performed using a string search
        self.assertQuerysetEqual(
            Article.objects.filter(pub_date__startswith='2005'),
            [
                '<Article: Article 5>',
                '<Article: Article 6>',
                '<Article: Article 4>',
                '<Article: Article 2>',
                '<Article: Article 3>',
                '<Article: Article 7>',
                '<Article: Article 1>',
            ]
        )

    def test_iterator(self):
        # Each QuerySet gets iterator(), which is a generator that "lazily"
        # returns results using database-level iteration.
        self.assertIsInstance(Article.objects.iterator(), collections.Iterator)

        self.assertQuerysetEqual(
            Article.objects.iterator(),
            [
                'Article 5',
                'Article 6',
                'Article 4',
                'Article 2',
                'Article 3',
                'Article 7',
                'Article 1',
            ],
            transform=attrgetter('headline')
        )
        # iterator() can be used on any QuerySet.
        self.assertQuerysetEqual(
            Article.objects.filter(headline__endswith='4').iterator(),
            ['Article 4'],
            transform=attrgetter('headline'))

    def test_count(self):
        # count() returns the number of objects matching search criteria.
        self.assertEqual(Article.objects.count(), 7)
        self.assertEqual(Article.objects.filter(pub_date__exact=datetime(2005, 7, 27)).count(), 3)
        self.assertEqual(Article.objects.filter(headline__startswith='Blah blah').count(), 0)

        # count() should respect sliced query sets.
        articles = Article.objects.all()
        self.assertEqual(articles.count(), 7)
        self.assertEqual(articles[:4].count(), 4)
        self.assertEqual(articles[1:100].count(), 6)
        self.assertEqual(articles[10:100].count(), 0)

        # Date and date/time lookups can also be done with strings.
        self.assertEqual(Article.objects.filter(pub_date__exact='2005-07-27 00:00:00').count(), 3)

    def test_in_bulk(self):
        # in_bulk() takes a list of IDs and returns a dictionary mapping IDs to objects.
        arts = Article.objects.in_bulk([self.a1.id, self.a2.id])
        self.assertEqual(arts[self.a1.id], self.a1)
        self.assertEqual(arts[self.a2.id], self.a2)
        self.assertEqual(
            Article.objects.in_bulk(),
            {
                self.a1.id: self.a1,
                self.a2.id: self.a2,
                self.a3.id: self.a3,
                self.a4.id: self.a4,
                self.a5.id: self.a5,
                self.a6.id: self.a6,
                self.a7.id: self.a7,
            }
        )
        self.assertEqual(Article.objects.in_bulk([self.a3.id]), {self.a3.id: self.a3})
        self.assertEqual(Article.objects.in_bulk({self.a3.id}), {self.a3.id: self.a3})
        self.assertEqual(Article.objects.in_bulk(frozenset([self.a3.id])), {self.a3.id: self.a3})
        self.assertEqual(Article.objects.in_bulk((self.a3.id,)), {self.a3.id: self.a3})
        self.assertEqual(Article.objects.in_bulk([1000]), {})
        self.assertEqual(Article.objects.in_bulk([]), {})
        self.assertEqual(Article.objects.in_bulk(iter([self.a1.id])), {self.a1.id: self.a1})
        self.assertEqual(Article.objects.in_bulk(iter([])), {})
        with self.assertRaises(TypeError):
            Article.objects.in_bulk(headline__startswith='Blah')

    def test_in_bulk_lots_of_ids(self):
        test_range = 2000
        max_query_params = connection.features.max_query_params
        expected_num_queries = ceil(test_range / max_query_params) if max_query_params else 1
        Author.objects.bulk_create([Author() for i in range(test_range - Author.objects.count())])
        authors = {author.pk: author for author in Author.objects.all()}
        with self.assertNumQueries(expected_num_queries):
            self.assertEqual(Author.objects.in_bulk(authors), authors)

    def test_in_bulk_with_field(self):
        self.assertEqual(
            Article.objects.in_bulk([self.a1.slug, self.a2.slug, self.a3.slug], field_name='slug'),
            {
                self.a1.slug: self.a1,
                self.a2.slug: self.a2,
                self.a3.slug: self.a3,
            }
        )

    def test_in_bulk_non_unique_field(self):
        msg = "in_bulk()'s field_name must be a unique field but 'author' isn't."
        with self.assertRaisesMessage(ValueError, msg):
            Article.objects.in_bulk([self.au1], field_name='author')

    def test_values(self):
        # values() returns a list of dictionaries instead of object instances --
        # and you can specify which fields you want to retrieve.
        self.assertSequenceEqual(
            Article.objects.values('headline'),
            [
                {'headline': 'Article 5'},
                {'headline': 'Article 6'},
                {'headline': 'Article 4'},
                {'headline': 'Article 2'},
                {'headline': 'Article 3'},
                {'headline': 'Article 7'},
                {'headline': 'Article 1'},
            ],
        )
        self.assertSequenceEqual(
            Article.objects.filter(pub_date__exact=datetime(2005, 7, 27)).values('id'),
            [{'id': self.a2.id}, {'id': self.a3.id}, {'id': self.a7.id}],
        )
        self.assertSequenceEqual(
            Article.objects.values('id', 'headline'),
            [
                {'id': self.a5.id, 'headline': 'Article 5'},
                {'id': self.a6.id, 'headline': 'Article 6'},
                {'id': self.a4.id, 'headline': 'Article 4'},
                {'id': self.a2.id, 'headline': 'Article 2'},
                {'id': self.a3.id, 'headline': 'Article 3'},
                {'id': self.a7.id, 'headline': 'Article 7'},
                {'id': self.a1.id, 'headline': 'Article 1'},
            ],
        )
        # You can use values() with iterator() for memory savings,
        # because iterator() uses database-level iteration.
        self.assertSequenceEqual(
            list(Article.objects.values('id', 'headline').iterator()),
            [
                {'headline': 'Article 5', 'id': self.a5.id},
                {'headline': 'Article 6', 'id': self.a6.id},
                {'headline': 'Article 4', 'id': self.a4.id},
                {'headline': 'Article 2', 'id': self.a2.id},
                {'headline': 'Article 3', 'id': self.a3.id},
                {'headline': 'Article 7', 'id': self.a7.id},
                {'headline': 'Article 1', 'id': self.a1.id},
            ],
        )
        # The values() method works with "extra" fields specified in extra(select).
        self.assertSequenceEqual(
            Article.objects.extra(select={'id_plus_one': 'id + 1'}).values('id', 'id_plus_one'),
            [
                {'id': self.a5.id, 'id_plus_one': self.a5.id + 1},
                {'id': self.a6.id, 'id_plus_one': self.a6.id + 1},
                {'id': self.a4.id, 'id_plus_one': self.a4.id + 1},
                {'id': self.a2.id, 'id_plus_one': self.a2.id + 1},
                {'id': self.a3.id, 'id_plus_one': self.a3.id + 1},
                {'id': self.a7.id, 'id_plus_one': self.a7.id + 1},
                {'id': self.a1.id, 'id_plus_one': self.a1.id + 1},
            ],
        )
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
        self.assertSequenceEqual(
            Article.objects.filter(id=self.a1.id).extra(select=data).values(*data),
            [{
                'id_plus_one': self.a1.id + 1,
                'id_plus_two': self.a1.id + 2,
                'id_plus_three': self.a1.id + 3,
                'id_plus_four': self.a1.id + 4,
                'id_plus_five': self.a1.id + 5,
                'id_plus_six': self.a1.id + 6,
                'id_plus_seven': self.a1.id + 7,
                'id_plus_eight': self.a1.id + 8,
            }],
        )
        # You can specify fields from forward and reverse relations, just like filter().
        self.assertSequenceEqual(
            Article.objects.values('headline', 'author__name'),
            [
                {'headline': self.a5.headline, 'author__name': self.au2.name},
                {'headline': self.a6.headline, 'author__name': self.au2.name},
                {'headline': self.a4.headline, 'author__name': self.au1.name},
                {'headline': self.a2.headline, 'author__name': self.au1.name},
                {'headline': self.a3.headline, 'author__name': self.au1.name},
                {'headline': self.a7.headline, 'author__name': self.au2.name},
                {'headline': self.a1.headline, 'author__name': self.au1.name},
            ],
        )
        self.assertSequenceEqual(
            Author.objects.values('name', 'article__headline').order_by('name', 'article__headline'),
            [
                {'name': self.au1.name, 'article__headline': self.a1.headline},
                {'name': self.au1.name, 'article__headline': self.a2.headline},
                {'name': self.au1.name, 'article__headline': self.a3.headline},
                {'name': self.au1.name, 'article__headline': self.a4.headline},
                {'name': self.au2.name, 'article__headline': self.a5.headline},
                {'name': self.au2.name, 'article__headline': self.a6.headline},
                {'name': self.au2.name, 'article__headline': self.a7.headline},
            ],
        )
        self.assertSequenceEqual(
            (
                Author.objects
                .values('name', 'article__headline', 'article__tag__name')
                .order_by('name', 'article__headline', 'article__tag__name')
            ),
            [
                {'name': self.au1.name, 'article__headline': self.a1.headline, 'article__tag__name': self.t1.name},
                {'name': self.au1.name, 'article__headline': self.a2.headline, 'article__tag__name': self.t1.name},
                {'name': self.au1.name, 'article__headline': self.a3.headline, 'article__tag__name': self.t1.name},
                {'name': self.au1.name, 'article__headline': self.a3.headline, 'article__tag__name': self.t2.name},
                {'name': self.au1.name, 'article__headline': self.a4.headline, 'article__tag__name': self.t2.name},
                {'name': self.au2.name, 'article__headline': self.a5.headline, 'article__tag__name': self.t2.name},
                {'name': self.au2.name, 'article__headline': self.a5.headline, 'article__tag__name': self.t3.name},
                {'name': self.au2.name, 'article__headline': self.a6.headline, 'article__tag__name': self.t3.name},
                {'name': self.au2.name, 'article__headline': self.a7.headline, 'article__tag__name': self.t3.name},
            ],
        )
        # However, an exception FieldDoesNotExist will be thrown if you specify
        # a nonexistent field name in values() (a field that is neither in the
        # model nor in extra(select)).
        msg = (
            "Cannot resolve keyword 'id_plus_two' into field. Choices are: "
            "author, author_id, headline, id, id_plus_one, pub_date, slug, tag"
        )
        with self.assertRaisesMessage(FieldError, msg):
            Article.objects.extra(select={'id_plus_one': 'id + 1'}).values('id', 'id_plus_two')
        # If you don't specify field names to values(), all are returned.
        self.assertSequenceEqual(
            Article.objects.filter(id=self.a5.id).values(),
            [{
                'id': self.a5.id,
                'author_id': self.au2.id,
                'headline': 'Article 5',
                'pub_date': datetime(2005, 8, 1, 9, 0),
                'slug': 'a5',
            }],
        )

    def test_values_list(self):
        # values_list() is similar to values(), except that the results are
        # returned as a list of tuples, rather than a list of dictionaries.
        # Within each tuple, the order of the elements is the same as the order
        # of fields in the values_list() call.
        self.assertSequenceEqual(
            Article.objects.values_list('headline'),
            [
                ('Article 5',),
                ('Article 6',),
                ('Article 4',),
                ('Article 2',),
                ('Article 3',),
                ('Article 7',),
                ('Article 1',),
            ],
        )
        self.assertSequenceEqual(
            Article.objects.values_list('id').order_by('id'),
            [(self.a1.id,), (self.a2.id,), (self.a3.id,), (self.a4.id,), (self.a5.id,), (self.a6.id,), (self.a7.id,)],
        )
        self.assertSequenceEqual(
            Article.objects.values_list('id', flat=True).order_by('id'),
            [self.a1.id, self.a2.id, self.a3.id, self.a4.id, self.a5.id, self.a6.id, self.a7.id],
        )
        self.assertSequenceEqual(
            Article.objects.extra(select={'id_plus_one': 'id+1'}).order_by('id').values_list('id'),
            [(self.a1.id,), (self.a2.id,), (self.a3.id,), (self.a4.id,), (self.a5.id,), (self.a6.id,), (self.a7.id,)],
        )
        self.assertSequenceEqual(
            Article.objects.extra(select={'id_plus_one': 'id+1'}).order_by('id').values_list('id_plus_one', 'id'),
            [
                (self.a1.id + 1, self.a1.id),
                (self.a2.id + 1, self.a2.id),
                (self.a3.id + 1, self.a3.id),
                (self.a4.id + 1, self.a4.id),
                (self.a5.id + 1, self.a5.id),
                (self.a6.id + 1, self.a6.id),
                (self.a7.id + 1, self.a7.id)
            ],
        )
        self.assertSequenceEqual(
            Article.objects.extra(select={'id_plus_one': 'id+1'}).order_by('id').values_list('id', 'id_plus_one'),
            [
                (self.a1.id, self.a1.id + 1),
                (self.a2.id, self.a2.id + 1),
                (self.a3.id, self.a3.id + 1),
                (self.a4.id, self.a4.id + 1),
                (self.a5.id, self.a5.id + 1),
                (self.a6.id, self.a6.id + 1),
                (self.a7.id, self.a7.id + 1)
            ],
        )
        args = ('name', 'article__headline', 'article__tag__name')
        self.assertSequenceEqual(
            Author.objects.values_list(*args).order_by(*args),
            [
                (self.au1.name, self.a1.headline, self.t1.name),
                (self.au1.name, self.a2.headline, self.t1.name),
                (self.au1.name, self.a3.headline, self.t1.name),
                (self.au1.name, self.a3.headline, self.t2.name),
                (self.au1.name, self.a4.headline, self.t2.name),
                (self.au2.name, self.a5.headline, self.t2.name),
                (self.au2.name, self.a5.headline, self.t3.name),
                (self.au2.name, self.a6.headline, self.t3.name),
                (self.au2.name, self.a7.headline, self.t3.name),
            ],
        )
        with self.assertRaises(TypeError):
            Article.objects.values_list('id', 'headline', flat=True)

    def test_get_next_previous_by(self):
        # Every DateField and DateTimeField creates get_next_by_FOO() and
        # get_previous_by_FOO() methods. In the case of identical date values,
        # these methods will use the ID as a fallback check. This guarantees
        # that no records are skipped or duplicated.
        self.assertEqual(repr(self.a1.get_next_by_pub_date()), '<Article: Article 2>')
        self.assertEqual(repr(self.a2.get_next_by_pub_date()), '<Article: Article 3>')
        self.assertEqual(repr(self.a2.get_next_by_pub_date(headline__endswith='6')), '<Article: Article 6>')
        self.assertEqual(repr(self.a3.get_next_by_pub_date()), '<Article: Article 7>')
        self.assertEqual(repr(self.a4.get_next_by_pub_date()), '<Article: Article 6>')
        with self.assertRaises(Article.DoesNotExist):
            self.a5.get_next_by_pub_date()
        self.assertEqual(repr(self.a6.get_next_by_pub_date()), '<Article: Article 5>')
        self.assertEqual(repr(self.a7.get_next_by_pub_date()), '<Article: Article 4>')

        self.assertEqual(repr(self.a7.get_previous_by_pub_date()), '<Article: Article 3>')
        self.assertEqual(repr(self.a6.get_previous_by_pub_date()), '<Article: Article 4>')
        self.assertEqual(repr(self.a5.get_previous_by_pub_date()), '<Article: Article 6>')
        self.assertEqual(repr(self.a4.get_previous_by_pub_date()), '<Article: Article 7>')
        self.assertEqual(repr(self.a3.get_previous_by_pub_date()), '<Article: Article 2>')
        self.assertEqual(repr(self.a2.get_previous_by_pub_date()), '<Article: Article 1>')

    def test_escaping(self):
        # Underscores, percent signs and backslashes have special meaning in the
        # underlying SQL code, but Django handles the quoting of them automatically.
        Article.objects.create(headline='Article_ with underscore', pub_date=datetime(2005, 11, 20))

        self.assertQuerysetEqual(
            Article.objects.filter(headline__startswith='Article'),
            [
                '<Article: Article_ with underscore>',
                '<Article: Article 5>',
                '<Article: Article 6>',
                '<Article: Article 4>',
                '<Article: Article 2>',
                '<Article: Article 3>',
                '<Article: Article 7>',
                '<Article: Article 1>',
            ]
        )
        self.assertQuerysetEqual(
            Article.objects.filter(headline__startswith='Article_'),
            ['<Article: Article_ with underscore>']
        )
        Article.objects.create(headline='Article% with percent sign', pub_date=datetime(2005, 11, 21))
        self.assertQuerysetEqual(
            Article.objects.filter(headline__startswith='Article'),
            [
                '<Article: Article% with percent sign>',
                '<Article: Article_ with underscore>',
                '<Article: Article 5>',
                '<Article: Article 6>',
                '<Article: Article 4>',
                '<Article: Article 2>',
                '<Article: Article 3>',
                '<Article: Article 7>',
                '<Article: Article 1>',
            ]
        )
        self.assertQuerysetEqual(
            Article.objects.filter(headline__startswith='Article%'),
            ['<Article: Article% with percent sign>']
        )
        Article.objects.create(headline='Article with \\ backslash', pub_date=datetime(2005, 11, 22))
        self.assertQuerysetEqual(
            Article.objects.filter(headline__contains='\\'),
            [r'<Article: Article with \ backslash>']
        )

    def test_exclude(self):
        Article.objects.create(headline='Article_ with underscore', pub_date=datetime(2005, 11, 20))
        Article.objects.create(headline='Article% with percent sign', pub_date=datetime(2005, 11, 21))
        Article.objects.create(headline='Article with \\ backslash', pub_date=datetime(2005, 11, 22))

        # exclude() is the opposite of filter() when doing lookups:
        self.assertQuerysetEqual(
            Article.objects.filter(headline__contains='Article').exclude(headline__contains='with'),
            [
                '<Article: Article 5>',
                '<Article: Article 6>',
                '<Article: Article 4>',
                '<Article: Article 2>',
                '<Article: Article 3>',
                '<Article: Article 7>',
                '<Article: Article 1>',
            ]
        )
        self.assertQuerysetEqual(
            Article.objects.exclude(headline__startswith="Article_"),
            [
                '<Article: Article with \\ backslash>',
                '<Article: Article% with percent sign>',
                '<Article: Article 5>',
                '<Article: Article 6>',
                '<Article: Article 4>',
                '<Article: Article 2>',
                '<Article: Article 3>',
                '<Article: Article 7>',
                '<Article: Article 1>',
            ]
        )
        self.assertQuerysetEqual(
            Article.objects.exclude(headline="Article 7"),
            [
                '<Article: Article with \\ backslash>',
                '<Article: Article% with percent sign>',
                '<Article: Article_ with underscore>',
                '<Article: Article 5>',
                '<Article: Article 6>',
                '<Article: Article 4>',
                '<Article: Article 2>',
                '<Article: Article 3>',
                '<Article: Article 1>',
            ]
        )

    def test_none(self):
        # none() returns a QuerySet that behaves like any other QuerySet object
        self.assertQuerysetEqual(Article.objects.none(), [])
        self.assertQuerysetEqual(Article.objects.none().filter(headline__startswith='Article'), [])
        self.assertQuerysetEqual(Article.objects.filter(headline__startswith='Article').none(), [])
        self.assertEqual(Article.objects.none().count(), 0)
        self.assertEqual(Article.objects.none().update(headline="This should not take effect"), 0)
        self.assertQuerysetEqual([article for article in Article.objects.none().iterator()], [])

    def test_in(self):
        # using __in with an empty list should return an empty query set
        self.assertQuerysetEqual(Article.objects.filter(id__in=[]), [])
        self.assertQuerysetEqual(
            Article.objects.exclude(id__in=[]),
            [
                '<Article: Article 5>',
                '<Article: Article 6>',
                '<Article: Article 4>',
                '<Article: Article 2>',
                '<Article: Article 3>',
                '<Article: Article 7>',
                '<Article: Article 1>',
            ]
        )

    def test_in_different_database(self):
        with self.assertRaisesMessage(
            ValueError,
            "Subqueries aren't allowed across different databases. Force the "
            "inner query to be evaluated using `list(inner_query)`."
        ):
            list(Article.objects.filter(id__in=Article.objects.using('other').all()))

    def test_error_messages(self):
        # Programming errors are pointed out with nice error messages
        with self.assertRaisesMessage(
            FieldError,
            "Cannot resolve keyword 'pub_date_year' into field. Choices are: "
            "author, author_id, headline, id, pub_date, slug, tag"
        ):
            Article.objects.filter(pub_date_year='2005').count()

        with self.assertRaisesMessage(
            FieldError,
            "Unsupported lookup 'starts' for CharField or join on the field "
            "not permitted."
        ):
            Article.objects.filter(headline__starts='Article')

    def test_relation_nested_lookup_error(self):
        # An invalid nested lookup on a related field raises a useful error.
        msg = 'Related Field got invalid lookup: editor'
        with self.assertRaisesMessage(FieldError, msg):
            Article.objects.filter(author__editor__name='James')
        msg = 'Related Field got invalid lookup: foo'
        with self.assertRaisesMessage(FieldError, msg):
            Tag.objects.filter(articles__foo='bar')

    def test_regex(self):
        # Create some articles with a bit more interesting headlines for testing field lookups:
        for a in Article.objects.all():
            a.delete()
        now = datetime.now()
        Article.objects.create(pub_date=now, headline='f')
        Article.objects.create(pub_date=now, headline='fo')
        Article.objects.create(pub_date=now, headline='foo')
        Article.objects.create(pub_date=now, headline='fooo')
        Article.objects.create(pub_date=now, headline='hey-Foo')
        Article.objects.create(pub_date=now, headline='bar')
        Article.objects.create(pub_date=now, headline='AbBa')
        Article.objects.create(pub_date=now, headline='baz')
        Article.objects.create(pub_date=now, headline='baxZ')
        # zero-or-more
        self.assertQuerysetEqual(
            Article.objects.filter(headline__regex=r'fo*'),
            ['<Article: f>', '<Article: fo>', '<Article: foo>', '<Article: fooo>']
        )
        self.assertQuerysetEqual(
            Article.objects.filter(headline__iregex=r'fo*'),
            [
                '<Article: f>',
                '<Article: fo>',
                '<Article: foo>',
                '<Article: fooo>',
                '<Article: hey-Foo>',
            ]
        )
        # one-or-more
        self.assertQuerysetEqual(
            Article.objects.filter(headline__regex=r'fo+'),
            ['<Article: fo>', '<Article: foo>', '<Article: fooo>']
        )
        # wildcard
        self.assertQuerysetEqual(
            Article.objects.filter(headline__regex=r'fooo?'),
            ['<Article: foo>', '<Article: fooo>']
        )
        # leading anchor
        self.assertQuerysetEqual(
            Article.objects.filter(headline__regex=r'^b'),
            ['<Article: bar>', '<Article: baxZ>', '<Article: baz>']
        )
        self.assertQuerysetEqual(Article.objects.filter(headline__iregex=r'^a'), ['<Article: AbBa>'])
        # trailing anchor
        self.assertQuerysetEqual(Article.objects.filter(headline__regex=r'z$'), ['<Article: baz>'])
        self.assertQuerysetEqual(
            Article.objects.filter(headline__iregex=r'z$'),
            ['<Article: baxZ>', '<Article: baz>']
        )
        # character sets
        self.assertQuerysetEqual(
            Article.objects.filter(headline__regex=r'ba[rz]'),
            ['<Article: bar>', '<Article: baz>']
        )
        self.assertQuerysetEqual(Article.objects.filter(headline__regex=r'ba.[RxZ]'), ['<Article: baxZ>'])
        self.assertQuerysetEqual(
            Article.objects.filter(headline__iregex=r'ba[RxZ]'),
            ['<Article: bar>', '<Article: baxZ>', '<Article: baz>']
        )

        # and more articles:
        Article.objects.create(pub_date=now, headline='foobar')
        Article.objects.create(pub_date=now, headline='foobaz')
        Article.objects.create(pub_date=now, headline='ooF')
        Article.objects.create(pub_date=now, headline='foobarbaz')
        Article.objects.create(pub_date=now, headline='zoocarfaz')
        Article.objects.create(pub_date=now, headline='barfoobaz')
        Article.objects.create(pub_date=now, headline='bazbaRFOO')

        # alternation
        self.assertQuerysetEqual(
            Article.objects.filter(headline__regex=r'oo(f|b)'),
            [
                '<Article: barfoobaz>',
                '<Article: foobar>',
                '<Article: foobarbaz>',
                '<Article: foobaz>',
            ]
        )
        self.assertQuerysetEqual(
            Article.objects.filter(headline__iregex=r'oo(f|b)'),
            [
                '<Article: barfoobaz>',
                '<Article: foobar>',
                '<Article: foobarbaz>',
                '<Article: foobaz>',
                '<Article: ooF>',
            ]
        )
        self.assertQuerysetEqual(
            Article.objects.filter(headline__regex=r'^foo(f|b)'),
            ['<Article: foobar>', '<Article: foobarbaz>', '<Article: foobaz>']
        )

        # greedy matching
        self.assertQuerysetEqual(
            Article.objects.filter(headline__regex=r'b.*az'),
            [
                '<Article: barfoobaz>',
                '<Article: baz>',
                '<Article: bazbaRFOO>',
                '<Article: foobarbaz>',
                '<Article: foobaz>',
            ]
        )
        self.assertQuerysetEqual(
            Article.objects.filter(headline__iregex=r'b.*ar'),
            [
                '<Article: bar>',
                '<Article: barfoobaz>',
                '<Article: bazbaRFOO>',
                '<Article: foobar>',
                '<Article: foobarbaz>',
            ]
        )

    @skipUnlessDBFeature('supports_regex_backreferencing')
    def test_regex_backreferencing(self):
        # grouping and backreferences
        now = datetime.now()
        Article.objects.create(pub_date=now, headline='foobar')
        Article.objects.create(pub_date=now, headline='foobaz')
        Article.objects.create(pub_date=now, headline='ooF')
        Article.objects.create(pub_date=now, headline='foobarbaz')
        Article.objects.create(pub_date=now, headline='zoocarfaz')
        Article.objects.create(pub_date=now, headline='barfoobaz')
        Article.objects.create(pub_date=now, headline='bazbaRFOO')
        self.assertQuerysetEqual(
            Article.objects.filter(headline__regex=r'b(.).*b\1'),
            ['<Article: barfoobaz>', '<Article: bazbaRFOO>', '<Article: foobarbaz>']
        )

    def test_regex_null(self):
        """
        A regex lookup does not fail on null/None values
        """
        Season.objects.create(year=2012, gt=None)
        self.assertQuerysetEqual(Season.objects.filter(gt__regex=r'^$'), [])

    def test_regex_non_string(self):
        """
        A regex lookup does not fail on non-string fields
        """
        Season.objects.create(year=2013, gt=444)
        self.assertQuerysetEqual(Season.objects.filter(gt__regex=r'^444$'), ['<Season: 2013>'])

    def test_regex_non_ascii(self):
        """
        A regex lookup does not trip on non-ASCII characters.
        """
        Player.objects.create(name='\u2660')
        Player.objects.get(name__regex='\u2660')

    def test_nonfield_lookups(self):
        """
        A lookup query containing non-fields raises the proper exception.
        """
        msg = "Unsupported lookup 'blahblah' for CharField or join on the field not permitted."
        with self.assertRaisesMessage(FieldError, msg):
            Article.objects.filter(headline__blahblah=99)
        with self.assertRaisesMessage(FieldError, msg):
            Article.objects.filter(headline__blahblah__exact=99)
        msg = (
            "Cannot resolve keyword 'blahblah' into field. Choices are: "
            "author, author_id, headline, id, pub_date, slug, tag"
        )
        with self.assertRaisesMessage(FieldError, msg):
            Article.objects.filter(blahblah=99)

    def test_lookup_collision(self):
        """
        Genuine field names don't collide with built-in lookup types
        ('year', 'gt', 'range', 'in' etc.) (#11670).
        """
        # 'gt' is used as a code number for the year, e.g. 111=>2009.
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
        hunter_pence.games.set(Game.objects.filter(season__year__in=[2009, 2010]))
        pudge = Player.objects.create(name="Ivan Rodriquez")
        pudge.games.set(Game.objects.filter(season__year=2009))
        pedro_feliz = Player.objects.create(name="Pedro Feliz")
        pedro_feliz.games.set(Game.objects.filter(season__year__in=[2011]))
        johnson = Player.objects.create(name="Johnson")
        johnson.games.set(Game.objects.filter(season__year__in=[2011]))

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

    def test_chain_date_time_lookups(self):
        self.assertQuerysetEqual(
            Article.objects.filter(pub_date__month__gt=7),
            ['<Article: Article 5>', '<Article: Article 6>'],
            ordered=False
        )
        self.assertQuerysetEqual(
            Article.objects.filter(pub_date__day__gte=27),
            ['<Article: Article 2>', '<Article: Article 3>',
             '<Article: Article 4>', '<Article: Article 7>'],
            ordered=False
        )
        self.assertQuerysetEqual(
            Article.objects.filter(pub_date__hour__lt=8),
            ['<Article: Article 1>', '<Article: Article 2>',
             '<Article: Article 3>', '<Article: Article 4>',
             '<Article: Article 7>'],
            ordered=False
        )
        self.assertQuerysetEqual(
            Article.objects.filter(pub_date__minute__lte=0),
            ['<Article: Article 1>', '<Article: Article 2>',
             '<Article: Article 3>', '<Article: Article 4>',
             '<Article: Article 5>', '<Article: Article 6>',
             '<Article: Article 7>'],
            ordered=False
        )

    def test_exact_none_transform(self):
        """Transforms are used for __exact=None."""
        Season.objects.create(year=1, nulled_text_field='not null')
        self.assertFalse(Season.objects.filter(nulled_text_field__isnull=True))
        self.assertTrue(Season.objects.filter(nulled_text_field__nulled__isnull=True))
        self.assertTrue(Season.objects.filter(nulled_text_field__nulled__exact=None))
        self.assertTrue(Season.objects.filter(nulled_text_field__nulled=None))

    def test_exact_sliced_queryset_limit_one(self):
        self.assertCountEqual(
            Article.objects.filter(author=Author.objects.all()[:1]),
            [self.a1, self.a2, self.a3, self.a4]
        )

    def test_exact_sliced_queryset_limit_one_offset(self):
        self.assertCountEqual(
            Article.objects.filter(author=Author.objects.all()[1:2]),
            [self.a5, self.a6, self.a7]
        )

    def test_exact_sliced_queryset_not_limited_to_one(self):
        msg = (
            'The QuerySet value for an exact lookup must be limited to one '
            'result using slicing.'
        )
        with self.assertRaisesMessage(ValueError, msg):
            list(Article.objects.filter(author=Author.objects.all()[:2]))
        with self.assertRaisesMessage(ValueError, msg):
            list(Article.objects.filter(author=Author.objects.all()[1:]))

    def test_custom_field_none_rhs(self):
        """
        __exact=value is transformed to __isnull=True if Field.get_prep_value()
        converts value to None.
        """
        season = Season.objects.create(year=2012, nulled_text_field=None)
        self.assertTrue(Season.objects.filter(pk=season.pk, nulled_text_field__isnull=True))
        self.assertTrue(Season.objects.filter(pk=season.pk, nulled_text_field=''))
