from copy import deepcopy
import datetime

from django.core.exceptions import MultipleObjectsReturned, FieldError
from django.db import models
from django.db.models.query_utils import InvalidQuery
from django.db.models.fields import FieldDoesNotExist
from django.test import TestCase
from django.utils import six
from django.utils.translation import ugettext_lazy

from .models import Article, Reporter, Assignment


class ManyToOneTests(TestCase):
    def setUp(self):
        # Create a few Reporters.
        self.r = Reporter(first_name='John', last_name='Smith', email='john@example.com')
        self.r.save()
        self.r2 = Reporter(first_name='Paul', last_name='Jones', email='paul@example.com')
        self.r2.save()
        # Create an Article.
        self.a = Article(id=None, headline="This is a test",
                         pub_date=datetime.date(2005, 7, 27), reporter=self.r)
        self.a.save()

    def test_get(self):
        # Article objects have access to their related Reporter objects.
        r = self.a.reporter
        self.assertEqual(r.id, self.r.id)
        # These are strings instead of unicode strings because that's what was used in
        # the creation of this reporter (and we haven't refreshed the data from the
        # database, which always returns unicode strings).
        self.assertEqual((r.first_name, self.r.last_name), ('John', 'Smith'))

    def test_create(self):
        # You can also instantiate an Article by passing the Reporter's ID
        # instead of a Reporter object.
        a3 = Article(id=None, headline="Third article",
                     pub_date=datetime.date(2005, 7, 27), reporter_id=self.r.id)
        a3.save()
        self.assertEqual(a3.reporter.id, self.r.id)

        # Similarly, the reporter ID can be a string.
        a4 = Article(id=None, headline="Fourth article",
                     pub_date=datetime.date(2005, 7, 27), reporter_id=str(self.r.id))
        a4.save()
        self.assertEqual(repr(a4.reporter), "<Reporter: John Smith>")

    def test_add(self):
        # Create an Article via the Reporter object.
        new_article = self.r.article_set.create(headline="John's second story",
                                                pub_date=datetime.date(2005, 7, 29))
        self.assertEqual(repr(new_article), "<Article: John's second story>")
        self.assertEqual(new_article.reporter.id, self.r.id)

        # Create a new article, and add it to the article set.
        new_article2 = Article(headline="Paul's story", pub_date=datetime.date(2006, 1, 17))
        self.r.article_set.add(new_article2)
        self.assertEqual(new_article2.reporter.id, self.r.id)
        self.assertQuerysetEqual(self.r.article_set.all(),
            [
                "<Article: John's second story>",
                "<Article: Paul's story>",
                "<Article: This is a test>",
            ])

        # Add the same article to a different article set - check that it moves.
        self.r2.article_set.add(new_article2)
        self.assertEqual(new_article2.reporter.id, self.r2.id)
        self.assertQuerysetEqual(self.r2.article_set.all(), ["<Article: Paul's story>"])

        # Adding an object of the wrong type raises TypeError.
        with six.assertRaisesRegex(self, TypeError, "'Article' instance expected, got <Reporter.*"):
            self.r.article_set.add(self.r2)
        self.assertQuerysetEqual(self.r.article_set.all(),
            [
                "<Article: John's second story>",
                "<Article: This is a test>",
            ])

    def test_assign(self):
        new_article = self.r.article_set.create(headline="John's second story",
                                                pub_date=datetime.date(2005, 7, 29))
        new_article2 = self.r2.article_set.create(headline="Paul's story",
                                                  pub_date=datetime.date(2006, 1, 17))
        # Assign the article to the reporter directly using the descriptor.
        new_article2.reporter = self.r
        new_article2.save()
        self.assertEqual(repr(new_article2.reporter), "<Reporter: John Smith>")
        self.assertEqual(new_article2.reporter.id, self.r.id)
        self.assertQuerysetEqual(self.r.article_set.all(), [
            "<Article: John's second story>",
            "<Article: Paul's story>",
            "<Article: This is a test>",
        ])
        self.assertQuerysetEqual(self.r2.article_set.all(), [])
        # Set the article back again using set descriptor.
        self.r2.article_set = [new_article, new_article2]
        self.assertQuerysetEqual(self.r.article_set.all(), ["<Article: This is a test>"])
        self.assertQuerysetEqual(self.r2.article_set.all(),
            [
                "<Article: John's second story>",
                "<Article: Paul's story>",
            ])

        # Funny case - assignment notation can only go so far; because the
        # ForeignKey cannot be null, existing members of the set must remain.
        self.r.article_set = [new_article]
        self.assertQuerysetEqual(self.r.article_set.all(),
            [
                "<Article: John's second story>",
                "<Article: This is a test>",
            ])
        self.assertQuerysetEqual(self.r2.article_set.all(), ["<Article: Paul's story>"])
        # Reporter cannot be null - there should not be a clear or remove method
        self.assertFalse(hasattr(self.r2.article_set, 'remove'))
        self.assertFalse(hasattr(self.r2.article_set, 'clear'))

    def test_selects(self):
        new_article = self.r.article_set.create(headline="John's second story",
                                                pub_date=datetime.date(2005, 7, 29))
        new_article2 = self.r2.article_set.create(headline="Paul's story",
                                                  pub_date=datetime.date(2006, 1, 17))
        # Reporter objects have access to their related Article objects.
        self.assertQuerysetEqual(self.r.article_set.all(), [
            "<Article: John's second story>",
            "<Article: This is a test>",
        ])
        self.assertQuerysetEqual(self.r.article_set.filter(headline__startswith='This'),
                                 ["<Article: This is a test>"])
        self.assertEqual(self.r.article_set.count(), 2)
        self.assertEqual(self.r2.article_set.count(), 1)
        # Get articles by id
        self.assertQuerysetEqual(Article.objects.filter(id__exact=self.a.id),
                                 ["<Article: This is a test>"])
        self.assertQuerysetEqual(Article.objects.filter(pk=self.a.id),
                                 ["<Article: This is a test>"])
        # Query on an article property
        self.assertQuerysetEqual(Article.objects.filter(headline__startswith='This'),
                                 ["<Article: This is a test>"])
        # The API automatically follows relationships as far as you need.
        # Use double underscores to separate relationships.
        # This works as many levels deep as you want. There's no limit.
        # Find all Articles for any Reporter whose first name is "John".
        self.assertQuerysetEqual(Article.objects.filter(reporter__first_name__exact='John'),
            [
                "<Article: John's second story>",
                "<Article: This is a test>",
            ])
        # Check that implied __exact also works
        self.assertQuerysetEqual(Article.objects.filter(reporter__first_name='John'),
            [
                "<Article: John's second story>",
                "<Article: This is a test>",
            ])
        # Query twice over the related field.
        self.assertQuerysetEqual(
            Article.objects.filter(reporter__first_name__exact='John',
                                   reporter__last_name__exact='Smith'),
            [
                "<Article: John's second story>",
                "<Article: This is a test>",
            ])
        # The underlying query only makes one join when a related table is referenced twice.
        queryset = Article.objects.filter(reporter__first_name__exact='John',
                                       reporter__last_name__exact='Smith')
        self.assertNumQueries(1, list, queryset)
        self.assertEqual(queryset.query.get_compiler(queryset.db).as_sql()[0].count('INNER JOIN'), 1)

        # The automatically joined table has a predictable name.
        self.assertQuerysetEqual(
            Article.objects.filter(reporter__first_name__exact='John').extra(
                where=["many_to_one_reporter.last_name='Smith'"]),
            [
                "<Article: John's second story>",
                "<Article: This is a test>",
            ])
        # ... and should work fine with the unicode that comes out of forms.Form.cleaned_data
        self.assertQuerysetEqual(
            Article.objects.filter(reporter__first_name__exact='John'
                                  ).extra(where=["many_to_one_reporter.last_name='%s'" % 'Smith']),
            [
                "<Article: John's second story>",
                "<Article: This is a test>",
            ])
        # Find all Articles for a Reporter.
        # Use direct ID check, pk check, and object comparison
        self.assertQuerysetEqual(
            Article.objects.filter(reporter__id__exact=self.r.id),
            [
                "<Article: John's second story>",
                "<Article: This is a test>",
            ])
        self.assertQuerysetEqual(
            Article.objects.filter(reporter__pk=self.r.id),
            [
                "<Article: John's second story>",
                "<Article: This is a test>",
            ])
        self.assertQuerysetEqual(
            Article.objects.filter(reporter=self.r.id),
            [
                "<Article: John's second story>",
                "<Article: This is a test>",
            ])
        self.assertQuerysetEqual(
            Article.objects.filter(reporter=self.r),
            [
                "<Article: John's second story>",
                "<Article: This is a test>",
            ])
        self.assertQuerysetEqual(
            Article.objects.filter(reporter__in=[self.r.id,self.r2.id]).distinct(),
            [
                    "<Article: John's second story>",
                    "<Article: Paul's story>",
                    "<Article: This is a test>",
            ])
        self.assertQuerysetEqual(
            Article.objects.filter(reporter__in=[self.r,self.r2]).distinct(),
            [
                "<Article: John's second story>",
                "<Article: Paul's story>",
                "<Article: This is a test>",
            ])
        # You can also use a queryset instead of a literal list of instances.
        # The queryset must be reduced to a list of values using values(),
        # then converted into a query
        self.assertQuerysetEqual(
            Article.objects.filter(
                        reporter__in=Reporter.objects.filter(first_name='John').values('pk').query
                    ).distinct(),
            [
                "<Article: John's second story>",
                "<Article: This is a test>",
            ])

    def test_reverse_selects(self):
        a3 = Article.objects.create(id=None, headline="Third article",
                                    pub_date=datetime.date(2005, 7, 27), reporter_id=self.r.id)
        a4 = Article.objects.create(id=None, headline="Fourth article",
                                    pub_date=datetime.date(2005, 7, 27), reporter_id=str(self.r.id))
        # Reporters can be queried
        self.assertQuerysetEqual(Reporter.objects.filter(id__exact=self.r.id),
                                 ["<Reporter: John Smith>"])
        self.assertQuerysetEqual(Reporter.objects.filter(pk=self.r.id),
                                 ["<Reporter: John Smith>"])
        self.assertQuerysetEqual(Reporter.objects.filter(first_name__startswith='John'),
                                 ["<Reporter: John Smith>"])
        # Reporters can query in opposite direction of ForeignKey definition
        self.assertQuerysetEqual(Reporter.objects.filter(article__id__exact=self.a.id),
                                 ["<Reporter: John Smith>"])
        self.assertQuerysetEqual(Reporter.objects.filter(article__pk=self.a.id),
                                 ["<Reporter: John Smith>"])
        self.assertQuerysetEqual(Reporter.objects.filter(article=self.a.id),
                                 ["<Reporter: John Smith>"])
        self.assertQuerysetEqual(Reporter.objects.filter(article=self.a),
                                 ["<Reporter: John Smith>"])
        self.assertQuerysetEqual(
            Reporter.objects.filter(article__in=[self.a.id,a3.id]).distinct(),
            ["<Reporter: John Smith>"])
        self.assertQuerysetEqual(
            Reporter.objects.filter(article__in=[self.a.id,a3]).distinct(),
            ["<Reporter: John Smith>"])
        self.assertQuerysetEqual(
            Reporter.objects.filter(article__in=[self.a,a3]).distinct(),
            ["<Reporter: John Smith>"])
        self.assertQuerysetEqual(
            Reporter.objects.filter(article__headline__startswith='T'),
            ["<Reporter: John Smith>", "<Reporter: John Smith>"],
            ordered=False
        )
        self.assertQuerysetEqual(
            Reporter.objects.filter(article__headline__startswith='T').distinct(),
            ["<Reporter: John Smith>"])

        # Counting in the opposite direction works in conjunction with distinct()
        self.assertEqual(
            Reporter.objects.filter(article__headline__startswith='T').count(), 2)
        self.assertEqual(
            Reporter.objects.filter(article__headline__startswith='T').distinct().count(), 1)

        # Queries can go round in circles.
        self.assertQuerysetEqual(
            Reporter.objects.filter(article__reporter__first_name__startswith='John'),
            [
                "<Reporter: John Smith>",
                "<Reporter: John Smith>",
                "<Reporter: John Smith>",
            ],
            ordered=False
        )
        self.assertQuerysetEqual(
            Reporter.objects.filter(article__reporter__first_name__startswith='John').distinct(),
            ["<Reporter: John Smith>"])
        self.assertQuerysetEqual(
            Reporter.objects.filter(article__reporter__exact=self.r).distinct(),
            ["<Reporter: John Smith>"])

        # Check that implied __exact also works.
        self.assertQuerysetEqual(
            Reporter.objects.filter(article__reporter=self.r).distinct(),
            ["<Reporter: John Smith>"])

        # It's possible to use values() calls across many-to-one relations.
        # (Note, too, that we clear the ordering here so as not to drag the
        # 'headline' field into the columns being used to determine uniqueness)
        d = {'reporter__first_name': 'John', 'reporter__last_name': 'Smith'}
        self.assertEqual([d],
            list(Article.objects.filter(reporter=self.r).distinct().order_by()
                 .values('reporter__first_name', 'reporter__last_name')))

    def test_select_related(self):
        # Check that Article.objects.select_related().dates() works properly when
        # there are multiple Articles with the same date but different foreign-key
        # objects (Reporters).
        r1 = Reporter.objects.create(first_name='Mike', last_name='Royko', email='royko@suntimes.com')
        r2 = Reporter.objects.create(first_name='John', last_name='Kass', email='jkass@tribune.com')
        Article.objects.create(headline='First', pub_date=datetime.date(1980, 4, 23), reporter=r1)
        Article.objects.create(headline='Second', pub_date=datetime.date(1980, 4, 23), reporter=r2)
        self.assertEqual(list(Article.objects.select_related().dates('pub_date', 'day')),
            [
                datetime.date(1980, 4, 23),
                datetime.date(2005, 7, 27),
            ])
        self.assertEqual(list(Article.objects.select_related().dates('pub_date', 'month')),
            [
                datetime.date(1980, 4, 1),
                datetime.date(2005, 7, 1),
            ])
        self.assertEqual(list(Article.objects.select_related().dates('pub_date', 'year')),
            [
                datetime.date(1980, 1, 1),
                datetime.date(2005, 1, 1),
            ])

    def test_delete(self):
        new_article = self.r.article_set.create(headline="John's second story",
                                                pub_date=datetime.date(2005, 7, 29))
        new_article2 = self.r2.article_set.create(headline="Paul's story",
                                                  pub_date=datetime.date(2006, 1, 17))
        a3 = Article.objects.create(id=None, headline="Third article",
                                    pub_date=datetime.date(2005, 7, 27), reporter_id=self.r.id)
        a4 = Article.objects.create(id=None, headline="Fourth article",
                                    pub_date=datetime.date(2005, 7, 27), reporter_id=str(self.r.id))
        # If you delete a reporter, his articles will be deleted.
        self.assertQuerysetEqual(Article.objects.all(),
            [
                "<Article: Fourth article>",
                "<Article: John's second story>",
                "<Article: Paul's story>",
                "<Article: Third article>",
                "<Article: This is a test>",
            ])
        self.assertQuerysetEqual(Reporter.objects.order_by('first_name'),
            [
                "<Reporter: John Smith>",
                "<Reporter: Paul Jones>",
            ])
        self.r2.delete()
        self.assertQuerysetEqual(Article.objects.all(),
            [
                "<Article: Fourth article>",
                "<Article: John's second story>",
                "<Article: Third article>",
                "<Article: This is a test>",
            ])
        self.assertQuerysetEqual(Reporter.objects.order_by('first_name'),
                                 ["<Reporter: John Smith>"])
        # You can delete using a JOIN in the query.
        Reporter.objects.filter(article__headline__startswith='This').delete()
        self.assertQuerysetEqual(Reporter.objects.all(), [])
        self.assertQuerysetEqual(Article.objects.all(), [])

    def test_regression_12876(self):
        # Regression for #12876 -- Model methods that include queries that
        # recursive don't cause recursion depth problems under deepcopy.
        self.r.cached_query = Article.objects.filter(reporter=self.r)
        self.assertEqual(repr(deepcopy(self.r)), "<Reporter: John Smith>")

    def test_explicit_fk(self):
        # Create a new Article with get_or_create using an explicit value
        # for a ForeignKey.
        a2, created = Article.objects.get_or_create(id=None,
                                                    headline="John's second test",
                                                    pub_date=datetime.date(2011, 5, 7),
                                                    reporter_id=self.r.id)
        self.assertTrue(created)
        self.assertEqual(a2.reporter.id, self.r.id)

        # You can specify filters containing the explicit FK value.
        self.assertQuerysetEqual(
            Article.objects.filter(reporter_id__exact=self.r.id),
            [
                "<Article: John's second test>",
                "<Article: This is a test>",
            ])

        # Create an Article by Paul for the same date.
        a3 = Article.objects.create(id=None, headline="Paul's commentary",
                                    pub_date=datetime.date(2011, 5, 7),
                                    reporter_id=self.r2.id)
        self.assertEqual(a3.reporter.id, self.r2.id)

        # Get should respect explicit foreign keys as well.
        self.assertRaises(MultipleObjectsReturned,
                          Article.objects.get, reporter_id=self.r.id)
        self.assertEqual(repr(a3),
                         repr(Article.objects.get(reporter_id=self.r2.id,
                                             pub_date=datetime.date(2011, 5, 7))))

    def test_manager_class_caching(self):
        r1 = Reporter.objects.create(first_name='Mike')
        r2 = Reporter.objects.create(first_name='John')

        # Same twice
        self.assertTrue(r1.article_set.__class__ is r1.article_set.__class__)

        # Same as each other
        self.assertTrue(r1.article_set.__class__ is r2.article_set.__class__)

    def test_create_relation_with_ugettext_lazy(self):
        reporter = Reporter.objects.create(first_name='John',
                                           last_name='Smith',
                                           email='john.smith@example.com')
        lazy = ugettext_lazy('test')
        reporter.article_set.create(headline=lazy,
                                    pub_date=datetime.date(2011, 6, 10))
        notlazy = six.text_type(lazy)
        article = reporter.article_set.get()
        self.assertEqual(article.headline, notlazy)

    def test_values_list_exception(self):
        expected_message = "Cannot resolve keyword 'notafield' into field. Choices are: %s"

        self.assertRaisesMessage(FieldError,
                                 expected_message % ', '.join(Reporter._meta.get_all_field_names()),
                                 Article.objects.values_list,
                                 'reporter__notafield')
        self.assertRaisesMessage(FieldError,
                                 expected_message % ', '.join(['EXTRA',] + Article._meta.get_all_field_names()),
                                 Article.objects.extra(select={'EXTRA': 'EXTRA_SELECT'}).values_list,
                                 'notafield')


class FieldCloningTests(TestCase):
    def test_basic_cloning(self):
        original_field = models.CharField(max_length=47)
        clone_result = original_field.clone_for_foreignkey(
            'test_name',
            False,
            'test_tablespace',
            original_field.creation_counter,
            original_field.creation_counter + 1,
            'dummy_column',
            fk_field='dummy value',
        )
        self.assertEqual(len(clone_result), 1)
        new_name, new_field = clone_result[0]
        self.assertEqual(new_name, 'test_name')
        self.assertIsNot(original_field, new_field)
        self.assertLess(original_field.creation_counter,
                        new_field.creation_counter)
        self.assertLess(new_field.creation_counter,
                        original_field.creation_counter + 1)
        self.assertEqual(original_field.max_length,
                         new_field.max_length)
        self.assertEqual(new_field.db_column, 'dummy_column')
        self.assertEqual(new_field.auxiliary_to, 'dummy value')
        self.assertEqual(new_field.db_tablespace, 'test_tablespace')

    def test_autofield_cloning(self):
        original_field = models.AutoField(primary_key=True)
        clone_result = original_field.clone_for_foreignkey(
            'test_name',
            False,
            'test_tablespace',
            original_field.creation_counter,
            original_field.creation_counter + 1,
            'dummy_column',
        )
        self.assertEqual(len(clone_result), 1)
        new_name, new_field = clone_result[0]
        self.assertIsInstance(new_field, models.IntegerField)
        self.assertFalse(new_field.primary_key)


class AuxiliaryFieldTests(TestCase):
    def create_some_objects(self):
        # Create a few Reporters.
        self.r = Reporter(first_name='John', last_name='Smith', email='john@example.com')
        self.r.save()
        self.r2 = Reporter(first_name='Paul', last_name='Jones', email='paul@example.com')
        self.r2.save()
        # Create an Assignment.
        self.a = Assignment(description='Write an article', assignee=self.r)
        self.a.save()

    def test_aux_created(self):
        fk = Article._meta.get_field('reporter')
        aux = Article._meta.get_field('reporter_id')

        # The aux field should compare more than its owner to ensure
        # correct order of fields.
        self.assertLess(fk, aux)
        self.assertIs(fk.auxiliary_field, aux)
        self.assertIs(aux.auxiliary_to, fk)
        self.assertIsNot(fk, aux)

    def test_aux_not_created_when_specified(self):
        with self.assertRaises(FieldDoesNotExist):
            Assignment._meta.get_field('assignee_id')

        fk = Assignment._meta.get_field('assignee')
        aux = Assignment._meta.get_field('person_id')

        self.assertEqual(fk.attname, aux.name)
        self.assertIs(fk.auxiliary_field, aux)
        self.assertIs(aux.auxiliary_to, fk)

    def test_custom_aux_get(self):
        self.create_some_objects()
        r = self.a.assignee
        self.assertEqual(r.id, self.r.id)
        self.assertEqual((r.first_name, self.r.last_name), ('John', 'Smith'))
        self.assertEqual(self.a.person_id, self.r.id)

    def test_custom_aux_assign(self):
        self.create_some_objects()
        self.assertEqual(self.a.person_id, self.r.pk)

        self.a.assignee = self.r2
        self.a.save()

        self.assertQuerysetEqual(self.r.assignments.all(), [])
        self.assertQuerysetEqual(self.r2.assignments.all(), [
            '<Assignment: Write an article>',
        ])

    def test_custom_aux_join(self):
        self.create_some_objects()
        qs = Reporter.objects.filter(assignments__description__contains='article')
        self.assertQuerysetEqual(qs, ['<Reporter: John Smith>'])
        qs = Reporter.objects.exclude(assignments__description__contains='article')
        self.assertQuerysetEqual(qs, ['<Reporter: Paul Jones>'])

    def test_custom_aux_defer_select_related(self):
        with self.assertRaises(InvalidQuery):
            list(Assignment.objects.defer('person_id').select_related('assignee'))

    def test_custom_aux_select_related(self):
        self.create_some_objects()

        with self.assertNumQueries(1):
            a = Assignment.objects.select_related('assignee').get()
            self.assertEqual(a.pk, self.a.pk)
            self.assertEqual(a.assignee.first_name, self.r.first_name)
            self.assertEqual(a.assignee.last_name, self.r.last_name)
