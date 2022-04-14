# Unittests for fixtures.
import json
import os
import re
from io import StringIO
from pathlib import Path

from django.core import management, serializers
from django.core.exceptions import ImproperlyConfigured
from django.core.serializers.base import DeserializationError
from django.db import IntegrityError, transaction
from django.db.models import signals
from django.test import (
    TestCase,
    TransactionTestCase,
    override_settings,
    skipIfDBFeature,
    skipUnlessDBFeature,
)

from .models import (
    Absolute,
    Animal,
    Article,
    Book,
    Child,
    Circle1,
    Circle2,
    Circle3,
    ExternalDependency,
    M2MCircular1ThroughAB,
    M2MCircular1ThroughBC,
    M2MCircular1ThroughCA,
    M2MCircular2ThroughAB,
    M2MComplexA,
    M2MComplexB,
    M2MComplexCircular1A,
    M2MComplexCircular1B,
    M2MComplexCircular1C,
    M2MComplexCircular2A,
    M2MComplexCircular2B,
    M2MSimpleA,
    M2MSimpleB,
    M2MSimpleCircularA,
    M2MSimpleCircularB,
    M2MThroughAB,
    NaturalKeyWithFKDependency,
    NKChild,
    Parent,
    Person,
    RefToNKChild,
    Store,
    Stuff,
    Thingy,
    Widget,
)

_cur_dir = os.path.dirname(os.path.abspath(__file__))


class TestFixtures(TestCase):
    def animal_pre_save_check(self, signal, sender, instance, **kwargs):
        self.pre_save_checks.append(
            (
                "Count = %s (%s)" % (instance.count, type(instance.count)),
                "Weight = %s (%s)" % (instance.weight, type(instance.weight)),
            )
        )

    def test_duplicate_pk(self):
        """
        This is a regression test for ticket #3790.
        """
        # Load a fixture that uses PK=1
        management.call_command(
            "loaddata",
            "sequence",
            verbosity=0,
        )

        # Create a new animal. Without a sequence reset, this new object
        # will take a PK of 1 (on Postgres), and the save will fail.

        animal = Animal(
            name="Platypus",
            latin_name="Ornithorhynchus anatinus",
            count=2,
            weight=2.2,
        )
        animal.save()
        self.assertGreater(animal.id, 1)

    def test_loaddata_not_found_fields_not_ignore(self):
        """
        Test for ticket #9279 -- Error is raised for entries in
        the serialized data for fields that have been removed
        from the database when not ignored.
        """
        with self.assertRaises(DeserializationError):
            management.call_command(
                "loaddata",
                "sequence_extra",
                verbosity=0,
            )

    def test_loaddata_not_found_fields_ignore(self):
        """
        Test for ticket #9279 -- Ignores entries in
        the serialized data for fields that have been removed
        from the database.
        """
        management.call_command(
            "loaddata",
            "sequence_extra",
            ignore=True,
            verbosity=0,
        )
        self.assertEqual(Animal.specimens.all()[0].name, "Lion")

    def test_loaddata_not_found_fields_ignore_xml(self):
        """
        Test for ticket #19998 -- Ignore entries in the XML serialized data
        for fields that have been removed from the model definition.
        """
        management.call_command(
            "loaddata",
            "sequence_extra_xml",
            ignore=True,
            verbosity=0,
        )
        self.assertEqual(Animal.specimens.all()[0].name, "Wolf")

    @skipIfDBFeature("interprets_empty_strings_as_nulls")
    def test_pretty_print_xml(self):
        """
        Regression test for ticket #4558 -- pretty printing of XML fixtures
        doesn't affect parsing of None values.
        """
        # Load a pretty-printed XML fixture with Nulls.
        management.call_command(
            "loaddata",
            "pretty.xml",
            verbosity=0,
        )
        self.assertIsNone(Stuff.objects.all()[0].name)
        self.assertIsNone(Stuff.objects.all()[0].owner)

    @skipUnlessDBFeature("interprets_empty_strings_as_nulls")
    def test_pretty_print_xml_empty_strings(self):
        """
        Regression test for ticket #4558 -- pretty printing of XML fixtures
        doesn't affect parsing of None values.
        """
        # Load a pretty-printed XML fixture with Nulls.
        management.call_command(
            "loaddata",
            "pretty.xml",
            verbosity=0,
        )
        self.assertEqual(Stuff.objects.all()[0].name, "")
        self.assertIsNone(Stuff.objects.all()[0].owner)

    def test_absolute_path(self):
        """
        Regression test for ticket #6436 --
        os.path.join will throw away the initial parts of a path if it
        encounters an absolute path.
        This means that if a fixture is specified as an absolute path,
        we need to make sure we don't discover the absolute path in every
        fixture directory.
        """
        load_absolute_path = os.path.join(
            os.path.dirname(__file__), "fixtures", "absolute.json"
        )
        management.call_command(
            "loaddata",
            load_absolute_path,
            verbosity=0,
        )
        self.assertEqual(Absolute.objects.count(), 1)

    def test_relative_path(self, path=["fixtures", "absolute.json"]):
        relative_path = os.path.join(*path)
        cwd = os.getcwd()
        try:
            os.chdir(_cur_dir)
            management.call_command(
                "loaddata",
                relative_path,
                verbosity=0,
            )
        finally:
            os.chdir(cwd)
        self.assertEqual(Absolute.objects.count(), 1)

    @override_settings(FIXTURE_DIRS=[os.path.join(_cur_dir, "fixtures_1")])
    def test_relative_path_in_fixture_dirs(self):
        self.test_relative_path(path=["inner", "absolute.json"])

    def test_path_containing_dots(self):
        management.call_command(
            "loaddata",
            "path.containing.dots.json",
            verbosity=0,
        )
        self.assertEqual(Absolute.objects.count(), 1)

    def test_unknown_format(self):
        """
        Test for ticket #4371 -- Loading data of an unknown format should fail
        Validate that error conditions are caught correctly
        """
        msg = (
            "Problem installing fixture 'bad_fix.ture1': unkn is not a known "
            "serialization format."
        )
        with self.assertRaisesMessage(management.CommandError, msg):
            management.call_command(
                "loaddata",
                "bad_fix.ture1.unkn",
                verbosity=0,
            )

    @override_settings(SERIALIZATION_MODULES={"unkn": "unexistent.path"})
    def test_unimportable_serializer(self):
        """
        Failing serializer import raises the proper error
        """
        with self.assertRaisesMessage(ImportError, "No module named 'unexistent'"):
            management.call_command(
                "loaddata",
                "bad_fix.ture1.unkn",
                verbosity=0,
            )

    def test_invalid_data(self):
        """
        Test for ticket #4371 -- Loading a fixture file with invalid data
        using explicit filename.
        Test for ticket #18213 -- warning conditions are caught correctly
        """
        msg = "No fixture data found for 'bad_fixture2'. (File format may be invalid.)"
        with self.assertWarnsMessage(RuntimeWarning, msg):
            management.call_command(
                "loaddata",
                "bad_fixture2.xml",
                verbosity=0,
            )

    def test_invalid_data_no_ext(self):
        """
        Test for ticket #4371 -- Loading a fixture file with invalid data
        without file extension.
        Test for ticket #18213 -- warning conditions are caught correctly
        """
        msg = "No fixture data found for 'bad_fixture2'. (File format may be invalid.)"
        with self.assertWarnsMessage(RuntimeWarning, msg):
            management.call_command(
                "loaddata",
                "bad_fixture2",
                verbosity=0,
            )

    def test_empty(self):
        """
        Test for ticket #18213 -- Loading a fixture file with no data output a warning.
        Previously empty fixture raises an error exception, see ticket #4371.
        """
        msg = "No fixture data found for 'empty'. (File format may be invalid.)"
        with self.assertWarnsMessage(RuntimeWarning, msg):
            management.call_command(
                "loaddata",
                "empty",
                verbosity=0,
            )

    def test_error_message(self):
        """
        Regression for #9011 - error message is correct.
        Change from error to warning for ticket #18213.
        """
        msg = "No fixture data found for 'bad_fixture2'. (File format may be invalid.)"
        with self.assertWarnsMessage(RuntimeWarning, msg):
            management.call_command(
                "loaddata",
                "bad_fixture2",
                "animal",
                verbosity=0,
            )

    def test_pg_sequence_resetting_checks(self):
        """
        Test for ticket #7565 -- PostgreSQL sequence resetting checks shouldn't
        ascend to parent models when inheritance is used
        (since they are treated individually).
        """
        management.call_command(
            "loaddata",
            "model-inheritance.json",
            verbosity=0,
        )
        self.assertEqual(Parent.objects.all()[0].id, 1)
        self.assertEqual(Child.objects.all()[0].id, 1)

    def test_close_connection_after_loaddata(self):
        """
        Test for ticket #7572 -- MySQL has a problem if the same connection is
        used to create tables, load data, and then query over that data.
        To compensate, we close the connection after running loaddata.
        This ensures that a new connection is opened when test queries are
        issued.
        """
        management.call_command(
            "loaddata",
            "big-fixture.json",
            verbosity=0,
        )
        articles = Article.objects.exclude(id=9)
        self.assertEqual(
            list(articles.values_list("id", flat=True)), [1, 2, 3, 4, 5, 6, 7, 8]
        )
        # Just for good measure, run the same query again.
        # Under the influence of ticket #7572, this will
        # give a different result to the previous call.
        self.assertEqual(
            list(articles.values_list("id", flat=True)), [1, 2, 3, 4, 5, 6, 7, 8]
        )

    def test_field_value_coerce(self):
        """
        Test for tickets #8298, #9942 - Field values should be coerced into the
        correct type by the deserializer, not as part of the database write.
        """
        self.pre_save_checks = []
        signals.pre_save.connect(self.animal_pre_save_check)
        try:
            management.call_command(
                "loaddata",
                "animal.xml",
                verbosity=0,
            )
            self.assertEqual(
                self.pre_save_checks,
                [("Count = 42 (<class 'int'>)", "Weight = 1.2 (<class 'float'>)")],
            )
        finally:
            signals.pre_save.disconnect(self.animal_pre_save_check)

    def test_dumpdata_uses_default_manager(self):
        """
        Regression for #11286
        Dumpdata honors the default manager. Dump the current contents of
        the database as a JSON fixture
        """
        management.call_command(
            "loaddata",
            "animal.xml",
            verbosity=0,
        )
        management.call_command(
            "loaddata",
            "sequence.json",
            verbosity=0,
        )
        animal = Animal(
            name="Platypus",
            latin_name="Ornithorhynchus anatinus",
            count=2,
            weight=2.2,
        )
        animal.save()

        out = StringIO()
        management.call_command(
            "dumpdata",
            "fixtures_regress.animal",
            format="json",
            stdout=out,
        )

        # Output order isn't guaranteed, so check for parts
        data = out.getvalue()

        # Get rid of artifacts like '000000002' to eliminate the differences
        # between different Python versions.
        data = re.sub("0{6,}[0-9]", "", data)

        animals_data = sorted(
            [
                {
                    "pk": 1,
                    "model": "fixtures_regress.animal",
                    "fields": {
                        "count": 3,
                        "weight": 1.2,
                        "name": "Lion",
                        "latin_name": "Panthera leo",
                    },
                },
                {
                    "pk": 10,
                    "model": "fixtures_regress.animal",
                    "fields": {
                        "count": 42,
                        "weight": 1.2,
                        "name": "Emu",
                        "latin_name": "Dromaius novaehollandiae",
                    },
                },
                {
                    "pk": animal.pk,
                    "model": "fixtures_regress.animal",
                    "fields": {
                        "count": 2,
                        "weight": 2.2,
                        "name": "Platypus",
                        "latin_name": "Ornithorhynchus anatinus",
                    },
                },
            ],
            key=lambda x: x["pk"],
        )

        data = sorted(json.loads(data), key=lambda x: x["pk"])

        self.maxDiff = 1024
        self.assertEqual(data, animals_data)

    def test_proxy_model_included(self):
        """
        Regression for #11428 - Proxy models aren't included when you dumpdata
        """
        out = StringIO()
        # Create an instance of the concrete class
        widget = Widget.objects.create(name="grommet")
        management.call_command(
            "dumpdata",
            "fixtures_regress.widget",
            "fixtures_regress.widgetproxy",
            format="json",
            stdout=out,
        )
        self.assertJSONEqual(
            out.getvalue(),
            '[{"pk": %d, "model": "fixtures_regress.widget", '
            '"fields": {"name": "grommet"}}]' % widget.pk,
        )

    @skipUnlessDBFeature("supports_forward_references")
    def test_loaddata_works_when_fixture_has_forward_refs(self):
        """
        Forward references cause fixtures not to load in MySQL (InnoDB).
        """
        management.call_command(
            "loaddata",
            "forward_ref.json",
            verbosity=0,
        )
        self.assertEqual(Book.objects.all()[0].id, 1)
        self.assertEqual(Person.objects.all()[0].id, 4)

    def test_loaddata_raises_error_when_fixture_has_invalid_foreign_key(self):
        """
        Data with nonexistent child key references raises error.
        """
        with self.assertRaisesMessage(IntegrityError, "Problem installing fixture"):
            management.call_command(
                "loaddata",
                "forward_ref_bad_data.json",
                verbosity=0,
            )

    @skipUnlessDBFeature("supports_forward_references")
    @override_settings(
        FIXTURE_DIRS=[
            os.path.join(_cur_dir, "fixtures_1"),
            os.path.join(_cur_dir, "fixtures_2"),
        ]
    )
    def test_loaddata_forward_refs_split_fixtures(self):
        """
        Regression for #17530 - should be able to cope with forward references
        when the fixtures are not in the same files or directories.
        """
        management.call_command(
            "loaddata",
            "forward_ref_1.json",
            "forward_ref_2.json",
            verbosity=0,
        )
        self.assertEqual(Book.objects.all()[0].id, 1)
        self.assertEqual(Person.objects.all()[0].id, 4)

    def test_loaddata_no_fixture_specified(self):
        """
        Error is quickly reported when no fixtures is provided in the command
        line.
        """
        msg = (
            "No database fixture specified. Please provide the path of at least one "
            "fixture in the command line."
        )
        with self.assertRaisesMessage(management.CommandError, msg):
            management.call_command(
                "loaddata",
                verbosity=0,
            )

    def test_ticket_20820(self):
        """
        Regression for ticket #20820 -- loaddata on a model that inherits
        from a model with a M2M shouldn't blow up.
        """
        management.call_command(
            "loaddata",
            "special-article.json",
            verbosity=0,
        )

    def test_ticket_22421(self):
        """
        Regression for ticket #22421 -- loaddata on a model that inherits from
        a grand-parent model with a M2M but via an abstract parent shouldn't
        blow up.
        """
        management.call_command(
            "loaddata",
            "feature.json",
            verbosity=0,
        )

    def test_loaddata_with_m2m_to_self(self):
        """
        Regression test for ticket #17946.
        """
        management.call_command(
            "loaddata",
            "m2mtoself.json",
            verbosity=0,
        )

    @override_settings(
        FIXTURE_DIRS=[
            os.path.join(_cur_dir, "fixtures_1"),
            os.path.join(_cur_dir, "fixtures_1"),
        ]
    )
    def test_fixture_dirs_with_duplicates(self):
        """
        settings.FIXTURE_DIRS cannot contain duplicates in order to avoid
        repeated fixture loading.
        """
        with self.assertRaisesMessage(
            ImproperlyConfigured, "settings.FIXTURE_DIRS contains duplicates."
        ):
            management.call_command("loaddata", "absolute.json", verbosity=0)

    @override_settings(FIXTURE_DIRS=[os.path.join(_cur_dir, "fixtures")])
    def test_fixture_dirs_with_default_fixture_path(self):
        """
        settings.FIXTURE_DIRS cannot contain a default fixtures directory
        for application (app/fixtures) in order to avoid repeated fixture loading.
        """
        msg = (
            "'%s' is a default fixture directory for the '%s' app "
            "and cannot be listed in settings.FIXTURE_DIRS."
            % (os.path.join(_cur_dir, "fixtures"), "fixtures_regress")
        )
        with self.assertRaisesMessage(ImproperlyConfigured, msg):
            management.call_command("loaddata", "absolute.json", verbosity=0)

    @override_settings(
        FIXTURE_DIRS=[
            os.path.join(_cur_dir, "fixtures_1"),
            os.path.join(_cur_dir, "fixtures_2"),
        ]
    )
    def test_loaddata_with_valid_fixture_dirs(self):
        management.call_command(
            "loaddata",
            "absolute.json",
            verbosity=0,
        )

    @override_settings(FIXTURE_DIRS=[Path(_cur_dir) / "fixtures_1"])
    def test_fixtures_dir_pathlib(self):
        management.call_command("loaddata", "inner/absolute.json", verbosity=0)
        self.assertQuerysetEqual(Absolute.objects.all(), [1], transform=lambda o: o.pk)


class NaturalKeyFixtureTests(TestCase):
    def test_nk_deserialize(self):
        """
        Test for ticket #13030 - Python based parser version
        natural keys deserialize with fk to inheriting model
        """
        management.call_command(
            "loaddata",
            "model-inheritance.json",
            verbosity=0,
        )
        management.call_command(
            "loaddata",
            "nk-inheritance.json",
            verbosity=0,
        )
        self.assertEqual(NKChild.objects.get(pk=1).data, "apple")

        self.assertEqual(RefToNKChild.objects.get(pk=1).nk_fk.data, "apple")

    def test_nk_deserialize_xml(self):
        """
        Test for ticket #13030 - XML version
        natural keys deserialize with fk to inheriting model
        """
        management.call_command(
            "loaddata",
            "model-inheritance.json",
            verbosity=0,
        )
        management.call_command(
            "loaddata",
            "nk-inheritance.json",
            verbosity=0,
        )
        management.call_command(
            "loaddata",
            "nk-inheritance2.xml",
            verbosity=0,
        )
        self.assertEqual(NKChild.objects.get(pk=2).data, "banana")
        self.assertEqual(RefToNKChild.objects.get(pk=2).nk_fk.data, "apple")

    def test_nk_on_serialize(self):
        """
        Natural key requirements are taken into account when serializing models.
        """
        management.call_command(
            "loaddata",
            "forward_ref_lookup.json",
            verbosity=0,
        )

        out = StringIO()
        management.call_command(
            "dumpdata",
            "fixtures_regress.book",
            "fixtures_regress.person",
            "fixtures_regress.store",
            verbosity=0,
            format="json",
            use_natural_foreign_keys=True,
            use_natural_primary_keys=True,
            stdout=out,
        )
        self.assertJSONEqual(
            out.getvalue(),
            """
            [{"fields": {"main": null, "name": "Amazon"},
            "model": "fixtures_regress.store"},
            {"fields": {"main": null, "name": "Borders"},
            "model": "fixtures_regress.store"},
            {"fields": {"name": "Neal Stephenson"}, "model": "fixtures_regress.person"},
            {"pk": 1, "model": "fixtures_regress.book",
            "fields": {"stores": [["Amazon"], ["Borders"]],
            "name": "Cryptonomicon", "author": ["Neal Stephenson"]}}]
            """,
        )

    def test_dependency_sorting(self):
        """
        It doesn't matter what order you mention the models,  Store *must* be
        serialized before then Person, and both must be serialized before Book.
        """
        sorted_deps = serializers.sort_dependencies(
            [("fixtures_regress", [Book, Person, Store])]
        )
        self.assertEqual(sorted_deps, [Store, Person, Book])

    def test_dependency_sorting_2(self):
        sorted_deps = serializers.sort_dependencies(
            [("fixtures_regress", [Book, Store, Person])]
        )
        self.assertEqual(sorted_deps, [Store, Person, Book])

    def test_dependency_sorting_3(self):
        sorted_deps = serializers.sort_dependencies(
            [("fixtures_regress", [Store, Book, Person])]
        )
        self.assertEqual(sorted_deps, [Store, Person, Book])

    def test_dependency_sorting_4(self):
        sorted_deps = serializers.sort_dependencies(
            [("fixtures_regress", [Store, Person, Book])]
        )
        self.assertEqual(sorted_deps, [Store, Person, Book])

    def test_dependency_sorting_5(self):
        sorted_deps = serializers.sort_dependencies(
            [("fixtures_regress", [Person, Book, Store])]
        )
        self.assertEqual(sorted_deps, [Store, Person, Book])

    def test_dependency_sorting_6(self):
        sorted_deps = serializers.sort_dependencies(
            [("fixtures_regress", [Person, Store, Book])]
        )
        self.assertEqual(sorted_deps, [Store, Person, Book])

    def test_dependency_sorting_dangling(self):
        sorted_deps = serializers.sort_dependencies(
            [("fixtures_regress", [Person, Circle1, Store, Book])]
        )
        self.assertEqual(sorted_deps, [Circle1, Store, Person, Book])

    def test_dependency_sorting_tight_circular(self):
        with self.assertRaisesMessage(
            RuntimeError,
            "Can't resolve dependencies for fixtures_regress.Circle1, "
            "fixtures_regress.Circle2 in serialized app list.",
        ):
            serializers.sort_dependencies(
                [("fixtures_regress", [Person, Circle2, Circle1, Store, Book])]
            )

    def test_dependency_sorting_tight_circular_2(self):
        with self.assertRaisesMessage(
            RuntimeError,
            "Can't resolve dependencies for fixtures_regress.Circle1, "
            "fixtures_regress.Circle2 in serialized app list.",
        ):
            serializers.sort_dependencies(
                [("fixtures_regress", [Circle1, Book, Circle2])]
            )

    def test_dependency_self_referential(self):
        with self.assertRaisesMessage(
            RuntimeError,
            "Can't resolve dependencies for fixtures_regress.Circle3 in "
            "serialized app list.",
        ):
            serializers.sort_dependencies([("fixtures_regress", [Book, Circle3])])

    def test_dependency_sorting_long(self):
        with self.assertRaisesMessage(
            RuntimeError,
            "Can't resolve dependencies for fixtures_regress.Circle1, "
            "fixtures_regress.Circle2, fixtures_regress.Circle3 in serialized "
            "app list.",
        ):
            serializers.sort_dependencies(
                [("fixtures_regress", [Person, Circle2, Circle1, Circle3, Store, Book])]
            )

    def test_dependency_sorting_normal(self):
        sorted_deps = serializers.sort_dependencies(
            [("fixtures_regress", [Person, ExternalDependency, Book])]
        )
        self.assertEqual(sorted_deps, [Person, Book, ExternalDependency])

    def test_normal_pk(self):
        """
        Normal primary keys work on a model with natural key capabilities.
        """
        management.call_command(
            "loaddata",
            "non_natural_1.json",
            verbosity=0,
        )
        management.call_command(
            "loaddata",
            "forward_ref_lookup.json",
            verbosity=0,
        )
        management.call_command(
            "loaddata",
            "non_natural_2.xml",
            verbosity=0,
        )
        books = Book.objects.all()
        self.assertQuerysetEqual(
            books,
            [
                "<Book: Cryptonomicon by Neal Stephenson (available at Amazon, "
                "Borders)>",
                "<Book: Ender's Game by Orson Scott Card (available at Collins "
                "Bookstore)>",
                "<Book: Permutation City by Greg Egan (available at Angus and "
                "Robertson)>",
            ],
            transform=repr,
        )


class NaturalKeyFixtureOnOtherDatabaseTests(TestCase):
    databases = {"other"}

    def test_natural_key_dependencies(self):
        """
        Natural keys with foreing keys in dependencies works in a multiple
        database setup.
        """
        management.call_command(
            "loaddata",
            "nk_with_foreign_key.json",
            database="other",
            verbosity=0,
        )
        obj = NaturalKeyWithFKDependency.objects.using("other").get()
        self.assertEqual(obj.name, "The Lord of the Rings")
        self.assertEqual(obj.author.name, "J.R.R. Tolkien")


class M2MNaturalKeyFixtureTests(TestCase):
    """Tests for ticket #14426."""

    def test_dependency_sorting_m2m_simple(self):
        """
        M2M relations without explicit through models SHOULD count as dependencies

        Regression test for bugs that could be caused by flawed fixes to
        #14226, namely if M2M checks are removed from sort_dependencies
        altogether.
        """
        sorted_deps = serializers.sort_dependencies(
            [("fixtures_regress", [M2MSimpleA, M2MSimpleB])]
        )
        self.assertEqual(sorted_deps, [M2MSimpleB, M2MSimpleA])

    def test_dependency_sorting_m2m_simple_circular(self):
        """
        Resolving circular M2M relations without explicit through models should
        fail loudly
        """
        with self.assertRaisesMessage(
            RuntimeError,
            "Can't resolve dependencies for fixtures_regress.M2MSimpleCircularA, "
            "fixtures_regress.M2MSimpleCircularB in serialized app list.",
        ):
            serializers.sort_dependencies(
                [("fixtures_regress", [M2MSimpleCircularA, M2MSimpleCircularB])]
            )

    def test_dependency_sorting_m2m_complex(self):
        """
        M2M relations with explicit through models should NOT count as
        dependencies.  The through model itself will have dependencies, though.
        """
        sorted_deps = serializers.sort_dependencies(
            [("fixtures_regress", [M2MComplexA, M2MComplexB, M2MThroughAB])]
        )
        # Order between M2MComplexA and M2MComplexB doesn't matter. The through
        # model has dependencies to them though, so it should come last.
        self.assertEqual(sorted_deps[-1], M2MThroughAB)

    def test_dependency_sorting_m2m_complex_circular_1(self):
        """
        Circular M2M relations with explicit through models should be serializable
        """
        A, B, C, AtoB, BtoC, CtoA = (
            M2MComplexCircular1A,
            M2MComplexCircular1B,
            M2MComplexCircular1C,
            M2MCircular1ThroughAB,
            M2MCircular1ThroughBC,
            M2MCircular1ThroughCA,
        )
        sorted_deps = serializers.sort_dependencies(
            [("fixtures_regress", [A, B, C, AtoB, BtoC, CtoA])]
        )
        # The dependency sorting should not result in an error, and the
        # through model should have dependencies to the other models and as
        # such come last in the list.
        self.assertEqual(sorted_deps[:3], [A, B, C])
        self.assertEqual(sorted_deps[3:], [AtoB, BtoC, CtoA])

    def test_dependency_sorting_m2m_complex_circular_2(self):
        """
        Circular M2M relations with explicit through models should be serializable
        This test tests the circularity with explicit natural_key.dependencies
        """
        sorted_deps = serializers.sort_dependencies(
            [
                (
                    "fixtures_regress",
                    [M2MComplexCircular2A, M2MComplexCircular2B, M2MCircular2ThroughAB],
                )
            ]
        )
        self.assertEqual(sorted_deps[:2], [M2MComplexCircular2A, M2MComplexCircular2B])
        self.assertEqual(sorted_deps[2:], [M2MCircular2ThroughAB])

    def test_dump_and_load_m2m_simple(self):
        """
        Test serializing and deserializing back models with simple M2M relations
        """
        a = M2MSimpleA.objects.create(data="a")
        b1 = M2MSimpleB.objects.create(data="b1")
        b2 = M2MSimpleB.objects.create(data="b2")
        a.b_set.add(b1)
        a.b_set.add(b2)

        out = StringIO()
        management.call_command(
            "dumpdata",
            "fixtures_regress.M2MSimpleA",
            "fixtures_regress.M2MSimpleB",
            use_natural_foreign_keys=True,
            stdout=out,
        )

        for model in [M2MSimpleA, M2MSimpleB]:
            model.objects.all().delete()

        objects = serializers.deserialize("json", out.getvalue())
        for obj in objects:
            obj.save()

        new_a = M2MSimpleA.objects.get_by_natural_key("a")
        self.assertCountEqual(new_a.b_set.all(), [b1, b2])


class TestTicket11101(TransactionTestCase):

    available_apps = ["fixtures_regress"]

    @skipUnlessDBFeature("supports_transactions")
    def test_ticket_11101(self):
        """Fixtures can be rolled back (ticket #11101)."""
        with transaction.atomic():
            management.call_command(
                "loaddata",
                "thingy.json",
                verbosity=0,
            )
            self.assertEqual(Thingy.objects.count(), 1)
            transaction.set_rollback(True)
        self.assertEqual(Thingy.objects.count(), 0)


class TestLoadFixtureFromOtherAppDirectory(TestCase):
    """
    #23612 -- fixtures path should be normalized to allow referencing relative
    paths on Windows.
    """

    current_dir = os.path.abspath(os.path.dirname(__file__))
    # relative_prefix is something like tests/fixtures_regress or
    # fixtures_regress depending on how runtests.py is invoked.
    # All path separators must be / in order to be a proper regression test on
    # Windows, so replace as appropriate.
    relative_prefix = os.path.relpath(current_dir, os.getcwd()).replace("\\", "/")
    fixtures = [relative_prefix + "/fixtures/absolute.json"]

    def test_fixtures_loaded(self):
        count = Absolute.objects.count()
        self.assertGreater(count, 0, "Fixtures not loaded properly.")
