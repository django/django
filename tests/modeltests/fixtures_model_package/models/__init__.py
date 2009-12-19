from django.db import models
from django.conf import settings

class Article(models.Model):
    headline = models.CharField(max_length=100, default='Default headline')
    pub_date = models.DateTimeField()

    def __unicode__(self):
        return self.headline

    class Meta:
        app_label = 'fixtures_model_package'
        ordering = ('-pub_date', 'headline')

__test__ = {'API_TESTS': """
>>> from django.core import management
>>> from django.db.models import get_app

# Reset the database representation of this app.
# This will return the database to a clean initial state.
>>> management.call_command('flush', verbosity=0, interactive=False)

# Syncdb introduces 1 initial data object from initial_data.json.
>>> Article.objects.all()
[<Article: Python program becomes self aware>]

# Load fixture 1. Single JSON file, with two objects.
>>> management.call_command('loaddata', 'fixture1.json', verbosity=0)
>>> Article.objects.all()
[<Article: Time to reform copyright>, <Article: Poker has no place on ESPN>, <Article: Python program becomes self aware>]

# Load fixture 2. JSON file imported by default. Overwrites some existing objects
>>> management.call_command('loaddata', 'fixture2.json', verbosity=0)
>>> Article.objects.all()
[<Article: Django conquers world!>, <Article: Copyright is fine the way it is>, <Article: Poker has no place on ESPN>, <Article: Python program becomes self aware>]

# Load a fixture that doesn't exist
>>> management.call_command('loaddata', 'unknown.json', verbosity=0)

# object list is unaffected
>>> Article.objects.all()
[<Article: Django conquers world!>, <Article: Copyright is fine the way it is>, <Article: Poker has no place on ESPN>, <Article: Python program becomes self aware>]
"""}


from django.test import TestCase

class SampleTestCase(TestCase):
    fixtures = ['fixture1.json', 'fixture2.json']

    def testClassFixtures(self):
        "Check that test case has installed 4 fixture objects"
        self.assertEqual(Article.objects.count(), 4)
        self.assertEquals(str(Article.objects.all()), "[<Article: Django conquers world!>, <Article: Copyright is fine the way it is>, <Article: Poker has no place on ESPN>, <Article: Python program becomes self aware>]")
