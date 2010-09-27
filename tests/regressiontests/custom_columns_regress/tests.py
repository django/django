from django.test import TestCase
from django.core.exceptions import FieldError

from models import Author, Article

def pks(objects):
    """ Return pks to be able to compare lists"""
    return [o.pk for o in objects]

class CustomColumnRegression(TestCase):

    def assertRaisesMessage(self, exc, msg, func, *args, **kwargs):
        try:
            func(*args, **kwargs)
        except Exception, e:
            self.assertEqual(msg, str(e))
            self.assertTrue(isinstance(e, exc), "Expected %s, got %s" % (exc, type(e)))

    def setUp(self):
        self.a1 = Author.objects.create(first_name='John', last_name='Smith')
        self.a2 = Author.objects.create(first_name='Peter', last_name='Jones')
        self.authors = [self.a1, self.a2]

    def test_basic_creation(self):
        self.assertEqual(self.a1.Author_ID, 1)

        art = Article(headline='Django lets you build web apps easily', primary_author=self.a1)
        art.save()
        art.authors = [self.a1, self.a2]

    def test_author_querying(self):
        self.assertQuerysetEqual(
            Author.objects.all().order_by('last_name'),
            ['<Author: Peter Jones>', '<Author: John Smith>']
        )

    def test_author_filtering(self):
        self.assertQuerysetEqual(
            Author.objects.filter(first_name__exact='John'),
            ['<Author: John Smith>']
        )

    def test_author_get(self):
        self.assertEqual(self.a1, Author.objects.get(first_name__exact='John'))

    def test_filter_on_nonexistant_field(self):
        self.assertRaisesMessage(
            FieldError,
            "Cannot resolve keyword 'firstname' into field. Choices are: Author_ID, article, first_name, last_name, primary_set",
            Author.objects.filter,
            firstname__exact='John'
        )

    def test_author_get_attributes(self):
        a = Author.objects.get(last_name__exact='Smith')
        self.assertEqual('John', a.first_name)
        self.assertEqual('Smith', a.last_name)
        self.assertRaisesMessage(
            AttributeError,
            "'Author' object has no attribute 'firstname'",
            getattr,
            a, 'firstname'
        )

        self.assertRaisesMessage(
            AttributeError,
            "'Author' object has no attribute 'last'",
            getattr,
            a, 'last'
        )

    def test_m2m_table(self):
        art = Article.objects.create(headline='Django lets you build web apps easily', primary_author=self.a1)
        art.authors = self.authors
        self.assertQuerysetEqual(
            art.authors.all().order_by('last_name'),
            ['<Author: Peter Jones>', '<Author: John Smith>']
        )
        self.assertQuerysetEqual(
            self.a1.article_set.all(),
            ['<Article: Django lets you build web apps easily>']
        )
        self.assertQuerysetEqual(
            art.authors.filter(last_name='Jones'),
            ['<Author: Peter Jones>']
        )
