from __future__ import absolute_import

from django.contrib.sites.models import Site
from django.core import management
from django.db import connection, IntegrityError
from django.test import TestCase, TransactionTestCase, skipUnlessDBFeature
from django.utils import six

from .models import Article, Book, Spy, Tag, Visa


class TestCaseFixtureLoadingTests(TestCase):
    fixtures = ['fixture1.json', 'fixture2.json']

    def testClassFixtures(self):
        "Check that test case has installed 3 fixture objects"
        self.assertEqual(Article.objects.count(), 3)
        self.assertQuerysetEqual(Article.objects.all(), [
            '<Article: Django conquers world!>',
            '<Article: Copyright is fine the way it is>',
            '<Article: Poker has no place on ESPN>',
        ])


class DumpDataAssertMixin(object):

    def _dumpdata_assert(self, args, output, format='json', natural_keys=False,
                         use_base_manager=False, exclude_list=[]):
        new_io = six.StringIO()
        management.call_command('dumpdata', *args, **{'format': format,
                                                      'stdout': new_io,
                                                      'stderr': new_io,
                                                      'use_natural_keys': natural_keys,
                                                      'use_base_manager': use_base_manager,
                                                      'exclude': exclude_list})
        command_output = new_io.getvalue().strip()
        if format == "json":
            self.assertJSONEqual(command_output, output)
        elif format == "xml":
            self.assertXMLEqual(command_output, output)
        else:
            self.assertEqual(command_output, output)


class FixtureLoadingTests(DumpDataAssertMixin, TestCase):

    def test_initial_data(self):
        # syncdb introduces 1 initial data object from initial_data.json.
        self.assertQuerysetEqual(Book.objects.all(), [
            '<Book: Achieving self-awareness of Python programs>'
        ])

    def test_loading_and_dumping(self):
        Site.objects.all().delete()
        # Load fixture 1. Single JSON file, with two objects.
        management.call_command('loaddata', 'fixture1.json', verbosity=0, commit=False)
        self.assertQuerysetEqual(Article.objects.all(), [
            '<Article: Time to reform copyright>',
            '<Article: Poker has no place on ESPN>',
        ])

        # Dump the current contents of the database as a JSON fixture
        self._dumpdata_assert(['fixtures'], '[{"pk": 1, "model": "fixtures.category", "fields": {"description": "Latest news stories", "title": "News Stories"}}, {"pk": 2, "model": "fixtures.article", "fields": {"headline": "Poker has no place on ESPN", "pub_date": "2006-06-16T12:00:00"}}, {"pk": 3, "model": "fixtures.article", "fields": {"headline": "Time to reform copyright", "pub_date": "2006-06-16T13:00:00"}}, {"pk": 10, "model": "fixtures.book", "fields": {"name": "Achieving self-awareness of Python programs", "authors": []}}]')

        # Try just dumping the contents of fixtures.Category
        self._dumpdata_assert(['fixtures.Category'], '[{"pk": 1, "model": "fixtures.category", "fields": {"description": "Latest news stories", "title": "News Stories"}}]')

        # ...and just fixtures.Article
        self._dumpdata_assert(['fixtures.Article'], '[{"pk": 2, "model": "fixtures.article", "fields": {"headline": "Poker has no place on ESPN", "pub_date": "2006-06-16T12:00:00"}}, {"pk": 3, "model": "fixtures.article", "fields": {"headline": "Time to reform copyright", "pub_date": "2006-06-16T13:00:00"}}]')

        # ...and both
        self._dumpdata_assert(['fixtures.Category', 'fixtures.Article'], '[{"pk": 1, "model": "fixtures.category", "fields": {"description": "Latest news stories", "title": "News Stories"}}, {"pk": 2, "model": "fixtures.article", "fields": {"headline": "Poker has no place on ESPN", "pub_date": "2006-06-16T12:00:00"}}, {"pk": 3, "model": "fixtures.article", "fields": {"headline": "Time to reform copyright", "pub_date": "2006-06-16T13:00:00"}}]')

        # Specify a specific model twice
        self._dumpdata_assert(['fixtures.Article', 'fixtures.Article'], '[{"pk": 2, "model": "fixtures.article", "fields": {"headline": "Poker has no place on ESPN", "pub_date": "2006-06-16T12:00:00"}}, {"pk": 3, "model": "fixtures.article", "fields": {"headline": "Time to reform copyright", "pub_date": "2006-06-16T13:00:00"}}]')

        # Specify a dump that specifies Article both explicitly and implicitly
        self._dumpdata_assert(['fixtures.Article', 'fixtures'], '[{"pk": 1, "model": "fixtures.category", "fields": {"description": "Latest news stories", "title": "News Stories"}}, {"pk": 2, "model": "fixtures.article", "fields": {"headline": "Poker has no place on ESPN", "pub_date": "2006-06-16T12:00:00"}}, {"pk": 3, "model": "fixtures.article", "fields": {"headline": "Time to reform copyright", "pub_date": "2006-06-16T13:00:00"}}, {"pk": 10, "model": "fixtures.book", "fields": {"name": "Achieving self-awareness of Python programs", "authors": []}}]')

        # Same again, but specify in the reverse order
        self._dumpdata_assert(['fixtures'], '[{"pk": 1, "model": "fixtures.category", "fields": {"description": "Latest news stories", "title": "News Stories"}}, {"pk": 2, "model": "fixtures.article", "fields": {"headline": "Poker has no place on ESPN", "pub_date": "2006-06-16T12:00:00"}}, {"pk": 3, "model": "fixtures.article", "fields": {"headline": "Time to reform copyright", "pub_date": "2006-06-16T13:00:00"}}, {"pk": 10, "model": "fixtures.book", "fields": {"name": "Achieving self-awareness of Python programs", "authors": []}}]')

        # Specify one model from one application, and an entire other application.
        self._dumpdata_assert(['fixtures.Category', 'sites'], '[{"pk": 1, "model": "fixtures.category", "fields": {"description": "Latest news stories", "title": "News Stories"}}, {"pk": 1, "model": "sites.site", "fields": {"domain": "example.com", "name": "example.com"}}]')

        # Load fixture 2. JSON file imported by default. Overwrites some existing objects
        management.call_command('loaddata', 'fixture2.json', verbosity=0, commit=False)
        self.assertQuerysetEqual(Article.objects.all(), [
            '<Article: Django conquers world!>',
            '<Article: Copyright is fine the way it is>',
            '<Article: Poker has no place on ESPN>',
        ])

        # Load fixture 3, XML format.
        management.call_command('loaddata', 'fixture3.xml', verbosity=0, commit=False)
        self.assertQuerysetEqual(Article.objects.all(), [
            '<Article: XML identified as leading cause of cancer>',
            '<Article: Django conquers world!>',
            '<Article: Copyright is fine the way it is>',
            '<Article: Poker on TV is great!>',
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
            '<Book: Achieving self-awareness of Python programs>',
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
        ])

        # By default, you get raw keys on dumpdata
        self._dumpdata_assert(['fixtures.book'], '[{"pk": 1, "model": "fixtures.book", "fields": {"name": "Music for all ages", "authors": [3, 1]}}, {"pk": 10, "model": "fixtures.book", "fields": {"name": "Achieving self-awareness of Python programs", "authors": []}}]')

        # But you can get natural keys if you ask for them and they are available
        self._dumpdata_assert(['fixtures.book'], '[{"pk": 1, "model": "fixtures.book", "fields": {"name": "Music for all ages", "authors": [["Artist formerly known as \\"Prince\\""], ["Django Reinhardt"]]}}, {"pk": 10, "model": "fixtures.book", "fields": {"name": "Achieving self-awareness of Python programs", "authors": []}}]', natural_keys=True)

        # Dump the current contents of the database as a JSON fixture
        self._dumpdata_assert(['fixtures'], '[{"pk": 1, "model": "fixtures.category", "fields": {"description": "Latest news stories", "title": "News Stories"}}, {"pk": 2, "model": "fixtures.article", "fields": {"headline": "Poker on TV is great!", "pub_date": "2006-06-16T11:00:00"}}, {"pk": 3, "model": "fixtures.article", "fields": {"headline": "Copyright is fine the way it is", "pub_date": "2006-06-16T14:00:00"}}, {"pk": 4, "model": "fixtures.article", "fields": {"headline": "Django conquers world!", "pub_date": "2006-06-16T15:00:00"}}, {"pk": 5, "model": "fixtures.article", "fields": {"headline": "XML identified as leading cause of cancer", "pub_date": "2006-06-16T16:00:00"}}, {"pk": 1, "model": "fixtures.tag", "fields": {"tagged_type": ["fixtures", "article"], "name": "copyright", "tagged_id": 3}}, {"pk": 2, "model": "fixtures.tag", "fields": {"tagged_type": ["fixtures", "article"], "name": "legal", "tagged_id": 3}}, {"pk": 3, "model": "fixtures.tag", "fields": {"tagged_type": ["fixtures", "article"], "name": "django", "tagged_id": 4}}, {"pk": 4, "model": "fixtures.tag", "fields": {"tagged_type": ["fixtures", "article"], "name": "world domination", "tagged_id": 4}}, {"pk": 1, "model": "fixtures.person", "fields": {"name": "Django Reinhardt"}}, {"pk": 2, "model": "fixtures.person", "fields": {"name": "Stephane Grappelli"}}, {"pk": 3, "model": "fixtures.person", "fields": {"name": "Artist formerly known as \\"Prince\\""}}, {"pk": 1, "model": "fixtures.visa", "fields": {"person": ["Django Reinhardt"], "permissions": [["add_user", "auth", "user"], ["change_user", "auth", "user"], ["delete_user", "auth", "user"]]}}, {"pk": 2, "model": "fixtures.visa", "fields": {"person": ["Stephane Grappelli"], "permissions": [["add_user", "auth", "user"], ["delete_user", "auth", "user"]]}}, {"pk": 3, "model": "fixtures.visa", "fields": {"person": ["Artist formerly known as \\"Prince\\""], "permissions": [["change_user", "auth", "user"]]}}, {"pk": 1, "model": "fixtures.book", "fields": {"name": "Music for all ages", "authors": [["Artist formerly known as \\"Prince\\""], ["Django Reinhardt"]]}}, {"pk": 10, "model": "fixtures.book", "fields": {"name": "Achieving self-awareness of Python programs", "authors": []}}]', natural_keys=True)

        # Dump the current contents of the database as an XML fixture
        self._dumpdata_assert(['fixtures'], """<?xml version="1.0" encoding="utf-8"?>
<django-objects version="1.0"><object pk="1" model="fixtures.category"><field type="CharField" name="title">News Stories</field><field type="TextField" name="description">Latest news stories</field></object><object pk="2" model="fixtures.article"><field type="CharField" name="headline">Poker on TV is great!</field><field type="DateTimeField" name="pub_date">2006-06-16T11:00:00</field></object><object pk="3" model="fixtures.article"><field type="CharField" name="headline">Copyright is fine the way it is</field><field type="DateTimeField" name="pub_date">2006-06-16T14:00:00</field></object><object pk="4" model="fixtures.article"><field type="CharField" name="headline">Django conquers world!</field><field type="DateTimeField" name="pub_date">2006-06-16T15:00:00</field></object><object pk="5" model="fixtures.article"><field type="CharField" name="headline">XML identified as leading cause of cancer</field><field type="DateTimeField" name="pub_date">2006-06-16T16:00:00</field></object><object pk="1" model="fixtures.tag"><field type="CharField" name="name">copyright</field><field to="contenttypes.contenttype" name="tagged_type" rel="ManyToOneRel"><natural>fixtures</natural><natural>article</natural></field><field type="PositiveIntegerField" name="tagged_id">3</field></object><object pk="2" model="fixtures.tag"><field type="CharField" name="name">legal</field><field to="contenttypes.contenttype" name="tagged_type" rel="ManyToOneRel"><natural>fixtures</natural><natural>article</natural></field><field type="PositiveIntegerField" name="tagged_id">3</field></object><object pk="3" model="fixtures.tag"><field type="CharField" name="name">django</field><field to="contenttypes.contenttype" name="tagged_type" rel="ManyToOneRel"><natural>fixtures</natural><natural>article</natural></field><field type="PositiveIntegerField" name="tagged_id">4</field></object><object pk="4" model="fixtures.tag"><field type="CharField" name="name">world domination</field><field to="contenttypes.contenttype" name="tagged_type" rel="ManyToOneRel"><natural>fixtures</natural><natural>article</natural></field><field type="PositiveIntegerField" name="tagged_id">4</field></object><object pk="1" model="fixtures.person"><field type="CharField" name="name">Django Reinhardt</field></object><object pk="2" model="fixtures.person"><field type="CharField" name="name">Stephane Grappelli</field></object><object pk="3" model="fixtures.person"><field type="CharField" name="name">Artist formerly known as "Prince"</field></object><object pk="1" model="fixtures.visa"><field to="fixtures.person" name="person" rel="ManyToOneRel"><natural>Django Reinhardt</natural></field><field to="auth.permission" name="permissions" rel="ManyToManyRel"><object><natural>add_user</natural><natural>auth</natural><natural>user</natural></object><object><natural>change_user</natural><natural>auth</natural><natural>user</natural></object><object><natural>delete_user</natural><natural>auth</natural><natural>user</natural></object></field></object><object pk="2" model="fixtures.visa"><field to="fixtures.person" name="person" rel="ManyToOneRel"><natural>Stephane Grappelli</natural></field><field to="auth.permission" name="permissions" rel="ManyToManyRel"><object><natural>add_user</natural><natural>auth</natural><natural>user</natural></object><object><natural>delete_user</natural><natural>auth</natural><natural>user</natural></object></field></object><object pk="3" model="fixtures.visa"><field to="fixtures.person" name="person" rel="ManyToOneRel"><natural>Artist formerly known as "Prince"</natural></field><field to="auth.permission" name="permissions" rel="ManyToManyRel"><object><natural>change_user</natural><natural>auth</natural><natural>user</natural></object></field></object><object pk="1" model="fixtures.book"><field type="CharField" name="name">Music for all ages</field><field to="fixtures.person" name="authors" rel="ManyToManyRel"><object><natural>Artist formerly known as "Prince"</natural></object><object><natural>Django Reinhardt</natural></object></field></object><object pk="10" model="fixtures.book"><field type="CharField" name="name">Achieving self-awareness of Python programs</field><field to="fixtures.person" name="authors" rel="ManyToManyRel"></field></object></django-objects>""", format='xml', natural_keys=True)

    def test_dumpdata_with_excludes(self):
        # Load fixture1 which has a site, two articles, and a category
        Site.objects.all().delete()
        management.call_command('loaddata', 'fixture1.json', verbosity=0, commit=False)

        # Excluding fixtures app should only leave sites
        self._dumpdata_assert(
            ['sites', 'fixtures'],
            '[{"pk": 1, "model": "sites.site", "fields": {"domain": "example.com", "name": "example.com"}}]',
            exclude_list=['fixtures'])

        # Excluding fixtures.Article/Book should leave fixtures.Category
        self._dumpdata_assert(
            ['sites', 'fixtures'],
            '[{"pk": 1, "model": "sites.site", "fields": {"domain": "example.com", "name": "example.com"}}, {"pk": 1, "model": "fixtures.category", "fields": {"description": "Latest news stories", "title": "News Stories"}}]',
            exclude_list=['fixtures.Article', 'fixtures.Book'])

        # Excluding fixtures and fixtures.Article/Book should be a no-op
        self._dumpdata_assert(
            ['sites', 'fixtures'],
            '[{"pk": 1, "model": "sites.site", "fields": {"domain": "example.com", "name": "example.com"}}, {"pk": 1, "model": "fixtures.category", "fields": {"description": "Latest news stories", "title": "News Stories"}}]',
            exclude_list=['fixtures.Article', 'fixtures.Book'])

        # Excluding sites and fixtures.Article/Book should only leave fixtures.Category
        self._dumpdata_assert(
            ['sites', 'fixtures'],
            '[{"pk": 1, "model": "fixtures.category", "fields": {"description": "Latest news stories", "title": "News Stories"}}]',
            exclude_list=['fixtures.Article', 'fixtures.Book', 'sites'])

        # Excluding a bogus app should throw an error
        with six.assertRaisesRegex(self, management.CommandError,
                "Unknown app in excludes: foo_app"):
            self._dumpdata_assert(['fixtures', 'sites'], '', exclude_list=['foo_app'])

        # Excluding a bogus model should throw an error
        with six.assertRaisesRegex(self, management.CommandError,
                "Unknown model in excludes: fixtures.FooModel"):
            self._dumpdata_assert(['fixtures', 'sites'], '', exclude_list=['fixtures.FooModel'])

    def test_dumpdata_with_filtering_manager(self):
        spy1 = Spy.objects.create(name='Paul')
        spy2 = Spy.objects.create(name='Alex', cover_blown=True)
        self.assertQuerysetEqual(Spy.objects.all(),
                                 ['<Spy: Paul>'])
        # Use the default manager
        self._dumpdata_assert(['fixtures.Spy'], '[{"pk": %d, "model": "fixtures.spy", "fields": {"cover_blown": false}}]' % spy1.pk)
        # Dump using Django's base manager. Should return all objects,
        # even those normally filtered by the manager
        self._dumpdata_assert(['fixtures.Spy'], '[{"pk": %d, "model": "fixtures.spy", "fields": {"cover_blown": true}}, {"pk": %d, "model": "fixtures.spy", "fields": {"cover_blown": false}}]' % (spy2.pk, spy1.pk), use_base_manager=True)

    def test_compress_format_loading(self):
        # Load fixture 4 (compressed), using format specification
        management.call_command('loaddata', 'fixture4.json', verbosity=0, commit=False)
        self.assertQuerysetEqual(Article.objects.all(), [
            '<Article: Django pets kitten>',
        ])

    def test_compressed_specified_loading(self):
        # Load fixture 5 (compressed), using format *and* compression specification
        management.call_command('loaddata', 'fixture5.json.zip', verbosity=0, commit=False)
        self.assertQuerysetEqual(Article.objects.all(), [
            '<Article: WoW subscribers now outnumber readers>',
        ])

    def test_compressed_loading(self):
        # Load fixture 5 (compressed), only compression specification
        management.call_command('loaddata', 'fixture5.zip', verbosity=0, commit=False)
        self.assertQuerysetEqual(Article.objects.all(), [
            '<Article: WoW subscribers now outnumber readers>',
        ])

    def test_ambiguous_compressed_fixture(self):
        # The name "fixture5" is ambigous, so loading it will raise an error
        with self.assertRaises(management.CommandError) as cm:
            management.call_command('loaddata', 'fixture5', verbosity=0, commit=False)
            self.assertIn("Multiple fixtures named 'fixture5'", cm.exception.args[0])

    def test_db_loading(self):
        # Load db fixtures 1 and 2. These will load using the 'default' database identifier implicitly
        management.call_command('loaddata', 'db_fixture_1', verbosity=0, commit=False)
        management.call_command('loaddata', 'db_fixture_2', verbosity=0, commit=False)
        self.assertQuerysetEqual(Article.objects.all(), [
            '<Article: Who needs more than one database?>',
            '<Article: Who needs to use compressed data?>',
        ])

    def test_loaddata_error_message(self):
        """
        Verifies that loading a fixture which contains an invalid object
        outputs an error message which contains the pk of the object
        that triggered the error.
        """
        # MySQL needs a little prodding to reject invalid data.
        # This won't affect other tests because the database connection
        # is closed at the end of each test.
        if connection.vendor == 'mysql':
            connection.cursor().execute("SET sql_mode = 'TRADITIONAL'")
        with self.assertRaises(IntegrityError) as cm:
            management.call_command('loaddata', 'invalid.json', verbosity=0, commit=False)
            self.assertIn("Could not load fixtures.Article(pk=1):", cm.exception.args[0])

    def test_loading_using(self):
        # Load db fixtures 1 and 2. These will load using the 'default' database identifier explicitly
        management.call_command('loaddata', 'db_fixture_1', verbosity=0, using='default', commit=False)
        management.call_command('loaddata', 'db_fixture_2', verbosity=0, using='default', commit=False)
        self.assertQuerysetEqual(Article.objects.all(), [
            '<Article: Who needs more than one database?>',
            '<Article: Who needs to use compressed data?>',
        ])

    def test_unmatched_identifier_loading(self):
        # Try to load db fixture 3. This won't load because the database identifier doesn't match
        management.call_command('loaddata', 'db_fixture_3', verbosity=0, commit=False)
        self.assertQuerysetEqual(Article.objects.all(), [])

        management.call_command('loaddata', 'db_fixture_3', verbosity=0, using='default', commit=False)
        self.assertQuerysetEqual(Article.objects.all(), [])

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
        self._dumpdata_assert(['fixtures'], '[{"pk": 1, "model": "fixtures.category", "fields": {"description": "Latest news stories", "title": "News Stories"}}, {"pk": 2, "model": "fixtures.article", "fields": {"headline": "Poker has no place on ESPN", "pub_date": "2006-06-16T12:00:00"}}, {"pk": 3, "model": "fixtures.article", "fields": {"headline": "Time to reform copyright", "pub_date": "2006-06-16T13:00:00"}}, {"pk": 1, "model": "fixtures.tag", "fields": {"tagged_type": ["fixtures", "article"], "name": "copyright", "tagged_id": 3}}, {"pk": 2, "model": "fixtures.tag", "fields": {"tagged_type": ["fixtures", "article"], "name": "law", "tagged_id": 3}}, {"pk": 1, "model": "fixtures.person", "fields": {"name": "Django Reinhardt"}}, {"pk": 2, "model": "fixtures.person", "fields": {"name": "Stephane Grappelli"}}, {"pk": 3, "model": "fixtures.person", "fields": {"name": "Prince"}}, {"pk": 10, "model": "fixtures.book", "fields": {"name": "Achieving self-awareness of Python programs", "authors": []}}]', natural_keys=True)

        # Dump the current contents of the database as an XML fixture
        self._dumpdata_assert(['fixtures'], """<?xml version="1.0" encoding="utf-8"?>
<django-objects version="1.0"><object pk="1" model="fixtures.category"><field type="CharField" name="title">News Stories</field><field type="TextField" name="description">Latest news stories</field></object><object pk="2" model="fixtures.article"><field type="CharField" name="headline">Poker has no place on ESPN</field><field type="DateTimeField" name="pub_date">2006-06-16T12:00:00</field></object><object pk="3" model="fixtures.article"><field type="CharField" name="headline">Time to reform copyright</field><field type="DateTimeField" name="pub_date">2006-06-16T13:00:00</field></object><object pk="1" model="fixtures.tag"><field type="CharField" name="name">copyright</field><field to="contenttypes.contenttype" name="tagged_type" rel="ManyToOneRel"><natural>fixtures</natural><natural>article</natural></field><field type="PositiveIntegerField" name="tagged_id">3</field></object><object pk="2" model="fixtures.tag"><field type="CharField" name="name">law</field><field to="contenttypes.contenttype" name="tagged_type" rel="ManyToOneRel"><natural>fixtures</natural><natural>article</natural></field><field type="PositiveIntegerField" name="tagged_id">3</field></object><object pk="1" model="fixtures.person"><field type="CharField" name="name">Django Reinhardt</field></object><object pk="2" model="fixtures.person"><field type="CharField" name="name">Stephane Grappelli</field></object><object pk="3" model="fixtures.person"><field type="CharField" name="name">Prince</field></object><object pk="10" model="fixtures.book"><field type="CharField" name="name">Achieving self-awareness of Python programs</field><field to="fixtures.person" name="authors" rel="ManyToManyRel"></field></object></django-objects>""", format='xml', natural_keys=True)


class FixtureTransactionTests(DumpDataAssertMixin, TransactionTestCase):

    @skipUnlessDBFeature('supports_forward_references')
    def test_format_discovery(self):
        # Load fixture 1 again, using format discovery
        management.call_command('loaddata', 'fixture1', verbosity=0, commit=False)
        self.assertQuerysetEqual(Article.objects.all(), [
            '<Article: Time to reform copyright>',
            '<Article: Poker has no place on ESPN>',
        ])

        # Try to load fixture 2 using format discovery; this will fail
        # because there are two fixture2's in the fixtures directory
        with self.assertRaises(management.CommandError) as cm:
            management.call_command('loaddata', 'fixture2', verbosity=0)
            self.assertIn("Multiple fixtures named 'fixture2'", cm.exception.args[0])

        # object list is unaffected
        self.assertQuerysetEqual(Article.objects.all(), [
            '<Article: Time to reform copyright>',
            '<Article: Poker has no place on ESPN>',
        ])

        # Dump the current contents of the database as a JSON fixture
        self._dumpdata_assert(['fixtures'], '[{"pk": 1, "model": "fixtures.category", "fields": {"description": "Latest news stories", "title": "News Stories"}}, {"pk": 2, "model": "fixtures.article", "fields": {"headline": "Poker has no place on ESPN", "pub_date": "2006-06-16T12:00:00"}}, {"pk": 3, "model": "fixtures.article", "fields": {"headline": "Time to reform copyright", "pub_date": "2006-06-16T13:00:00"}}, {"pk": 10, "model": "fixtures.book", "fields": {"name": "Achieving self-awareness of Python programs", "authors": []}}]')

        # Load fixture 4 (compressed), using format discovery
        management.call_command('loaddata', 'fixture4', verbosity=0, commit=False)
        self.assertQuerysetEqual(Article.objects.all(), [
            '<Article: Django pets kitten>',
            '<Article: Time to reform copyright>',
            '<Article: Poker has no place on ESPN>',
        ])
