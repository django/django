"""
37. Fixtures.

Fixtures are a way of loading data into the database in bulk. Fixure data
can be stored in any serializable format (including JSON and XML). Fixtures
are identified by name, and are stored in either a directory named 'fixtures'
in the application directory, on in one of the directories named in the
``FIXTURE_DIRS`` setting.
"""

from django.db import models
from django.conf import settings

class Category(models.Model):
    title = models.CharField(max_length=100)
    description = models.TextField()

    def __unicode__(self):
        return self.title

    class Meta:
        ordering = ('title',)

class Article(models.Model):
    headline = models.CharField(max_length=100, default='Default headline')
    pub_date = models.DateTimeField()

    def __unicode__(self):
        return self.headline

    class Meta:
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

# Dump the current contents of the database as a JSON fixture
>>> management.call_command('dumpdata', 'fixtures', format='json')
[{"pk": 1, "model": "fixtures.category", "fields": {"description": "Latest news stories", "title": "News Stories"}}, {"pk": 3, "model": "fixtures.article", "fields": {"headline": "Time to reform copyright", "pub_date": "2006-06-16 13:00:00"}}, {"pk": 2, "model": "fixtures.article", "fields": {"headline": "Poker has no place on ESPN", "pub_date": "2006-06-16 12:00:00"}}, {"pk": 1, "model": "fixtures.article", "fields": {"headline": "Python program becomes self aware", "pub_date": "2006-06-16 11:00:00"}}]

# Try just dumping the contents of fixtures.Category
>>> management.call_command('dumpdata', 'fixtures.Category', format='json')
[{"pk": 1, "model": "fixtures.category", "fields": {"description": "Latest news stories", "title": "News Stories"}}]

# ...and just fixtures.Article
>>> management.call_command('dumpdata', 'fixtures.Article', format='json')
[{"pk": 3, "model": "fixtures.article", "fields": {"headline": "Time to reform copyright", "pub_date": "2006-06-16 13:00:00"}}, {"pk": 2, "model": "fixtures.article", "fields": {"headline": "Poker has no place on ESPN", "pub_date": "2006-06-16 12:00:00"}}, {"pk": 1, "model": "fixtures.article", "fields": {"headline": "Python program becomes self aware", "pub_date": "2006-06-16 11:00:00"}}]

# ...and both
>>> management.call_command('dumpdata', 'fixtures.Category', 'fixtures.Article', format='json')
[{"pk": 1, "model": "fixtures.category", "fields": {"description": "Latest news stories", "title": "News Stories"}}, {"pk": 3, "model": "fixtures.article", "fields": {"headline": "Time to reform copyright", "pub_date": "2006-06-16 13:00:00"}}, {"pk": 2, "model": "fixtures.article", "fields": {"headline": "Poker has no place on ESPN", "pub_date": "2006-06-16 12:00:00"}}, {"pk": 1, "model": "fixtures.article", "fields": {"headline": "Python program becomes self aware", "pub_date": "2006-06-16 11:00:00"}}]

# Specify a specific model twice
>>> management.call_command('dumpdata', 'fixtures.Article', 'fixtures.Article', format='json')
[{"pk": 3, "model": "fixtures.article", "fields": {"headline": "Time to reform copyright", "pub_date": "2006-06-16 13:00:00"}}, {"pk": 2, "model": "fixtures.article", "fields": {"headline": "Poker has no place on ESPN", "pub_date": "2006-06-16 12:00:00"}}, {"pk": 1, "model": "fixtures.article", "fields": {"headline": "Python program becomes self aware", "pub_date": "2006-06-16 11:00:00"}}]

# Specify a dump that specifies Article both explicitly and implicitly
>>> management.call_command('dumpdata', 'fixtures.Article', 'fixtures', format='json')
[{"pk": 1, "model": "fixtures.category", "fields": {"description": "Latest news stories", "title": "News Stories"}}, {"pk": 3, "model": "fixtures.article", "fields": {"headline": "Time to reform copyright", "pub_date": "2006-06-16 13:00:00"}}, {"pk": 2, "model": "fixtures.article", "fields": {"headline": "Poker has no place on ESPN", "pub_date": "2006-06-16 12:00:00"}}, {"pk": 1, "model": "fixtures.article", "fields": {"headline": "Python program becomes self aware", "pub_date": "2006-06-16 11:00:00"}}]

# Same again, but specify in the reverse order
>>> management.call_command('dumpdata', 'fixtures', 'fixtures.Article', format='json')
[{"pk": 1, "model": "fixtures.category", "fields": {"description": "Latest news stories", "title": "News Stories"}}, {"pk": 3, "model": "fixtures.article", "fields": {"headline": "Time to reform copyright", "pub_date": "2006-06-16 13:00:00"}}, {"pk": 2, "model": "fixtures.article", "fields": {"headline": "Poker has no place on ESPN", "pub_date": "2006-06-16 12:00:00"}}, {"pk": 1, "model": "fixtures.article", "fields": {"headline": "Python program becomes self aware", "pub_date": "2006-06-16 11:00:00"}}]

# Specify one model from one application, and an entire other application.
>>> management.call_command('dumpdata', 'fixtures.Category', 'sites', format='json')
[{"pk": 1, "model": "fixtures.category", "fields": {"description": "Latest news stories", "title": "News Stories"}}, {"pk": 1, "model": "sites.site", "fields": {"domain": "example.com", "name": "example.com"}}]

# Load fixture 2. JSON file imported by default. Overwrites some existing objects
>>> management.call_command('loaddata', 'fixture2.json', verbosity=0)
>>> Article.objects.all()
[<Article: Django conquers world!>, <Article: Copyright is fine the way it is>, <Article: Poker has no place on ESPN>, <Article: Python program becomes self aware>]

# Load fixture 3, XML format.
>>> management.call_command('loaddata', 'fixture3.xml', verbosity=0)
>>> Article.objects.all()
[<Article: XML identified as leading cause of cancer>, <Article: Django conquers world!>, <Article: Copyright is fine the way it is>, <Article: Poker on TV is great!>, <Article: Python program becomes self aware>]

# Load a fixture that doesn't exist
>>> management.call_command('loaddata', 'unknown.json', verbosity=0)

# object list is unaffected
>>> Article.objects.all()
[<Article: XML identified as leading cause of cancer>, <Article: Django conquers world!>, <Article: Copyright is fine the way it is>, <Article: Poker on TV is great!>, <Article: Python program becomes self aware>]
"""}

# Database flushing does not work on MySQL with the default storage engine
# because it requires transaction support.
if settings.DATABASE_ENGINE != 'mysql':
    __test__['API_TESTS'] += \
"""
# Reset the database representation of this app. This will delete all data.
>>> management.call_command('flush', verbosity=0, interactive=False)
>>> Article.objects.all()
[<Article: Python program becomes self aware>]

# Load fixture 1 again, using format discovery
>>> management.call_command('loaddata', 'fixture1', verbosity=0)
>>> Article.objects.all()
[<Article: Time to reform copyright>, <Article: Poker has no place on ESPN>, <Article: Python program becomes self aware>]

# Try to load fixture 2 using format discovery; this will fail
# because there are two fixture2's in the fixtures directory
>>> management.call_command('loaddata', 'fixture2', verbosity=0) # doctest: +ELLIPSIS
Multiple fixtures named 'fixture2' in '...fixtures'. Aborting.

# object list is unaffected
>>> Article.objects.all()
[<Article: Time to reform copyright>, <Article: Poker has no place on ESPN>, <Article: Python program becomes self aware>]

# Dump the current contents of the database as a JSON fixture
>>> management.call_command('dumpdata', 'fixtures', format='json')
[{"pk": 1, "model": "fixtures.category", "fields": {"description": "Latest news stories", "title": "News Stories"}}, {"pk": 3, "model": "fixtures.article", "fields": {"headline": "Time to reform copyright", "pub_date": "2006-06-16 13:00:00"}}, {"pk": 2, "model": "fixtures.article", "fields": {"headline": "Poker has no place on ESPN", "pub_date": "2006-06-16 12:00:00"}}, {"pk": 1, "model": "fixtures.article", "fields": {"headline": "Python program becomes self aware", "pub_date": "2006-06-16 11:00:00"}}]

# Load fixture 4 (compressed), using format discovery
>>> management.call_command('loaddata', 'fixture4', verbosity=0)
>>> Article.objects.all()
[<Article: Django pets kitten>, <Article: Time to reform copyright>, <Article: Poker has no place on ESPN>, <Article: Python program becomes self aware>]

>>> management.call_command('flush', verbosity=0, interactive=False)

# Load fixture 4 (compressed), using format specification
>>> management.call_command('loaddata', 'fixture4.json', verbosity=0)
>>> Article.objects.all()
[<Article: Django pets kitten>, <Article: Python program becomes self aware>]

>>> management.call_command('flush', verbosity=0, interactive=False)

# Load fixture 5 (compressed), using format *and* compression specification
>>> management.call_command('loaddata', 'fixture5.json.zip', verbosity=0)
>>> Article.objects.all()
[<Article: WoW subscribers now outnumber readers>, <Article: Python program becomes self aware>]

>>> management.call_command('flush', verbosity=0, interactive=False)

# Load fixture 5 (compressed), only compression specification
>>> management.call_command('loaddata', 'fixture5.zip', verbosity=0)
>>> Article.objects.all()
[<Article: WoW subscribers now outnumber readers>, <Article: Python program becomes self aware>]

>>> management.call_command('flush', verbosity=0, interactive=False)

# Try to load fixture 5 using format and compression discovery; this will fail
# because there are two fixture5's in the fixtures directory
>>> management.call_command('loaddata', 'fixture5', verbosity=0) # doctest: +ELLIPSIS
Multiple fixtures named 'fixture5' in '...fixtures'. Aborting.

"""

from django.test import TestCase

class SampleTestCase(TestCase):
    fixtures = ['fixture1.json', 'fixture2.json']

    def testClassFixtures(self):
        "Check that test case has installed 4 fixture objects"
        self.assertEqual(Article.objects.count(), 4)
        self.assertEquals(str(Article.objects.all()), "[<Article: Django conquers world!>, <Article: Copyright is fine the way it is>, <Article: Poker has no place on ESPN>, <Article: Python program becomes self aware>]")
