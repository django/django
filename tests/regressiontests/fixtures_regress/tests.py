# -*- coding: utf-8 -*-
# Unittests for fixtures.
import os
import sys
try:
    from cStringIO import StringIO
except ImportError:
    from StringIO import StringIO

from django.core import management
from django.core.management.commands.dumpdata import sort_dependencies
from django.core.management.base import CommandError
from django.db.models import signals
from django.test import TestCase

from models import Animal, Stuff
from models import Absolute, Parent, Child
from models import Article, Widget
from models import Store, Person, Book
from models import NKChild, RefToNKChild
from models import Circle1, Circle2, Circle3
from models import ExternalDependency


pre_save_checks = []
def animal_pre_save_check(signal, sender, instance, **kwargs):
    "A signal that is used to check the type of data loaded from fixtures"
    pre_save_checks.append(
        (
            'Count = %s (%s)' % (instance.count, type(instance.count)),
            'Weight = %s (%s)' % (instance.weight, type(instance.weight)),
        )
    )


class TestFixtures(TestCase):
    def test_duplicate_pk(self):
        """
        This is a regression test for ticket #3790.
        """
        # Load a fixture that uses PK=1
        management.call_command(
            'loaddata',
            'sequence',
            verbosity=0,
            commit=False
        )

        # Create a new animal. Without a sequence reset, this new object
        # will take a PK of 1 (on Postgres), and the save will fail.

        animal = Animal(
            name='Platypus',
            latin_name='Ornithorhynchus anatinus',
            count=2,
            weight=2.2
        )
        animal.save()
        self.assertEqual(animal.id, 2)

    def test_pretty_print_xml(self):
        """
        Regression test for ticket #4558 -- pretty printing of XML fixtures
        doesn't affect parsing of None values.
        """
        # Load a pretty-printed XML fixture with Nulls.
        management.call_command(
            'loaddata',
            'pretty.xml',
            verbosity=0,
            commit=False
        )
        self.assertEqual(Stuff.objects.all()[0].name, None)
        self.assertEqual(Stuff.objects.all()[0].owner, None)

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
            os.path.dirname(__file__),
            'fixtures',
            'absolute.json'
        )
        management.call_command(
            'loaddata',
            load_absolute_path,
            verbosity=0,
            commit=False
        )
        self.assertEqual(Absolute.load_count, 1)


    def test_unknown_format(self):
        """
        Test for ticket #4371 -- Loading data of an unknown format should fail
        Validate that error conditions are caught correctly
        """
        stderr = StringIO()
        management.call_command(
            'loaddata',
            'bad_fixture1.unkn',
            verbosity=0,
            commit=False,
            stderr=stderr,
        )
        self.assertEqual(
            stderr.getvalue(),
            "Problem installing fixture 'bad_fixture1': unkn is not a known serialization format.\n"
        )

    def test_invalid_data(self):
        """
        Test for ticket #4371 -- Loading a fixture file with invalid data
        using explicit filename.
        Validate that error conditions are caught correctly
        """
        stderr = StringIO()
        management.call_command(
            'loaddata',
            'bad_fixture2.xml',
            verbosity=0,
            commit=False,
            stderr=stderr,
        )
        self.assertEqual(
            stderr.getvalue(),
            "No fixture data found for 'bad_fixture2'. (File format may be invalid.)\n"
        )

    def test_invalid_data_no_ext(self):
        """
        Test for ticket #4371 -- Loading a fixture file with invalid data
        without file extension.
        Validate that error conditions are caught correctly
        """
        stderr = StringIO()
        management.call_command(
            'loaddata',
            'bad_fixture2',
            verbosity=0,
            commit=False,
            stderr=stderr,
        )
        self.assertEqual(
            stderr.getvalue(),
            "No fixture data found for 'bad_fixture2'. (File format may be invalid.)\n"
        )

    def test_empty(self):
        """
        Test for ticket #4371 -- Loading a fixture file with no data returns an error.
        Validate that error conditions are caught correctly
        """
        stderr = StringIO()
        management.call_command(
            'loaddata',
            'empty',
            verbosity=0,
            commit=False,
            stderr=stderr,
        )
        self.assertEqual(
            stderr.getvalue(),
            "No fixture data found for 'empty'. (File format may be invalid.)\n"
        )

    def test_abort_loaddata_on_error(self):
        """
        Test for ticket #4371 -- If any of the fixtures contain an error,
        loading is aborted.
        Validate that error conditions are caught correctly
        """
        stderr = StringIO()
        management.call_command(
            'loaddata',
            'empty',
            verbosity=0,
            commit=False,
            stderr=stderr,
        )
        self.assertEqual(
            stderr.getvalue(),
            "No fixture data found for 'empty'. (File format may be invalid.)\n"
        )

    def test_error_message(self):
        """
        (Regression for #9011 - error message is correct)
        """
        stderr = StringIO()
        management.call_command(
            'loaddata',
            'bad_fixture2',
            'animal',
            verbosity=0,
            commit=False,
            stderr=stderr,
        )
        self.assertEqual(
            stderr.getvalue(),
            "No fixture data found for 'bad_fixture2'. (File format may be invalid.)\n"
        )

    def test_pg_sequence_resetting_checks(self):
        """
        Test for ticket #7565 -- PostgreSQL sequence resetting checks shouldn't
        ascend to parent models when inheritance is used
        (since they are treated individually).
        """
        management.call_command(
            'loaddata',
            'model-inheritance.json',
            verbosity=0,
            commit=False
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
            'loaddata',
            'big-fixture.json',
            verbosity=0,
            commit=False
        )
        articles = Article.objects.exclude(id=9)
        self.assertEqual(
            list(articles.values_list('id', flat=True)),
            [1, 2, 3, 4, 5, 6, 7, 8]
        )
        # Just for good measure, run the same query again.
        # Under the influence of ticket #7572, this will
        # give a different result to the previous call.
        self.assertEqual(
            list(articles.values_list('id', flat=True)),
            [1, 2, 3, 4, 5, 6, 7, 8]
        )

    def test_field_value_coerce(self):
        """
        Test for tickets #8298, #9942 - Field values should be coerced into the
        correct type by the deserializer, not as part of the database write.
        """
        global pre_save_checks
        pre_save_checks = []
        signals.pre_save.connect(animal_pre_save_check)
        management.call_command(
            'loaddata',
            'animal.xml',
            verbosity=0,
            commit=False,
        )
        self.assertEqual(
            pre_save_checks,
            [
                ("Count = 42 (<type 'int'>)", "Weight = 1.2 (<type 'float'>)")
            ]
        )
        signals.pre_save.disconnect(animal_pre_save_check)

    def test_dumpdata_uses_default_manager(self):
        """
        Regression for #11286
        Ensure that dumpdata honors the default manager
        Dump the current contents of the database as a JSON fixture
        """
        management.call_command(
            'loaddata',
            'animal.xml',
            verbosity=0,
            commit=False,
        )
        management.call_command(
            'loaddata',
            'sequence.json',
            verbosity=0,
            commit=False,
        )
        animal = Animal(
            name='Platypus',
            latin_name='Ornithorhynchus anatinus',
            count=2,
            weight=2.2
        )
        animal.save()

        stdout = StringIO()
        management.call_command(
            'dumpdata',
            'fixtures_regress.animal',
            format='json',
            stdout=stdout
        )

        # Output order isn't guaranteed, so check for parts
        data = stdout.getvalue()
        lion_json = '{"pk": 1, "model": "fixtures_regress.animal", "fields": {"count": 3, "weight": 1.2, "name": "Lion", "latin_name": "Panthera leo"}}'
        emu_json = '{"pk": 10, "model": "fixtures_regress.animal", "fields": {"count": 42, "weight": 1.2, "name": "Emu", "latin_name": "Dromaius novaehollandiae"}}'
        platypus_json = '{"pk": 11, "model": "fixtures_regress.animal", "fields": {"count": 2, "weight": 2.2000000000000002, "name": "Platypus", "latin_name": "Ornithorhynchus anatinus"}}'

        self.assertEqual(len(data), len('[%s]' % ', '.join([lion_json, emu_json, platypus_json])))
        self.assertTrue(lion_json in data)
        self.assertTrue(emu_json in data)
        self.assertTrue(platypus_json in data)

    def test_proxy_model_included(self):
        """
        Regression for #11428 - Proxy models aren't included when you dumpdata
        """
        stdout = StringIO()
        # Create an instance of the concrete class
        Widget(name='grommet').save()
        management.call_command(
            'dumpdata',
            'fixtures_regress.widget',
            'fixtures_regress.widgetproxy',
            format='json',
            stdout=stdout
        )
        self.assertEqual(
            stdout.getvalue(),
            """[{"pk": 1, "model": "fixtures_regress.widget", "fields": {"name": "grommet"}}]"""
            )


class NaturalKeyFixtureTests(TestCase):
    def assertRaisesMessage(self, exc, msg, func, *args, **kwargs):
        try:
            func(*args, **kwargs)
        except Exception, e:
            self.assertEqual(msg, str(e))
            self.assertTrue(isinstance(e, exc), "Expected %s, got %s" % (exc, type(e)))

    def test_nk_deserialize(self):
        """
        Test for ticket #13030 - Python based parser version
        natural keys deserialize with fk to inheriting model
        """
        management.call_command(
            'loaddata',
            'model-inheritance.json',
            verbosity=0,
            commit=False
        )
        management.call_command(
            'loaddata',
            'nk-inheritance.json',
            verbosity=0,
            commit=False
        )
        self.assertEqual(
            NKChild.objects.get(pk=1).data,
            'apple'
        )

        self.assertEqual(
            RefToNKChild.objects.get(pk=1).nk_fk.data,
            'apple'
        )

    def test_nk_deserialize_xml(self):
        """
        Test for ticket #13030 - XML version
        natural keys deserialize with fk to inheriting model
        """
        management.call_command(
            'loaddata',
            'model-inheritance.json',
            verbosity=0,
            commit=False
        )
        management.call_command(
            'loaddata',
            'nk-inheritance.json',
            verbosity=0,
            commit=False
        )
        management.call_command(
            'loaddata',
            'nk-inheritance2.xml',
            verbosity=0,
            commit=False
        )
        self.assertEqual(
            NKChild.objects.get(pk=2).data,
            'banana'
        )
        self.assertEqual(
            RefToNKChild.objects.get(pk=2).nk_fk.data,
            'apple'
        )

    def test_nk_on_serialize(self):
        """
        Check that natural key requirements are taken into account
        when serializing models
        """
        management.call_command(
            'loaddata',
            'forward_ref_lookup.json',
            verbosity=0,
            commit=False
            )

        stdout = StringIO()
        management.call_command(
            'dumpdata',
            'fixtures_regress.book',
            'fixtures_regress.person',
            'fixtures_regress.store',
            verbosity=0,
            format='json',
            use_natural_keys=True,
            stdout=stdout,
        )
        self.assertEqual(
            stdout.getvalue(),
            """[{"pk": 2, "model": "fixtures_regress.store", "fields": {"name": "Amazon"}}, {"pk": 3, "model": "fixtures_regress.store", "fields": {"name": "Borders"}}, {"pk": 4, "model": "fixtures_regress.person", "fields": {"name": "Neal Stephenson"}}, {"pk": 1, "model": "fixtures_regress.book", "fields": {"stores": [["Amazon"], ["Borders"]], "name": "Cryptonomicon", "author": ["Neal Stephenson"]}}]"""
        )

    def test_dependency_sorting(self):
        """
        Now lets check the dependency sorting explicitly
        It doesn't matter what order you mention the models
        Store *must* be serialized before then Person, and both
        must be serialized before Book.
        """
        sorted_deps = sort_dependencies(
            [('fixtures_regress', [Book, Person, Store])]
        )
        self.assertEqual(
            sorted_deps,
            [Store, Person, Book]
        )

    def test_dependency_sorting_2(self):
        sorted_deps = sort_dependencies(
            [('fixtures_regress', [Book, Store, Person])]
        )
        self.assertEqual(
            sorted_deps,
            [Store, Person, Book]
        )

    def test_dependency_sorting_3(self):
        sorted_deps = sort_dependencies(
            [('fixtures_regress', [Store, Book, Person])]
        )
        self.assertEqual(
            sorted_deps,
            [Store, Person, Book]
        )

    def test_dependency_sorting_4(self):
        sorted_deps = sort_dependencies(
            [('fixtures_regress', [Store, Person, Book])]
        )
        self.assertEqual(
            sorted_deps,
            [Store, Person, Book]
        )

    def test_dependency_sorting_5(self):
        sorted_deps = sort_dependencies(
            [('fixtures_regress', [Person, Book, Store])]
        )
        self.assertEqual(
            sorted_deps,
            [Store, Person, Book]
        )

    def test_dependency_sorting_6(self):
        sorted_deps = sort_dependencies(
            [('fixtures_regress', [Person, Store, Book])]
        )
        self.assertEqual(
            sorted_deps,
            [Store, Person, Book]
        )

    def test_dependency_sorting_dangling(self):
        sorted_deps = sort_dependencies(
            [('fixtures_regress', [Person, Circle1, Store, Book])]
        )
        self.assertEqual(
            sorted_deps,
            [Circle1, Store, Person, Book]
        )

    def test_dependency_sorting_tight_circular(self):
        self.assertRaisesMessage(
            CommandError,
            """Can't resolve dependencies for fixtures_regress.Circle1, fixtures_regress.Circle2 in serialized app list.""",
            sort_dependencies,
            [('fixtures_regress', [Person, Circle2, Circle1, Store, Book])],
        )

    def test_dependency_sorting_tight_circular_2(self):
        self.assertRaisesMessage(
            CommandError,
            """Can't resolve dependencies for fixtures_regress.Circle1, fixtures_regress.Circle2 in serialized app list.""",
            sort_dependencies,
            [('fixtures_regress', [Circle1, Book, Circle2])],
        )

    def test_dependency_self_referential(self):
        self.assertRaisesMessage(
            CommandError,
            """Can't resolve dependencies for fixtures_regress.Circle3 in serialized app list.""",
            sort_dependencies,
            [('fixtures_regress', [Book, Circle3])],
        )

    def test_dependency_sorting_long(self):
        self.assertRaisesMessage(
            CommandError,
            """Can't resolve dependencies for fixtures_regress.Circle1, fixtures_regress.Circle2, fixtures_regress.Circle3 in serialized app list.""",
            sort_dependencies,
            [('fixtures_regress', [Person, Circle2, Circle1, Circle3, Store, Book])],
        )

    def test_dependency_sorting_normal(self):
        sorted_deps = sort_dependencies(
            [('fixtures_regress', [Person, ExternalDependency, Book])]
        )
        self.assertEqual(
            sorted_deps,
            [Person, Book, ExternalDependency]
        )

    def test_normal_pk(self):
        """
        Check that normal primary keys still work
        on a model with natural key capabilities
        """
        management.call_command(
            'loaddata',
            'non_natural_1.json',
            verbosity=0,
            commit=False
        )
        management.call_command(
            'loaddata',
            'forward_ref_lookup.json',
            verbosity=0,
            commit=False
        )
        management.call_command(
            'loaddata',
            'non_natural_2.xml',
            verbosity=0,
            commit=False
        )
        books = Book.objects.all()
        self.assertEqual(
            books.__repr__(),
            """[<Book: Cryptonomicon by Neal Stephenson (available at Amazon, Borders)>, <Book: Ender's Game by Orson Scott Card (available at Collins Bookstore)>, <Book: Permutation City by Greg Egan (available at Angus and Robertson)>]"""
        )
