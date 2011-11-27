from django.core import management
from django.test import TestCase

from .models import Article, Book


class SampleTestCase(TestCase):
    fixtures = ['fixture1.json', 'fixture2.json']

    def testClassFixtures(self):
        "Test cases can load fixture objects into models defined in packages"
        self.assertEqual(Article.objects.count(), 3)
        self.assertQuerysetEqual(
            Article.objects.all(),[
                u"Django conquers world!",
                u"Copyright is fine the way it is",
                u"Poker has no place on ESPN",
            ],
            lambda a: a.headline
        )


class FixtureTestCase(TestCase):
    def test_initial_data(self):
        "Fixtures can load initial data into models defined in packages"
        # syncdb introduces 1 initial data object from initial_data.json
        self.assertQuerysetEqual(
            Book.objects.all(), [
                u'Achieving self-awareness of Python programs'
            ],
            lambda a: a.name
        )

    def test_loaddata(self):
        "Fixtures can load data into models defined in packages"
        # Load fixture 1. Single JSON file, with two objects
        management.call_command("loaddata", "fixture1.json", verbosity=0, commit=False)
        self.assertQuerysetEqual(
            Article.objects.all(), [
                u"Time to reform copyright",
                u"Poker has no place on ESPN",
            ],
            lambda a: a.headline,
        )

        # Load fixture 2. JSON file imported by default. Overwrites some
        # existing objects
        management.call_command("loaddata", "fixture2.json", verbosity=0, commit=False)
        self.assertQuerysetEqual(
            Article.objects.all(), [
                u"Django conquers world!",
                u"Copyright is fine the way it is",
                u"Poker has no place on ESPN",
            ],
            lambda a: a.headline,
        )

        # Load a fixture that doesn't exist
        management.call_command("loaddata", "unknown.json", verbosity=0, commit=False)
        self.assertQuerysetEqual(
            Article.objects.all(), [
                u"Django conquers world!",
                u"Copyright is fine the way it is",
                u"Poker has no place on ESPN",
            ],
            lambda a: a.headline,
        )
