import StringIO
import sys

from django.conf import settings
from django.core import management
from django.db import DEFAULT_DB_ALIAS
from django.test import TestCase, TransactionTestCase, skipUnlessDBFeature

from models import Article, Blog, Book, Category, Person, Spy, Tag, Visa


class TestCaseFixtureLoadingTests(TestCase):
    fixtures = ['fixture1.json', 'fixture2.json']

    def testClassFixtures(self):
        "Check that test case has installed 4 fixture objects"
        self.assertEqual(Article.objects.count(), 4)
        self.assertQuerysetEqual(Article.objects.all(), [
            '<Article: Django conquers world!>',
            '<Article: Copyright is fine the way it is>',
            '<Article: Poker has no place on ESPN>',
            '<Article: Python program becomes self aware>'
        ])

class FixtureLoadingTests(TestCase):

    def _dumpdata_assert(self, args, output, format='json', natural_keys=False,
                         use_base_manager=False, exclude_list=[]):
        new_io = StringIO.StringIO()
        management.call_command('dumpdata', *args, **{'format':format,
                                                      'stdout':new_io,
                                                      'stderr':new_io,
                                                      'use_natural_keys':natural_keys,
                                                      'use_base_manager':use_base_manager,
                                                      'exclude': exclude_list})
        command_output = new_io.getvalue().strip()
        self.assertEqual(command_output, output)

    def test_initial_data(self):
        # Syncdb introduces 1 initial data object from initial_data.json.
        self.assertQuerysetEqual(Article.objects.all(), [
            '<Article: Python program becomes self aware>'
        ])

    def test_loading_and_dumping(self):
        new_io = StringIO.StringIO()

        # Load fixture 1. Single JSON file, with two objects.
        management.call_command('loaddata', 'fixture1.json', verbosity=0, commit=False)
        self.assertQuerysetEqual(Article.objects.all(), [
            '<Article: Time to reform copyright>',
            '<Article: Poker has no place on ESPN>',
            '<Article: Python program becomes self aware>'
        ])

        # Dump the current contents of the database as a JSON fixture
        self._dumpdata_assert(['fixtures'], '[{"pk": 1, "model": "fixtures.category", "fields": {"description": "Latest news stories", "title": "News Stories"}}, {"pk": 3, "model": "fixtures.article", "fields": {"headline": "Time to reform copyright", "pub_date": "2006-06-16 13:00:00"}}, {"pk": 2, "model": "fixtures.article", "fields": {"headline": "Poker has no place on ESPN", "pub_date": "2006-06-16 12:00:00"}}, {"pk": 1, "model": "fixtures.article", "fields": {"headline": "Python program becomes self aware", "pub_date": "2006-06-16 11:00:00"}}]')

        # Try just dumping the contents of fixtures.Category
        self._dumpdata_assert(['fixtures.Category'], '[{"pk": 1, "model": "fixtures.category", "fields": {"description": "Latest news stories", "title": "News Stories"}}]')

        # ...and just fixtures.Article
        self._dumpdata_assert(['fixtures.Article'], '[{"pk": 3, "model": "fixtures.article", "fields": {"headline": "Time to reform copyright", "pub_date": "2006-06-16 13:00:00"}}, {"pk": 2, "model": "fixtures.article", "fields": {"headline": "Poker has no place on ESPN", "pub_date": "2006-06-16 12:00:00"}}, {"pk": 1, "model": "fixtures.article", "fields": {"headline": "Python program becomes self aware", "pub_date": "2006-06-16 11:00:00"}}]')

        # ...and both
        self._dumpdata_assert(['fixtures.Category', 'fixtures.Article'], '[{"pk": 1, "model": "fixtures.category", "fields": {"description": "Latest news stories", "title": "News Stories"}}, {"pk": 3, "model": "fixtures.article", "fields": {"headline": "Time to reform copyright", "pub_date": "2006-06-16 13:00:00"}}, {"pk": 2, "model": "fixtures.article", "fields": {"headline": "Poker has no place on ESPN", "pub_date": "2006-06-16 12:00:00"}}, {"pk": 1, "model": "fixtures.article", "fields": {"headline": "Python program becomes self aware", "pub_date": "2006-06-16 11:00:00"}}]')

        # Specify a specific model twice
        self._dumpdata_assert(['fixtures.Article', 'fixtures.Article'], '[{"pk": 3, "model": "fixtures.article", "fields": {"headline": "Time to reform copyright", "pub_date": "2006-06-16 13:00:00"}}, {"pk": 2, "model": "fixtures.article", "fields": {"headline": "Poker has no place on ESPN", "pub_date": "2006-06-16 12:00:00"}}, {"pk": 1, "model": "fixtures.article", "fields": {"headline": "Python program becomes self aware", "pub_date": "2006-06-16 11:00:00"}}]')

        # Specify a dump that specifies Article both explicitly and implicitly
        self._dumpdata_assert(['fixtures.Article', 'fixtures'], '[{"pk": 1, "model": "fixtures.category", "fields": {"description": "Latest news stories", "title": "News Stories"}}, {"pk": 3, "model": "fixtures.article", "fields": {"headline": "Time to reform copyright", "pub_date": "2006-06-16 13:00:00"}}, {"pk": 2, "model": "fixtures.article", "fields": {"headline": "Poker has no place on ESPN", "pub_date": "2006-06-16 12:00:00"}}, {"pk": 1, "model": "fixtures.article", "fields": {"headline": "Python program becomes self aware", "pub_date": "2006-06-16 11:00:00"}}]')

        # Same again, but specify in the reverse order
        self._dumpdata_assert(['fixtures'], '[{"pk": 1, "model": "fixtures.category", "fields": {"description": "Latest news stories", "title": "News Stories"}}, {"pk": 3, "model": "fixtures.article", "fields": {"headline": "Time to reform copyright", "pub_date": "2006-06-16 13:00:00"}}, {"pk": 2, "model": "fixtures.article", "fields": {"headline": "Poker has no place on ESPN", "pub_date": "2006-06-16 12:00:00"}}, {"pk": 1, "model": "fixtures.article", "fields": {"headline": "Python program becomes self aware", "pub_date": "2006-06-16 11:00:00"}}]')

        # Specify one model from one application, and an entire other application.
        self._dumpdata_assert(['fixtures.Category', 'sites'], '[{"pk": 1, "model": "fixtures.category", "fields": {"description": "Latest news stories", "title": "News Stories"}}, {"pk": 1, "model": "sites.site", "fields": {"domain": "example.com", "name": "example.com"}}]')

        # Load fixture 2. JSON file imported by default. Overwrites some existing objects
        management.call_command('loaddata', 'fixture2.json', verbosity=0, commit=False)
        self.assertQuerysetEqual(Article.objects.all(), [
            '<Article: Django conquers world!>',
            '<Article: Copyright is fine the way it is>',
            '<Article: Poker has no place on ESPN>',
            '<Article: Python program becomes self aware>'
        ])

        # Load fixture 3, XML format.
        management.call_command('loaddata', 'fixture3.xml', verbosity=0, commit=False)
        self.assertQuerysetEqual(Article.objects.all(), [
            '<Article: XML identified as leading cause of cancer>',
            '<Article: Django conquers world!>',
            '<Article: Copyright is fine the way it is>',
            '<Article: Poker on TV is great!>',
            '<Article: Python program becomes self aware>'
        ])

        # Load fixture 6, JSON file with dynamic ContentType fields. Testing ManyToOne.
        management.call_command('loaddata', 'fixture6.json', verbosity=0, commit=False)
        self.assertQuerysetEqual(Tag.objects.all(), [
            '<Tag: <Article: Copyright is fine the way it is> tagged "copyright">',
            '<Tag: <Article: Copyright is fine the way it is> tagged "law">'
        ])

        # Load fixture 7, XML file with dynamic ContentType fields. Testing ManyToOne.
        management.call_command('loaddata', 'fixture7.xml', verbosity=0, commit=False)
        self.assertQuerysetEqual(Tag.objects.all(), [
            '<Tag: <Article: Copyright is fine the way it is> tagged "copyright">',
            '<Tag: <Article: Copyright is fine the way it is> tagged "legal">',
            '<Tag: <Article: Django conquers world!> tagged "django">',
            '<Tag: <Article: Django conquers world!> tagged "world domination">'
        ])

        # Load fixture 8, JSON file with dynamic Permission fields. Testing ManyToMany.
        management.call_command('loaddata', 'fixture8.json', verbosity=0, commit=False)
        self.assertQuerysetEqual(Visa.objects.all(), [
            '<Visa: Django Reinhardt Can add user, Can change user, Can delete user>',
            '<Visa: Stephane Grappelli Can add user>',
            '<Visa: Prince >'
        ])

        # Load fixture 9, XML file with dynamic Permission fields. Testing ManyToMany.
        management.call_command('loaddata', 'fixture9.xml', verbosity=0, commit=False)
        self.assertQuerysetEqual(Visa.objects.all(), [
            '<Visa: Django Reinhardt Can add user, Can change user, Can delete user>',
            '<Visa: Stephane Grappelli Can add user, Can delete user>',
            '<Visa: Artist formerly known as "Prince" Can change user>'
        ])

        self.assertQuerysetEqual(Book.objects.all(), [
            '<Book: Music for all ages by Artist formerly known as "Prince" and Django Reinhardt>'
        ])

        # Load a fixture that doesn't exist
        management.call_command('loaddata', 'unknown.json', verbosity=0, commit=False)

        # object list is unaffected
        self.assertQuerysetEqual(Article.objects.all(), [
            '<Article: XML identified as leading cause of cancer>',
            '<Article: Django conquers world!>',
            '<Article: Copyright is fine the way it is>',
            '<Article: Poker on TV is great!>',
            '<Article: Python program becomes self aware>'
        ])

        # By default, you get raw keys on dumpdata
        self._dumpdata_assert(['fixtures.book'], '[{"pk": 1, "model": "fixtures.book", "fields": {"name": "Music for all ages", "authors": [3, 1]}}]')

        # But you can get natural keys if you ask for them and they are available
        self._dumpdata_assert(['fixtures.book'], '[{"pk": 1, "model": "fixtures.book", "fields": {"name": "Music for all ages", "authors": [["Artist formerly known as \\"Prince\\""], ["Django Reinhardt"]]}}]', natural_keys=True)

        # Dump the current contents of the database as a JSON fixture
        self._dumpdata_assert(['fixtures'], '[{"pk": 1, "model": "fixtures.category", "fields": {"description": "Latest news stories", "title": "News Stories"}}, {"pk": 5, "model": "fixtures.article", "fields": {"headline": "XML identified as leading cause of cancer", "pub_date": "2006-06-16 16:00:00"}}, {"pk": 4, "model": "fixtures.article", "fields": {"headline": "Django conquers world!", "pub_date": "2006-06-16 15:00:00"}}, {"pk": 3, "model": "fixtures.article", "fields": {"headline": "Copyright is fine the way it is", "pub_date": "2006-06-16 14:00:00"}}, {"pk": 2, "model": "fixtures.article", "fields": {"headline": "Poker on TV is great!", "pub_date": "2006-06-16 11:00:00"}}, {"pk": 1, "model": "fixtures.article", "fields": {"headline": "Python program becomes self aware", "pub_date": "2006-06-16 11:00:00"}}, {"pk": 1, "model": "fixtures.tag", "fields": {"tagged_type": ["fixtures", "article"], "name": "copyright", "tagged_id": 3}}, {"pk": 2, "model": "fixtures.tag", "fields": {"tagged_type": ["fixtures", "article"], "name": "legal", "tagged_id": 3}}, {"pk": 3, "model": "fixtures.tag", "fields": {"tagged_type": ["fixtures", "article"], "name": "django", "tagged_id": 4}}, {"pk": 4, "model": "fixtures.tag", "fields": {"tagged_type": ["fixtures", "article"], "name": "world domination", "tagged_id": 4}}, {"pk": 3, "model": "fixtures.person", "fields": {"name": "Artist formerly known as \\"Prince\\""}}, {"pk": 1, "model": "fixtures.person", "fields": {"name": "Django Reinhardt"}}, {"pk": 2, "model": "fixtures.person", "fields": {"name": "Stephane Grappelli"}}, {"pk": 1, "model": "fixtures.visa", "fields": {"person": ["Django Reinhardt"], "permissions": [["add_user", "auth", "user"], ["change_user", "auth", "user"], ["delete_user", "auth", "user"]]}}, {"pk": 2, "model": "fixtures.visa", "fields": {"person": ["Stephane Grappelli"], "permissions": [["add_user", "auth", "user"], ["delete_user", "auth", "user"]]}}, {"pk": 3, "model": "fixtures.visa", "fields": {"person": ["Artist formerly known as \\"Prince\\""], "permissions": [["change_user", "auth", "user"]]}}, {"pk": 1, "model": "fixtures.book", "fields": {"name": "Music for all ages", "authors": [["Artist formerly known as \\"Prince\\""], ["Django Reinhardt"]]}}]', natural_keys=True)

        # Dump the current contents of the database as an XML fixture
        self._dumpdata_assert(['fixtures'], """<?xml version="1.0" encoding="utf-8"?>
<django-objects version="1.0"><object pk="1" model="fixtures.category"><field type="CharField" name="title">News Stories</field><field type="TextField" name="description">Latest news stories</field></object><object pk="5" model="fixtures.article"><field type="CharField" name="headline">XML identified as leading cause of cancer</field><field type="DateTimeField" name="pub_date">2006-06-16 16:00:00</field></object><object pk="4" model="fixtures.article"><field type="CharField" name="headline">Django conquers world!</field><field type="DateTimeField" name="pub_date">2006-06-16 15:00:00</field></object><object pk="3" model="fixtures.article"><field type="CharField" name="headline">Copyright is fine the way it is</field><field type="DateTimeField" name="pub_date">2006-06-16 14:00:00</field></object><object pk="2" model="fixtures.article"><field type="CharField" name="headline">Poker on TV is great!</field><field type="DateTimeField" name="pub_date">2006-06-16 11:00:00</field></object><object pk="1" model="fixtures.article"><field type="CharField" name="headline">Python program becomes self aware</field><field type="DateTimeField" name="pub_date">2006-06-16 11:00:00</field></object><object pk="1" model="fixtures.tag"><field type="CharField" name="name">copyright</field><field to="contenttypes.contenttype" name="tagged_type" rel="ManyToOneRel"><natural>fixtures</natural><natural>article</natural></field><field type="PositiveIntegerField" name="tagged_id">3</field></object><object pk="2" model="fixtures.tag"><field type="CharField" name="name">legal</field><field to="contenttypes.contenttype" name="tagged_type" rel="ManyToOneRel"><natural>fixtures</natural><natural>article</natural></field><field type="PositiveIntegerField" name="tagged_id">3</field></object><object pk="3" model="fixtures.tag"><field type="CharField" name="name">django</field><field to="contenttypes.contenttype" name="tagged_type" rel="ManyToOneRel"><natural>fixtures</natural><natural>article</natural></field><field type="PositiveIntegerField" name="tagged_id">4</field></object><object pk="4" model="fixtures.tag"><field type="CharField" name="name">world domination</field><field to="contenttypes.contenttype" name="tagged_type" rel="ManyToOneRel"><natural>fixtures</natural><natural>article</natural></field><field type="PositiveIntegerField" name="tagged_id">4</field></object><object pk="3" model="fixtures.person"><field type="CharField" name="name">Artist formerly known as "Prince"</field></object><object pk="1" model="fixtures.person"><field type="CharField" name="name">Django Reinhardt</field></object><object pk="2" model="fixtures.person"><field type="CharField" name="name">Stephane Grappelli</field></object><object pk="1" model="fixtures.visa"><field to="fixtures.person" name="person" rel="ManyToOneRel"><natural>Django Reinhardt</natural></field><field to="auth.permission" name="permissions" rel="ManyToManyRel"><object><natural>add_user</natural><natural>auth</natural><natural>user</natural></object><object><natural>change_user</natural><natural>auth</natural><natural>user</natural></object><object><natural>delete_user</natural><natural>auth</natural><natural>user</natural></object></field></object><object pk="2" model="fixtures.visa"><field to="fixtures.person" name="person" rel="ManyToOneRel"><natural>Stephane Grappelli</natural></field><field to="auth.permission" name="permissions" rel="ManyToManyRel"><object><natural>add_user</natural><natural>auth</natural><natural>user</natural></object><object><natural>delete_user</natural><natural>auth</natural><natural>user</natural></object></field></object><object pk="3" model="fixtures.visa"><field to="fixtures.person" name="person" rel="ManyToOneRel"><natural>Artist formerly known as "Prince"</natural></field><field to="auth.permission" name="permissions" rel="ManyToManyRel"><object><natural>change_user</natural><natural>auth</natural><natural>user</natural></object></field></object><object pk="1" model="fixtures.book"><field type="CharField" name="name">Music for all ages</field><field to="fixtures.person" name="authors" rel="ManyToManyRel"><object><natural>Artist formerly known as "Prince"</natural></object><object><natural>Django Reinhardt</natural></object></field></object></django-objects>""", format='xml', natural_keys=True)

    def test_dumpdata_with_excludes(self):
        # Load fixture1 which has a site, two articles, and a category
        management.call_command('loaddata', 'fixture1.json', verbosity=0, commit=False)

        # Excluding fixtures app should only leave sites
        self._dumpdata_assert(
            ['sites', 'fixtures'],
            '[{"pk": 1, "model": "sites.site", "fields": {"domain": "example.com", "name": "example.com"}}]',
            exclude_list=['fixtures'])

        # Excluding fixtures.Article should leave fixtures.Category
        self._dumpdata_assert(
            ['sites', 'fixtures'],
            '[{"pk": 1, "model": "sites.site", "fields": {"domain": "example.com", "name": "example.com"}}, {"pk": 1, "model": "fixtures.category", "fields": {"description": "Latest news stories", "title": "News Stories"}}]',
            exclude_list=['fixtures.Article'])

        # Excluding fixtures and fixtures.Article should be a no-op
        self._dumpdata_assert(
            ['sites', 'fixtures'],
            '[{"pk": 1, "model": "sites.site", "fields": {"domain": "example.com", "name": "example.com"}}, {"pk": 1, "model": "fixtures.category", "fields": {"description": "Latest news stories", "title": "News Stories"}}]',
            exclude_list=['fixtures.Article'])

        # Excluding sites and fixtures.Article should only leave fixtures.Category
        self._dumpdata_assert(
            ['sites', 'fixtures'],
            '[{"pk": 1, "model": "fixtures.category", "fields": {"description": "Latest news stories", "title": "News Stories"}}]',
            exclude_list=['fixtures.Article', 'sites'])

        # Excluding a bogus app should throw an error
        self.assertRaises(SystemExit,
                          self._dumpdata_assert,
                          ['fixtures', 'sites'],
                          '',
                          exclude_list=['foo_app'])

        # Excluding a bogus model should throw an error
        self.assertRaises(SystemExit,
                          self._dumpdata_assert,
                          ['fixtures', 'sites'],
                          '',
                          exclude_list=['fixtures.FooModel'])

    def test_dumpdata_with_filtering_manager(self):
        Spy(name='Paul').save()
        Spy(name='Alex', cover_blown=True).save()
        self.assertQuerysetEqual(Spy.objects.all(),
                                 ['<Spy: Paul>'])
        # Use the default manager
        self._dumpdata_assert(['fixtures.Spy'],'[{"pk": 1, "model": "fixtures.spy", "fields": {"cover_blown": false}}]')
        # Dump using Django's base manager. Should return all objects,
        # even those normally filtered by the manager
        self._dumpdata_assert(['fixtures.Spy'], '[{"pk": 2, "model": "fixtures.spy", "fields": {"cover_blown": true}}, {"pk": 1, "model": "fixtures.spy", "fields": {"cover_blown": false}}]', use_base_manager=True)

    def test_compress_format_loading(self):
        # Load fixture 4 (compressed), using format specification
        management.call_command('loaddata', 'fixture4.json', verbosity=0, commit=False)
        self.assertQuerysetEqual(Article.objects.all(), [
            '<Article: Django pets kitten>',
            '<Article: Python program becomes self aware>'
        ])

    def test_compressed_specified_loading(self):
        # Load fixture 5 (compressed), using format *and* compression specification
        management.call_command('loaddata', 'fixture5.json.zip', verbosity=0, commit=False)
        self.assertQuerysetEqual(Article.objects.all(), [
            '<Article: WoW subscribers now outnumber readers>',
            '<Article: Python program becomes self aware>'
        ])

    def test_compressed_loading(self):
        # Load fixture 5 (compressed), only compression specification
        management.call_command('loaddata', 'fixture5.zip', verbosity=0, commit=False)
        self.assertQuerysetEqual(Article.objects.all(), [
            '<Article: WoW subscribers now outnumber readers>',
            '<Article: Python program becomes self aware>'
        ])

    def test_ambiguous_compressed_fixture(self):
        # The name "fixture5" is ambigous, so loading it will raise an error
        new_io = StringIO.StringIO()
        management.call_command('loaddata', 'fixture5', verbosity=0, stderr=new_io, commit=False)
        output = new_io.getvalue().strip().split('\n')
        self.assertEqual(len(output), 1)
        self.assertTrue(output[0].startswith("Multiple fixtures named 'fixture5'"))

    def test_db_loading(self):
        # Load db fixtures 1 and 2. These will load using the 'default' database identifier implicitly
        management.call_command('loaddata', 'db_fixture_1', verbosity=0, commit=False)
        management.call_command('loaddata', 'db_fixture_2', verbosity=0, commit=False)
        self.assertQuerysetEqual(Article.objects.all(), [
            '<Article: Who needs more than one database?>',
            '<Article: Who needs to use compressed data?>',
            '<Article: Python program becomes self aware>'
        ])

    def test_loading_using(self):
        # Load db fixtures 1 and 2. These will load using the 'default' database identifier explicitly
        management.call_command('loaddata', 'db_fixture_1', verbosity=0, using='default', commit=False)
        management.call_command('loaddata', 'db_fixture_2', verbosity=0, using='default', commit=False)
        self.assertQuerysetEqual(Article.objects.all(), [
            '<Article: Who needs more than one database?>',
            '<Article: Who needs to use compressed data?>',
            '<Article: Python program becomes self aware>'
        ])

    def test_unmatched_identifier_loading(self):
        # Try to load db fixture 3. This won't load because the database identifier doesn't match
        management.call_command('loaddata', 'db_fixture_3', verbosity=0, commit=False)
        self.assertQuerysetEqual(Article.objects.all(), [
            '<Article: Python program becomes self aware>'
        ])

        management.call_command('loaddata', 'db_fixture_3', verbosity=0, using='default', commit=False)
        self.assertQuerysetEqual(Article.objects.all(), [
            '<Article: Python program becomes self aware>'
        ])

    def test_output_formats(self):
        # Load back in fixture 1, we need the articles from it
        management.call_command('loaddata', 'fixture1', verbosity=0, commit=False)

        # Try to load fixture 6 using format discovery
        management.call_command('loaddata', 'fixture6', verbosity=0, commit=False)
        self.assertQuerysetEqual(Tag.objects.all(), [
            '<Tag: <Article: Time to reform copyright> tagged "copyright">',
            '<Tag: <Article: Time to reform copyright> tagged "law">'
        ])

        # Dump the current contents of the database as a JSON fixture
        self._dumpdata_assert(['fixtures'], '[{"pk": 1, "model": "fixtures.category", "fields": {"description": "Latest news stories", "title": "News Stories"}}, {"pk": 3, "model": "fixtures.article", "fields": {"headline": "Time to reform copyright", "pub_date": "2006-06-16 13:00:00"}}, {"pk": 2, "model": "fixtures.article", "fields": {"headline": "Poker has no place on ESPN", "pub_date": "2006-06-16 12:00:00"}}, {"pk": 1, "model": "fixtures.article", "fields": {"headline": "Python program becomes self aware", "pub_date": "2006-06-16 11:00:00"}}, {"pk": 1, "model": "fixtures.tag", "fields": {"tagged_type": ["fixtures", "article"], "name": "copyright", "tagged_id": 3}}, {"pk": 2, "model": "fixtures.tag", "fields": {"tagged_type": ["fixtures", "article"], "name": "law", "tagged_id": 3}}, {"pk": 1, "model": "fixtures.person", "fields": {"name": "Django Reinhardt"}}, {"pk": 3, "model": "fixtures.person", "fields": {"name": "Prince"}}, {"pk": 2, "model": "fixtures.person", "fields": {"name": "Stephane Grappelli"}}]', natural_keys=True)

        # Dump the current contents of the database as an XML fixture
        self._dumpdata_assert(['fixtures'], """<?xml version="1.0" encoding="utf-8"?>
<django-objects version="1.0"><object pk="1" model="fixtures.category"><field type="CharField" name="title">News Stories</field><field type="TextField" name="description">Latest news stories</field></object><object pk="3" model="fixtures.article"><field type="CharField" name="headline">Time to reform copyright</field><field type="DateTimeField" name="pub_date">2006-06-16 13:00:00</field></object><object pk="2" model="fixtures.article"><field type="CharField" name="headline">Poker has no place on ESPN</field><field type="DateTimeField" name="pub_date">2006-06-16 12:00:00</field></object><object pk="1" model="fixtures.article"><field type="CharField" name="headline">Python program becomes self aware</field><field type="DateTimeField" name="pub_date">2006-06-16 11:00:00</field></object><object pk="1" model="fixtures.tag"><field type="CharField" name="name">copyright</field><field to="contenttypes.contenttype" name="tagged_type" rel="ManyToOneRel"><natural>fixtures</natural><natural>article</natural></field><field type="PositiveIntegerField" name="tagged_id">3</field></object><object pk="2" model="fixtures.tag"><field type="CharField" name="name">law</field><field to="contenttypes.contenttype" name="tagged_type" rel="ManyToOneRel"><natural>fixtures</natural><natural>article</natural></field><field type="PositiveIntegerField" name="tagged_id">3</field></object><object pk="1" model="fixtures.person"><field type="CharField" name="name">Django Reinhardt</field></object><object pk="3" model="fixtures.person"><field type="CharField" name="name">Prince</field></object><object pk="2" model="fixtures.person"><field type="CharField" name="name">Stephane Grappelli</field></object></django-objects>""", format='xml', natural_keys=True)

class FixtureTransactionTests(TransactionTestCase):
    def _dumpdata_assert(self, args, output, format='json'):
        new_io = StringIO.StringIO()
        management.call_command('dumpdata', *args, **{'format':format, 'stdout':new_io})
        command_output = new_io.getvalue().strip()
        self.assertEqual(command_output, output)

    @skipUnlessDBFeature('supports_forward_references')
    def test_format_discovery(self):
        # Load fixture 1 again, using format discovery
        management.call_command('loaddata', 'fixture1', verbosity=0, commit=False)
        self.assertQuerysetEqual(Article.objects.all(), [
            '<Article: Time to reform copyright>',
            '<Article: Poker has no place on ESPN>',
            '<Article: Python program becomes self aware>'
        ])

        # Try to load fixture 2 using format discovery; this will fail
        # because there are two fixture2's in the fixtures directory
        new_io = StringIO.StringIO()
        management.call_command('loaddata', 'fixture2', verbosity=0, stderr=new_io)
        output = new_io.getvalue().strip().split('\n')
        self.assertEqual(len(output), 1)
        self.assertTrue(output[0].startswith("Multiple fixtures named 'fixture2'"))

        # object list is unaffected
        self.assertQuerysetEqual(Article.objects.all(), [
            '<Article: Time to reform copyright>',
            '<Article: Poker has no place on ESPN>',
            '<Article: Python program becomes self aware>'
        ])

        # Dump the current contents of the database as a JSON fixture
        self._dumpdata_assert(['fixtures'], '[{"pk": 1, "model": "fixtures.category", "fields": {"description": "Latest news stories", "title": "News Stories"}}, {"pk": 3, "model": "fixtures.article", "fields": {"headline": "Time to reform copyright", "pub_date": "2006-06-16 13:00:00"}}, {"pk": 2, "model": "fixtures.article", "fields": {"headline": "Poker has no place on ESPN", "pub_date": "2006-06-16 12:00:00"}}, {"pk": 1, "model": "fixtures.article", "fields": {"headline": "Python program becomes self aware", "pub_date": "2006-06-16 11:00:00"}}]')

        # Load fixture 4 (compressed), using format discovery
        management.call_command('loaddata', 'fixture4', verbosity=0, commit=False)
        self.assertQuerysetEqual(Article.objects.all(), [
            '<Article: Django pets kitten>',
            '<Article: Time to reform copyright>',
            '<Article: Poker has no place on ESPN>',
            '<Article: Python program becomes self aware>'
        ])
