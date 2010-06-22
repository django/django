from datetime import date

from django.test import TestCase

from models import Article

class CustomMethodsTestCase(TestCase):
    def test_custom_methods(self):
        # Create a couple of Articles.
        a = Article(id=None, headline='Area man programs in Python', pub_date=date(2005, 7, 27))
        a.save()
        b = Article(id=None, headline='Beatles reunite', pub_date=date(2005, 7, 27))
        b.save()

        # Test the custom methods.
        self.assertFalse(a.was_published_today())

        self.assertQuerysetEqual(a.articles_from_same_day_1(),
                                 ['<Article: Beatles reunite>'])
        self.assertQuerysetEqual(a.articles_from_same_day_2(),
                                 ['<Article: Beatles reunite>'])
        self.assertQuerysetEqual(b.articles_from_same_day_1(),
                                 ['<Article: Area man programs in Python>'])
        self.assertQuerysetEqual(b.articles_from_same_day_2(),
                                 ['<Article: Area man programs in Python>'])

