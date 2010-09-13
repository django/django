from django.core import management
from django.test import TestCase

from models import Article


class SampleTestCase(TestCase):
    fixtures = ['fixture1.json', 'fixture2.json']

    def testClassFixtures(self):
        "Test cases can load fixture objects into models defined in packages"
        self.assertEqual(Article.objects.count(), 4)
        self.assertQuerysetEqual(
            Article.objects.all(),[
                "Django conquers world!",
                "Copyright is fine the way it is",
                "Poker has no place on ESPN",
                "Python program becomes self aware"
            ],
            lambda a: a.headline
        )


class FixtureTestCase(TestCase):
    def test_initial_data(self):
        "Fixtures can load initial data into models defined in packages"
        #Syncdb introduces 1 initial data object from initial_data.json
        self.assertQuerysetEqual(
            Article.objects.all(), [
                "Python program becomes self aware"
            ],
            lambda a: a.headline
        )

    def test_loaddata(self):
        "Fixtures can load data into models defined in packages"
        # Load fixture 1. Single JSON file, with two objects
        management.call_command("loaddata", "fixture1.json", verbosity=0, commit=False)
        self.assertQuerysetEqual(
            Article.objects.all(), [
                "Time to reform copyright",
                "Poker has no place on ESPN",
                "Python program becomes self aware",
            ],
            lambda a: a.headline,
        )

        # Load fixture 2. JSON file imported by default. Overwrites some
        # existing objects
        management.call_command("loaddata", "fixture2.json", verbosity=0, commit=False)
        self.assertQuerysetEqual(
            Article.objects.all(), [
                "Django conquers world!",
                "Copyright is fine the way it is",
                "Poker has no place on ESPN",
                "Python program becomes self aware",
            ],
            lambda a: a.headline,
        )

        # Load a fixture that doesn't exist
        management.call_command("loaddata", "unknown.json", verbosity=0, commit=False)
        self.assertQuerysetEqual(
            Article.objects.all(), [
                "Django conquers world!",
                "Copyright is fine the way it is",
                "Poker has no place on ESPN",
                "Python program becomes self aware",
            ],
            lambda a: a.headline,
        )
