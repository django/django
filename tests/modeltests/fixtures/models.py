"""
37. Fixtures.

Fixtures are a way of loading data into the database in bulk. Fixure data
can be stored in any serializable format (including JSON and XML). Fixtures
are identified by name, and are stored in either a directory named 'fixtures'
in the application directory, on in one of the directories named in the
``FIXTURE_DIRS`` setting.
"""

from django.contrib.auth.models import Permission
from django.contrib.contenttypes import generic
from django.contrib.contenttypes.models import ContentType
from django.db import models, DEFAULT_DB_ALIAS
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

class Blog(models.Model):
    name = models.CharField(max_length=100)
    featured = models.ForeignKey(Article, related_name='fixtures_featured_set')
    articles = models.ManyToManyField(Article, blank=True,
                                      related_name='fixtures_articles_set')

    def __unicode__(self):
        return self.name


class Tag(models.Model):
    name = models.CharField(max_length=100)
    tagged_type = models.ForeignKey(ContentType, related_name="fixtures_tag_set")
    tagged_id = models.PositiveIntegerField(default=0)
    tagged = generic.GenericForeignKey(ct_field='tagged_type',
                                       fk_field='tagged_id')

    def __unicode__(self):
        return '<%s: %s> tagged "%s"' % (self.tagged.__class__.__name__,
                                         self.tagged, self.name)

class PersonManager(models.Manager):
    def get_by_natural_key(self, name):
        return self.get(name=name)

class Person(models.Model):
    objects = PersonManager()
    name = models.CharField(max_length=100)
    def __unicode__(self):
        return self.name

    class Meta:
        ordering = ('name',)

    def natural_key(self):
        return (self.name,)

class Visa(models.Model):
    person = models.ForeignKey(Person)
    permissions = models.ManyToManyField(Permission, blank=True)

    def __unicode__(self):
        return '%s %s' % (self.person.name,
                          ', '.join(p.name for p in self.permissions.all()))

class Book(models.Model):
    name = models.CharField(max_length=100)
    authors = models.ManyToManyField(Person)

    def __unicode__(self):
        return '%s by %s' % (self.name,
                          ' and '.join(a.name for a in self.authors.all()))

    class Meta:
        ordering = ('name',)

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

# Load fixture 6, JSON file with dynamic ContentType fields. Testing ManyToOne.
>>> management.call_command('loaddata', 'fixture6.json', verbosity=0)
>>> Tag.objects.all()
[<Tag: <Article: Copyright is fine the way it is> tagged "copyright">, <Tag: <Article: Copyright is fine the way it is> tagged "law">]

# Load fixture 7, XML file with dynamic ContentType fields. Testing ManyToOne.
>>> management.call_command('loaddata', 'fixture7.xml', verbosity=0)
>>> Tag.objects.all()
[<Tag: <Article: Copyright is fine the way it is> tagged "copyright">, <Tag: <Article: Copyright is fine the way it is> tagged "legal">, <Tag: <Article: Django conquers world!> tagged "django">, <Tag: <Article: Django conquers world!> tagged "world domination">]

# Load fixture 8, JSON file with dynamic Permission fields. Testing ManyToMany.
>>> management.call_command('loaddata', 'fixture8.json', verbosity=0)
>>> Visa.objects.all()
[<Visa: Django Reinhardt Can add user, Can change user, Can delete user>, <Visa: Stephane Grappelli Can add user>, <Visa: Prince >]

# Load fixture 9, XML file with dynamic Permission fields. Testing ManyToMany.
>>> management.call_command('loaddata', 'fixture9.xml', verbosity=0)
>>> Visa.objects.all()
[<Visa: Django Reinhardt Can add user, Can change user, Can delete user>, <Visa: Stephane Grappelli Can add user, Can delete user>, <Visa: Artist formerly known as "Prince" Can change user>]

>>> Book.objects.all()
[<Book: Music for all ages by Artist formerly known as "Prince" and Django Reinhardt>]

# Load a fixture that doesn't exist
>>> management.call_command('loaddata', 'unknown.json', verbosity=0)

# object list is unaffected
>>> Article.objects.all()
[<Article: XML identified as leading cause of cancer>, <Article: Django conquers world!>, <Article: Copyright is fine the way it is>, <Article: Poker on TV is great!>, <Article: Python program becomes self aware>]

# By default, you get raw keys on dumpdata
>>> management.call_command('dumpdata', 'fixtures.book', format='json')
[{"pk": 1, "model": "fixtures.book", "fields": {"name": "Music for all ages", "authors": [3, 1]}}]

# But you can get natural keys if you ask for them and they are available
>>> management.call_command('dumpdata', 'fixtures.book', format='json', use_natural_keys=True)
[{"pk": 1, "model": "fixtures.book", "fields": {"name": "Music for all ages", "authors": [["Artist formerly known as \\"Prince\\""], ["Django Reinhardt"]]}}]

# Dump the current contents of the database as a JSON fixture
>>> management.call_command('dumpdata', 'fixtures', format='json', use_natural_keys=True)
[{"pk": 1, "model": "fixtures.category", "fields": {"description": "Latest news stories", "title": "News Stories"}}, {"pk": 5, "model": "fixtures.article", "fields": {"headline": "XML identified as leading cause of cancer", "pub_date": "2006-06-16 16:00:00"}}, {"pk": 4, "model": "fixtures.article", "fields": {"headline": "Django conquers world!", "pub_date": "2006-06-16 15:00:00"}}, {"pk": 3, "model": "fixtures.article", "fields": {"headline": "Copyright is fine the way it is", "pub_date": "2006-06-16 14:00:00"}}, {"pk": 2, "model": "fixtures.article", "fields": {"headline": "Poker on TV is great!", "pub_date": "2006-06-16 11:00:00"}}, {"pk": 1, "model": "fixtures.article", "fields": {"headline": "Python program becomes self aware", "pub_date": "2006-06-16 11:00:00"}}, {"pk": 1, "model": "fixtures.tag", "fields": {"tagged_type": ["fixtures", "article"], "name": "copyright", "tagged_id": 3}}, {"pk": 2, "model": "fixtures.tag", "fields": {"tagged_type": ["fixtures", "article"], "name": "legal", "tagged_id": 3}}, {"pk": 3, "model": "fixtures.tag", "fields": {"tagged_type": ["fixtures", "article"], "name": "django", "tagged_id": 4}}, {"pk": 4, "model": "fixtures.tag", "fields": {"tagged_type": ["fixtures", "article"], "name": "world domination", "tagged_id": 4}}, {"pk": 3, "model": "fixtures.person", "fields": {"name": "Artist formerly known as \\"Prince\\""}}, {"pk": 1, "model": "fixtures.person", "fields": {"name": "Django Reinhardt"}}, {"pk": 2, "model": "fixtures.person", "fields": {"name": "Stephane Grappelli"}}, {"pk": 1, "model": "fixtures.visa", "fields": {"person": ["Django Reinhardt"], "permissions": [["add_user", "auth", "user"], ["change_user", "auth", "user"], ["delete_user", "auth", "user"]]}}, {"pk": 2, "model": "fixtures.visa", "fields": {"person": ["Stephane Grappelli"], "permissions": [["add_user", "auth", "user"], ["delete_user", "auth", "user"]]}}, {"pk": 3, "model": "fixtures.visa", "fields": {"person": ["Artist formerly known as \\"Prince\\""], "permissions": [["change_user", "auth", "user"]]}}, {"pk": 1, "model": "fixtures.book", "fields": {"name": "Music for all ages", "authors": [["Artist formerly known as \\"Prince\\""], ["Django Reinhardt"]]}}]

# Dump the current contents of the database as an XML fixture
>>> management.call_command('dumpdata', 'fixtures', format='xml', use_natural_keys=True)
<?xml version="1.0" encoding="utf-8"?>
<django-objects version="1.0"><object pk="1" model="fixtures.category"><field type="CharField" name="title">News Stories</field><field type="TextField" name="description">Latest news stories</field></object><object pk="5" model="fixtures.article"><field type="CharField" name="headline">XML identified as leading cause of cancer</field><field type="DateTimeField" name="pub_date">2006-06-16 16:00:00</field></object><object pk="4" model="fixtures.article"><field type="CharField" name="headline">Django conquers world!</field><field type="DateTimeField" name="pub_date">2006-06-16 15:00:00</field></object><object pk="3" model="fixtures.article"><field type="CharField" name="headline">Copyright is fine the way it is</field><field type="DateTimeField" name="pub_date">2006-06-16 14:00:00</field></object><object pk="2" model="fixtures.article"><field type="CharField" name="headline">Poker on TV is great!</field><field type="DateTimeField" name="pub_date">2006-06-16 11:00:00</field></object><object pk="1" model="fixtures.article"><field type="CharField" name="headline">Python program becomes self aware</field><field type="DateTimeField" name="pub_date">2006-06-16 11:00:00</field></object><object pk="1" model="fixtures.tag"><field type="CharField" name="name">copyright</field><field to="contenttypes.contenttype" name="tagged_type" rel="ManyToOneRel"><natural>fixtures</natural><natural>article</natural></field><field type="PositiveIntegerField" name="tagged_id">3</field></object><object pk="2" model="fixtures.tag"><field type="CharField" name="name">legal</field><field to="contenttypes.contenttype" name="tagged_type" rel="ManyToOneRel"><natural>fixtures</natural><natural>article</natural></field><field type="PositiveIntegerField" name="tagged_id">3</field></object><object pk="3" model="fixtures.tag"><field type="CharField" name="name">django</field><field to="contenttypes.contenttype" name="tagged_type" rel="ManyToOneRel"><natural>fixtures</natural><natural>article</natural></field><field type="PositiveIntegerField" name="tagged_id">4</field></object><object pk="4" model="fixtures.tag"><field type="CharField" name="name">world domination</field><field to="contenttypes.contenttype" name="tagged_type" rel="ManyToOneRel"><natural>fixtures</natural><natural>article</natural></field><field type="PositiveIntegerField" name="tagged_id">4</field></object><object pk="3" model="fixtures.person"><field type="CharField" name="name">Artist formerly known as "Prince"</field></object><object pk="1" model="fixtures.person"><field type="CharField" name="name">Django Reinhardt</field></object><object pk="2" model="fixtures.person"><field type="CharField" name="name">Stephane Grappelli</field></object><object pk="1" model="fixtures.visa"><field to="fixtures.person" name="person" rel="ManyToOneRel"><natural>Django Reinhardt</natural></field><field to="auth.permission" name="permissions" rel="ManyToManyRel"><object><natural>add_user</natural><natural>auth</natural><natural>user</natural></object><object><natural>change_user</natural><natural>auth</natural><natural>user</natural></object><object><natural>delete_user</natural><natural>auth</natural><natural>user</natural></object></field></object><object pk="2" model="fixtures.visa"><field to="fixtures.person" name="person" rel="ManyToOneRel"><natural>Stephane Grappelli</natural></field><field to="auth.permission" name="permissions" rel="ManyToManyRel"><object><natural>add_user</natural><natural>auth</natural><natural>user</natural></object><object><natural>delete_user</natural><natural>auth</natural><natural>user</natural></object></field></object><object pk="3" model="fixtures.visa"><field to="fixtures.person" name="person" rel="ManyToOneRel"><natural>Artist formerly known as "Prince"</natural></field><field to="auth.permission" name="permissions" rel="ManyToManyRel"><object><natural>change_user</natural><natural>auth</natural><natural>user</natural></object></field></object><object pk="1" model="fixtures.book"><field type="CharField" name="name">Music for all ages</field><field to="fixtures.person" name="authors" rel="ManyToManyRel"><object><natural>Artist formerly known as "Prince"</natural></object><object><natural>Django Reinhardt</natural></object></field></object></django-objects>

"""}

# Database flushing does not work on MySQL with the default storage engine
# because it requires transaction support.
if settings.DATABASES[DEFAULT_DB_ALIAS]['ENGINE'] != 'django.db.backends.mysql':
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

>>> management.call_command('flush', verbosity=0, interactive=False)

# Load db fixtures 1 and 2. These will load using the 'default' database identifier implicitly
>>> management.call_command('loaddata', 'db_fixture_1', verbosity=0)
>>> management.call_command('loaddata', 'db_fixture_2', verbosity=0)
>>> Article.objects.all()
[<Article: Who needs more than one database?>, <Article: Who needs to use compressed data?>, <Article: Python program becomes self aware>]

>>> management.call_command('flush', verbosity=0, interactive=False)

# Load db fixtures 1 and 2. These will load using the 'default' database identifier explicitly
>>> management.call_command('loaddata', 'db_fixture_1', verbosity=0, using='default')
>>> management.call_command('loaddata', 'db_fixture_2', verbosity=0, using='default')
>>> Article.objects.all()
[<Article: Who needs more than one database?>, <Article: Who needs to use compressed data?>, <Article: Python program becomes self aware>]

>>> management.call_command('flush', verbosity=0, interactive=False)

# Try to load db fixture 3. This won't load because the database identifier doesn't match
>>> management.call_command('loaddata', 'db_fixture_3', verbosity=0)
>>> Article.objects.all()
[<Article: Python program becomes self aware>]

>>> management.call_command('loaddata', 'db_fixture_3', verbosity=0, using='default')
>>> Article.objects.all()
[<Article: Python program becomes self aware>]

>>> management.call_command('flush', verbosity=0, interactive=False)

# Try to load fixture 1, but this time, exclude the 'fixtures' app.
>>> management.call_command('loaddata', 'fixture1', verbosity=0, exclude='fixtures')
>>> Article.objects.all()
[<Article: Python program becomes self aware>]

>>> Category.objects.all()
[]

# Load back in fixture 1, we need the articles from it
>>> management.call_command('loaddata', 'fixture1', verbosity=0)

# Try to load fixture 6 using format discovery
>>> management.call_command('loaddata', 'fixture6', verbosity=0)
>>> Tag.objects.all()
[<Tag: <Article: Time to reform copyright> tagged "copyright">, <Tag: <Article: Time to reform copyright> tagged "law">]

# Dump the current contents of the database as a JSON fixture
>>> management.call_command('dumpdata', 'fixtures', format='json', use_natural_keys=True)
[{"pk": 1, "model": "fixtures.category", "fields": {"description": "Latest news stories", "title": "News Stories"}}, {"pk": 3, "model": "fixtures.article", "fields": {"headline": "Time to reform copyright", "pub_date": "2006-06-16 13:00:00"}}, {"pk": 2, "model": "fixtures.article", "fields": {"headline": "Poker has no place on ESPN", "pub_date": "2006-06-16 12:00:00"}}, {"pk": 1, "model": "fixtures.article", "fields": {"headline": "Python program becomes self aware", "pub_date": "2006-06-16 11:00:00"}}, {"pk": 1, "model": "fixtures.tag", "fields": {"tagged_type": ["fixtures", "article"], "name": "copyright", "tagged_id": 3}}, {"pk": 2, "model": "fixtures.tag", "fields": {"tagged_type": ["fixtures", "article"], "name": "law", "tagged_id": 3}}, {"pk": 1, "model": "fixtures.person", "fields": {"name": "Django Reinhardt"}}, {"pk": 3, "model": "fixtures.person", "fields": {"name": "Prince"}}, {"pk": 2, "model": "fixtures.person", "fields": {"name": "Stephane Grappelli"}}]

# Dump the current contents of the database as an XML fixture
>>> management.call_command('dumpdata', 'fixtures', format='xml', use_natural_keys=True)
<?xml version="1.0" encoding="utf-8"?>
<django-objects version="1.0"><object pk="1" model="fixtures.category"><field type="CharField" name="title">News Stories</field><field type="TextField" name="description">Latest news stories</field></object><object pk="3" model="fixtures.article"><field type="CharField" name="headline">Time to reform copyright</field><field type="DateTimeField" name="pub_date">2006-06-16 13:00:00</field></object><object pk="2" model="fixtures.article"><field type="CharField" name="headline">Poker has no place on ESPN</field><field type="DateTimeField" name="pub_date">2006-06-16 12:00:00</field></object><object pk="1" model="fixtures.article"><field type="CharField" name="headline">Python program becomes self aware</field><field type="DateTimeField" name="pub_date">2006-06-16 11:00:00</field></object><object pk="1" model="fixtures.tag"><field type="CharField" name="name">copyright</field><field to="contenttypes.contenttype" name="tagged_type" rel="ManyToOneRel"><natural>fixtures</natural><natural>article</natural></field><field type="PositiveIntegerField" name="tagged_id">3</field></object><object pk="2" model="fixtures.tag"><field type="CharField" name="name">law</field><field to="contenttypes.contenttype" name="tagged_type" rel="ManyToOneRel"><natural>fixtures</natural><natural>article</natural></field><field type="PositiveIntegerField" name="tagged_id">3</field></object><object pk="1" model="fixtures.person"><field type="CharField" name="name">Django Reinhardt</field></object><object pk="3" model="fixtures.person"><field type="CharField" name="name">Prince</field></object><object pk="2" model="fixtures.person"><field type="CharField" name="name">Stephane Grappelli</field></object></django-objects>

"""

from django.test import TestCase

class SampleTestCase(TestCase):
    fixtures = ['fixture1.json', 'fixture2.json']

    def testClassFixtures(self):
        "Check that test case has installed 4 fixture objects"
        self.assertEqual(Article.objects.count(), 4)
        self.assertEquals(str(Article.objects.all()), "[<Article: Django conquers world!>, <Article: Copyright is fine the way it is>, <Article: Poker has no place on ESPN>, <Article: Python program becomes self aware>]")
