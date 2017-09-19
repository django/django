import threading
from datetime import datetime, timedelta

from django.core.exceptions import MultipleObjectsReturned, ObjectDoesNotExist
from django.db import DEFAULT_DB_ALIAS, DatabaseError, connections
from django.db.models.manager import BaseManager
from django.db.models.query import EmptyQuerySet, QuerySet
from django.test import (
    SimpleTestCase, TestCase, TransactionTestCase, skipIfDBFeature,
    skipUnlessDBFeature,
)
from django.utils.translation import gettext_lazy

from .models import Article, ArticleSelectOnSave, FeaturedArticle, SelfRef


class ModelInstanceCreationTests(TestCase):

    def test_object_is_not_written_to_database_until_save_was_called(self):
        a = Article(
            id=None,
            headline='Parrot programs in Python',
            pub_date=datetime(2005, 7, 28),
        )
        self.assertIsNone(a.id)
        self.assertEqual(Article.objects.all().count(), 0)

        # Save it into the database. You have to call save() explicitly.
        a.save()
        self.assertIsNotNone(a.id)
        self.assertEqual(Article.objects.all().count(), 1)

    def test_can_initialize_model_instance_using_positional_arguments(self):
        """
        You can initialize a model instance using positional arguments,
        which should match the field order as defined in the model.
        """
        a = Article(None, 'Second article', datetime(2005, 7, 29))
        a.save()

        self.assertEqual(a.headline, 'Second article')
        self.assertEqual(a.pub_date, datetime(2005, 7, 29, 0, 0))

    def test_can_create_instance_using_kwargs(self):
        a = Article(
            id=None,
            headline='Third article',
            pub_date=datetime(2005, 7, 30),
        )
        a.save()
        self.assertEqual(a.headline, 'Third article')
        self.assertEqual(a.pub_date, datetime(2005, 7, 30, 0, 0))

    def test_autofields_generate_different_values_for_each_instance(self):
        a1 = Article.objects.create(headline='First', pub_date=datetime(2005, 7, 30, 0, 0))
        a2 = Article.objects.create(headline='First', pub_date=datetime(2005, 7, 30, 0, 0))
        a3 = Article.objects.create(headline='First', pub_date=datetime(2005, 7, 30, 0, 0))
        self.assertNotEqual(a3.id, a1.id)
        self.assertNotEqual(a3.id, a2.id)

    def test_can_mix_and_match_position_and_kwargs(self):
        # You can also mix and match position and keyword arguments, but
        # be sure not to duplicate field information.
        a = Article(None, 'Fourth article', pub_date=datetime(2005, 7, 31))
        a.save()
        self.assertEqual(a.headline, 'Fourth article')

    def test_cannot_create_instance_with_invalid_kwargs(self):
        with self.assertRaisesMessage(TypeError, "'foo' is an invalid keyword argument for this function"):
            Article(
                id=None,
                headline='Some headline',
                pub_date=datetime(2005, 7, 31),
                foo='bar',
            )

    def test_can_leave_off_value_for_autofield_and_it_gets_value_on_save(self):
        """
        You can leave off the value for an AutoField when creating an
        object, because it'll get filled in automatically when you save().
        """
        a = Article(headline='Article 5', pub_date=datetime(2005, 7, 31))
        a.save()
        self.assertEqual(a.headline, 'Article 5')
        self.assertIsNotNone(a.id)

    def test_leaving_off_a_field_with_default_set_the_default_will_be_saved(self):
        a = Article(pub_date=datetime(2005, 7, 31))
        a.save()
        self.assertEqual(a.headline, 'Default headline')

    def test_for_datetimefields_saves_as_much_precision_as_was_given(self):
        """as much precision in *seconds*"""
        a1 = Article(
            headline='Article 7',
            pub_date=datetime(2005, 7, 31, 12, 30),
        )
        a1.save()
        self.assertEqual(Article.objects.get(id__exact=a1.id).pub_date, datetime(2005, 7, 31, 12, 30))

        a2 = Article(
            headline='Article 8',
            pub_date=datetime(2005, 7, 31, 12, 30, 45),
        )
        a2.save()
        self.assertEqual(Article.objects.get(id__exact=a2.id).pub_date, datetime(2005, 7, 31, 12, 30, 45))

    def test_saving_an_object_again_does_not_create_a_new_object(self):
        a = Article(headline='original', pub_date=datetime(2014, 5, 16))
        a.save()
        current_id = a.id

        a.save()
        self.assertEqual(a.id, current_id)

        a.headline = 'Updated headline'
        a.save()
        self.assertEqual(a.id, current_id)

    def test_querysets_checking_for_membership(self):
        headlines = [
            'Parrot programs in Python', 'Second article', 'Third article']
        some_pub_date = datetime(2014, 5, 16, 12, 1)
        for headline in headlines:
            Article(headline=headline, pub_date=some_pub_date).save()
        a = Article(headline='Some headline', pub_date=some_pub_date)
        a.save()

        # You can use 'in' to test for membership...
        self.assertIn(a, Article.objects.all())
        # ... but there will often be more efficient ways if that is all you need:
        self.assertTrue(Article.objects.filter(id=a.id).exists())


class ModelTest(TestCase):
    def test_objects_attribute_is_only_available_on_the_class_itself(self):
        with self.assertRaisesMessage(AttributeError, "Manager isn't accessible via Article instances"):
            getattr(Article(), "objects",)
        self.assertFalse(hasattr(Article(), 'objects'))
        self.assertTrue(hasattr(Article, 'objects'))

    def test_queryset_delete_removes_all_items_in_that_queryset(self):
        headlines = [
            'An article', 'Article One', 'Amazing article', 'Boring article']
        some_pub_date = datetime(2014, 5, 16, 12, 1)
        for headline in headlines:
            Article(headline=headline, pub_date=some_pub_date).save()
        self.assertQuerysetEqual(
            Article.objects.all().order_by('headline'),
            ["<Article: Amazing article>",
             "<Article: An article>",
             "<Article: Article One>",
             "<Article: Boring article>"]
        )
        Article.objects.filter(headline__startswith='A').delete()
        self.assertQuerysetEqual(Article.objects.all().order_by('headline'), ["<Article: Boring article>"])

    def test_not_equal_and_equal_operators_behave_as_expected_on_instances(self):
        some_pub_date = datetime(2014, 5, 16, 12, 1)
        a1 = Article.objects.create(headline='First', pub_date=some_pub_date)
        a2 = Article.objects.create(headline='Second', pub_date=some_pub_date)
        self.assertNotEqual(a1, a2)
        self.assertEqual(a1, Article.objects.get(id__exact=a1.id))

        self.assertNotEqual(Article.objects.get(id__exact=a1.id), Article.objects.get(id__exact=a2.id))

    @skipUnlessDBFeature('supports_microsecond_precision')
    def test_microsecond_precision(self):
        # In PostgreSQL, microsecond-level precision is available.
        a9 = Article(
            headline='Article 9',
            pub_date=datetime(2005, 7, 31, 12, 30, 45, 180),
        )
        a9.save()
        self.assertEqual(Article.objects.get(pk=a9.pk).pub_date, datetime(2005, 7, 31, 12, 30, 45, 180))

    @skipIfDBFeature('supports_microsecond_precision')
    def test_microsecond_precision_not_supported(self):
        # In MySQL, microsecond-level precision isn't always available. You'll
        # lose microsecond-level precision once the data is saved.
        a9 = Article(
            headline='Article 9',
            pub_date=datetime(2005, 7, 31, 12, 30, 45, 180),
        )
        a9.save()
        self.assertEqual(
            Article.objects.get(id__exact=a9.id).pub_date,
            datetime(2005, 7, 31, 12, 30, 45),
        )

    @skipIfDBFeature('supports_microsecond_precision')
    def test_microsecond_precision_not_supported_edge_case(self):
        # In MySQL, microsecond-level precision isn't always available. You'll
        # lose microsecond-level precision once the data is saved.
        a = Article.objects.create(
            headline='Article',
            pub_date=datetime(2008, 12, 31, 23, 59, 59, 999999),
        )
        self.assertEqual(
            Article.objects.get(pk=a.pk).pub_date,
            datetime(2008, 12, 31, 23, 59, 59),
        )

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
        Article.objects.create(
            headline='Article 11',
            pub_date=datetime(2008, 1, 1),
        )
        Article.objects.create(
            headline='Article 12',
            pub_date=datetime(2008, 12, 31, 23, 59, 59, 999999),
        )
        self.assertQuerysetEqual(
            Article.objects.filter(pub_date__year=2008),
            ["<Article: Article 11>", "<Article: Article 12>"]
        )

    def test_unicode_data(self):
        # Unicode data works, too.
        a = Article(
            headline='\u6797\u539f \u3081\u3050\u307f',
            pub_date=datetime(2005, 7, 28),
        )
        a.save()
        self.assertEqual(Article.objects.get(pk=a.id).headline, '\u6797\u539f \u3081\u3050\u307f')

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

        s = {a10, a11, a12}
        self.assertIn(Article.objects.get(headline='Article 11'), s)

    def test_extra_method_select_argument_with_dashes_and_values(self):
        # The 'select' argument to extra() supports names with dashes in
        # them, as long as you use values().
        Article.objects.create(
            headline="Article 10",
            pub_date=datetime(2005, 7, 31, 12, 30, 45),
        )
        Article.objects.create(
            headline='Article 11',
            pub_date=datetime(2008, 1, 1),
        )
        Article.objects.create(
            headline='Article 12',
            pub_date=datetime(2008, 12, 31, 23, 59, 59, 999999),
        )

        dicts = Article.objects.filter(
            pub_date__year=2008).extra(
            select={'dashed-value': '1'}).values('headline', 'dashed-value')
        self.assertEqual(
            [sorted(d.items()) for d in dicts],
            [[('dashed-value', 1), ('headline', 'Article 11')], [('dashed-value', 1), ('headline', 'Article 12')]]
        )

    def test_extra_method_select_argument_with_dashes(self):
        # If you use 'select' with extra() and names containing dashes on a
        # query that's *not* a values() query, those extra 'select' values
        # will silently be ignored.
        Article.objects.create(
            headline="Article 10",
            pub_date=datetime(2005, 7, 31, 12, 30, 45),
        )
        Article.objects.create(
            headline='Article 11',
            pub_date=datetime(2008, 1, 1),
        )
        Article.objects.create(
            headline='Article 12',
            pub_date=datetime(2008, 12, 31, 23, 59, 59, 999999),
        )

        articles = Article.objects.filter(
            pub_date__year=2008).extra(select={'dashed-value': '1', 'undashedvalue': '2'})
        self.assertEqual(articles[0].undashedvalue, 2)

    def test_create_relation_with_gettext_lazy(self):
        """
        gettext_lazy objects work when saving model instances
        through various methods. Refs #10498.
        """
        notlazy = 'test'
        lazy = gettext_lazy(notlazy)
        Article.objects.create(headline=lazy, pub_date=datetime.now())
        article = Article.objects.get()
        self.assertEqual(article.headline, notlazy)
        # test that assign + save works with Promise objects
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
        msg = "EmptyQuerySet can't be instantiated"
        with self.assertRaisesMessage(TypeError, msg):
            EmptyQuerySet()
        self.assertIsInstance(Article.objects.none(), EmptyQuerySet)
        self.assertNotIsInstance('', EmptyQuerySet)

    def test_emptyqs_values(self):
        # test for #15959
        Article.objects.create(headline='foo', pub_date=datetime.now())
        with self.assertNumQueries(0):
            qs = Article.objects.none().values_list('pk')
            self.assertIsInstance(qs, EmptyQuerySet)
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

    def test_eq(self):
        self.assertEqual(Article(id=1), Article(id=1))
        self.assertNotEqual(Article(id=1), object())
        self.assertNotEqual(object(), Article(id=1))
        a = Article()
        self.assertEqual(a, a)
        self.assertNotEqual(Article(), a)

    def test_hash(self):
        # Value based on PK
        self.assertEqual(hash(Article(id=1)), hash(1))
        msg = 'Model instances without primary key value are unhashable'
        with self.assertRaisesMessage(TypeError, msg):
            # No PK value -> unhashable (because save() would then change
            # hash)
            hash(Article())

    def test_delete_and_access_field(self):
        # Accessing a field after it's deleted from a model reloads its value.
        pub_date = datetime.now()
        article = Article.objects.create(headline='foo', pub_date=pub_date)
        new_pub_date = article.pub_date + timedelta(days=10)
        article.headline = 'bar'
        article.pub_date = new_pub_date
        del article.headline
        with self.assertNumQueries(1):
            self.assertEqual(article.headline, 'foo')
        # Fields that weren't deleted aren't reloaded.
        self.assertEqual(article.pub_date, new_pub_date)


class ModelLookupTest(TestCase):
    def setUp(self):
        # Create an Article.
        self.a = Article(
            id=None,
            headline='Swallow programs in Python',
            pub_date=datetime(2005, 7, 28),
        )
        # Save it into the database. You have to call save() explicitly.
        self.a.save()

    def test_all_lookup(self):
        # Change values by changing the attributes, then calling save().
        self.a.headline = 'Parrot programs in Python'
        self.a.save()

        # Article.objects.all() returns all the articles in the database.
        self.assertQuerysetEqual(Article.objects.all(), ['<Article: Parrot programs in Python>'])

    def test_rich_lookup(self):
        # Django provides a rich database lookup API.
        self.assertEqual(Article.objects.get(id__exact=self.a.id), self.a)
        self.assertEqual(Article.objects.get(headline__startswith='Swallow'), self.a)
        self.assertEqual(Article.objects.get(pub_date__year=2005), self.a)
        self.assertEqual(Article.objects.get(pub_date__year=2005, pub_date__month=7), self.a)
        self.assertEqual(Article.objects.get(pub_date__year=2005, pub_date__month=7, pub_date__day=28), self.a)
        self.assertEqual(Article.objects.get(pub_date__week_day=5), self.a)

    def test_equal_lookup(self):
        # The "__exact" lookup type can be omitted, as a shortcut.
        self.assertEqual(Article.objects.get(id=self.a.id), self.a)
        self.assertEqual(Article.objects.get(headline='Swallow programs in Python'), self.a)

        self.assertQuerysetEqual(
            Article.objects.filter(pub_date__year=2005),
            ['<Article: Swallow programs in Python>'],
        )
        self.assertQuerysetEqual(
            Article.objects.filter(pub_date__year=2004),
            [],
        )
        self.assertQuerysetEqual(
            Article.objects.filter(pub_date__year=2005, pub_date__month=7),
            ['<Article: Swallow programs in Python>'],
        )

        self.assertQuerysetEqual(
            Article.objects.filter(pub_date__week_day=5),
            ['<Article: Swallow programs in Python>'],
        )
        self.assertQuerysetEqual(
            Article.objects.filter(pub_date__week_day=6),
            [],
        )

    def test_does_not_exist(self):
        # Django raises an Article.DoesNotExist exception for get() if the
        # parameters don't match any object.
        with self.assertRaisesMessage(ObjectDoesNotExist, "Article matching query does not exist."):
            Article.objects.get(id__exact=2000,)
        # To avoid dict-ordering related errors check only one lookup
        # in single assert.
        with self.assertRaises(ObjectDoesNotExist):
            Article.objects.get(pub_date__year=2005, pub_date__month=8)
        with self.assertRaisesMessage(ObjectDoesNotExist, "Article matching query does not exist."):
            Article.objects.get(pub_date__week_day=6,)

    def test_lookup_by_primary_key(self):
        # Lookup by a primary key is the most common case, so Django
        # provides a shortcut for primary-key exact lookups.
        # The following is identical to articles.get(id=a.id).
        self.assertEqual(Article.objects.get(pk=self.a.id), self.a)

        # pk can be used as a shortcut for the primary key name in any query.
        self.assertQuerysetEqual(Article.objects.filter(pk__in=[self.a.id]), ["<Article: Swallow programs in Python>"])

        # Model instances of the same type and same ID are considered equal.
        a = Article.objects.get(pk=self.a.id)
        b = Article.objects.get(pk=self.a.id)
        self.assertEqual(a, b)

    def test_too_many(self):
        # Create a very similar object
        a = Article(
            id=None,
            headline='Swallow bites Python',
            pub_date=datetime(2005, 7, 28),
        )
        a.save()

        self.assertEqual(Article.objects.count(), 2)

        # Django raises an Article.MultipleObjectsReturned exception if the
        # lookup matches more than one object
        msg = "get() returned more than one Article -- it returned 2!"
        with self.assertRaisesMessage(MultipleObjectsReturned, msg):
            Article.objects.get(headline__startswith='Swallow',)
        with self.assertRaisesMessage(MultipleObjectsReturned, msg):
            Article.objects.get(pub_date__year=2005,)
        with self.assertRaisesMessage(MultipleObjectsReturned, msg):
            Article.objects.get(pub_date__year=2005, pub_date__month=7)


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


class ManagerTest(SimpleTestCase):
    QUERYSET_PROXY_METHODS = [
        'none',
        'count',
        'dates',
        'datetimes',
        'distinct',
        'extra',
        'get',
        'get_or_create',
        'update_or_create',
        'create',
        'bulk_create',
        'filter',
        'aggregate',
        'annotate',
        'complex_filter',
        'exclude',
        'in_bulk',
        'iterator',
        'earliest',
        'latest',
        'first',
        'last',
        'order_by',
        'select_for_update',
        'select_related',
        'prefetch_related',
        'values',
        'values_list',
        'update',
        'reverse',
        'defer',
        'only',
        'using',
        'exists',
        '_insert',
        '_update',
        'raw',
        'union',
        'intersection',
        'difference',
    ]

    def test_manager_methods(self):
        """
        This test ensures that the correct set of methods from `QuerySet`
        are copied onto `Manager`.

        It's particularly useful to prevent accidentally leaking new methods
        into `Manager`. New `QuerySet` methods that should also be copied onto
        `Manager` will need to be added to `ManagerTest.QUERYSET_PROXY_METHODS`.
        """
        self.assertEqual(
            sorted(BaseManager._get_queryset_methods(QuerySet)),
            sorted(self.QUERYSET_PROXY_METHODS),
        )


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
        with self.assertRaisesMessage(DatabaseError, 'Forced update did not affect any rows.'):
            with self.assertNumQueries(1):
                asos.save(force_update=True)

    def test_select_on_save_lying_update(self):
        """
        select_on_save works correctly if the database doesn't return correct
        information about matched rows from UPDATE.
        """
        # Change the manager to not return "row matched" for update().
        # We are going to change the Article's _base_manager class
        # dynamically. This is a bit of a hack, but it seems hard to
        # test this properly otherwise. Article's manager, because
        # proxy models use their parent model's _base_manager.

        orig_class = Article._base_manager._queryset_class

        class FakeQuerySet(QuerySet):
            # Make sure the _update method below is in fact called.
            called = False

            def _update(self, *args, **kwargs):
                FakeQuerySet.called = True
                super()._update(*args, **kwargs)
                return 0

        try:
            Article._base_manager._queryset_class = FakeQuerySet
            asos = ArticleSelectOnSave.objects.create(pub_date=datetime.now())
            with self.assertNumQueries(3):
                asos.save()
                self.assertTrue(FakeQuerySet.called)
            # This is not wanted behavior, but this is how Django has always
            # behaved for databases that do not return correct information
            # about matched rows for UPDATE.
            with self.assertRaisesMessage(DatabaseError, 'Forced update did not affect any rows.'):
                asos.save(force_update=True)
            msg = (
                "An error occurred in the current transaction. You can't "
                "execute queries until the end of the 'atomic' block."
            )
            with self.assertRaisesMessage(DatabaseError, msg):
                asos.save(update_fields=['pub_date'])
        finally:
            Article._base_manager._queryset_class = orig_class


class ModelRefreshTests(TestCase):
    def _truncate_ms(self, val):
        # MySQL < 5.6.4 removes microseconds from the datetimes which can cause
        # problems when comparing the original value to that loaded from DB
        return val - timedelta(microseconds=val.microsecond)

    def test_refresh(self):
        a = Article.objects.create(pub_date=self._truncate_ms(datetime.now()))
        Article.objects.create(pub_date=self._truncate_ms(datetime.now()))
        Article.objects.filter(pk=a.pk).update(headline='new headline')
        with self.assertNumQueries(1):
            a.refresh_from_db()
            self.assertEqual(a.headline, 'new headline')

        orig_pub_date = a.pub_date
        new_pub_date = a.pub_date + timedelta(10)
        Article.objects.update(headline='new headline 2', pub_date=new_pub_date)
        with self.assertNumQueries(1):
            a.refresh_from_db(fields=['headline'])
            self.assertEqual(a.headline, 'new headline 2')
            self.assertEqual(a.pub_date, orig_pub_date)
        with self.assertNumQueries(1):
            a.refresh_from_db()
            self.assertEqual(a.pub_date, new_pub_date)

    def test_unknown_kwarg(self):
        s = SelfRef.objects.create()
        msg = "refresh_from_db() got an unexpected keyword argument 'unknown_kwarg'"
        with self.assertRaisesMessage(TypeError, msg):
            s.refresh_from_db(unknown_kwarg=10)

    def test_refresh_fk(self):
        s1 = SelfRef.objects.create()
        s2 = SelfRef.objects.create()
        s3 = SelfRef.objects.create(selfref=s1)
        s3_copy = SelfRef.objects.get(pk=s3.pk)
        s3_copy.selfref.touched = True
        s3.selfref = s2
        s3.save()
        with self.assertNumQueries(1):
            s3_copy.refresh_from_db()
        with self.assertNumQueries(1):
            # The old related instance was thrown away (the selfref_id has
            # changed). It needs to be reloaded on access, so one query
            # executed.
            self.assertFalse(hasattr(s3_copy.selfref, 'touched'))
            self.assertEqual(s3_copy.selfref, s2)

    def test_refresh_null_fk(self):
        s1 = SelfRef.objects.create()
        s2 = SelfRef.objects.create(selfref=s1)
        s2.selfref = None
        s2.refresh_from_db()
        self.assertEqual(s2.selfref, s1)

    def test_refresh_unsaved(self):
        pub_date = self._truncate_ms(datetime.now())
        a = Article.objects.create(pub_date=pub_date)
        a2 = Article(id=a.pk)
        with self.assertNumQueries(1):
            a2.refresh_from_db()
        self.assertEqual(a2.pub_date, pub_date)
        self.assertEqual(a2._state.db, "default")

    def test_refresh_fk_on_delete_set_null(self):
        a = Article.objects.create(
            headline='Parrot programs in Python',
            pub_date=datetime(2005, 7, 28),
        )
        s1 = SelfRef.objects.create(article=a)
        a.delete()
        s1.refresh_from_db()
        self.assertIsNone(s1.article_id)
        self.assertIsNone(s1.article)

    def test_refresh_no_fields(self):
        a = Article.objects.create(pub_date=self._truncate_ms(datetime.now()))
        with self.assertNumQueries(0):
            a.refresh_from_db(fields=[])

    def test_refresh_clears_reverse_related(self):
        """refresh_from_db() clear cached reverse relations."""
        article = Article.objects.create(
            headline='Parrot programs in Python',
            pub_date=datetime(2005, 7, 28),
        )
        self.assertFalse(hasattr(article, 'featured'))
        FeaturedArticle.objects.create(article_id=article.pk)
        article.refresh_from_db()
        self.assertTrue(hasattr(article, 'featured'))
