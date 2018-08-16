from datetime import datetime, timedelta

from django.db.models import CharField, Value as V
from django.db.models.functions import Coalesce, Length, Now, Upper
from django.test import TestCase
from django.utils import timezone

from .models import Article, Author

lorem_ipsum = """
    Lorem ipsum dolor sit amet, consectetur adipiscing elit, sed do eiusmod
    tempor incididunt ut labore et dolore magna aliqua."""


class FunctionTests(TestCase):

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

    def test_func_transform_bilateral(self):
        class UpperBilateral(Upper):
            bilateral = True

        try:
            CharField.register_lookup(UpperBilateral)
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
            CharField._unregister_lookup(UpperBilateral)

    def test_func_transform_bilateral_multivalue(self):
        class UpperBilateral(Upper):
            bilateral = True

        try:
            CharField.register_lookup(UpperBilateral)
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
            CharField._unregister_lookup(UpperBilateral)

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
