from django.test import TestCase

from django.core.exceptions import FieldError

from models import Author, Article

class CustomColumnsTestCase(TestCase):
    fixtures = ['custom_columns_testdata.json']

    def test_column_interface(self):
        # Although the table and column names on Author have been set to
        # custom values, nothing about using the Author model has
        # changed...
        self.assertEqual(Author.objects.get(first_name='John').id,
                         1)

        # Query the available authors
        self.assertQuerysetEqual(Author.objects.all(),
                                 ['<Author: Peter Jones>', '<Author: John Smith>'])
        self.assertQuerysetEqual(Author.objects.filter(first_name__exact='John'),
                                 ['<Author: John Smith>'])
        self.assertEqual(repr(Author.objects.get(first_name__exact='John')),
                         '<Author: John Smith>')
        self.assertRaises(FieldError,
                          Author.objects.filter,
                          firstname__exact='John')

        js = Author.objects.get(last_name__exact='Smith')

        self.assertEqual(js.first_name,
                         u'John')
        self.assertEqual(js.last_name,
                         u'Smith')
        self.assertRaises(AttributeError,
                          getattr,
                          js, 'firstname')
        self.assertRaises(AttributeError,
                          getattr,
                          js, 'last')

        # Although the Article table uses a custom m2m table,
        # nothing about using the m2m relationship has changed...

        # Get all the authors for an article
        art = Article.objects.get(headline='Django lets you build web apps easily')
        self.assertQuerysetEqual(art.authors.all(),
                                 ['<Author: Peter Jones>', '<Author: John Smith>'])
        # Get the articles for an author
        self.assertQuerysetEqual(js.article_set.all(),
                                 ['<Article: Django lets you build web apps easily>'])
        # Query the authors across the m2m relation
        self.assertQuerysetEqual(art.authors.filter(last_name='Jones'),
                                 ['<Author: Peter Jones>'])
