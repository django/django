from __future__ import absolute_import, unicode_literals

from datetime import datetime
import threading

from django.core.exceptions import ObjectDoesNotExist, MultipleObjectsReturned
from django.db import connections, DEFAULT_DB_ALIAS
from django.db import DatabaseError
from django.db.models.fields import Field, FieldDoesNotExist
from django.db.models.query import QuerySet, EmptyQuerySet, ValuesListQuerySet
from django.test import TestCase, TransactionTestCase, skipIfDBFeature, skipUnlessDBFeature
from django.utils import six
from django.utils.translation import ugettext_lazy

from .models import Article, SelfRef, ArticleSelectOnSave


class ModelTest(TestCase):

    def test_lookup(self):
        # No articles are in the system yet.
        self.assertQuerysetEqual(Article.objects.all(), [])

        # Create an Article.
        a = Article(
            id=None,
            headline='Area man programs in Python',
            pub_date=datetime(2005, 7, 28),
        )

        # Save it into the database. You have to call save() explicitly.
        a.save()

        # Now it has an ID.
        self.assertTrue(a.id != None)

        # Models have a pk property that is an alias for the primary key
        # attribute (by default, the 'id' attribute).
        self.assertEqual(a.pk, a.id)

        # Access database columns via Python attributes.
        self.assertEqual(a.headline, 'Area man programs in Python')
        self.assertEqual(a.pub_date, datetime(2005, 7, 28, 0, 0))

        # Change values by changing the attributes, then calling save().
        a.headline = 'Area woman programs in Python'
        a.save()

        # Article.objects.all() returns all the articles in the database.
        self.assertQuerysetEqual(Article.objects.all(),
            ['<Article: Area woman programs in Python>'])

        # Django provides a rich database lookup API.
        self.assertEqual(Article.objects.get(id__exact=a.id), a)
        self.assertEqual(Article.objects.get(headline__startswith='Area woman'), a)
        self.assertEqual(Article.objects.get(pub_date__year=2005), a)
        self.assertEqual(Article.objects.get(pub_date__year=2005, pub_date__month=7), a)
        self.assertEqual(Article.objects.get(pub_date__year=2005, pub_date__month=7, pub_date__day=28), a)
        self.assertEqual(Article.objects.get(pub_date__week_day=5), a)

        # The "__exact" lookup type can be omitted, as a shortcut.
        self.assertEqual(Article.objects.get(id=a.id), a)
        self.assertEqual(Article.objects.get(headline='Area woman programs in Python'), a)

        self.assertQuerysetEqual(
            Article.objects.filter(pub_date__year=2005),
            ['<Article: Area woman programs in Python>'],
        )
        self.assertQuerysetEqual(
            Article.objects.filter(pub_date__year=2004),
            [],
        )
        self.assertQuerysetEqual(
            Article.objects.filter(pub_date__year=2005, pub_date__month=7),
            ['<Article: Area woman programs in Python>'],
        )

        self.assertQuerysetEqual(
            Article.objects.filter(pub_date__week_day=5),
            ['<Article: Area woman programs in Python>'],
        )
        self.assertQuerysetEqual(
            Article.objects.filter(pub_date__week_day=6),
            [],
        )

        # Django raises an Article.DoesNotExist exception for get() if the
        # parameters don't match any object.
        six.assertRaisesRegex(self,
            ObjectDoesNotExist,
            "Article matching query does not exist.",
            Article.objects.get,
            id__exact=2000,
        )
        # To avoid dict-ordering related errors check only one lookup
        # in single assert.
        self.assertRaises(
            ObjectDoesNotExist,
            Article.objects.get,
            pub_date__year=2005,
            pub_date__month=8,
        )

        six.assertRaisesRegex(self,
            ObjectDoesNotExist,
            "Article matching query does not exist.",
            Article.objects.get,
            pub_date__week_day=6,
        )

        # Lookup by a primary key is the most common case, so Django
        # provides a shortcut for primary-key exact lookups.
        # The following is identical to articles.get(id=a.id).
        self.assertEqual(Article.objects.get(pk=a.id), a)

        # pk can be used as a shortcut for the primary key name in any query.
        self.assertQuerysetEqual(Article.objects.filter(pk__in=[a.id]),
            ["<Article: Area woman programs in Python>"])

        # Model instances of the same type and same ID are considered equal.
        a = Article.objects.get(pk=a.id)
        b = Article.objects.get(pk=a.id)
        self.assertEqual(a, b)

        # Create a very similar object
        a = Article(
            id=None,
            headline='Area man programs in Python',
            pub_date=datetime(2005, 7, 28),
        )
        a.save()

        self.assertEqual(Article.objects.count(), 2)

        # Django raises an Article.MultipleObjectsReturned exception if the
        # lookup matches more than one object
        six.assertRaisesRegex(self,
            MultipleObjectsReturned,
            "get\(\) returned more than one Article -- it returned 2!",
            Article.objects.get,
            headline__startswith='Area',
        )

        six.assertRaisesRegex(self,
            MultipleObjectsReturned,
            "get\(\) returned more than one Article -- it returned 2!",
            Article.objects.get,
            pub_date__year=2005,
        )

        six.assertRaisesRegex(self,
            MultipleObjectsReturned,
            "get\(\) returned more than one Article -- it returned 2!",
            Article.objects.get,
            pub_date__year=2005,
            pub_date__month=7,
        )

    def test_object_creation(self):
        # Create an Article.
        a = Article(
            id=None,
            headline='Area man programs in Python',
            pub_date=datetime(2005, 7, 28),
        )

        # Save it into the database. You have to call save() explicitly.
        a.save()

        # You can initialize a model instance using positional arguments,
        # which should match the field order as defined in the model.
        a2 = Article(None, 'Second article', datetime(2005, 7, 29))
        a2.save()

        self.assertNotEqual(a2.id, a.id)
        self.assertEqual(a2.headline, 'Second article')
        self.assertEqual(a2.pub_date, datetime(2005, 7, 29, 0, 0))

        # ...or, you can use keyword arguments.
        a3 = Article(
            id=None,
            headline='Third article',
            pub_date=datetime(2005, 7, 30),
        )
        a3.save()

        self.assertNotEqual(a3.id, a.id)
        self.assertNotEqual(a3.id, a2.id)
        self.assertEqual(a3.headline, 'Third article')
        self.assertEqual(a3.pub_date, datetime(2005, 7, 30, 0, 0))

        # You can also mix and match position and keyword arguments, but
        # be sure not to duplicate field information.
        a4 = Article(None, 'Fourth article', pub_date=datetime(2005, 7, 31))
        a4.save()
        self.assertEqual(a4.headline, 'Fourth article')

        # Don't use invalid keyword arguments.
        six.assertRaisesRegex(self,
            TypeError,
            "'foo' is an invalid keyword argument for this function",
            Article,
            id=None,
            headline='Invalid',
            pub_date=datetime(2005, 7, 31),
            foo='bar',
        )

        # You can leave off the value for an AutoField when creating an
        # object, because it'll get filled in automatically when you save().
        a5 = Article(headline='Article 6', pub_date=datetime(2005, 7, 31))
        a5.save()
        self.assertEqual(a5.headline, 'Article 6')

        # If you leave off a field with "default" set, Django will use
        # the default.
        a6 = Article(pub_date=datetime(2005, 7, 31))
        a6.save()
        self.assertEqual(a6.headline, 'Default headline')

        # For DateTimeFields, Django saves as much precision (in seconds)
        # as you give it.
        a7 = Article(
            headline='Article 7',
            pub_date=datetime(2005, 7, 31, 12, 30),
        )
        a7.save()
        self.assertEqual(Article.objects.get(id__exact=a7.id).pub_date,
            datetime(2005, 7, 31, 12, 30))

        a8 = Article(
            headline='Article 8',
            pub_date=datetime(2005, 7, 31, 12, 30, 45),
        )
        a8.save()
        self.assertEqual(Article.objects.get(id__exact=a8.id).pub_date,
            datetime(2005, 7, 31, 12, 30, 45))

        # Saving an object again doesn't create a new object -- it just saves
        # the old one.
        current_id = a8.id
        a8.save()
        self.assertEqual(a8.id, current_id)
        a8.headline = 'Updated article 8'
        a8.save()
        self.assertEqual(a8.id, current_id)

        # Check that != and == operators behave as expecte on instances
        self.assertTrue(a7 != a8)
        self.assertFalse(a7 == a8)
        self.assertEqual(a8, Article.objects.get(id__exact=a8.id))

        self.assertTrue(Article.objects.get(id__exact=a8.id) != Article.objects.get(id__exact=a7.id))
        self.assertFalse(Article.objects.get(id__exact=a8.id) == Article.objects.get(id__exact=a7.id))

        # You can use 'in' to test for membership...
        self.assertTrue(a8 in Article.objects.all())

        # ... but there will often be more efficient ways if that is all you need:
        self.assertTrue(Article.objects.filter(id=a8.id).exists())

        # datetimes() returns a list of available dates of the given scope for
        # the given field.
        self.assertQuerysetEqual(
            Article.objects.datetimes('pub_date', 'year'),
            ["datetime.datetime(2005, 1, 1, 0, 0)"])
        self.assertQuerysetEqual(
            Article.objects.datetimes('pub_date', 'month'),
            ["datetime.datetime(2005, 7, 1, 0, 0)"])
        self.assertQuerysetEqual(
            Article.objects.datetimes('pub_date', 'day'),
            ["datetime.datetime(2005, 7, 28, 0, 0)",
             "datetime.datetime(2005, 7, 29, 0, 0)",
             "datetime.datetime(2005, 7, 30, 0, 0)",
             "datetime.datetime(2005, 7, 31, 0, 0)"])
        self.assertQuerysetEqual(
            Article.objects.datetimes('pub_date', 'day', order='ASC'),
            ["datetime.datetime(2005, 7, 28, 0, 0)",
             "datetime.datetime(2005, 7, 29, 0, 0)",
             "datetime.datetime(2005, 7, 30, 0, 0)",
             "datetime.datetime(2005, 7, 31, 0, 0)"])
        self.assertQuerysetEqual(
            Article.objects.datetimes('pub_date', 'day', order='DESC'),
            ["datetime.datetime(2005, 7, 31, 0, 0)",
             "datetime.datetime(2005, 7, 30, 0, 0)",
             "datetime.datetime(2005, 7, 29, 0, 0)",
             "datetime.datetime(2005, 7, 28, 0, 0)"])

        # datetimes() requires valid arguments.
        self.assertRaises(
            TypeError,
            Article.objects.dates,
        )

        six.assertRaisesRegex(self,
            FieldDoesNotExist,
            "Article has no field named 'invalid_field'",
            Article.objects.dates,
            "invalid_field",
            "year",
        )

        six.assertRaisesRegex(self,
            AssertionError,
            "'kind' must be one of 'year', 'month' or 'day'.",
            Article.objects.dates,
            "pub_date",
            "bad_kind",
        )

        six.assertRaisesRegex(self,
            AssertionError,
            "'order' must be either 'ASC' or 'DESC'.",
            Article.objects.dates,
            "pub_date",
            "year",
            order="bad order",
        )

        # Use iterator() with datetimes() to return a generator that lazily
        # requests each result one at a time, to save memory.
        dates = []
        for article in Article.objects.datetimes('pub_date', 'day', order='DESC').iterator():
            dates.append(article)
        self.assertEqual(dates, [
            datetime(2005, 7, 31, 0, 0),
            datetime(2005, 7, 30, 0, 0),
            datetime(2005, 7, 29, 0, 0),
            datetime(2005, 7, 28, 0, 0)])

        # You can combine queries with & and |.
        s1 = Article.objects.filter(id__exact=a.id)
        s2 = Article.objects.filter(id__exact=a2.id)
        self.assertQuerysetEqual(s1 | s2,
            ["<Article: Area man programs in Python>",
             "<Article: Second article>"])
        self.assertQuerysetEqual(s1 & s2, [])

        # You can get the number of objects like this:
        self.assertEqual(len(Article.objects.filter(id__exact=a.id)), 1)

        # You can get items using index and slice notation.
        self.assertEqual(Article.objects.all()[0], a)
        self.assertQuerysetEqual(Article.objects.all()[1:3],
            ["<Article: Second article>", "<Article: Third article>"])

        s3 = Article.objects.filter(id__exact=a3.id)
        self.assertQuerysetEqual((s1 | s2 | s3)[::2],
            ["<Article: Area man programs in Python>",
             "<Article: Third article>"])

        # Slicing works with longs (Python 2 only -- Python 3 doesn't have longs).
        if six.PY2:
            self.assertEqual(Article.objects.all()[long(0)], a)
            self.assertQuerysetEqual(Article.objects.all()[long(1):long(3)],
                ["<Article: Second article>", "<Article: Third article>"])
            self.assertQuerysetEqual((s1 | s2 | s3)[::long(2)],
                ["<Article: Area man programs in Python>",
                "<Article: Third article>"])

            # And can be mixed with ints.
            self.assertQuerysetEqual(Article.objects.all()[1:long(3)],
                ["<Article: Second article>", "<Article: Third article>"])

        # Slices (without step) are lazy:
        self.assertQuerysetEqual(Article.objects.all()[0:5].filter(),
            ["<Article: Area man programs in Python>",
             "<Article: Second article>",
             "<Article: Third article>",
             "<Article: Article 6>",
             "<Article: Default headline>"])

        # Slicing again works:
        self.assertQuerysetEqual(Article.objects.all()[0:5][0:2],
            ["<Article: Area man programs in Python>",
             "<Article: Second article>"])
        self.assertQuerysetEqual(Article.objects.all()[0:5][:2],
            ["<Article: Area man programs in Python>",
             "<Article: Second article>"])
        self.assertQuerysetEqual(Article.objects.all()[0:5][4:],
            ["<Article: Default headline>"])
        self.assertQuerysetEqual(Article.objects.all()[0:5][5:], [])

        # Some more tests!
        self.assertQuerysetEqual(Article.objects.all()[2:][0:2],
            ["<Article: Third article>", "<Article: Article 6>"])
        self.assertQuerysetEqual(Article.objects.all()[2:][:2],
            ["<Article: Third article>", "<Article: Article 6>"])
        self.assertQuerysetEqual(Article.objects.all()[2:][2:3],
            ["<Article: Default headline>"])

        # Using an offset without a limit is also possible.
        self.assertQuerysetEqual(Article.objects.all()[5:],
            ["<Article: Fourth article>",
             "<Article: Article 7>",
             "<Article: Updated article 8>"])

        # Also, once you have sliced you can't filter, re-order or combine
        six.assertRaisesRegex(self,
            AssertionError,
            "Cannot filter a query once a slice has been taken.",
            Article.objects.all()[0:5].filter,
            id=a.id,
        )

        six.assertRaisesRegex(self,
            AssertionError,
            "Cannot reorder a query once a slice has been taken.",
            Article.objects.all()[0:5].order_by,
            'id',
        )

        try:
            Article.objects.all()[0:1] & Article.objects.all()[4:5]
            self.fail('Should raise an AssertionError')
        except AssertionError as e:
            self.assertEqual(str(e), "Cannot combine queries once a slice has been taken.")
        except Exception as e:
            self.fail('Should raise an AssertionError, not %s' % e)

        # Negative slices are not supported, due to database constraints.
        # (hint: inverting your ordering might do what you need).
        try:
            Article.objects.all()[-1]
            self.fail('Should raise an AssertionError')
        except AssertionError as e:
            self.assertEqual(str(e), "Negative indexing is not supported.")
        except Exception as e:
            self.fail('Should raise an AssertionError, not %s' % e)

        error = None
        try:
            Article.objects.all()[0:-5]
        except Exception as e:
            error = e
        self.assertIsInstance(error, AssertionError)
        self.assertEqual(str(error), "Negative indexing is not supported.")

        # An Article instance doesn't have access to the "objects" attribute.
        # That's only available on the class.
        six.assertRaisesRegex(self,
            AttributeError,
            "Manager isn't accessible via Article instances",
            getattr,
            a7,
            "objects",
        )

        # Bulk delete test: How many objects before and after the delete?
        self.assertQuerysetEqual(Article.objects.all(),
            ["<Article: Area man programs in Python>",
             "<Article: Second article>",
             "<Article: Third article>",
             "<Article: Article 6>",
             "<Article: Default headline>",
             "<Article: Fourth article>",
             "<Article: Article 7>",
             "<Article: Updated article 8>"])
        Article.objects.filter(id__lte=a4.id).delete()
        self.assertQuerysetEqual(Article.objects.all(),
            ["<Article: Article 6>",
             "<Article: Default headline>",
             "<Article: Article 7>",
             "<Article: Updated article 8>"])

    @skipUnlessDBFeature('supports_microsecond_precision')
    def test_microsecond_precision(self):
        # In PostgreSQL, microsecond-level precision is available.
        a9 = Article(
            headline='Article 9',
            pub_date=datetime(2005, 7, 31, 12, 30, 45, 180),
        )
        a9.save()
        self.assertEqual(Article.objects.get(pk=a9.pk).pub_date,
            datetime(2005, 7, 31, 12, 30, 45, 180))

    @skipIfDBFeature('supports_microsecond_precision')
    def test_microsecond_precision_not_supported(self):
        # In MySQL, microsecond-level precision isn't available. You'll lose
        # microsecond-level precision once the data is saved.
        a9 = Article(
            headline='Article 9',
            pub_date=datetime(2005, 7, 31, 12, 30, 45, 180),
        )
        a9.save()
        self.assertEqual(Article.objects.get(id__exact=a9.id).pub_date,
            datetime(2005, 7, 31, 12, 30, 45))

    def test_manually_specify_primary_key(self):
        # You can manually specify the primary key when creating a new object.
        a101 = Article(
            id=101,
            headline='Article 101',
            pub_date=datetime(2005, 7, 31, 12, 30, 45),
        )
        a101.save()
        a101 = Article.objects.get(pk=101)
        self.assertEqual(a101.headline, 'Article 101')

    def test_create_method(self):
        # You can create saved objects in a single step
        a10 = Article.objects.create(
            headline="Article 10",
            pub_date=datetime(2005, 7, 31, 12, 30, 45),
        )
        self.assertEqual(Article.objects.get(headline="Article 10"), a10)

    def test_year_lookup_edge_case(self):
        # Edge-case test: A year lookup should retrieve all objects in
        # the given year, including Jan. 1 and Dec. 31.
        a11 = Article.objects.create(
            headline='Article 11',
            pub_date=datetime(2008, 1, 1),
        )
        a12 = Article.objects.create(
            headline='Article 12',
            pub_date=datetime(2008, 12, 31, 23, 59, 59, 999999),
        )
        self.assertQuerysetEqual(Article.objects.filter(pub_date__year=2008),
            ["<Article: Article 11>", "<Article: Article 12>"])

    def test_unicode_data(self):
        # Unicode data works, too.
        a = Article(
            headline='\u6797\u539f \u3081\u3050\u307f',
            pub_date=datetime(2005, 7, 28),
        )
        a.save()
        self.assertEqual(Article.objects.get(pk=a.id).headline,
            '\u6797\u539f \u3081\u3050\u307f')

    def test_hash_function(self):
        # Model instances have a hash function, so they can be used in sets
        # or as dictionary keys. Two models compare as equal if their primary
        # keys are equal.
        a10 = Article.objects.create(
            headline="Article 10",
            pub_date=datetime(2005, 7, 31, 12, 30, 45),
        )
        a11 = Article.objects.create(
            headline='Article 11',
            pub_date=datetime(2008, 1, 1),
        )
        a12 = Article.objects.create(
            headline='Article 12',
            pub_date=datetime(2008, 12, 31, 23, 59, 59, 999999),
        )

        s = set([a10, a11, a12])
        self.assertTrue(Article.objects.get(headline='Article 11') in s)

    def test_field_ordering(self):
        """
        Field instances have a `__lt__` comparison function to define an
        ordering based on their creation. Prior to #17851 this ordering
        comparison relied on the now unsupported `__cmp__` and was assuming
        compared objects were both Field instances raising `AttributeError`
        when it should have returned `NotImplemented`.
        """
        f1 = Field()
        f2 = Field(auto_created=True)
        f3 = Field()
        self.assertTrue(f2 < f1)
        self.assertTrue(f3 > f1)
        self.assertFalse(f1 == None)
        self.assertFalse(f2 in (None, 1, ''))

    def test_extra_method_select_argument_with_dashes_and_values(self):
        # The 'select' argument to extra() supports names with dashes in
        # them, as long as you use values().
        a10 = Article.objects.create(
            headline="Article 10",
            pub_date=datetime(2005, 7, 31, 12, 30, 45),
        )
        a11 = Article.objects.create(
            headline='Article 11',
            pub_date=datetime(2008, 1, 1),
        )
        a12 = Article.objects.create(
            headline='Article 12',
            pub_date=datetime(2008, 12, 31, 23, 59, 59, 999999),
        )

        dicts = Article.objects.filter(
            pub_date__year=2008).extra(
                select={'dashed-value': '1'}
            ).values('headline', 'dashed-value')
        self.assertEqual([sorted(d.items()) for d in dicts],
            [[('dashed-value', 1), ('headline', 'Article 11')], [('dashed-value', 1), ('headline', 'Article 12')]])

    def test_extra_method_select_argument_with_dashes(self):
        # If you use 'select' with extra() and names containing dashes on a
        # query that's *not* a values() query, those extra 'select' values
        # will silently be ignored.
        a10 = Article.objects.create(
            headline="Article 10",
            pub_date=datetime(2005, 7, 31, 12, 30, 45),
        )
        a11 = Article.objects.create(
            headline='Article 11',
            pub_date=datetime(2008, 1, 1),
        )
        a12 = Article.objects.create(
            headline='Article 12',
            pub_date=datetime(2008, 12, 31, 23, 59, 59, 999999),
        )

        articles = Article.objects.filter(
            pub_date__year=2008).extra(
                select={'dashed-value': '1', 'undashedvalue': '2'})
        self.assertEqual(articles[0].undashedvalue, 2)

    def test_create_relation_with_ugettext_lazy(self):
        """
        Test that ugettext_lazy objects work when saving model instances
        through various methods. Refs #10498.
        """
        notlazy = 'test'
        lazy = ugettext_lazy(notlazy)
        reporter = Article.objects.create(headline=lazy, pub_date=datetime.now())
        article = Article.objects.get()
        self.assertEqual(article.headline, notlazy)
        # test that assign + save works with Promise objecs
        article.headline = lazy
        article.save()
        self.assertEqual(article.headline, notlazy)
        # test .update()
        Article.objects.update(headline=lazy)
        article = Article.objects.get()
        self.assertEqual(article.headline, notlazy)
        # still test bulk_create()
        Article.objects.all().delete()
        Article.objects.bulk_create([Article(headline=lazy, pub_date=datetime.now())])
        article = Article.objects.get()
        self.assertEqual(article.headline, notlazy)

    def test_emptyqs(self):
        # Can't be instantiated
        with self.assertRaises(TypeError):
            EmptyQuerySet()
        self.assertIsInstance(Article.objects.none(), EmptyQuerySet)

    def test_emptyqs_values(self):
        # test for #15959
        Article.objects.create(headline='foo', pub_date=datetime.now())
        with self.assertNumQueries(0):
            qs = Article.objects.none().values_list('pk')
            self.assertIsInstance(qs, EmptyQuerySet)
            self.assertIsInstance(qs, ValuesListQuerySet)
            self.assertEqual(len(qs), 0)

    def test_emptyqs_customqs(self):
        # A hacky test for custom QuerySet subclass - refs #17271
        Article.objects.create(headline='foo', pub_date=datetime.now())
        class CustomQuerySet(QuerySet):
            def do_something(self):
                return 'did something'

        qs = Article.objects.all()
        qs.__class__ = CustomQuerySet
        qs = qs.none()
        with self.assertNumQueries(0):
            self.assertEqual(len(qs), 0)
            self.assertIsInstance(qs, EmptyQuerySet)
            self.assertEqual(qs.do_something(), 'did something')

    def test_emptyqs_values_order(self):
        # Tests for ticket #17712
        Article.objects.create(headline='foo', pub_date=datetime.now())
        with self.assertNumQueries(0):
            self.assertEqual(len(Article.objects.none().values_list('id').order_by('id')), 0)
        with self.assertNumQueries(0):
            self.assertEqual(len(Article.objects.none().filter(
                id__in=Article.objects.values_list('id', flat=True))), 0)

    @skipUnlessDBFeature('can_distinct_on_fields')
    def test_emptyqs_distinct(self):
        # Tests for #19426
        Article.objects.create(headline='foo', pub_date=datetime.now())
        with self.assertNumQueries(0):
            self.assertEqual(len(Article.objects.none().distinct('headline', 'pub_date')), 0)

    def test_ticket_20278(self):
        sr = SelfRef.objects.create()
        with self.assertRaises(ObjectDoesNotExist):
            SelfRef.objects.get(selfref=sr)


class ConcurrentSaveTests(TransactionTestCase):

    available_apps = ['basic']

    @skipUnlessDBFeature('test_db_allows_multiple_connections')
    def test_concurrent_delete_with_save(self):
        """
        Test fetching, deleting and finally saving an object - we should get
        an insert in this case.
        """
        a = Article.objects.create(headline='foo', pub_date=datetime.now())
        exceptions = []
        def deleter():
            try:
                # Do not delete a directly - doing so alters its state.
                Article.objects.filter(pk=a.pk).delete()
                connections[DEFAULT_DB_ALIAS].commit_unless_managed()
            except Exception as e:
                exceptions.append(e)
            finally:
                connections[DEFAULT_DB_ALIAS].close()
        self.assertEqual(len(exceptions), 0)
        t = threading.Thread(target=deleter)
        t.start()
        t.join()
        a.save()
        self.assertEqual(Article.objects.get(pk=a.pk).headline, 'foo')


class SelectOnSaveTests(TestCase):
    def test_select_on_save(self):
        a1 = Article.objects.create(pub_date=datetime.now())
        with self.assertNumQueries(1):
            a1.save()
        asos = ArticleSelectOnSave.objects.create(pub_date=datetime.now())
        with self.assertNumQueries(2):
            asos.save()
        with self.assertNumQueries(1):
            asos.save(force_update=True)
        Article.objects.all().delete()
        with self.assertRaises(DatabaseError):
            with self.assertNumQueries(1):
                asos.save(force_update=True)

    def test_select_on_save_lying_update(self):
        """
        Test that select_on_save works correctly if the database
        doesn't return correct information about matched rows from
        UPDATE.
        """
        # Change the manager to not return "row matched" for update().
        # We are going to change the Article's _base_manager class
        # dynamically. This is a bit of a hack, but it seems hard to
        # test this properly otherwise. Article's manager, because
        # proxy models use their parent model's _base_manager.

        orig_class = Article._base_manager.__class__

        class FakeQuerySet(QuerySet):
            # Make sure the _update method below is in fact called.
            called = False

            def _update(self, *args, **kwargs):
                FakeQuerySet.called = True
                super(FakeQuerySet, self)._update(*args, **kwargs)
                return 0

        class FakeManager(orig_class):
            def get_queryset(self):
                return FakeQuerySet(self.model)
        try:
            Article._base_manager.__class__ = FakeManager
            asos = ArticleSelectOnSave.objects.create(pub_date=datetime.now())
            with self.assertNumQueries(2):
                asos.save()
                self.assertTrue(FakeQuerySet.called)
            # This is not wanted behaviour, but this is how Django has always
            # behaved for databases that do not return correct information
            # about matched rows for UPDATE.
            with self.assertRaises(DatabaseError):
                asos.save(force_update=True)
            with self.assertRaises(DatabaseError):
                asos.save(update_fields=['pub_date'])
        finally:
            Article._base_manager.__class__ = orig_class
