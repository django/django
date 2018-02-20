from datetime import datetime, timedelta
from decimal import Decimal
from unittest import skipIf, skipUnless

from django.db import connection
from django.db.models import CharField, TextField, Value as V
from django.db.models.expressions import RawSQL
from django.db.models.functions import (
    Coalesce, Concat, ConcatPair, Greatest, Least, Length, Lower, Now, Substr,
    Upper,
)
from django.test import TestCase, skipIfDBFeature, skipUnlessDBFeature
from django.utils import timezone

from .models import Article, Author, DecimalModel, Fan

lorem_ipsum = """
    Lorem ipsum dolor sit amet, consectetur adipiscing elit, sed do eiusmod
    tempor incididunt ut labore et dolore magna aliqua."""


def truncate_microseconds(value):
    return value if connection.features.supports_microsecond_precision else value.replace(microsecond=0)


class FunctionTests(TestCase):

    def test_coalesce(self):
        Author.objects.create(name='John Smith', alias='smithj')
        Author.objects.create(name='Rhonda')
        authors = Author.objects.annotate(display_name=Coalesce('alias', 'name'))

        self.assertQuerysetEqual(
            authors.order_by('name'), [
                'smithj',
                'Rhonda',
            ],
            lambda a: a.display_name
        )

        with self.assertRaisesMessage(ValueError, 'Coalesce must take at least two expressions'):
            Author.objects.annotate(display_name=Coalesce('alias'))

    def test_coalesce_mixed_values(self):
        a1 = Author.objects.create(name='John Smith', alias='smithj')
        a2 = Author.objects.create(name='Rhonda')
        ar1 = Article.objects.create(
            title="How to Django",
            text=lorem_ipsum,
            written=timezone.now(),
        )
        ar1.authors.add(a1)
        ar1.authors.add(a2)

        # mixed Text and Char
        article = Article.objects.annotate(
            headline=Coalesce('summary', 'text', output_field=TextField()),
        )

        self.assertQuerysetEqual(
            article.order_by('title'), [
                lorem_ipsum,
            ],
            lambda a: a.headline
        )

        # mixed Text and Char wrapped
        article = Article.objects.annotate(
            headline=Coalesce(Lower('summary'), Lower('text'), output_field=TextField()),
        )

        self.assertQuerysetEqual(
            article.order_by('title'), [
                lorem_ipsum.lower(),
            ],
            lambda a: a.headline
        )

    def test_coalesce_ordering(self):
        Author.objects.create(name='John Smith', alias='smithj')
        Author.objects.create(name='Rhonda')

        authors = Author.objects.order_by(Coalesce('alias', 'name'))
        self.assertQuerysetEqual(
            authors, [
                'Rhonda',
                'John Smith',
            ],
            lambda a: a.name
        )

        authors = Author.objects.order_by(Coalesce('alias', 'name').asc())
        self.assertQuerysetEqual(
            authors, [
                'Rhonda',
                'John Smith',
            ],
            lambda a: a.name
        )

        authors = Author.objects.order_by(Coalesce('alias', 'name').desc())
        self.assertQuerysetEqual(
            authors, [
                'John Smith',
                'Rhonda',
            ],
            lambda a: a.name
        )

    def test_greatest(self):
        now = timezone.now()
        before = now - timedelta(hours=1)

        Article.objects.create(
            title="Testing with Django",
            written=before,
            published=now,
        )

        articles = Article.objects.annotate(
            last_updated=Greatest('written', 'published'),
        )
        self.assertEqual(articles.first().last_updated, truncate_microseconds(now))

    @skipUnlessDBFeature('greatest_least_ignores_nulls')
    def test_greatest_ignores_null(self):
        now = timezone.now()

        Article.objects.create(title="Testing with Django", written=now)

        articles = Article.objects.annotate(
            last_updated=Greatest('written', 'published'),
        )
        self.assertEqual(articles.first().last_updated, now)

    @skipIfDBFeature('greatest_least_ignores_nulls')
    def test_greatest_propagates_null(self):
        now = timezone.now()

        Article.objects.create(title="Testing with Django", written=now)

        articles = Article.objects.annotate(
            last_updated=Greatest('written', 'published'),
        )
        self.assertIsNone(articles.first().last_updated)

    @skipIf(connection.vendor == 'mysql', "This doesn't work on MySQL")
    def test_greatest_coalesce_workaround(self):
        past = datetime(1900, 1, 1)
        now = timezone.now()

        Article.objects.create(title="Testing with Django", written=now)

        articles = Article.objects.annotate(
            last_updated=Greatest(
                Coalesce('written', past),
                Coalesce('published', past),
            ),
        )
        self.assertEqual(articles.first().last_updated, now)

    @skipUnless(connection.vendor == 'mysql', "MySQL-specific workaround")
    def test_greatest_coalesce_workaround_mysql(self):
        past = datetime(1900, 1, 1)
        now = timezone.now()

        Article.objects.create(title="Testing with Django", written=now)

        past_sql = RawSQL("cast(%s as datetime)", (past,))
        articles = Article.objects.annotate(
            last_updated=Greatest(
                Coalesce('written', past_sql),
                Coalesce('published', past_sql),
            ),
        )
        self.assertEqual(articles.first().last_updated, truncate_microseconds(now))

    def test_greatest_all_null(self):
        Article.objects.create(title="Testing with Django", written=timezone.now())

        articles = Article.objects.annotate(last_updated=Greatest('published', 'updated'))
        self.assertIsNone(articles.first().last_updated)

    def test_greatest_one_expressions(self):
        with self.assertRaisesMessage(ValueError, 'Greatest must take at least two expressions'):
            Greatest('written')

    def test_greatest_related_field(self):
        author = Author.objects.create(name='John Smith', age=45)
        Fan.objects.create(name='Margaret', age=50, author=author)

        authors = Author.objects.annotate(
            highest_age=Greatest('age', 'fans__age'),
        )
        self.assertEqual(authors.first().highest_age, 50)

    def test_greatest_update(self):
        author = Author.objects.create(name='James Smith', goes_by='Jim')

        Author.objects.update(alias=Greatest('name', 'goes_by'))

        author.refresh_from_db()
        self.assertEqual(author.alias, 'Jim')

    def test_greatest_decimal_filter(self):
        obj = DecimalModel.objects.create(n1=Decimal('1.1'), n2=Decimal('1.2'))
        self.assertCountEqual(
            DecimalModel.objects.annotate(
                greatest=Greatest('n1', 'n2'),
            ).filter(greatest=Decimal('1.2')),
            [obj],
        )

    def test_least(self):
        now = timezone.now()
        before = now - timedelta(hours=1)

        Article.objects.create(
            title="Testing with Django",
            written=before,
            published=now,
        )

        articles = Article.objects.annotate(
            first_updated=Least('written', 'published'),
        )
        self.assertEqual(articles.first().first_updated, truncate_microseconds(before))

    @skipUnlessDBFeature('greatest_least_ignores_nulls')
    def test_least_ignores_null(self):
        now = timezone.now()

        Article.objects.create(title="Testing with Django", written=now)

        articles = Article.objects.annotate(
            first_updated=Least('written', 'published'),
        )
        self.assertEqual(articles.first().first_updated, now)

    @skipIfDBFeature('greatest_least_ignores_nulls')
    def test_least_propagates_null(self):
        now = timezone.now()

        Article.objects.create(title="Testing with Django", written=now)

        articles = Article.objects.annotate(
            first_updated=Least('written', 'published'),
        )
        self.assertIsNone(articles.first().first_updated)

    @skipIf(connection.vendor == 'mysql', "This doesn't work on MySQL")
    def test_least_coalesce_workaround(self):
        future = datetime(2100, 1, 1)
        now = timezone.now()

        Article.objects.create(title="Testing with Django", written=now)

        articles = Article.objects.annotate(
            last_updated=Least(
                Coalesce('written', future),
                Coalesce('published', future),
            ),
        )
        self.assertEqual(articles.first().last_updated, now)

    @skipUnless(connection.vendor == 'mysql', "MySQL-specific workaround")
    def test_least_coalesce_workaround_mysql(self):
        future = datetime(2100, 1, 1)
        now = timezone.now()

        Article.objects.create(title="Testing with Django", written=now)

        future_sql = RawSQL("cast(%s as datetime)", (future,))
        articles = Article.objects.annotate(
            last_updated=Least(
                Coalesce('written', future_sql),
                Coalesce('published', future_sql),
            ),
        )
        self.assertEqual(articles.first().last_updated, truncate_microseconds(now))

    def test_least_all_null(self):
        Article.objects.create(title="Testing with Django", written=timezone.now())

        articles = Article.objects.annotate(first_updated=Least('published', 'updated'))
        self.assertIsNone(articles.first().first_updated)

    def test_least_one_expressions(self):
        with self.assertRaisesMessage(ValueError, 'Least must take at least two expressions'):
            Least('written')

    def test_least_related_field(self):
        author = Author.objects.create(name='John Smith', age=45)
        Fan.objects.create(name='Margaret', age=50, author=author)

        authors = Author.objects.annotate(
            lowest_age=Least('age', 'fans__age'),
        )
        self.assertEqual(authors.first().lowest_age, 45)

    def test_least_update(self):
        author = Author.objects.create(name='James Smith', goes_by='Jim')

        Author.objects.update(alias=Least('name', 'goes_by'))

        author.refresh_from_db()
        self.assertEqual(author.alias, 'James Smith')

    def test_least_decimal_filter(self):
        obj = DecimalModel.objects.create(n1=Decimal('1.1'), n2=Decimal('1.2'))
        self.assertCountEqual(
            DecimalModel.objects.annotate(
                least=Least('n1', 'n2'),
            ).filter(least=Decimal('1.1')),
            [obj],
        )

    def test_concat(self):
        Author.objects.create(name='Jayden')
        Author.objects.create(name='John Smith', alias='smithj', goes_by='John')
        Author.objects.create(name='Margaret', goes_by='Maggie')
        Author.objects.create(name='Rhonda', alias='adnohR')

        authors = Author.objects.annotate(joined=Concat('alias', 'goes_by'))
        self.assertQuerysetEqual(
            authors.order_by('name'), [
                '',
                'smithjJohn',
                'Maggie',
                'adnohR',
            ],
            lambda a: a.joined
        )

        with self.assertRaisesMessage(ValueError, 'Concat must take at least two expressions'):
            Author.objects.annotate(joined=Concat('alias'))

    def test_concat_many(self):
        Author.objects.create(name='Jayden')
        Author.objects.create(name='John Smith', alias='smithj', goes_by='John')
        Author.objects.create(name='Margaret', goes_by='Maggie')
        Author.objects.create(name='Rhonda', alias='adnohR')

        authors = Author.objects.annotate(
            joined=Concat('name', V(' ('), 'goes_by', V(')'), output_field=CharField()),
        )

        self.assertQuerysetEqual(
            authors.order_by('name'), [
                'Jayden ()',
                'John Smith (John)',
                'Margaret (Maggie)',
                'Rhonda ()',
            ],
            lambda a: a.joined
        )

    def test_concat_mixed_char_text(self):
        Article.objects.create(title='The Title', text=lorem_ipsum, written=timezone.now())
        article = Article.objects.annotate(
            title_text=Concat('title', V(' - '), 'text', output_field=TextField()),
        ).get(title='The Title')
        self.assertEqual(article.title + ' - ' + article.text, article.title_text)

        # wrap the concat in something else to ensure that we're still
        # getting text rather than bytes
        article = Article.objects.annotate(
            title_text=Upper(Concat('title', V(' - '), 'text', output_field=TextField())),
        ).get(title='The Title')
        expected = article.title + ' - ' + article.text
        self.assertEqual(expected.upper(), article.title_text)

    @skipUnless(connection.vendor == 'sqlite', "sqlite specific implementation detail.")
    def test_concat_coalesce_idempotent(self):
        pair = ConcatPair(V('a'), V('b'))
        # Check nodes counts
        self.assertEqual(len(list(pair.flatten())), 3)
        self.assertEqual(len(list(pair.coalesce().flatten())), 7)  # + 2 Coalesce + 2 Value()
        self.assertEqual(len(list(pair.flatten())), 3)

    def test_concat_sql_generation_idempotency(self):
        qs = Article.objects.annotate(description=Concat('title', V(': '), 'summary'))
        # Multiple compilations should not alter the generated query.
        self.assertEqual(str(qs.query), str(qs.all().query))

    def test_lower(self):
        Author.objects.create(name='John Smith', alias='smithj')
        Author.objects.create(name='Rhonda')
        authors = Author.objects.annotate(lower_name=Lower('name'))

        self.assertQuerysetEqual(
            authors.order_by('name'), [
                'john smith',
                'rhonda',
            ],
            lambda a: a.lower_name
        )

        Author.objects.update(name=Lower('name'))
        self.assertQuerysetEqual(
            authors.order_by('name'), [
                ('john smith', 'john smith'),
                ('rhonda', 'rhonda'),
            ],
            lambda a: (a.lower_name, a.name)
        )

        with self.assertRaisesMessage(TypeError, "'Lower' takes exactly 1 argument (2 given)"):
            Author.objects.update(name=Lower('name', 'name'))

    def test_upper(self):
        Author.objects.create(name='John Smith', alias='smithj')
        Author.objects.create(name='Rhonda')
        authors = Author.objects.annotate(upper_name=Upper('name'))

        self.assertQuerysetEqual(
            authors.order_by('name'), [
                'JOHN SMITH',
                'RHONDA',
            ],
            lambda a: a.upper_name
        )

        Author.objects.update(name=Upper('name'))
        self.assertQuerysetEqual(
            authors.order_by('name'), [
                ('JOHN SMITH', 'JOHN SMITH'),
                ('RHONDA', 'RHONDA'),
            ],
            lambda a: (a.upper_name, a.name)
        )

    def test_length(self):
        Author.objects.create(name='John Smith', alias='smithj')
        Author.objects.create(name='Rhonda')
        authors = Author.objects.annotate(
            name_length=Length('name'),
            alias_length=Length('alias'))

        self.assertQuerysetEqual(
            authors.order_by('name'), [
                (10, 6),
                (6, None),
            ],
            lambda a: (a.name_length, a.alias_length)
        )

        self.assertEqual(authors.filter(alias_length__lte=Length('name')).count(), 1)

    def test_length_ordering(self):
        Author.objects.create(name='John Smith', alias='smithj')
        Author.objects.create(name='John Smith', alias='smithj1')
        Author.objects.create(name='Rhonda', alias='ronny')

        authors = Author.objects.order_by(Length('name'), Length('alias'))

        self.assertQuerysetEqual(
            authors, [
                ('Rhonda', 'ronny'),
                ('John Smith', 'smithj'),
                ('John Smith', 'smithj1'),
            ],
            lambda a: (a.name, a.alias)
        )

    def test_substr(self):
        Author.objects.create(name='John Smith', alias='smithj')
        Author.objects.create(name='Rhonda')
        authors = Author.objects.annotate(name_part=Substr('name', 5, 3))

        self.assertQuerysetEqual(
            authors.order_by('name'), [
                ' Sm',
                'da',
            ],
            lambda a: a.name_part
        )

        authors = Author.objects.annotate(name_part=Substr('name', 2))
        self.assertQuerysetEqual(
            authors.order_by('name'), [
                'ohn Smith',
                'honda',
            ],
            lambda a: a.name_part
        )

        # if alias is null, set to first 5 lower characters of the name
        Author.objects.filter(alias__isnull=True).update(
            alias=Lower(Substr('name', 1, 5)),
        )

        self.assertQuerysetEqual(
            authors.order_by('name'), [
                'smithj',
                'rhond',
            ],
            lambda a: a.alias
        )

    def test_substr_start(self):
        Author.objects.create(name='John Smith', alias='smithj')
        a = Author.objects.annotate(
            name_part_1=Substr('name', 1),
            name_part_2=Substr('name', 2),
        ).get(alias='smithj')

        self.assertEqual(a.name_part_1[1:], a.name_part_2)

        with self.assertRaisesMessage(ValueError, "'pos' must be greater than 0"):
            Author.objects.annotate(raises=Substr('name', 0))

    def test_substr_with_expressions(self):
        Author.objects.create(name='John Smith', alias='smithj')
        Author.objects.create(name='Rhonda')
        authors = Author.objects.annotate(name_part=Substr('name', 5, 3))
        self.assertQuerysetEqual(
            authors.order_by('name'), [
                ' Sm',
                'da',
            ],
            lambda a: a.name_part
        )

    def test_nested_function_ordering(self):
        Author.objects.create(name='John Smith')
        Author.objects.create(name='Rhonda Simpson', alias='ronny')

        authors = Author.objects.order_by(Length(Coalesce('alias', 'name')))
        self.assertQuerysetEqual(
            authors, [
                'Rhonda Simpson',
                'John Smith',
            ],
            lambda a: a.name
        )

        authors = Author.objects.order_by(Length(Coalesce('alias', 'name')).desc())
        self.assertQuerysetEqual(
            authors, [
                'John Smith',
                'Rhonda Simpson',
            ],
            lambda a: a.name
        )

    def test_now(self):
        ar1 = Article.objects.create(
            title='How to Django',
            text=lorem_ipsum,
            written=timezone.now(),
        )
        ar2 = Article.objects.create(
            title='How to Time Travel',
            text=lorem_ipsum,
            written=timezone.now(),
        )

        num_updated = Article.objects.filter(id=ar1.id, published=None).update(published=Now())
        self.assertEqual(num_updated, 1)

        num_updated = Article.objects.filter(id=ar1.id, published=None).update(published=Now())
        self.assertEqual(num_updated, 0)

        ar1.refresh_from_db()
        self.assertIsInstance(ar1.published, datetime)

        ar2.published = Now() + timedelta(days=2)
        ar2.save()
        ar2.refresh_from_db()
        self.assertIsInstance(ar2.published, datetime)

        self.assertQuerysetEqual(
            Article.objects.filter(published__lte=Now()),
            ['How to Django'],
            lambda a: a.title
        )
        self.assertQuerysetEqual(
            Article.objects.filter(published__gt=Now()),
            ['How to Time Travel'],
            lambda a: a.title
        )

    def test_length_transform(self):
        try:
            CharField.register_lookup(Length, 'length')
            Author.objects.create(name='John Smith', alias='smithj')
            Author.objects.create(name='Rhonda')
            authors = Author.objects.filter(name__length__gt=7)
            self.assertQuerysetEqual(
                authors.order_by('name'), [
                    'John Smith',
                ],
                lambda a: a.name
            )
        finally:
            CharField._unregister_lookup(Length, 'length')

    def test_lower_transform(self):
        try:
            CharField.register_lookup(Lower, 'lower')
            Author.objects.create(name='John Smith', alias='smithj')
            Author.objects.create(name='Rhonda')
            authors = Author.objects.filter(name__lower__exact='john smith')
            self.assertQuerysetEqual(
                authors.order_by('name'), [
                    'John Smith',
                ],
                lambda a: a.name
            )
        finally:
            CharField._unregister_lookup(Lower, 'lower')

    def test_upper_transform(self):
        try:
            CharField.register_lookup(Upper, 'upper')
            Author.objects.create(name='John Smith', alias='smithj')
            Author.objects.create(name='Rhonda')
            authors = Author.objects.filter(name__upper__exact='JOHN SMITH')
            self.assertQuerysetEqual(
                authors.order_by('name'), [
                    'John Smith',
                ],
                lambda a: a.name
            )
        finally:
            CharField._unregister_lookup(Upper, 'upper')

    def test_func_transform_bilateral(self):
        class UpperBilateral(Upper):
            bilateral = True

        try:
            CharField.register_lookup(UpperBilateral, 'upper')
            Author.objects.create(name='John Smith', alias='smithj')
            Author.objects.create(name='Rhonda')
            authors = Author.objects.filter(name__upper__exact='john smith')
            self.assertQuerysetEqual(
                authors.order_by('name'), [
                    'John Smith',
                ],
                lambda a: a.name
            )
        finally:
            CharField._unregister_lookup(UpperBilateral, 'upper')

    def test_func_transform_bilateral_multivalue(self):
        class UpperBilateral(Upper):
            bilateral = True

        try:
            CharField.register_lookup(UpperBilateral, 'upper')
            Author.objects.create(name='John Smith', alias='smithj')
            Author.objects.create(name='Rhonda')
            authors = Author.objects.filter(name__upper__in=['john smith', 'rhonda'])
            self.assertQuerysetEqual(
                authors.order_by('name'), [
                    'John Smith',
                    'Rhonda',
                ],
                lambda a: a.name
            )
        finally:
            CharField._unregister_lookup(UpperBilateral, 'upper')

    def test_function_as_filter(self):
        Author.objects.create(name='John Smith', alias='SMITHJ')
        Author.objects.create(name='Rhonda')
        self.assertQuerysetEqual(
            Author.objects.filter(alias=Upper(V('smithj'))),
            ['John Smith'], lambda x: x.name
        )
        self.assertQuerysetEqual(
            Author.objects.exclude(alias=Upper(V('smithj'))),
            ['Rhonda'], lambda x: x.name
        )
