import sys
import unittest
import warnings
from io import StringIO

from django.contrib.sites.models import Site
from django.core import management
from django.core.management import CommandError
from django.core.management.commands.dumpdata import ProxyModelWarning
from django.db import IntegrityError, connection
from django.test import TestCase, skipUnlessDBFeature

from .models import Article, PrimaryKeyUUIDModel, ProxySpy, Spy
from .tests import DumpDataAssertMixin

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


class ForceInsertLoadingTests(DumpDataAssertMixin, TestCase):
    def test_dumpdata_with_excludes(self):
        # Load fixture1 which has a site, two articles, and a category
        Site.objects.all().delete()
        management.call_command(
            "loaddata", "--force_insert", "fixture1.json", verbosity=0
        )

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
        management.call_command(
            "loaddata", "--force_insert", "fixture_with[special]chars", verbosity=0
        )
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

    def test_dumpdata_objects_with_prefetch_related(self):
        management.call_command(
            "loaddata", "--force_insert", "fixture6.json", "fixture8.json", verbosity=0
        )
        with self.assertNumQueries(5):
            self._dumpdata_assert(
                ["fixtures.visa"],
                '[{"fields": {"permissions": [["add_user", "auth", "user"]],'
                '"person": ["Stephane Grappelli"]},'
                '"model": "fixtures.visa", "pk": 2},'
                '{"fields": {"permissions": [], "person": ["Prince"]},'
                '"model": "fixtures.visa", "pk": 3}]',
                natural_foreign_keys=True,
                primary_keys="2,3",
            )

    def test_compress_format_loading(self):
        # Load fixture 4 (compressed), using format specification
        management.call_command(
            "loaddata", "--force_insert", "fixture4.json", verbosity=0
        )
        self.assertEqual(Article.objects.get().headline, "Django pets kitten")

    def test_compressed_specified_loading(self):
        # Load fixture 5 (compressed), using format *and* compression specification
        management.call_command(
            "loaddata", "--force_insert", "fixture5.json.zip", verbosity=0
        )
        self.assertEqual(
            Article.objects.get().headline,
            "WoW subscribers now outnumber readers",
        )

    def test_compressed_loading(self):
        # Load fixture 5 (compressed), only compression specification
        management.call_command(
            "loaddata", "--force_insert", "fixture5.zip", verbosity=0
        )
        self.assertEqual(
            Article.objects.get().headline,
            "WoW subscribers now outnumber readers",
        )

    def test_compressed_loading_gzip(self):
        management.call_command(
            "loaddata", "--force_insert", "fixture5.json.gz", verbosity=0
        )
        self.assertEqual(
            Article.objects.get().headline,
            "WoW subscribers now outnumber readers",
        )

    @unittest.skipUnless(HAS_BZ2, "No bz2 library detected.")
    def test_compressed_loading_bz2(self):
        management.call_command(
            "loaddata", "--force_insert", "fixture5.json.bz2", verbosity=0
        )
        self.assertEqual(
            Article.objects.get().headline,
            "WoW subscribers now outnumber readers",
        )

    @unittest.skipUnless(HAS_LZMA, "No lzma library detected.")
    def test_compressed_loading_lzma(self):
        management.call_command(
            "loaddata", "--force_insert", "fixture5.json.lzma", verbosity=0
        )
        self.assertEqual(
            Article.objects.get().headline,
            "WoW subscribers now outnumber readers",
        )

    @unittest.skipUnless(HAS_LZMA, "No lzma library detected.")
    def test_compressed_loading_xz(self):
        management.call_command(
            "loaddata", "--force_insert", "fixture5.json.xz", verbosity=0
        )
        self.assertEqual(
            Article.objects.get().headline,
            "WoW subscribers now outnumber readers",
        )

    def test_ambiguous_compressed_fixture(self):
        # The name "fixture5" is ambiguous, so loading raises an error.
        msg = "Multiple fixtures named 'fixture5'"
        with self.assertRaisesMessage(management.CommandError, msg):
            management.call_command(
                "loaddata", "--force_insert", "fixture5", verbosity=0
            )

    def test_db_loading(self):
        # Load db fixtures 1 and 2. These will load using the 'default'
        # database identifier implicitly.
        management.call_command(
            "loaddata", "--force_insert", "db_fixture_1", verbosity=0
        )
        management.call_command(
            "loaddata", "--force_insert", "db_fixture_2", verbosity=0
        )
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
            management.call_command(
                "loaddata", "--force_insert", "invalid.json", verbosity=0
            )

    @skipUnlessDBFeature("prohibits_null_characters_in_text_exception")
    def test_loaddata_null_characters_on_postgresql(self):
        error, msg = connection.features.prohibits_null_characters_in_text_exception
        msg = f"Could not load fixtures.Article(pk=2): {msg}"
        with self.assertRaisesMessage(error, msg):
            management.call_command(
                "loaddata", "--force_insert", "null_character_in_field_value.json"
            )

    def test_loaddata_app_option(self):
        with self.assertRaisesMessage(
            CommandError, "No fixture named 'db_fixture_1' found."
        ):
            management.call_command(
                "loaddata",
                "--force_insert",
                "db_fixture_1",
                verbosity=0,
                app_label="someotherapp",
            )
        self.assertQuerySetEqual(Article.objects.all(), [])
        management.call_command(
            "loaddata",
            "--force_insert",
            "db_fixture_1",
            verbosity=0,
            app_label="fixtures",
        )
        self.assertEqual(
            Article.objects.get().headline,
            "Who needs more than one database?",
        )

    def test_loading_using(self):
        # Load fixtures 1 and 2. These will load using the 'default' database
        # identifier explicitly.
        management.call_command(
            "loaddata",
            "--force_insert",
            "db_fixture_1",
            verbosity=0,
            database="default",
        )
        management.call_command(
            "loaddata",
            "--force_insert",
            "db_fixture_2",
            verbosity=0,
            database="default",
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
            management.call_command(
                "loaddata", "--force_insert", "db_fixture_3", verbosity=0
            )
        with self.assertRaisesMessage(
            CommandError, "No fixture named 'db_fixture_3' found."
        ):
            management.call_command(
                "loaddata",
                "--force_insert",
                "db_fixture_3",
                verbosity=0,
                database="default",
            )
        self.assertQuerySetEqual(Article.objects.all(), [])

    def test_exclude_option_errors(self):
        """Excluding a bogus app or model should raise an error."""
        msg = "No installed app with label 'foo_app'."
        with self.assertRaisesMessage(management.CommandError, msg):
            management.call_command(
                "loaddata",
                "--force_insert",
                "fixture1",
                exclude=["foo_app"],
                verbosity=0,
            )

        msg = "Unknown model: fixtures.FooModel"
        with self.assertRaisesMessage(management.CommandError, msg):
            management.call_command(
                "loaddata",
                "--force_insert",
                "fixture1",
                exclude=["fixtures.FooModel"],
                verbosity=0,
            )

    def test_stdin_without_format(self):
        """Reading from stdin raises an error if format isn't specified."""
        msg = "--format must be specified when reading from stdin."
        with self.assertRaisesMessage(management.CommandError, msg):
            management.call_command("loaddata", "--force_insert", "-", verbosity=0)


class BulkCreateLoadingTests(DumpDataAssertMixin, TestCase):
    def test_dumpdata_with_excludes(self):
        # Load fixture1 which has a site, two articles, and a category
        Site.objects.all().delete()
        management.call_command(
            "loaddata", "--bulk_create", "fixture1.json", verbosity=0
        )

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
        management.call_command(
            "loaddata", "--bulk_create", "fixture_with[special]chars", verbosity=0
        )
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

    @unittest.skip
    def test_dumpdata_objects_with_prefetch_related(self):
        management.call_command(
            "loaddata", "--bulk_create", "fixture6.json", "fixture8.json", verbosity=0
        )
        with self.assertNumQueries(5):
            self._dumpdata_assert(
                ["fixtures.visa"],
                '[{"fields": {"permissions": [["add_user", "auth", "user"]],'
                '"person": ["Stephane Grappelli"]},'
                '"model": "fixtures.visa", "pk": 2},'
                '{"fields": {"permissions": [], "person": ["Prince"]},'
                '"model": "fixtures.visa", "pk": 3}]',
                natural_foreign_keys=True,
                primary_keys="2,3",
            )

    def test_compress_format_loading(self):
        # Load fixture 4 (compressed), using format specification
        management.call_command(
            "loaddata", "--bulk_create", "fixture4.json", verbosity=0
        )
        self.assertEqual(Article.objects.get().headline, "Django pets kitten")

    def test_compressed_specified_loading(self):
        # Load fixture 5 (compressed), using format *and* compression specification
        management.call_command(
            "loaddata", "--bulk_create", "fixture5.json.zip", verbosity=0
        )
        self.assertEqual(
            Article.objects.get().headline,
            "WoW subscribers now outnumber readers",
        )

    def test_compressed_loading(self):
        # Load fixture 5 (compressed), only compression specification
        management.call_command(
            "loaddata", "--bulk_create", "fixture5.zip", verbosity=0
        )
        self.assertEqual(
            Article.objects.get().headline,
            "WoW subscribers now outnumber readers",
        )

    def test_compressed_loading_gzip(self):
        management.call_command(
            "loaddata", "--bulk_create", "fixture5.json.gz", verbosity=0
        )
        self.assertEqual(
            Article.objects.get().headline,
            "WoW subscribers now outnumber readers",
        )

    @unittest.skipUnless(HAS_BZ2, "No bz2 library detected.")
    def test_compressed_loading_bz2(self):
        management.call_command(
            "loaddata", "--bulk_create", "fixture5.json.bz2", verbosity=0
        )
        self.assertEqual(
            Article.objects.get().headline,
            "WoW subscribers now outnumber readers",
        )

    @unittest.skipUnless(HAS_LZMA, "No lzma library detected.")
    def test_compressed_loading_lzma(self):
        management.call_command(
            "loaddata", "--bulk_create", "fixture5.json.lzma", verbosity=0
        )
        self.assertEqual(
            Article.objects.get().headline,
            "WoW subscribers now outnumber readers",
        )

    @unittest.skipUnless(HAS_LZMA, "No lzma library detected.")
    def test_compressed_loading_xz(self):
        management.call_command(
            "loaddata", "--bulk_create", "fixture5.json.xz", verbosity=0
        )
        self.assertEqual(
            Article.objects.get().headline,
            "WoW subscribers now outnumber readers",
        )

    def test_ambiguous_compressed_fixture(self):
        # The name "fixture5" is ambiguous, so loading raises an error.
        msg = "Multiple fixtures named 'fixture5'"
        with self.assertRaisesMessage(management.CommandError, msg):
            management.call_command(
                "loaddata", "--bulk_create", "fixture5", verbosity=0
            )

    def test_db_loading(self):
        # Load db fixtures 1 and 2. These will load using the 'default'
        # database identifier implicitly.
        management.call_command(
            "loaddata", "--bulk_create", "db_fixture_1", verbosity=0
        )
        management.call_command(
            "loaddata", "--bulk_create", "db_fixture_2", verbosity=0
        )
        self.assertSequenceEqual(
            Article.objects.values_list("headline", flat=True),
            [
                "Who needs more than one database?",
                "Who needs to use compressed data?",
            ],
        )

    @skipUnlessDBFeature("prohibits_null_characters_in_text_exception")
    def test_loaddata_null_characters_on_postgresql(self):
        error, msg = connection.features.prohibits_null_characters_in_text_exception
        # msg = f"Could not load fixtures.Article(pk=2): {msg}"
        with self.assertRaisesMessage(error, msg):
            management.call_command(
                "loaddata", "--bulk_create", "null_character_in_field_value.json"
            )

    def test_loaddata_app_option(self):
        with self.assertRaisesMessage(
            CommandError, "No fixture named 'db_fixture_1' found."
        ):
            management.call_command(
                "loaddata",
                "--bulk_create",
                "db_fixture_1",
                verbosity=0,
                app_label="someotherapp",
            )
        self.assertQuerySetEqual(Article.objects.all(), [])
        management.call_command(
            "loaddata",
            "--bulk_create",
            "db_fixture_1",
            verbosity=0,
            app_label="fixtures",
        )
        self.assertEqual(
            Article.objects.get().headline,
            "Who needs more than one database?",
        )

    def test_loading_using(self):
        # Load fixtures 1 and 2. These will load using the 'default' database
        # identifier explicitly.
        management.call_command(
            "loaddata",
            "--bulk_create",
            "db_fixture_1",
            verbosity=0,
            database="default",
        )
        management.call_command(
            "loaddata",
            "--bulk_create",
            "db_fixture_2",
            verbosity=0,
            database="default",
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
            management.call_command(
                "loaddata", "--bulk_create", "db_fixture_3", verbosity=0
            )
        with self.assertRaisesMessage(
            CommandError, "No fixture named 'db_fixture_3' found."
        ):
            management.call_command(
                "loaddata",
                "--bulk_create",
                "db_fixture_3",
                verbosity=0,
                database="default",
            )
        self.assertQuerySetEqual(Article.objects.all(), [])

    def test_exclude_option_errors(self):
        """Excluding a bogus app or model should raise an error."""
        msg = "No installed app with label 'foo_app'."
        with self.assertRaisesMessage(management.CommandError, msg):
            management.call_command(
                "loaddata",
                "--bulk_create",
                "fixture1",
                exclude=["foo_app"],
                verbosity=0,
            )

        msg = "Unknown model: fixtures.FooModel"
        with self.assertRaisesMessage(management.CommandError, msg):
            management.call_command(
                "loaddata",
                "--bulk_create",
                "fixture1",
                exclude=["fixtures.FooModel"],
                verbosity=0,
            )

    def test_stdin_without_format(self):
        """Reading from stdin raises an error if format isn't specified."""
        msg = "--format must be specified when reading from stdin."
        with self.assertRaisesMessage(management.CommandError, msg):
            management.call_command("loaddata", "--bulk_create", "-", verbosity=0)
