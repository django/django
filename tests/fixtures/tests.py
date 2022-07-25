import gzip
import sys
import tempfile
import unittest
import warnings
from io import StringIO
from pathlib import Path
from unittest import mock

from django.apps import apps
from django.contrib.sites.models import Site
from django.core import management
from django.core.files.temp import NamedTemporaryFile
from django.core.management import CommandError
from django.core.management.commands.dumpdata import ProxyModelWarning
from django.core.serializers.base import ProgressBar
from django.db import IntegrityError, connection
from django.test import TestCase, TransactionTestCase, skipUnlessDBFeature

from .models import (
    Article,
    Category,
    CircularA,
    CircularB,
    NaturalKeyThing,
    PrimaryKeyUUIDModel,
    ProxySpy,
    Spy,
    Tag,
    Visa,
)

try:
    import bz2  # NOQA

    HAS_BZ2 = True
except ImportError:
    HAS_BZ2 = False

try:
    import lzma  # NOQA

    HAS_LZMA = True
except ImportError:
    HAS_LZMA = False


class TestCaseFixtureLoadingTests(TestCase):
    fixtures = ["fixture1.json", "fixture2.json"]

    def test_class_fixtures(self):
        "Test case has installed 3 fixture objects"
        self.assertSequenceEqual(
            Article.objects.values_list("headline", flat=True),
            [
                "Django conquers world!",
                "Copyright is fine the way it is",
                "Poker has no place on ESPN",
            ],
        )


class SubclassTestCaseFixtureLoadingTests(TestCaseFixtureLoadingTests):
    """
    Make sure that subclasses can remove fixtures from parent class (#21089).
    """

    fixtures = []

    def test_class_fixtures(self):
        "There were no fixture objects installed"
        self.assertEqual(Article.objects.count(), 0)


class DumpDataAssertMixin:
    def _dumpdata_assert(
        self,
        args,
        output,
        format="json",
        filename=None,
        natural_foreign_keys=False,
        natural_primary_keys=False,
        use_base_manager=False,
        exclude_list=[],
        primary_keys="",
    ):
        new_io = StringIO()
        filename = filename and Path(tempfile.gettempdir()) / filename
        management.call_command(
            "dumpdata",
            *args,
            format=format,
            stdout=new_io,
            stderr=new_io,
            output=filename,
            use_natural_foreign_keys=natural_foreign_keys,
            use_natural_primary_keys=natural_primary_keys,
            use_base_manager=use_base_manager,
            exclude=exclude_list,
            primary_keys=primary_keys,
        )
        if filename:
            file_root = filename.with_suffix("")
            compression_formats = {
                ".bz2": (open, file_root),
                ".gz": (gzip.open, filename),
                ".lzma": (open, file_root),
                ".xz": (open, file_root),
                ".zip": (open, file_root),
            }
            if HAS_BZ2:
                compression_formats[".bz2"] = (bz2.open, filename)
            if HAS_LZMA:
                compression_formats[".lzma"] = (lzma.open, filename)
                compression_formats[".xz"] = (lzma.open, filename)
            try:
                open_method, file_path = compression_formats[filename.suffix]
            except KeyError:
                open_method, file_path = open, filename
            with open_method(file_path, "rt") as f:
                command_output = f.read()
            file_path.unlink()
        else:
            command_output = new_io.getvalue().strip()
        if format == "json":
            self.assertJSONEqual(command_output, output)
        elif format == "xml":
            self.assertXMLEqual(command_output, output)
        else:
            self.assertEqual(command_output, output)


class FixtureLoadingTests(DumpDataAssertMixin, TestCase):
    def test_loading_and_dumping(self):
        apps.clear_cache()
        Site.objects.all().delete()
        # Load fixture 1. Single JSON file, with two objects.
        management.call_command("loaddata", "fixture1.json", verbosity=0)
        self.assertSequenceEqual(
            Article.objects.values_list("headline", flat=True),
            ["Time to reform copyright", "Poker has no place on ESPN"],
        )

        # Dump the current contents of the database as a JSON fixture
        self._dumpdata_assert(
            ["fixtures"],
            '[{"pk": 1, "model": "fixtures.category", "fields": '
            '{"description": "Latest news stories", "title": "News Stories"}}, '
            '{"pk": 2, "model": "fixtures.article", "fields": '
            '{"headline": "Poker has no place on ESPN", '
            '"pub_date": "2006-06-16T12:00:00"}}, '
            '{"pk": 3, "model": "fixtures.article", "fields": '
            '{"headline": "Time to reform copyright", '
            '"pub_date": "2006-06-16T13:00:00"}}]',
        )

        # Try just dumping the contents of fixtures.Category
        self._dumpdata_assert(
            ["fixtures.Category"],
            '[{"pk": 1, "model": "fixtures.category", "fields": '
            '{"description": "Latest news stories", "title": "News Stories"}}]',
        )

        # ...and just fixtures.Article
        self._dumpdata_assert(
            ["fixtures.Article"],
            '[{"pk": 2, "model": "fixtures.article", "fields": '
            '{"headline": "Poker has no place on ESPN", '
            '"pub_date": "2006-06-16T12:00:00"}}, '
            '{"pk": 3, "model": "fixtures.article", "fields": '
            '{"headline": "Time to reform copyright", '
            '"pub_date": "2006-06-16T13:00:00"}}]',
        )

        # ...and both
        self._dumpdata_assert(
            ["fixtures.Category", "fixtures.Article"],
            '[{"pk": 1, "model": "fixtures.category", "fields": '
            '{"description": "Latest news stories", "title": "News Stories"}}, '
            '{"pk": 2, "model": "fixtures.article", "fields": '
            '{"headline": "Poker has no place on ESPN", '
            '"pub_date": "2006-06-16T12:00:00"}}, '
            '{"pk": 3, "model": "fixtures.article", "fields": '
            '{"headline": "Time to reform copyright", '
            '"pub_date": "2006-06-16T13:00:00"}}]',
        )

        # Specify a specific model twice
        self._dumpdata_assert(
            ["fixtures.Article", "fixtures.Article"],
            (
                '[{"pk": 2, "model": "fixtures.article", "fields": '
                '{"headline": "Poker has no place on ESPN", '
                '"pub_date": "2006-06-16T12:00:00"}}, '
                '{"pk": 3, "model": "fixtures.article", "fields": '
                '{"headline": "Time to reform copyright", '
                '"pub_date": "2006-06-16T13:00:00"}}]'
            ),
        )

        # Specify a dump that specifies Article both explicitly and implicitly
        self._dumpdata_assert(
            ["fixtures.Article", "fixtures"],
            '[{"pk": 1, "model": "fixtures.category", "fields": '
            '{"description": "Latest news stories", "title": "News Stories"}}, '
            '{"pk": 2, "model": "fixtures.article", "fields": '
            '{"headline": "Poker has no place on ESPN", '
            '"pub_date": "2006-06-16T12:00:00"}}, '
            '{"pk": 3, "model": "fixtures.article", "fields": '
            '{"headline": "Time to reform copyright", '
            '"pub_date": "2006-06-16T13:00:00"}}]',
        )

        # Specify a dump that specifies Article both explicitly and implicitly,
        # but lists the app first (#22025).
        self._dumpdata_assert(
            ["fixtures", "fixtures.Article"],
            '[{"pk": 1, "model": "fixtures.category", "fields": '
            '{"description": "Latest news stories", "title": "News Stories"}}, '
            '{"pk": 2, "model": "fixtures.article", "fields": '
            '{"headline": "Poker has no place on ESPN", '
            '"pub_date": "2006-06-16T12:00:00"}}, '
            '{"pk": 3, "model": "fixtures.article", "fields": '
            '{"headline": "Time to reform copyright", '
            '"pub_date": "2006-06-16T13:00:00"}}]',
        )

        # Same again, but specify in the reverse order
        self._dumpdata_assert(
            ["fixtures"],
            '[{"pk": 1, "model": "fixtures.category", "fields": '
            '{"description": "Latest news stories", "title": "News Stories"}}, '
            '{"pk": 2, "model": "fixtures.article", "fields": '
            '{"headline": "Poker has no place on ESPN", '
            '"pub_date": "2006-06-16T12:00:00"}}, '
            '{"pk": 3, "model": "fixtures.article", "fields": '
            '{"headline": "Time to reform copyright", '
            '"pub_date": "2006-06-16T13:00:00"}}]',
        )

        # Specify one model from one application, and an entire other application.
        self._dumpdata_assert(
            ["fixtures.Category", "sites"],
            '[{"pk": 1, "model": "fixtures.category", "fields": '
            '{"description": "Latest news stories", "title": "News Stories"}}, '
            '{"pk": 1, "model": "sites.site", "fields": '
            '{"domain": "example.com", "name": "example.com"}}]',
        )

        # Load fixture 2. JSON file imported by default. Overwrites some
        # existing objects.
        management.call_command("loaddata", "fixture2.json", verbosity=0)
        self.assertSequenceEqual(
            Article.objects.values_list("headline", flat=True),
            [
                "Django conquers world!",
                "Copyright is fine the way it is",
                "Poker has no place on ESPN",
            ],
        )

        # Load fixture 3, XML format.
        management.call_command("loaddata", "fixture3.xml", verbosity=0)
        self.assertSequenceEqual(
            Article.objects.values_list("headline", flat=True),
            [
                "XML identified as leading cause of cancer",
                "Django conquers world!",
                "Copyright is fine the way it is",
                "Poker on TV is great!",
            ],
        )

        # Load fixture 6, JSON file with dynamic ContentType fields. Testing ManyToOne.
        management.call_command("loaddata", "fixture6.json", verbosity=0)
        self.assertQuerySetEqual(
            Tag.objects.all(),
            [
                '<Tag: <Article: Copyright is fine the way it is> tagged "copyright">',
                '<Tag: <Article: Copyright is fine the way it is> tagged "law">',
            ],
            transform=repr,
            ordered=False,
        )

        # Load fixture 7, XML file with dynamic ContentType fields. Testing ManyToOne.
        management.call_command("loaddata", "fixture7.xml", verbosity=0)
        self.assertQuerySetEqual(
            Tag.objects.all(),
            [
                '<Tag: <Article: Copyright is fine the way it is> tagged "copyright">',
                '<Tag: <Article: Copyright is fine the way it is> tagged "legal">',
                '<Tag: <Article: Django conquers world!> tagged "django">',
                '<Tag: <Article: Django conquers world!> tagged "world domination">',
            ],
            transform=repr,
            ordered=False,
        )

        # Load fixture 8, JSON file with dynamic Permission fields. Testing ManyToMany.
        management.call_command("loaddata", "fixture8.json", verbosity=0)
        self.assertQuerySetEqual(
            Visa.objects.all(),
            [
                "<Visa: Django Reinhardt Can add user, Can change user, Can delete "
                "user>",
                "<Visa: Stephane Grappelli Can add user>",
                "<Visa: Prince >",
            ],
            transform=repr,
            ordered=False,
        )

        # Load fixture 9, XML file with dynamic Permission fields. Testing ManyToMany.
        management.call_command("loaddata", "fixture9.xml", verbosity=0)
        self.assertQuerySetEqual(
            Visa.objects.all(),
            [
                "<Visa: Django Reinhardt Can add user, Can change user, Can delete "
                "user>",
                "<Visa: Stephane Grappelli Can add user, Can delete user>",
                '<Visa: Artist formerly known as "Prince" Can change user>',
            ],
            transform=repr,
            ordered=False,
        )

        # object list is unaffected
        self.assertSequenceEqual(
            Article.objects.values_list("headline", flat=True),
            [
                "XML identified as leading cause of cancer",
                "Django conquers world!",
                "Copyright is fine the way it is",
                "Poker on TV is great!",
            ],
        )

        # By default, you get raw keys on dumpdata
        self._dumpdata_assert(
            ["fixtures.book"],
            '[{"pk": 1, "model": "fixtures.book", "fields": '
            '{"name": "Music for all ages", "authors": [3, 1]}}]',
        )

        # But you can get natural keys if you ask for them and they are available
        self._dumpdata_assert(
            ["fixtures.book"],
            '[{"pk": 1, "model": "fixtures.book", "fields": '
            '{"name": "Music for all ages", "authors": '
            '[["Artist formerly known as \\"Prince\\""], ["Django Reinhardt"]]}}]',
            natural_foreign_keys=True,
        )

        # You can also omit the primary keys for models that we can get later
        # with natural keys.
        self._dumpdata_assert(
            ["fixtures.person"],
            '[{"fields": {"name": "Django Reinhardt"}, "model": "fixtures.person"}, '
            '{"fields": {"name": "Stephane Grappelli"}, "model": "fixtures.person"}, '
            '{"fields": {"name": "Artist formerly known as \\"Prince\\""}, '
            '"model": "fixtures.person"}]',
            natural_primary_keys=True,
        )

        # Dump the current contents of the database as a JSON fixture
        self._dumpdata_assert(
            ["fixtures"],
            '[{"pk": 1, "model": "fixtures.category", "fields": '
            '{"description": "Latest news stories", "title": "News Stories"}}, '
            '{"pk": 2, "model": "fixtures.article", "fields": '
            '{"headline": "Poker on TV is great!", '
            '"pub_date": "2006-06-16T11:00:00"}}, '
            '{"pk": 3, "model": "fixtures.article", "fields": '
            '{"headline": "Copyright is fine the way it is", '
            '"pub_date": "2006-06-16T14:00:00"}}, '
            '{"pk": 4, "model": "fixtures.article", "fields": '
            '{"headline": "Django conquers world!", '
            '"pub_date": "2006-06-16T15:00:00"}}, '
            '{"pk": 5, "model": "fixtures.article", "fields": '
            '{"headline": "XML identified as leading cause of cancer", '
            '"pub_date": "2006-06-16T16:00:00"}}, '
            '{"pk": 1, "model": "fixtures.tag", "fields": '
            '{"tagged_type": ["fixtures", "article"], "name": "copyright", '
            '"tagged_id": 3}}, '
            '{"pk": 2, "model": "fixtures.tag", "fields": '
            '{"tagged_type": ["fixtures", "article"], "name": "legal", '
            '"tagged_id": 3}}, '
            '{"pk": 3, "model": "fixtures.tag", "fields": '
            '{"tagged_type": ["fixtures", "article"], "name": "django", '
            '"tagged_id": 4}}, '
            '{"pk": 4, "model": "fixtures.tag", "fields": '
            '{"tagged_type": ["fixtures", "article"], "name": "world domination", '
            '"tagged_id": 4}}, '
            '{"pk": 1, "model": "fixtures.person", '
            '"fields": {"name": "Django Reinhardt"}}, '
            '{"pk": 2, "model": "fixtures.person", '
            '"fields": {"name": "Stephane Grappelli"}}, '
            '{"pk": 3, "model": "fixtures.person", '
            '"fields": {"name": "Artist formerly known as \\"Prince\\""}}, '
            '{"pk": 1, "model": "fixtures.visa", '
            '"fields": {"person": ["Django Reinhardt"], "permissions": '
            '[["add_user", "auth", "user"], ["change_user", "auth", "user"], '
            '["delete_user", "auth", "user"]]}}, '
            '{"pk": 2, "model": "fixtures.visa", "fields": '
            '{"person": ["Stephane Grappelli"], "permissions": '
            '[["add_user", "auth", "user"], ["delete_user", "auth", "user"]]}}, '
            '{"pk": 3, "model": "fixtures.visa", "fields": '
            '{"person": ["Artist formerly known as \\"Prince\\""], "permissions": '
            '[["change_user", "auth", "user"]]}}, '
            '{"pk": 1, "model": "fixtures.book", "fields": '
            '{"name": "Music for all ages", "authors": '
            '[["Artist formerly known as \\"Prince\\""], ["Django Reinhardt"]]}}]',
            natural_foreign_keys=True,
        )

        # Dump the current contents of the database as an XML fixture
        self._dumpdata_assert(
            ["fixtures"],
            '<?xml version="1.0" encoding="utf-8"?><django-objects version="1.0">'
            '<object pk="1" model="fixtures.category">'
            '<field type="CharField" name="title">News Stories</field>'
            '<field type="TextField" name="description">Latest news stories</field>'
            "</object>"
            '<object pk="2" model="fixtures.article">'
            '<field type="CharField" name="headline">Poker on TV is great!</field>'
            '<field type="DateTimeField" name="pub_date">2006-06-16T11:00:00</field>'
            "</object>"
            '<object pk="3" model="fixtures.article">'
            '<field type="CharField" name="headline">Copyright is fine the way it is'
            "</field>"
            '<field type="DateTimeField" name="pub_date">2006-06-16T14:00:00</field>'
            "</object>"
            '<object pk="4" model="fixtures.article">'
            '<field type="CharField" name="headline">Django conquers world!</field>'
            '<field type="DateTimeField" name="pub_date">2006-06-16T15:00:00</field>'
            "</object>"
            '<object pk="5" model="fixtures.article">'
            '<field type="CharField" name="headline">'
            "XML identified as leading cause of cancer</field>"
            '<field type="DateTimeField" name="pub_date">2006-06-16T16:00:00</field>'
            "</object>"
            '<object pk="1" model="fixtures.tag">'
            '<field type="CharField" name="name">copyright</field>'
            '<field to="contenttypes.contenttype" name="tagged_type" '
            'rel="ManyToOneRel"><natural>fixtures</natural><natural>article</natural>'
            "</field>"
            '<field type="PositiveIntegerField" name="tagged_id">3</field>'
            "</object>"
            '<object pk="2" model="fixtures.tag">'
            '<field type="CharField" name="name">legal</field>'
            '<field to="contenttypes.contenttype" name="tagged_type" '
            'rel="ManyToOneRel"><natural>fixtures</natural><natural>article</natural>'
            "</field>"
            '<field type="PositiveIntegerField" name="tagged_id">3</field></object>'
            '<object pk="3" model="fixtures.tag">'
            '<field type="CharField" name="name">django</field>'
            '<field to="contenttypes.contenttype" name="tagged_type" '
            'rel="ManyToOneRel"><natural>fixtures</natural><natural>article</natural>'
            "</field>"
            '<field type="PositiveIntegerField" name="tagged_id">4</field>'
            "</object>"
            '<object pk="4" model="fixtures.tag">'
            '<field type="CharField" name="name">world domination</field>'
            '<field to="contenttypes.contenttype" name="tagged_type" '
            'rel="ManyToOneRel"><natural>fixtures</natural><natural>article</natural>'
            "</field>"
            '<field type="PositiveIntegerField" name="tagged_id">4</field>'
            "</object>"
            '<object pk="1" model="fixtures.person">'
            '<field type="CharField" name="name">Django Reinhardt</field>'
            "</object>"
            '<object pk="2" model="fixtures.person">'
            '<field type="CharField" name="name">Stephane Grappelli</field>'
            "</object>"
            '<object pk="3" model="fixtures.person">'
            '<field type="CharField" name="name">Artist formerly known as "Prince"'
            "</field>"
            "</object>"
            '<object pk="1" model="fixtures.visa">'
            '<field to="fixtures.person" name="person" rel="ManyToOneRel">'
            "<natural>Django Reinhardt</natural></field>"
            '<field to="auth.permission" name="permissions" rel="ManyToManyRel">'
            "<object><natural>add_user</natural><natural>auth</natural>"
            "<natural>user</natural></object><object><natural>change_user</natural>"
            "<natural>auth</natural><natural>user</natural></object>"
            "<object><natural>delete_user</natural><natural>auth</natural>"
            "<natural>user</natural></object></field>"
            "</object>"
            '<object pk="2" model="fixtures.visa">'
            '<field to="fixtures.person" name="person" rel="ManyToOneRel">'
            "<natural>Stephane Grappelli</natural></field>"
            '<field to="auth.permission" name="permissions" rel="ManyToManyRel">'
            "<object><natural>add_user</natural><natural>auth</natural>"
            "<natural>user</natural></object>"
            "<object><natural>delete_user</natural><natural>auth</natural>"
            "<natural>user</natural></object></field>"
            "</object>"
            '<object pk="3" model="fixtures.visa">'
            '<field to="fixtures.person" name="person" rel="ManyToOneRel">'
            '<natural>Artist formerly known as "Prince"</natural></field>'
            '<field to="auth.permission" name="permissions" rel="ManyToManyRel">'
            "<object><natural>change_user</natural><natural>auth</natural>"
            "<natural>user</natural></object></field>"
            "</object>"
            '<object pk="1" model="fixtures.book">'
            '<field type="CharField" name="name">Music for all ages</field>'
            '<field to="fixtures.person" name="authors" rel="ManyToManyRel">'
            '<object><natural>Artist formerly known as "Prince"</natural></object>'
            "<object><natural>Django Reinhardt</natural></object></field>"
            "</object></django-objects>",
            format="xml",
            natural_foreign_keys=True,
        )

    def test_dumpdata_with_excludes(self):
        # Load fixture1 which has a site, two articles, and a category
        Site.objects.all().delete()
        management.call_command("loaddata", "fixture1.json", verbosity=0)

        # Excluding fixtures app should only leave sites
        self._dumpdata_assert(
            ["sites", "fixtures"],
            '[{"pk": 1, "model": "sites.site", "fields": '
            '{"domain": "example.com", "name": "example.com"}}]',
            exclude_list=["fixtures"],
        )

        # Excluding fixtures.Article/Book should leave fixtures.Category
        self._dumpdata_assert(
            ["sites", "fixtures"],
            '[{"pk": 1, "model": "sites.site", '
            '"fields": {"domain": "example.com", "name": "example.com"}}, '
            '{"pk": 1, "model": "fixtures.category", "fields": '
            '{"description": "Latest news stories", "title": "News Stories"}}]',
            exclude_list=["fixtures.Article", "fixtures.Book"],
        )

        # Excluding fixtures and fixtures.Article/Book should be a no-op
        self._dumpdata_assert(
            ["sites", "fixtures"],
            '[{"pk": 1, "model": "sites.site", '
            '"fields": {"domain": "example.com", "name": "example.com"}}, '
            '{"pk": 1, "model": "fixtures.category", '
            '"fields": {"description": "Latest news stories", '
            '"title": "News Stories"}}]',
            exclude_list=["fixtures.Article", "fixtures.Book"],
        )

        # Excluding sites and fixtures.Article/Book should only leave fixtures.Category
        self._dumpdata_assert(
            ["sites", "fixtures"],
            '[{"pk": 1, "model": "fixtures.category", "fields": '
            '{"description": "Latest news stories", "title": "News Stories"}}]',
            exclude_list=["fixtures.Article", "fixtures.Book", "sites"],
        )

        # Excluding a bogus app should throw an error
        with self.assertRaisesMessage(
            management.CommandError, "No installed app with label 'foo_app'."
        ):
            self._dumpdata_assert(["fixtures", "sites"], "", exclude_list=["foo_app"])

        # Excluding a bogus model should throw an error
        with self.assertRaisesMessage(
            management.CommandError, "Unknown model: fixtures.FooModel"
        ):
            self._dumpdata_assert(
                ["fixtures", "sites"], "", exclude_list=["fixtures.FooModel"]
            )

    @unittest.skipIf(
        sys.platform == "win32", "Windows doesn't support '?' in filenames."
    )
    def test_load_fixture_with_special_characters(self):
        management.call_command("loaddata", "fixture_with[special]chars", verbosity=0)
        self.assertEqual(
            Article.objects.get().headline,
            "How To Deal With Special Characters",
        )

    def test_dumpdata_with_filtering_manager(self):
        spy1 = Spy.objects.create(name="Paul")
        spy2 = Spy.objects.create(name="Alex", cover_blown=True)
        self.assertSequenceEqual(Spy.objects.all(), [spy1])
        # Use the default manager
        self._dumpdata_assert(
            ["fixtures.Spy"],
            '[{"pk": %d, "model": "fixtures.spy", "fields": {"cover_blown": false}}]'
            % spy1.pk,
        )
        # Dump using Django's base manager. Should return all objects,
        # even those normally filtered by the manager
        self._dumpdata_assert(
            ["fixtures.Spy"],
            '[{"pk": %d, "model": "fixtures.spy", "fields": {"cover_blown": true}}, '
            '{"pk": %d, "model": "fixtures.spy", "fields": {"cover_blown": false}}]'
            % (spy2.pk, spy1.pk),
            use_base_manager=True,
        )

    def test_dumpdata_with_pks(self):
        management.call_command("loaddata", "fixture1.json", verbosity=0)
        management.call_command("loaddata", "fixture2.json", verbosity=0)
        self._dumpdata_assert(
            ["fixtures.Article"],
            '[{"pk": 2, "model": "fixtures.article", '
            '"fields": {"headline": "Poker has no place on ESPN", '
            '"pub_date": "2006-06-16T12:00:00"}}, '
            '{"pk": 3, "model": "fixtures.article", "fields": '
            '{"headline": "Copyright is fine the way it is", '
            '"pub_date": "2006-06-16T14:00:00"}}]',
            primary_keys="2,3",
        )

        self._dumpdata_assert(
            ["fixtures.Article"],
            '[{"pk": 2, "model": "fixtures.article", '
            '"fields": {"headline": "Poker has no place on ESPN", '
            '"pub_date": "2006-06-16T12:00:00"}}]',
            primary_keys="2",
        )

        with self.assertRaisesMessage(
            management.CommandError, "You can only use --pks option with one model"
        ):
            self._dumpdata_assert(
                ["fixtures"],
                '[{"pk": 2, "model": "fixtures.article", "fields": '
                '{"headline": "Poker has no place on ESPN", '
                '"pub_date": "2006-06-16T12:00:00"}}, '
                '{"pk": 3, "model": "fixtures.article", "fields": '
                '{"headline": "Copyright is fine the way it is", '
                '"pub_date": "2006-06-16T14:00:00"}}]',
                primary_keys="2,3",
            )

        with self.assertRaisesMessage(
            management.CommandError, "You can only use --pks option with one model"
        ):
            self._dumpdata_assert(
                "",
                '[{"pk": 2, "model": "fixtures.article", "fields": '
                '{"headline": "Poker has no place on ESPN", '
                '"pub_date": "2006-06-16T12:00:00"}}, '
                '{"pk": 3, "model": "fixtures.article", "fields": '
                '{"headline": "Copyright is fine the way it is", '
                '"pub_date": "2006-06-16T14:00:00"}}]',
                primary_keys="2,3",
            )

        with self.assertRaisesMessage(
            management.CommandError, "You can only use --pks option with one model"
        ):
            self._dumpdata_assert(
                ["fixtures.Article", "fixtures.category"],
                '[{"pk": 2, "model": "fixtures.article", "fields": '
                '{"headline": "Poker has no place on ESPN", '
                '"pub_date": "2006-06-16T12:00:00"}}, '
                '{"pk": 3, "model": "fixtures.article", "fields": '
                '{"headline": "Copyright is fine the way it is", '
                '"pub_date": "2006-06-16T14:00:00"}}]',
                primary_keys="2,3",
            )

    def test_dumpdata_with_uuid_pks(self):
        m1 = PrimaryKeyUUIDModel.objects.create()
        m2 = PrimaryKeyUUIDModel.objects.create()
        output = StringIO()
        management.call_command(
            "dumpdata",
            "fixtures.PrimaryKeyUUIDModel",
            "--pks",
            ", ".join([str(m1.id), str(m2.id)]),
            stdout=output,
        )
        result = output.getvalue()
        self.assertIn('"pk": "%s"' % m1.id, result)
        self.assertIn('"pk": "%s"' % m2.id, result)

    def test_dumpdata_with_file_output(self):
        management.call_command("loaddata", "fixture1.json", verbosity=0)
        self._dumpdata_assert(
            ["fixtures"],
            '[{"pk": 1, "model": "fixtures.category", "fields": '
            '{"description": "Latest news stories", "title": "News Stories"}}, '
            '{"pk": 2, "model": "fixtures.article", "fields": '
            '{"headline": "Poker has no place on ESPN", '
            '"pub_date": "2006-06-16T12:00:00"}}, '
            '{"pk": 3, "model": "fixtures.article", "fields": '
            '{"headline": "Time to reform copyright", '
            '"pub_date": "2006-06-16T13:00:00"}}]',
            filename="dumpdata.json",
        )

    def test_dumpdata_with_file_gzip_output(self):
        management.call_command("loaddata", "fixture1.json", verbosity=0)
        self._dumpdata_assert(
            ["fixtures"],
            '[{"pk": 1, "model": "fixtures.category", "fields": '
            '{"description": "Latest news stories", "title": "News Stories"}}, '
            '{"pk": 2, "model": "fixtures.article", "fields": '
            '{"headline": "Poker has no place on ESPN", '
            '"pub_date": "2006-06-16T12:00:00"}}, '
            '{"pk": 3, "model": "fixtures.article", "fields": '
            '{"headline": "Time to reform copyright", '
            '"pub_date": "2006-06-16T13:00:00"}}]',
            filename="dumpdata.json.gz",
        )

    @unittest.skipUnless(HAS_BZ2, "No bz2 library detected.")
    def test_dumpdata_with_file_bz2_output(self):
        management.call_command("loaddata", "fixture1.json", verbosity=0)
        self._dumpdata_assert(
            ["fixtures"],
            '[{"pk": 1, "model": "fixtures.category", "fields": '
            '{"description": "Latest news stories", "title": "News Stories"}}, '
            '{"pk": 2, "model": "fixtures.article", "fields": '
            '{"headline": "Poker has no place on ESPN", '
            '"pub_date": "2006-06-16T12:00:00"}}, '
            '{"pk": 3, "model": "fixtures.article", "fields": '
            '{"headline": "Time to reform copyright", '
            '"pub_date": "2006-06-16T13:00:00"}}]',
            filename="dumpdata.json.bz2",
        )

    @unittest.skipUnless(HAS_LZMA, "No lzma library detected.")
    def test_dumpdata_with_file_lzma_output(self):
        management.call_command("loaddata", "fixture1.json", verbosity=0)
        self._dumpdata_assert(
            ["fixtures"],
            '[{"pk": 1, "model": "fixtures.category", "fields": '
            '{"description": "Latest news stories", "title": "News Stories"}}, '
            '{"pk": 2, "model": "fixtures.article", "fields": '
            '{"headline": "Poker has no place on ESPN", '
            '"pub_date": "2006-06-16T12:00:00"}}, '
            '{"pk": 3, "model": "fixtures.article", "fields": '
            '{"headline": "Time to reform copyright", '
            '"pub_date": "2006-06-16T13:00:00"}}]',
            filename="dumpdata.json.lzma",
        )

    @unittest.skipUnless(HAS_LZMA, "No lzma library detected.")
    def test_dumpdata_with_file_xz_output(self):
        management.call_command("loaddata", "fixture1.json", verbosity=0)
        self._dumpdata_assert(
            ["fixtures"],
            '[{"pk": 1, "model": "fixtures.category", "fields": '
            '{"description": "Latest news stories", "title": "News Stories"}}, '
            '{"pk": 2, "model": "fixtures.article", "fields": '
            '{"headline": "Poker has no place on ESPN", '
            '"pub_date": "2006-06-16T12:00:00"}}, '
            '{"pk": 3, "model": "fixtures.article", "fields": '
            '{"headline": "Time to reform copyright", '
            '"pub_date": "2006-06-16T13:00:00"}}]',
            filename="dumpdata.json.xz",
        )

    def test_dumpdata_with_file_zip_output(self):
        management.call_command("loaddata", "fixture1.json", verbosity=0)
        msg = "Unsupported file extension (.zip). Fixtures saved in 'dumpdata.json'."
        with self.assertWarnsMessage(RuntimeWarning, msg):
            self._dumpdata_assert(
                ["fixtures"],
                '[{"pk": 1, "model": "fixtures.category", "fields": '
                '{"description": "Latest news stories", "title": "News Stories"}}, '
                '{"pk": 2, "model": "fixtures.article", "fields": '
                '{"headline": "Poker has no place on ESPN", '
                '"pub_date": "2006-06-16T12:00:00"}}, '
                '{"pk": 3, "model": "fixtures.article", "fields": '
                '{"headline": "Time to reform copyright", '
                '"pub_date": "2006-06-16T13:00:00"}}]',
                filename="dumpdata.json.zip",
            )

    def test_dumpdata_progressbar(self):
        """
        Dumpdata shows a progress bar on the command line when --output is set,
        stdout is a tty, and verbosity > 0.
        """
        management.call_command("loaddata", "fixture1.json", verbosity=0)
        new_io = StringIO()
        new_io.isatty = lambda: True
        with NamedTemporaryFile() as file:
            options = {
                "format": "json",
                "stdout": new_io,
                "stderr": new_io,
                "output": file.name,
            }
            management.call_command("dumpdata", "fixtures", **options)
            self.assertTrue(
                new_io.getvalue().endswith(
                    "[" + "." * ProgressBar.progress_width + "]\n"
                )
            )

            # Test no progress bar when verbosity = 0
            options["verbosity"] = 0
            new_io = StringIO()
            new_io.isatty = lambda: True
            options.update({"stdout": new_io, "stderr": new_io})
            management.call_command("dumpdata", "fixtures", **options)
            self.assertEqual(new_io.getvalue(), "")

    def test_dumpdata_proxy_without_concrete(self):
        """
        A warning is displayed if a proxy model is dumped without its concrete
        parent.
        """
        ProxySpy.objects.create(name="Paul")
        msg = "fixtures.ProxySpy is a proxy model and won't be serialized."
        with self.assertWarnsMessage(ProxyModelWarning, msg):
            self._dumpdata_assert(["fixtures.ProxySpy"], "[]")

    def test_dumpdata_proxy_with_concrete(self):
        """
        A warning isn't displayed if a proxy model is dumped with its concrete
        parent.
        """
        spy = ProxySpy.objects.create(name="Paul")

        with warnings.catch_warnings(record=True) as warning_list:
            warnings.simplefilter("always")
            self._dumpdata_assert(
                ["fixtures.ProxySpy", "fixtures.Spy"],
                '[{"pk": %d, "model": "fixtures.spy", '
                '"fields": {"cover_blown": false}}]' % spy.pk,
            )
        self.assertEqual(len(warning_list), 0)

    def test_compress_format_loading(self):
        # Load fixture 4 (compressed), using format specification
        management.call_command("loaddata", "fixture4.json", verbosity=0)
        self.assertEqual(Article.objects.get().headline, "Django pets kitten")

    def test_compressed_specified_loading(self):
        # Load fixture 5 (compressed), using format *and* compression specification
        management.call_command("loaddata", "fixture5.json.zip", verbosity=0)
        self.assertEqual(
            Article.objects.get().headline,
            "WoW subscribers now outnumber readers",
        )

    def test_compressed_loading(self):
        # Load fixture 5 (compressed), only compression specification
        management.call_command("loaddata", "fixture5.zip", verbosity=0)
        self.assertEqual(
            Article.objects.get().headline,
            "WoW subscribers now outnumber readers",
        )

    def test_compressed_loading_gzip(self):
        management.call_command("loaddata", "fixture5.json.gz", verbosity=0)
        self.assertEqual(
            Article.objects.get().headline,
            "WoW subscribers now outnumber readers",
        )

    @unittest.skipUnless(HAS_BZ2, "No bz2 library detected.")
    def test_compressed_loading_bz2(self):
        management.call_command("loaddata", "fixture5.json.bz2", verbosity=0)
        self.assertEqual(
            Article.objects.get().headline,
            "WoW subscribers now outnumber readers",
        )

    @unittest.skipUnless(HAS_LZMA, "No lzma library detected.")
    def test_compressed_loading_lzma(self):
        management.call_command("loaddata", "fixture5.json.lzma", verbosity=0)
        self.assertEqual(
            Article.objects.get().headline,
            "WoW subscribers now outnumber readers",
        )

    @unittest.skipUnless(HAS_LZMA, "No lzma library detected.")
    def test_compressed_loading_xz(self):
        management.call_command("loaddata", "fixture5.json.xz", verbosity=0)
        self.assertEqual(
            Article.objects.get().headline,
            "WoW subscribers now outnumber readers",
        )

    def test_ambiguous_compressed_fixture(self):
        # The name "fixture5" is ambiguous, so loading raises an error.
        msg = "Multiple fixtures named 'fixture5'"
        with self.assertRaisesMessage(management.CommandError, msg):
            management.call_command("loaddata", "fixture5", verbosity=0)

    def test_db_loading(self):
        # Load db fixtures 1 and 2. These will load using the 'default'
        # database identifier implicitly.
        management.call_command("loaddata", "db_fixture_1", verbosity=0)
        management.call_command("loaddata", "db_fixture_2", verbosity=0)
        self.assertSequenceEqual(
            Article.objects.values_list("headline", flat=True),
            [
                "Who needs more than one database?",
                "Who needs to use compressed data?",
            ],
        )

    def test_loaddata_error_message(self):
        """
        Loading a fixture which contains an invalid object outputs an error
        message which contains the pk of the object that triggered the error.
        """
        # MySQL needs a little prodding to reject invalid data.
        # This won't affect other tests because the database connection
        # is closed at the end of each test.
        if connection.vendor == "mysql":
            with connection.cursor() as cursor:
                cursor.execute("SET sql_mode = 'TRADITIONAL'")
        msg = "Could not load fixtures.Article(pk=1):"
        with self.assertRaisesMessage(IntegrityError, msg):
            management.call_command("loaddata", "invalid.json", verbosity=0)

    @unittest.skipUnless(
        connection.vendor == "postgresql", "psycopg2 prohibits null characters in data."
    )
    def test_loaddata_null_characters_on_postgresql(self):
        msg = (
            "Could not load fixtures.Article(pk=2): "
            "A string literal cannot contain NUL (0x00) characters."
        )
        with self.assertRaisesMessage(ValueError, msg):
            management.call_command("loaddata", "null_character_in_field_value.json")

    def test_loaddata_app_option(self):
        with self.assertRaisesMessage(
            CommandError, "No fixture named 'db_fixture_1' found."
        ):
            management.call_command(
                "loaddata", "db_fixture_1", verbosity=0, app_label="someotherapp"
            )
        self.assertQuerySetEqual(Article.objects.all(), [])
        management.call_command(
            "loaddata", "db_fixture_1", verbosity=0, app_label="fixtures"
        )
        self.assertEqual(
            Article.objects.get().headline,
            "Who needs more than one database?",
        )

    def test_loaddata_verbosity_three(self):
        output = StringIO()
        management.call_command(
            "loaddata", "fixture1.json", verbosity=3, stdout=output, stderr=output
        )
        command_output = output.getvalue()
        self.assertIn(
            "\rProcessed 1 object(s).\rProcessed 2 object(s)."
            "\rProcessed 3 object(s).\rProcessed 4 object(s).\n",
            command_output,
        )

    def test_loading_using(self):
        # Load fixtures 1 and 2. These will load using the 'default' database
        # identifier explicitly.
        management.call_command(
            "loaddata", "db_fixture_1", verbosity=0, database="default"
        )
        management.call_command(
            "loaddata", "db_fixture_2", verbosity=0, database="default"
        )
        self.assertSequenceEqual(
            Article.objects.values_list("headline", flat=True),
            [
                "Who needs more than one database?",
                "Who needs to use compressed data?",
            ],
        )

    def test_unmatched_identifier_loading(self):
        # Db fixture 3 won't load because the database identifier doesn't
        # match.
        with self.assertRaisesMessage(
            CommandError, "No fixture named 'db_fixture_3' found."
        ):
            management.call_command("loaddata", "db_fixture_3", verbosity=0)
        with self.assertRaisesMessage(
            CommandError, "No fixture named 'db_fixture_3' found."
        ):
            management.call_command(
                "loaddata", "db_fixture_3", verbosity=0, database="default"
            )
        self.assertQuerySetEqual(Article.objects.all(), [])

    def test_output_formats(self):
        # Load back in fixture 1, we need the articles from it
        management.call_command("loaddata", "fixture1", verbosity=0)

        # Try to load fixture 6 using format discovery
        management.call_command("loaddata", "fixture6", verbosity=0)
        self.assertQuerySetEqual(
            Tag.objects.all(),
            [
                '<Tag: <Article: Time to reform copyright> tagged "copyright">',
                '<Tag: <Article: Time to reform copyright> tagged "law">',
            ],
            transform=repr,
            ordered=False,
        )

        # Dump the current contents of the database as a JSON fixture
        self._dumpdata_assert(
            ["fixtures"],
            '[{"pk": 1, "model": "fixtures.category", "fields": '
            '{"description": "Latest news stories", "title": "News Stories"}}, '
            '{"pk": 2, "model": "fixtures.article", "fields": '
            '{"headline": "Poker has no place on ESPN", '
            '"pub_date": "2006-06-16T12:00:00"}}, '
            '{"pk": 3, "model": "fixtures.article", "fields": '
            '{"headline": "Time to reform copyright", '
            '"pub_date": "2006-06-16T13:00:00"}}, '
            '{"pk": 1, "model": "fixtures.tag", "fields": '
            '{"tagged_type": ["fixtures", "article"], "name": "copyright", '
            '"tagged_id": 3}}, '
            '{"pk": 2, "model": "fixtures.tag", "fields": '
            '{"tagged_type": ["fixtures", "article"], "name": "law", "tagged_id": 3}}, '
            '{"pk": 1, "model": "fixtures.person", "fields": '
            '{"name": "Django Reinhardt"}}, '
            '{"pk": 2, "model": "fixtures.person", "fields": '
            '{"name": "Stephane Grappelli"}}, '
            '{"pk": 3, "model": "fixtures.person", "fields": {"name": "Prince"}}]',
            natural_foreign_keys=True,
        )

        # Dump the current contents of the database as an XML fixture
        self._dumpdata_assert(
            ["fixtures"],
            '<?xml version="1.0" encoding="utf-8"?><django-objects version="1.0">'
            '<object pk="1" model="fixtures.category">'
            '<field type="CharField" name="title">News Stories</field>'
            '<field type="TextField" name="description">Latest news stories</field>'
            "</object>"
            '<object pk="2" model="fixtures.article">'
            '<field type="CharField" name="headline">Poker has no place on ESPN</field>'
            '<field type="DateTimeField" name="pub_date">2006-06-16T12:00:00</field>'
            "</object>"
            '<object pk="3" model="fixtures.article">'
            '<field type="CharField" name="headline">Time to reform copyright</field>'
            '<field type="DateTimeField" name="pub_date">2006-06-16T13:00:00</field>'
            "</object>"
            '<object pk="1" model="fixtures.tag">'
            '<field type="CharField" name="name">copyright</field>'
            '<field to="contenttypes.contenttype" name="tagged_type" '
            'rel="ManyToOneRel"><natural>fixtures</natural>'
            "<natural>article</natural></field>"
            '<field type="PositiveIntegerField" name="tagged_id">3</field>'
            "</object>"
            '<object pk="2" model="fixtures.tag">'
            '<field type="CharField" name="name">law</field>'
            '<field to="contenttypes.contenttype" name="tagged_type" '
            'rel="ManyToOneRel"><natural>fixtures</natural>'
            "<natural>article</natural></field>"
            '<field type="PositiveIntegerField" name="tagged_id">3</field>'
            "</object>"
            '<object pk="1" model="fixtures.person">'
            '<field type="CharField" name="name">Django Reinhardt</field>'
            "</object>"
            '<object pk="2" model="fixtures.person">'
            '<field type="CharField" name="name">Stephane Grappelli</field>'
            "</object>"
            '<object pk="3" model="fixtures.person">'
            '<field type="CharField" name="name">Prince</field>'
            "</object></django-objects>",
            format="xml",
            natural_foreign_keys=True,
        )

    def test_loading_with_exclude_app(self):
        Site.objects.all().delete()
        management.call_command(
            "loaddata", "fixture1", exclude=["fixtures"], verbosity=0
        )
        self.assertFalse(Article.objects.exists())
        self.assertFalse(Category.objects.exists())
        self.assertEqual(Site.objects.get().domain, "example.com")

    def test_loading_with_exclude_model(self):
        Site.objects.all().delete()
        management.call_command(
            "loaddata", "fixture1", exclude=["fixtures.Article"], verbosity=0
        )
        self.assertFalse(Article.objects.exists())
        self.assertEqual(Category.objects.get().title, "News Stories")
        self.assertEqual(Site.objects.get().domain, "example.com")

    def test_exclude_option_errors(self):
        """Excluding a bogus app or model should raise an error."""
        msg = "No installed app with label 'foo_app'."
        with self.assertRaisesMessage(management.CommandError, msg):
            management.call_command(
                "loaddata", "fixture1", exclude=["foo_app"], verbosity=0
            )

        msg = "Unknown model: fixtures.FooModel"
        with self.assertRaisesMessage(management.CommandError, msg):
            management.call_command(
                "loaddata", "fixture1", exclude=["fixtures.FooModel"], verbosity=0
            )

    def test_stdin_without_format(self):
        """Reading from stdin raises an error if format isn't specified."""
        msg = "--format must be specified when reading from stdin."
        with self.assertRaisesMessage(management.CommandError, msg):
            management.call_command("loaddata", "-", verbosity=0)

    def test_loading_stdin(self):
        """Loading fixtures from stdin with json and xml."""
        tests_dir = Path(__file__).parent
        fixture_json = tests_dir / "fixtures" / "fixture1.json"
        fixture_xml = tests_dir / "fixtures" / "fixture3.xml"

        with mock.patch(
            "django.core.management.commands.loaddata.sys.stdin", fixture_json.open()
        ):
            management.call_command("loaddata", "--format=json", "-", verbosity=0)
            self.assertSequenceEqual(
                Article.objects.values_list("headline", flat=True),
                ["Time to reform copyright", "Poker has no place on ESPN"],
            )

        with mock.patch(
            "django.core.management.commands.loaddata.sys.stdin", fixture_xml.open()
        ):
            management.call_command("loaddata", "--format=xml", "-", verbosity=0)
            self.assertSequenceEqual(
                Article.objects.values_list("headline", flat=True),
                [
                    "XML identified as leading cause of cancer",
                    "Time to reform copyright",
                    "Poker on TV is great!",
                ],
            )


class NonexistentFixtureTests(TestCase):
    """
    Custom class to limit fixture dirs.
    """

    def test_loaddata_not_existent_fixture_file(self):
        stdout_output = StringIO()
        with self.assertRaisesMessage(
            CommandError, "No fixture named 'this_fixture_doesnt_exist' found."
        ):
            management.call_command(
                "loaddata", "this_fixture_doesnt_exist", stdout=stdout_output
            )

    @mock.patch("django.db.connection.enable_constraint_checking")
    @mock.patch("django.db.connection.disable_constraint_checking")
    def test_nonexistent_fixture_no_constraint_checking(
        self, disable_constraint_checking, enable_constraint_checking
    ):
        """
        If no fixtures match the loaddata command, constraints checks on the
        database shouldn't be disabled. This is performance critical on MSSQL.
        """
        with self.assertRaisesMessage(
            CommandError, "No fixture named 'this_fixture_doesnt_exist' found."
        ):
            management.call_command(
                "loaddata", "this_fixture_doesnt_exist", verbosity=0
            )
        disable_constraint_checking.assert_not_called()
        enable_constraint_checking.assert_not_called()


class FixtureTransactionTests(DumpDataAssertMixin, TransactionTestCase):

    available_apps = [
        "fixtures",
        "django.contrib.sites",
    ]

    @skipUnlessDBFeature("supports_forward_references")
    def test_format_discovery(self):
        # Load fixture 1 again, using format discovery
        management.call_command("loaddata", "fixture1", verbosity=0)
        self.assertSequenceEqual(
            Article.objects.values_list("headline", flat=True),
            ["Time to reform copyright", "Poker has no place on ESPN"],
        )

        # Try to load fixture 2 using format discovery; this will fail
        # because there are two fixture2's in the fixtures directory
        msg = "Multiple fixtures named 'fixture2'"
        with self.assertRaisesMessage(management.CommandError, msg):
            management.call_command("loaddata", "fixture2", verbosity=0)

        # object list is unaffected
        self.assertSequenceEqual(
            Article.objects.values_list("headline", flat=True),
            ["Time to reform copyright", "Poker has no place on ESPN"],
        )

        # Dump the current contents of the database as a JSON fixture
        self._dumpdata_assert(
            ["fixtures"],
            '[{"pk": 1, "model": "fixtures.category", "fields": '
            '{"description": "Latest news stories", "title": "News Stories"}}, '
            '{"pk": 2, "model": "fixtures.article", "fields": '
            '{"headline": "Poker has no place on ESPN", '
            '"pub_date": "2006-06-16T12:00:00"}}, '
            '{"pk": 3, "model": "fixtures.article", "fields": '
            '{"headline": "Time to reform copyright", '
            '"pub_date": "2006-06-16T13:00:00"}}]',
        )

        # Load fixture 4 (compressed), using format discovery
        management.call_command("loaddata", "fixture4", verbosity=0)
        self.assertSequenceEqual(
            Article.objects.values_list("headline", flat=True),
            [
                "Django pets kitten",
                "Time to reform copyright",
                "Poker has no place on ESPN",
            ],
        )


class ForwardReferenceTests(DumpDataAssertMixin, TestCase):
    def test_forward_reference_fk(self):
        management.call_command("loaddata", "forward_reference_fk.json", verbosity=0)
        t1, t2 = NaturalKeyThing.objects.all()
        self.assertEqual(t1.other_thing, t2)
        self.assertEqual(t2.other_thing, t1)
        self._dumpdata_assert(
            ["fixtures"],
            '[{"model": "fixtures.naturalkeything", "pk": 1, '
            '"fields": {"key": "t1", "other_thing": 2, "other_things": []}}, '
            '{"model": "fixtures.naturalkeything", "pk": 2, '
            '"fields": {"key": "t2", "other_thing": 1, "other_things": []}}]',
        )

    def test_forward_reference_fk_natural_key(self):
        management.call_command(
            "loaddata",
            "forward_reference_fk_natural_key.json",
            verbosity=0,
        )
        t1, t2 = NaturalKeyThing.objects.all()
        self.assertEqual(t1.other_thing, t2)
        self.assertEqual(t2.other_thing, t1)
        self._dumpdata_assert(
            ["fixtures"],
            '[{"model": "fixtures.naturalkeything", '
            '"fields": {"key": "t1", "other_thing": ["t2"], "other_things": []}}, '
            '{"model": "fixtures.naturalkeything", '
            '"fields": {"key": "t2", "other_thing": ["t1"], "other_things": []}}]',
            natural_primary_keys=True,
            natural_foreign_keys=True,
        )

    def test_forward_reference_m2m(self):
        management.call_command("loaddata", "forward_reference_m2m.json", verbosity=0)
        self.assertEqual(NaturalKeyThing.objects.count(), 3)
        t1 = NaturalKeyThing.objects.get_by_natural_key("t1")
        self.assertSequenceEqual(
            t1.other_things.order_by("key").values_list("key", flat=True),
            ["t2", "t3"],
        )
        self._dumpdata_assert(
            ["fixtures"],
            '[{"model": "fixtures.naturalkeything", "pk": 1, '
            '"fields": {"key": "t1", "other_thing": null, "other_things": [2, 3]}}, '
            '{"model": "fixtures.naturalkeything", "pk": 2, '
            '"fields": {"key": "t2", "other_thing": null, "other_things": []}}, '
            '{"model": "fixtures.naturalkeything", "pk": 3, '
            '"fields": {"key": "t3", "other_thing": null, "other_things": []}}]',
        )

    def test_forward_reference_m2m_natural_key(self):
        management.call_command(
            "loaddata",
            "forward_reference_m2m_natural_key.json",
            verbosity=0,
        )
        self.assertEqual(NaturalKeyThing.objects.count(), 3)
        t1 = NaturalKeyThing.objects.get_by_natural_key("t1")
        self.assertSequenceEqual(
            t1.other_things.order_by("key").values_list("key", flat=True),
            ["t2", "t3"],
        )
        self._dumpdata_assert(
            ["fixtures"],
            '[{"model": "fixtures.naturalkeything", '
            '"fields": {"key": "t1", "other_thing": null, '
            '"other_things": [["t2"], ["t3"]]}}, '
            '{"model": "fixtures.naturalkeything", '
            '"fields": {"key": "t2", "other_thing": null, "other_things": []}}, '
            '{"model": "fixtures.naturalkeything", '
            '"fields": {"key": "t3", "other_thing": null, "other_things": []}}]',
            natural_primary_keys=True,
            natural_foreign_keys=True,
        )


class CircularReferenceTests(DumpDataAssertMixin, TestCase):
    def test_circular_reference(self):
        management.call_command("loaddata", "circular_reference.json", verbosity=0)
        obj_a = CircularA.objects.get()
        obj_b = CircularB.objects.get()
        self.assertEqual(obj_a.obj, obj_b)
        self.assertEqual(obj_b.obj, obj_a)
        self._dumpdata_assert(
            ["fixtures"],
            '[{"model": "fixtures.circulara", "pk": 1, '
            '"fields": {"key": "x", "obj": 1}}, '
            '{"model": "fixtures.circularb", "pk": 1, '
            '"fields": {"key": "y", "obj": 1}}]',
        )

    def test_circular_reference_natural_key(self):
        management.call_command(
            "loaddata",
            "circular_reference_natural_key.json",
            verbosity=0,
        )
        obj_a = CircularA.objects.get()
        obj_b = CircularB.objects.get()
        self.assertEqual(obj_a.obj, obj_b)
        self.assertEqual(obj_b.obj, obj_a)
        self._dumpdata_assert(
            ["fixtures"],
            '[{"model": "fixtures.circulara", '
            '"fields": {"key": "x", "obj": ["y"]}}, '
            '{"model": "fixtures.circularb", '
            '"fields": {"key": "y", "obj": ["x"]}}]',
            natural_primary_keys=True,
            natural_foreign_keys=True,
        )
