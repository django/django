import logging
import os
import unittest
import warnings
from io import StringIO
from unittest import mock

from django.conf import STATICFILES_STORAGE_ALIAS, settings
from django.contrib.staticfiles.finders import get_finder, get_finders
from django.contrib.staticfiles.storage import staticfiles_storage
from django.core.exceptions import ImproperlyConfigured
from django.core.files.storage import default_storage
from django.db import (
    IntegrityError,
    connection,
    connections,
    models,
    router,
    transaction,
)
from django.forms import (
    CharField,
    EmailField,
    Form,
    IntegerField,
    ValidationError,
    formset_factory,
)
from django.http import HttpResponse
from django.template.loader import render_to_string
from django.test import (
    SimpleTestCase,
    TestCase,
    TransactionTestCase,
    skipIfDBFeature,
    skipUnlessDBFeature,
)
from django.test.html import HTMLParseError, parse_html
from django.test.testcases import DatabaseOperationForbidden
from django.test.utils import (
    CaptureQueriesContext,
    TestContextDecorator,
    ignore_warnings,
    isolate_apps,
    override_settings,
    setup_test_environment,
)
from django.urls import NoReverseMatch, path, reverse, reverse_lazy
from django.utils.deprecation import RemovedInDjango50Warning, RemovedInDjango51Warning
from django.utils.log import DEFAULT_LOGGING
from django.utils.version import PY311

from .models import Car, Person, PossessedCar
from .views import empty_response


class SkippingTestCase(SimpleTestCase):
    def _assert_skipping(self, func, expected_exc, msg=None):
        try:
            if msg is not None:
                with self.assertRaisesMessage(expected_exc, msg):
                    func()
            else:
                with self.assertRaises(expected_exc):
                    func()
        except unittest.SkipTest:
            self.fail("%s should not result in a skipped test." % func.__name__)

    def test_skip_unless_db_feature(self):
        """
        Testing the django.test.skipUnlessDBFeature decorator.
        """

        # Total hack, but it works, just want an attribute that's always true.
        @skipUnlessDBFeature("__class__")
        def test_func():
            raise ValueError

        @skipUnlessDBFeature("notprovided")
        def test_func2():
            raise ValueError

        @skipUnlessDBFeature("__class__", "__class__")
        def test_func3():
            raise ValueError

        @skipUnlessDBFeature("__class__", "notprovided")
        def test_func4():
            raise ValueError

        self._assert_skipping(test_func, ValueError)
        self._assert_skipping(test_func2, unittest.SkipTest)
        self._assert_skipping(test_func3, ValueError)
        self._assert_skipping(test_func4, unittest.SkipTest)

        class SkipTestCase(SimpleTestCase):
            @skipUnlessDBFeature("missing")
            def test_foo(self):
                pass

        self._assert_skipping(
            SkipTestCase("test_foo").test_foo,
            ValueError,
            "skipUnlessDBFeature cannot be used on test_foo (test_utils.tests."
            "SkippingTestCase.test_skip_unless_db_feature.<locals>.SkipTestCase%s) "
            "as SkippingTestCase.test_skip_unless_db_feature.<locals>.SkipTestCase "
            "doesn't allow queries against the 'default' database."
            # Python 3.11 uses fully qualified test name in the output.
            % (".test_foo" if PY311 else ""),
        )

    def test_skip_if_db_feature(self):
        """
        Testing the django.test.skipIfDBFeature decorator.
        """

        @skipIfDBFeature("__class__")
        def test_func():
            raise ValueError

        @skipIfDBFeature("notprovided")
        def test_func2():
            raise ValueError

        @skipIfDBFeature("__class__", "__class__")
        def test_func3():
            raise ValueError

        @skipIfDBFeature("__class__", "notprovided")
        def test_func4():
            raise ValueError

        @skipIfDBFeature("notprovided", "notprovided")
        def test_func5():
            raise ValueError

        self._assert_skipping(test_func, unittest.SkipTest)
        self._assert_skipping(test_func2, ValueError)
        self._assert_skipping(test_func3, unittest.SkipTest)
        self._assert_skipping(test_func4, unittest.SkipTest)
        self._assert_skipping(test_func5, ValueError)

        class SkipTestCase(SimpleTestCase):
            @skipIfDBFeature("missing")
            def test_foo(self):
                pass

        self._assert_skipping(
            SkipTestCase("test_foo").test_foo,
            ValueError,
            "skipIfDBFeature cannot be used on test_foo (test_utils.tests."
            "SkippingTestCase.test_skip_if_db_feature.<locals>.SkipTestCase%s) "
            "as SkippingTestCase.test_skip_if_db_feature.<locals>.SkipTestCase "
            "doesn't allow queries against the 'default' database."
            # Python 3.11 uses fully qualified test name in the output.
            % (".test_foo" if PY311 else ""),
        )


class SkippingClassTestCase(TestCase):
    def test_skip_class_unless_db_feature(self):
        @skipUnlessDBFeature("__class__")
        class NotSkippedTests(TestCase):
            def test_dummy(self):
                return

        @skipUnlessDBFeature("missing")
        @skipIfDBFeature("__class__")
        class SkippedTests(TestCase):
            def test_will_be_skipped(self):
                self.fail("We should never arrive here.")

        @skipIfDBFeature("__dict__")
        class SkippedTestsSubclass(SkippedTests):
            pass

        test_suite = unittest.TestSuite()
        test_suite.addTest(NotSkippedTests("test_dummy"))
        try:
            test_suite.addTest(SkippedTests("test_will_be_skipped"))
            test_suite.addTest(SkippedTestsSubclass("test_will_be_skipped"))
        except unittest.SkipTest:
            self.fail("SkipTest should not be raised here.")
        result = unittest.TextTestRunner(stream=StringIO()).run(test_suite)
        self.assertEqual(result.testsRun, 3)
        self.assertEqual(len(result.skipped), 2)
        self.assertEqual(result.skipped[0][1], "Database has feature(s) __class__")
        self.assertEqual(result.skipped[1][1], "Database has feature(s) __class__")

    def test_missing_default_databases(self):
        @skipIfDBFeature("missing")
        class MissingDatabases(SimpleTestCase):
            def test_assertion_error(self):
                pass

        suite = unittest.TestSuite()
        try:
            suite.addTest(MissingDatabases("test_assertion_error"))
        except unittest.SkipTest:
            self.fail("SkipTest should not be raised at this stage")
        runner = unittest.TextTestRunner(stream=StringIO())
        msg = (
            "skipIfDBFeature cannot be used on <class 'test_utils.tests."
            "SkippingClassTestCase.test_missing_default_databases.<locals>."
            "MissingDatabases'> as it doesn't allow queries against the "
            "'default' database."
        )
        with self.assertRaisesMessage(ValueError, msg):
            runner.run(suite)


@override_settings(ROOT_URLCONF="test_utils.urls")
class AssertNumQueriesTests(TestCase):
    def test_assert_num_queries(self):
        def test_func():
            raise ValueError

        with self.assertRaises(ValueError):
            self.assertNumQueries(2, test_func)

    def test_assert_num_queries_with_client(self):
        person = Person.objects.create(name="test")

        self.assertNumQueries(
            1, self.client.get, "/test_utils/get_person/%s/" % person.pk
        )

        self.assertNumQueries(
            1, self.client.get, "/test_utils/get_person/%s/" % person.pk
        )

        def test_func():
            self.client.get("/test_utils/get_person/%s/" % person.pk)
            self.client.get("/test_utils/get_person/%s/" % person.pk)

        self.assertNumQueries(2, test_func)


class AssertNumQueriesUponConnectionTests(TransactionTestCase):
    available_apps = []

    def test_ignores_connection_configuration_queries(self):
        real_ensure_connection = connection.ensure_connection
        connection.close()

        def make_configuration_query():
            is_opening_connection = connection.connection is None
            real_ensure_connection()

            if is_opening_connection:
                # Avoid infinite recursion. Creating a cursor calls
                # ensure_connection() which is currently mocked by this method.
                with connection.cursor() as cursor:
                    cursor.execute("SELECT 1" + connection.features.bare_select_suffix)

        ensure_connection = (
            "django.db.backends.base.base.BaseDatabaseWrapper.ensure_connection"
        )
        with mock.patch(ensure_connection, side_effect=make_configuration_query):
            with self.assertNumQueries(1):
                list(Car.objects.all())


class AssertQuerySetEqualTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.p1 = Person.objects.create(name="p1")
        cls.p2 = Person.objects.create(name="p2")

    def test_rename_assertquerysetequal_deprecation_warning(self):
        msg = "assertQuerysetEqual() is deprecated in favor of assertQuerySetEqual()."
        with self.assertRaisesMessage(RemovedInDjango51Warning, msg):
            self.assertQuerysetEqual()

    @ignore_warnings(category=RemovedInDjango51Warning)
    def test_deprecated_assertquerysetequal(self):
        self.assertQuerysetEqual(Person.objects.filter(name="p3"), [])

    def test_empty(self):
        self.assertQuerySetEqual(Person.objects.filter(name="p3"), [])

    def test_ordered(self):
        self.assertQuerySetEqual(
            Person.objects.order_by("name"),
            [self.p1, self.p2],
        )

    def test_unordered(self):
        self.assertQuerySetEqual(
            Person.objects.order_by("name"), [self.p2, self.p1], ordered=False
        )

    def test_queryset(self):
        self.assertQuerySetEqual(
            Person.objects.order_by("name"),
            Person.objects.order_by("name"),
        )

    def test_flat_values_list(self):
        self.assertQuerySetEqual(
            Person.objects.order_by("name").values_list("name", flat=True),
            ["p1", "p2"],
        )

    def test_transform(self):
        self.assertQuerySetEqual(
            Person.objects.order_by("name"),
            [self.p1.pk, self.p2.pk],
            transform=lambda x: x.pk,
        )

    def test_repr_transform(self):
        self.assertQuerySetEqual(
            Person.objects.order_by("name"),
            [repr(self.p1), repr(self.p2)],
            transform=repr,
        )

    def test_undefined_order(self):
        # Using an unordered queryset with more than one ordered value
        # is an error.
        msg = (
            "Trying to compare non-ordered queryset against more than one "
            "ordered value."
        )
        with self.assertRaisesMessage(ValueError, msg):
            self.assertQuerySetEqual(
                Person.objects.all(),
                [self.p1, self.p2],
            )
        # No error for one value.
        self.assertQuerySetEqual(Person.objects.filter(name="p1"), [self.p1])

    def test_repeated_values(self):
        """
        assertQuerySetEqual checks the number of appearance of each item
        when used with option ordered=False.
        """
        batmobile = Car.objects.create(name="Batmobile")
        k2000 = Car.objects.create(name="K 2000")
        PossessedCar.objects.bulk_create(
            [
                PossessedCar(car=batmobile, belongs_to=self.p1),
                PossessedCar(car=batmobile, belongs_to=self.p1),
                PossessedCar(car=k2000, belongs_to=self.p1),
                PossessedCar(car=k2000, belongs_to=self.p1),
                PossessedCar(car=k2000, belongs_to=self.p1),
                PossessedCar(car=k2000, belongs_to=self.p1),
            ]
        )
        with self.assertRaises(AssertionError):
            self.assertQuerySetEqual(
                self.p1.cars.all(), [batmobile, k2000], ordered=False
            )
        self.assertQuerySetEqual(
            self.p1.cars.all(), [batmobile] * 2 + [k2000] * 4, ordered=False
        )

    def test_maxdiff(self):
        names = ["Joe Smith %s" % i for i in range(20)]
        Person.objects.bulk_create([Person(name=name) for name in names])
        names.append("Extra Person")

        with self.assertRaises(AssertionError) as ctx:
            self.assertQuerySetEqual(
                Person.objects.filter(name__startswith="Joe"),
                names,
                ordered=False,
                transform=lambda p: p.name,
            )
        self.assertIn("Set self.maxDiff to None to see it.", str(ctx.exception))

        original = self.maxDiff
        self.maxDiff = None
        try:
            with self.assertRaises(AssertionError) as ctx:
                self.assertQuerySetEqual(
                    Person.objects.filter(name__startswith="Joe"),
                    names,
                    ordered=False,
                    transform=lambda p: p.name,
                )
        finally:
            self.maxDiff = original
        exception_msg = str(ctx.exception)
        self.assertNotIn("Set self.maxDiff to None to see it.", exception_msg)
        for name in names:
            self.assertIn(name, exception_msg)


@override_settings(ROOT_URLCONF="test_utils.urls")
class CaptureQueriesContextManagerTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.person_pk = str(Person.objects.create(name="test").pk)

    def test_simple(self):
        with CaptureQueriesContext(connection) as captured_queries:
            Person.objects.get(pk=self.person_pk)
        self.assertEqual(len(captured_queries), 1)
        self.assertIn(self.person_pk, captured_queries[0]["sql"])

        with CaptureQueriesContext(connection) as captured_queries:
            pass
        self.assertEqual(0, len(captured_queries))

    def test_within(self):
        with CaptureQueriesContext(connection) as captured_queries:
            Person.objects.get(pk=self.person_pk)
            self.assertEqual(len(captured_queries), 1)
            self.assertIn(self.person_pk, captured_queries[0]["sql"])

    def test_nested(self):
        with CaptureQueriesContext(connection) as captured_queries:
            Person.objects.count()
            with CaptureQueriesContext(connection) as nested_captured_queries:
                Person.objects.count()
        self.assertEqual(1, len(nested_captured_queries))
        self.assertEqual(2, len(captured_queries))

    def test_failure(self):
        with self.assertRaises(TypeError):
            with CaptureQueriesContext(connection):
                raise TypeError

    def test_with_client(self):
        with CaptureQueriesContext(connection) as captured_queries:
            self.client.get("/test_utils/get_person/%s/" % self.person_pk)
        self.assertEqual(len(captured_queries), 1)
        self.assertIn(self.person_pk, captured_queries[0]["sql"])

        with CaptureQueriesContext(connection) as captured_queries:
            self.client.get("/test_utils/get_person/%s/" % self.person_pk)
        self.assertEqual(len(captured_queries), 1)
        self.assertIn(self.person_pk, captured_queries[0]["sql"])

        with CaptureQueriesContext(connection) as captured_queries:
            self.client.get("/test_utils/get_person/%s/" % self.person_pk)
            self.client.get("/test_utils/get_person/%s/" % self.person_pk)
        self.assertEqual(len(captured_queries), 2)
        self.assertIn(self.person_pk, captured_queries[0]["sql"])
        self.assertIn(self.person_pk, captured_queries[1]["sql"])


@override_settings(ROOT_URLCONF="test_utils.urls")
class AssertNumQueriesContextManagerTests(TestCase):
    def test_simple(self):
        with self.assertNumQueries(0):
            pass

        with self.assertNumQueries(1):
            Person.objects.count()

        with self.assertNumQueries(2):
            Person.objects.count()
            Person.objects.count()

    def test_failure(self):
        msg = "1 != 2 : 1 queries executed, 2 expected\nCaptured queries were:\n1."
        with self.assertRaisesMessage(AssertionError, msg):
            with self.assertNumQueries(2):
                Person.objects.count()

        with self.assertRaises(TypeError):
            with self.assertNumQueries(4000):
                raise TypeError

    def test_with_client(self):
        person = Person.objects.create(name="test")

        with self.assertNumQueries(1):
            self.client.get("/test_utils/get_person/%s/" % person.pk)

        with self.assertNumQueries(1):
            self.client.get("/test_utils/get_person/%s/" % person.pk)

        with self.assertNumQueries(2):
            self.client.get("/test_utils/get_person/%s/" % person.pk)
            self.client.get("/test_utils/get_person/%s/" % person.pk)


@override_settings(ROOT_URLCONF="test_utils.urls")
class AssertTemplateUsedContextManagerTests(SimpleTestCase):
    def test_usage(self):
        with self.assertTemplateUsed("template_used/base.html"):
            render_to_string("template_used/base.html")

        with self.assertTemplateUsed(template_name="template_used/base.html"):
            render_to_string("template_used/base.html")

        with self.assertTemplateUsed("template_used/base.html"):
            render_to_string("template_used/include.html")

        with self.assertTemplateUsed("template_used/base.html"):
            render_to_string("template_used/extends.html")

        with self.assertTemplateUsed("template_used/base.html"):
            render_to_string("template_used/base.html")
            render_to_string("template_used/base.html")

    def test_nested_usage(self):
        with self.assertTemplateUsed("template_used/base.html"):
            with self.assertTemplateUsed("template_used/include.html"):
                render_to_string("template_used/include.html")

        with self.assertTemplateUsed("template_used/extends.html"):
            with self.assertTemplateUsed("template_used/base.html"):
                render_to_string("template_used/extends.html")

        with self.assertTemplateUsed("template_used/base.html"):
            with self.assertTemplateUsed("template_used/alternative.html"):
                render_to_string("template_used/alternative.html")
            render_to_string("template_used/base.html")

        with self.assertTemplateUsed("template_used/base.html"):
            render_to_string("template_used/extends.html")
            with self.assertTemplateNotUsed("template_used/base.html"):
                render_to_string("template_used/alternative.html")
            render_to_string("template_used/base.html")

    def test_not_used(self):
        with self.assertTemplateNotUsed("template_used/base.html"):
            pass
        with self.assertTemplateNotUsed("template_used/alternative.html"):
            pass

    def test_error_message(self):
        msg = "No templates used to render the response"
        with self.assertRaisesMessage(AssertionError, msg):
            with self.assertTemplateUsed("template_used/base.html"):
                pass

        with self.assertRaisesMessage(AssertionError, msg):
            with self.assertTemplateUsed(template_name="template_used/base.html"):
                pass

        msg2 = (
            "Template 'template_used/base.html' was not a template used to render "
            "the response. Actual template(s) used: template_used/alternative.html"
        )
        with self.assertRaisesMessage(AssertionError, msg2):
            with self.assertTemplateUsed("template_used/base.html"):
                render_to_string("template_used/alternative.html")

        with self.assertRaisesMessage(
            AssertionError, "No templates used to render the response"
        ):
            response = self.client.get("/test_utils/no_template_used/")
            self.assertTemplateUsed(response, "template_used/base.html")

    def test_msg_prefix(self):
        msg_prefix = "Prefix"
        msg = f"{msg_prefix}: No templates used to render the response"
        with self.assertRaisesMessage(AssertionError, msg):
            with self.assertTemplateUsed(
                "template_used/base.html", msg_prefix=msg_prefix
            ):
                pass

        with self.assertRaisesMessage(AssertionError, msg):
            with self.assertTemplateUsed(
                template_name="template_used/base.html",
                msg_prefix=msg_prefix,
            ):
                pass

        msg = (
            f"{msg_prefix}: Template 'template_used/base.html' was not a "
            f"template used to render the response. Actual template(s) used: "
            f"template_used/alternative.html"
        )
        with self.assertRaisesMessage(AssertionError, msg):
            with self.assertTemplateUsed(
                "template_used/base.html", msg_prefix=msg_prefix
            ):
                render_to_string("template_used/alternative.html")

    def test_count(self):
        with self.assertTemplateUsed("template_used/base.html", count=2):
            render_to_string("template_used/base.html")
            render_to_string("template_used/base.html")

        msg = (
            "Template 'template_used/base.html' was expected to be rendered "
            "3 time(s) but was actually rendered 2 time(s)."
        )
        with self.assertRaisesMessage(AssertionError, msg):
            with self.assertTemplateUsed("template_used/base.html", count=3):
                render_to_string("template_used/base.html")
                render_to_string("template_used/base.html")

    def test_failure(self):
        msg = "response and/or template_name argument must be provided"
        with self.assertRaisesMessage(TypeError, msg):
            with self.assertTemplateUsed():
                pass

        msg = "No templates used to render the response"
        with self.assertRaisesMessage(AssertionError, msg):
            with self.assertTemplateUsed(""):
                pass

        with self.assertRaisesMessage(AssertionError, msg):
            with self.assertTemplateUsed(""):
                render_to_string("template_used/base.html")

        with self.assertRaisesMessage(AssertionError, msg):
            with self.assertTemplateUsed(template_name=""):
                pass

        msg = (
            "Template 'template_used/base.html' was not a template used to "
            "render the response. Actual template(s) used: "
            "template_used/alternative.html"
        )
        with self.assertRaisesMessage(AssertionError, msg):
            with self.assertTemplateUsed("template_used/base.html"):
                render_to_string("template_used/alternative.html")

    def test_assert_used_on_http_response(self):
        response = HttpResponse()
        msg = "%s() is only usable on responses fetched using the Django test Client."
        with self.assertRaisesMessage(ValueError, msg % "assertTemplateUsed"):
            self.assertTemplateUsed(response, "template.html")
        with self.assertRaisesMessage(ValueError, msg % "assertTemplateNotUsed"):
            self.assertTemplateNotUsed(response, "template.html")


class HTMLEqualTests(SimpleTestCase):
    def test_html_parser(self):
        element = parse_html("<div><p>Hello</p></div>")
        self.assertEqual(len(element.children), 1)
        self.assertEqual(element.children[0].name, "p")
        self.assertEqual(element.children[0].children[0], "Hello")

        parse_html("<p>")
        parse_html("<p attr>")
        dom = parse_html("<p>foo")
        self.assertEqual(len(dom.children), 1)
        self.assertEqual(dom.name, "p")
        self.assertEqual(dom[0], "foo")

    def test_parse_html_in_script(self):
        parse_html('<script>var a = "<p" + ">";</script>')
        parse_html(
            """
            <script>
            var js_sha_link='<p>***</p>';
            </script>
        """
        )

        # script content will be parsed to text
        dom = parse_html(
            """
            <script><p>foo</p> '</scr'+'ipt>' <span>bar</span></script>
        """
        )
        self.assertEqual(len(dom.children), 1)
        self.assertEqual(dom.children[0], "<p>foo</p> '</scr'+'ipt>' <span>bar</span>")

    def test_self_closing_tags(self):
        self_closing_tags = [
            "area",
            "base",
            "br",
            "col",
            "embed",
            "hr",
            "img",
            "input",
            "link",
            "meta",
            "param",
            "source",
            "track",
            "wbr",
            # Deprecated tags
            "frame",
            "spacer",
        ]
        for tag in self_closing_tags:
            with self.subTest(tag):
                dom = parse_html("<p>Hello <%s> world</p>" % tag)
                self.assertEqual(len(dom.children), 3)
                self.assertEqual(dom[0], "Hello")
                self.assertEqual(dom[1].name, tag)
                self.assertEqual(dom[2], "world")

                dom = parse_html("<p>Hello <%s /> world</p>" % tag)
                self.assertEqual(len(dom.children), 3)
                self.assertEqual(dom[0], "Hello")
                self.assertEqual(dom[1].name, tag)
                self.assertEqual(dom[2], "world")

    def test_simple_equal_html(self):
        self.assertHTMLEqual("", "")
        self.assertHTMLEqual("<p></p>", "<p></p>")
        self.assertHTMLEqual("<p></p>", " <p> </p> ")
        self.assertHTMLEqual("<div><p>Hello</p></div>", "<div><p>Hello</p></div>")
        self.assertHTMLEqual("<div><p>Hello</p></div>", "<div> <p>Hello</p> </div>")
        self.assertHTMLEqual("<div>\n<p>Hello</p></div>", "<div><p>Hello</p></div>\n")
        self.assertHTMLEqual(
            "<div><p>Hello\nWorld !</p></div>", "<div><p>Hello World\n!</p></div>"
        )
        self.assertHTMLEqual(
            "<div><p>Hello\nWorld !</p></div>", "<div><p>Hello World\n!</p></div>"
        )
        self.assertHTMLEqual("<p>Hello  World   !</p>", "<p>Hello World\n\n!</p>")
        self.assertHTMLEqual("<p> </p>", "<p></p>")
        self.assertHTMLEqual("<p/>", "<p></p>")
        self.assertHTMLEqual("<p />", "<p></p>")
        self.assertHTMLEqual("<input checked>", '<input checked="checked">')
        self.assertHTMLEqual("<p>Hello", "<p> Hello")
        self.assertHTMLEqual("<p>Hello</p>World", "<p>Hello</p> World")

    def test_ignore_comments(self):
        self.assertHTMLEqual(
            "<div>Hello<!-- this is a comment --> World!</div>",
            "<div>Hello World!</div>",
        )

    def test_unequal_html(self):
        self.assertHTMLNotEqual("<p>Hello</p>", "<p>Hello!</p>")
        self.assertHTMLNotEqual("<p>foo&#20;bar</p>", "<p>foo&nbsp;bar</p>")
        self.assertHTMLNotEqual("<p>foo bar</p>", "<p>foo &nbsp;bar</p>")
        self.assertHTMLNotEqual("<p>foo nbsp</p>", "<p>foo &nbsp;</p>")
        self.assertHTMLNotEqual("<p>foo #20</p>", "<p>foo &#20;</p>")
        self.assertHTMLNotEqual(
            "<p><span>Hello</span><span>World</span></p>",
            "<p><span>Hello</span>World</p>",
        )
        self.assertHTMLNotEqual(
            "<p><span>Hello</span>World</p>",
            "<p><span>Hello</span><span>World</span></p>",
        )

    def test_attributes(self):
        self.assertHTMLEqual(
            '<input type="text" id="id_name" />', '<input id="id_name" type="text" />'
        )
        self.assertHTMLEqual(
            """<input type='text' id="id_name" />""",
            '<input id="id_name" type="text" />',
        )
        self.assertHTMLNotEqual(
            '<input type="text" id="id_name" />',
            '<input type="password" id="id_name" />',
        )

    def test_class_attribute(self):
        pairs = [
            ('<p class="foo bar"></p>', '<p class="bar foo"></p>'),
            ('<p class=" foo bar "></p>', '<p class="bar foo"></p>'),
            ('<p class="   foo    bar    "></p>', '<p class="bar foo"></p>'),
            ('<p class="foo\tbar"></p>', '<p class="bar foo"></p>'),
            ('<p class="\tfoo\tbar\t"></p>', '<p class="bar foo"></p>'),
            ('<p class="\t\t\tfoo\t\t\tbar\t\t\t"></p>', '<p class="bar foo"></p>'),
            ('<p class="\t \nfoo \t\nbar\n\t "></p>', '<p class="bar foo"></p>'),
        ]
        for html1, html2 in pairs:
            with self.subTest(html1):
                self.assertHTMLEqual(html1, html2)

    def test_boolean_attribute(self):
        html1 = "<input checked>"
        html2 = '<input checked="">'
        html3 = '<input checked="checked">'
        self.assertHTMLEqual(html1, html2)
        self.assertHTMLEqual(html1, html3)
        self.assertHTMLEqual(html2, html3)
        self.assertHTMLNotEqual(html1, '<input checked="invalid">')
        self.assertEqual(str(parse_html(html1)), "<input checked>")
        self.assertEqual(str(parse_html(html2)), "<input checked>")
        self.assertEqual(str(parse_html(html3)), "<input checked>")

    def test_non_boolean_attibutes(self):
        html1 = "<input value>"
        html2 = '<input value="">'
        html3 = '<input value="value">'
        self.assertHTMLEqual(html1, html2)
        self.assertHTMLNotEqual(html1, html3)
        self.assertEqual(str(parse_html(html1)), '<input value="">')
        self.assertEqual(str(parse_html(html2)), '<input value="">')

    def test_normalize_refs(self):
        pairs = [
            ("&#39;", "&#x27;"),
            ("&#39;", "'"),
            ("&#x27;", "&#39;"),
            ("&#x27;", "'"),
            ("'", "&#39;"),
            ("'", "&#x27;"),
            ("&amp;", "&#38;"),
            ("&amp;", "&#x26;"),
            ("&amp;", "&"),
            ("&#38;", "&amp;"),
            ("&#38;", "&#x26;"),
            ("&#38;", "&"),
            ("&#x26;", "&amp;"),
            ("&#x26;", "&#38;"),
            ("&#x26;", "&"),
            ("&", "&amp;"),
            ("&", "&#38;"),
            ("&", "&#x26;"),
        ]
        for pair in pairs:
            with self.subTest(repr(pair)):
                self.assertHTMLEqual(*pair)

    def test_complex_examples(self):
        self.assertHTMLEqual(
            """<tr><th><label for="id_first_name">First name:</label></th>
<td><input type="text" name="first_name" value="John" id="id_first_name" /></td></tr>
<tr><th><label for="id_last_name">Last name:</label></th>
<td><input type="text" id="id_last_name" name="last_name" value="Lennon" /></td></tr>
<tr><th><label for="id_birthday">Birthday:</label></th>
<td><input type="text" value="1940-10-9" name="birthday" id="id_birthday" /></td></tr>""",  # NOQA
            """
        <tr><th>
            <label for="id_first_name">First name:</label></th><td>
            <input type="text" name="first_name" value="John" id="id_first_name" />
        </td></tr>
        <tr><th>
            <label for="id_last_name">Last name:</label></th><td>
            <input type="text" name="last_name" value="Lennon" id="id_last_name" />
        </td></tr>
        <tr><th>
            <label for="id_birthday">Birthday:</label></th><td>
            <input type="text" name="birthday" value="1940-10-9" id="id_birthday" />
        </td></tr>
        """,
        )

        self.assertHTMLEqual(
            """<!DOCTYPE html>
        <html>
        <head>
            <link rel="stylesheet">
            <title>Document</title>
            <meta attribute="value">
        </head>
        <body>
            <p>
            This is a valid paragraph
            <div> this is a div AFTER the p</div>
        </body>
        </html>""",
            """
        <html>
        <head>
            <link rel="stylesheet">
            <title>Document</title>
            <meta attribute="value">
        </head>
        <body>
            <p> This is a valid paragraph
            <!-- browsers would close the p tag here -->
            <div> this is a div AFTER the p</div>
            </p> <!-- this is invalid HTML parsing, but it should make no
            difference in most cases -->
        </body>
        </html>""",
        )

    def test_html_contain(self):
        # equal html contains each other
        dom1 = parse_html("<p>foo")
        dom2 = parse_html("<p>foo</p>")
        self.assertIn(dom1, dom2)
        self.assertIn(dom2, dom1)

        dom2 = parse_html("<div><p>foo</p></div>")
        self.assertIn(dom1, dom2)
        self.assertNotIn(dom2, dom1)

        self.assertNotIn("<p>foo</p>", dom2)
        self.assertIn("foo", dom2)

        # when a root element is used ...
        dom1 = parse_html("<p>foo</p><p>bar</p>")
        dom2 = parse_html("<p>foo</p><p>bar</p>")
        self.assertIn(dom1, dom2)
        dom1 = parse_html("<p>foo</p>")
        self.assertIn(dom1, dom2)
        dom1 = parse_html("<p>bar</p>")
        self.assertIn(dom1, dom2)
        dom1 = parse_html("<div><p>foo</p><p>bar</p></div>")
        self.assertIn(dom2, dom1)

    def test_count(self):
        # equal html contains each other one time
        dom1 = parse_html("<p>foo")
        dom2 = parse_html("<p>foo</p>")
        self.assertEqual(dom1.count(dom2), 1)
        self.assertEqual(dom2.count(dom1), 1)

        dom2 = parse_html("<p>foo</p><p>bar</p>")
        self.assertEqual(dom2.count(dom1), 1)

        dom2 = parse_html("<p>foo foo</p><p>foo</p>")
        self.assertEqual(dom2.count("foo"), 3)

        dom2 = parse_html('<p class="bar">foo</p>')
        self.assertEqual(dom2.count("bar"), 0)
        self.assertEqual(dom2.count("class"), 0)
        self.assertEqual(dom2.count("p"), 0)
        self.assertEqual(dom2.count("o"), 2)

        dom2 = parse_html("<p>foo</p><p>foo</p>")
        self.assertEqual(dom2.count(dom1), 2)

        dom2 = parse_html('<div><p>foo<input type=""></p><p>foo</p></div>')
        self.assertEqual(dom2.count(dom1), 1)

        dom2 = parse_html("<div><div><p>foo</p></div></div>")
        self.assertEqual(dom2.count(dom1), 1)

        dom2 = parse_html("<p>foo<p>foo</p></p>")
        self.assertEqual(dom2.count(dom1), 1)

        dom2 = parse_html("<p>foo<p>bar</p></p>")
        self.assertEqual(dom2.count(dom1), 0)

        # HTML with a root element contains the same HTML with no root element.
        dom1 = parse_html("<p>foo</p><p>bar</p>")
        dom2 = parse_html("<div><p>foo</p><p>bar</p></div>")
        self.assertEqual(dom2.count(dom1), 1)

        # Target of search is a sequence of child elements and appears more
        # than once.
        dom2 = parse_html("<div><p>foo</p><p>bar</p><p>foo</p><p>bar</p></div>")
        self.assertEqual(dom2.count(dom1), 2)

        # Searched HTML has additional children.
        dom1 = parse_html("<a/><b/>")
        dom2 = parse_html("<a/><b/><c/>")
        self.assertEqual(dom2.count(dom1), 1)

        # No match found in children.
        dom1 = parse_html("<b/><a/>")
        self.assertEqual(dom2.count(dom1), 0)

        # Target of search found among children and grandchildren.
        dom1 = parse_html("<b/><b/>")
        dom2 = parse_html("<a><b/><b/></a><b/><b/>")
        self.assertEqual(dom2.count(dom1), 2)

    def test_root_element_escaped_html(self):
        html = "&lt;br&gt;"
        parsed = parse_html(html)
        self.assertEqual(str(parsed), html)

    def test_parsing_errors(self):
        with self.assertRaises(AssertionError):
            self.assertHTMLEqual("<p>", "")
        with self.assertRaises(AssertionError):
            self.assertHTMLEqual("", "<p>")
        error_msg = (
            "First argument is not valid HTML:\n"
            "('Unexpected end tag `div` (Line 1, Column 6)', (1, 6))"
        )
        with self.assertRaisesMessage(AssertionError, error_msg):
            self.assertHTMLEqual("< div></ div>", "<div></div>")
        with self.assertRaises(HTMLParseError):
            parse_html("</p>")

    def test_escaped_html_errors(self):
        msg = "<p>\n<foo>\n</p> != <p>\n&lt;foo&gt;\n</p>\n"
        with self.assertRaisesMessage(AssertionError, msg):
            self.assertHTMLEqual("<p><foo></p>", "<p>&lt;foo&gt;</p>")
        with self.assertRaisesMessage(AssertionError, msg):
            self.assertHTMLEqual("<p><foo></p>", "<p>&#60;foo&#62;</p>")

    def test_contains_html(self):
        response = HttpResponse(
            """<body>
        This is a form: <form method="get">
            <input type="text" name="Hello" />
        </form></body>"""
        )

        self.assertNotContains(response, "<input name='Hello' type='text'>")
        self.assertContains(response, '<form method="get">')

        self.assertContains(response, "<input name='Hello' type='text'>", html=True)
        self.assertNotContains(response, '<form method="get">', html=True)

        invalid_response = HttpResponse("""<body <bad>>""")

        with self.assertRaises(AssertionError):
            self.assertContains(invalid_response, "<p></p>")

        with self.assertRaises(AssertionError):
            self.assertContains(response, '<p "whats" that>')

    def test_unicode_handling(self):
        response = HttpResponse(
            '<p class="help">Some help text for the title (with Unicode ŠĐĆŽćžšđ)</p>'
        )
        self.assertContains(
            response,
            '<p class="help">Some help text for the title (with Unicode ŠĐĆŽćžšđ)</p>',
            html=True,
        )


class JSONEqualTests(SimpleTestCase):
    def test_simple_equal(self):
        json1 = '{"attr1": "foo", "attr2":"baz"}'
        json2 = '{"attr1": "foo", "attr2":"baz"}'
        self.assertJSONEqual(json1, json2)

    def test_simple_equal_unordered(self):
        json1 = '{"attr1": "foo", "attr2":"baz"}'
        json2 = '{"attr2":"baz", "attr1": "foo"}'
        self.assertJSONEqual(json1, json2)

    def test_simple_equal_raise(self):
        json1 = '{"attr1": "foo", "attr2":"baz"}'
        json2 = '{"attr2":"baz"}'
        with self.assertRaises(AssertionError):
            self.assertJSONEqual(json1, json2)

    def test_equal_parsing_errors(self):
        invalid_json = '{"attr1": "foo, "attr2":"baz"}'
        valid_json = '{"attr1": "foo", "attr2":"baz"}'
        with self.assertRaises(AssertionError):
            self.assertJSONEqual(invalid_json, valid_json)
        with self.assertRaises(AssertionError):
            self.assertJSONEqual(valid_json, invalid_json)

    def test_simple_not_equal(self):
        json1 = '{"attr1": "foo", "attr2":"baz"}'
        json2 = '{"attr2":"baz"}'
        self.assertJSONNotEqual(json1, json2)

    def test_simple_not_equal_raise(self):
        json1 = '{"attr1": "foo", "attr2":"baz"}'
        json2 = '{"attr1": "foo", "attr2":"baz"}'
        with self.assertRaises(AssertionError):
            self.assertJSONNotEqual(json1, json2)

    def test_not_equal_parsing_errors(self):
        invalid_json = '{"attr1": "foo, "attr2":"baz"}'
        valid_json = '{"attr1": "foo", "attr2":"baz"}'
        with self.assertRaises(AssertionError):
            self.assertJSONNotEqual(invalid_json, valid_json)
        with self.assertRaises(AssertionError):
            self.assertJSONNotEqual(valid_json, invalid_json)


class XMLEqualTests(SimpleTestCase):
    def test_simple_equal(self):
        xml1 = "<elem attr1='a' attr2='b' />"
        xml2 = "<elem attr1='a' attr2='b' />"
        self.assertXMLEqual(xml1, xml2)

    def test_simple_equal_unordered(self):
        xml1 = "<elem attr1='a' attr2='b' />"
        xml2 = "<elem attr2='b' attr1='a' />"
        self.assertXMLEqual(xml1, xml2)

    def test_simple_equal_raise(self):
        xml1 = "<elem attr1='a' />"
        xml2 = "<elem attr2='b' attr1='a' />"
        with self.assertRaises(AssertionError):
            self.assertXMLEqual(xml1, xml2)

    def test_simple_equal_raises_message(self):
        xml1 = "<elem attr1='a' />"
        xml2 = "<elem attr2='b' attr1='a' />"

        msg = """{xml1} != {xml2}
- <elem attr1='a' />
+ <elem attr2='b' attr1='a' />
?      ++++++++++
""".format(
            xml1=repr(xml1), xml2=repr(xml2)
        )

        with self.assertRaisesMessage(AssertionError, msg):
            self.assertXMLEqual(xml1, xml2)

    def test_simple_not_equal(self):
        xml1 = "<elem attr1='a' attr2='c' />"
        xml2 = "<elem attr1='a' attr2='b' />"
        self.assertXMLNotEqual(xml1, xml2)

    def test_simple_not_equal_raise(self):
        xml1 = "<elem attr1='a' attr2='b' />"
        xml2 = "<elem attr2='b' attr1='a' />"
        with self.assertRaises(AssertionError):
            self.assertXMLNotEqual(xml1, xml2)

    def test_parsing_errors(self):
        xml_unvalid = "<elem attr1='a attr2='b' />"
        xml2 = "<elem attr2='b' attr1='a' />"
        with self.assertRaises(AssertionError):
            self.assertXMLNotEqual(xml_unvalid, xml2)

    def test_comment_root(self):
        xml1 = "<?xml version='1.0'?><!-- comment1 --><elem attr1='a' attr2='b' />"
        xml2 = "<?xml version='1.0'?><!-- comment2 --><elem attr2='b' attr1='a' />"
        self.assertXMLEqual(xml1, xml2)

    def test_simple_equal_with_leading_or_trailing_whitespace(self):
        xml1 = "<elem>foo</elem> \t\n"
        xml2 = " \t\n<elem>foo</elem>"
        self.assertXMLEqual(xml1, xml2)

    def test_simple_not_equal_with_whitespace_in_the_middle(self):
        xml1 = "<elem>foo</elem><elem>bar</elem>"
        xml2 = "<elem>foo</elem> <elem>bar</elem>"
        self.assertXMLNotEqual(xml1, xml2)

    def test_doctype_root(self):
        xml1 = '<?xml version="1.0"?><!DOCTYPE root SYSTEM "example1.dtd"><root />'
        xml2 = '<?xml version="1.0"?><!DOCTYPE root SYSTEM "example2.dtd"><root />'
        self.assertXMLEqual(xml1, xml2)

    def test_processing_instruction(self):
        xml1 = (
            '<?xml version="1.0"?>'
            '<?xml-model href="http://www.example1.com"?><root />'
        )
        xml2 = (
            '<?xml version="1.0"?>'
            '<?xml-model href="http://www.example2.com"?><root />'
        )
        self.assertXMLEqual(xml1, xml2)
        self.assertXMLEqual(
            '<?xml-stylesheet href="style1.xslt" type="text/xsl"?><root />',
            '<?xml-stylesheet href="style2.xslt" type="text/xsl"?><root />',
        )


class SkippingExtraTests(TestCase):
    fixtures = ["should_not_be_loaded.json"]

    # HACK: This depends on internals of our TestCase subclasses
    def __call__(self, result=None):
        # Detect fixture loading by counting SQL queries, should be zero
        with self.assertNumQueries(0):
            super().__call__(result)

    @unittest.skip("Fixture loading should not be performed for skipped tests.")
    def test_fixtures_are_skipped(self):
        pass


class AssertRaisesMsgTest(SimpleTestCase):
    def test_assert_raises_message(self):
        msg = "'Expected message' not found in 'Unexpected message'"
        # context manager form of assertRaisesMessage()
        with self.assertRaisesMessage(AssertionError, msg):
            with self.assertRaisesMessage(ValueError, "Expected message"):
                raise ValueError("Unexpected message")

        # callable form
        def func():
            raise ValueError("Unexpected message")

        with self.assertRaisesMessage(AssertionError, msg):
            self.assertRaisesMessage(ValueError, "Expected message", func)

    def test_special_re_chars(self):
        """assertRaisesMessage shouldn't interpret RE special chars."""

        def func1():
            raise ValueError("[.*x+]y?")

        with self.assertRaisesMessage(ValueError, "[.*x+]y?"):
            func1()


class AssertWarnsMessageTests(SimpleTestCase):
    def test_context_manager(self):
        with self.assertWarnsMessage(UserWarning, "Expected message"):
            warnings.warn("Expected message", UserWarning)

    def test_context_manager_failure(self):
        msg = "Expected message' not found in 'Unexpected message'"
        with self.assertRaisesMessage(AssertionError, msg):
            with self.assertWarnsMessage(UserWarning, "Expected message"):
                warnings.warn("Unexpected message", UserWarning)

    def test_callable(self):
        def func():
            warnings.warn("Expected message", UserWarning)

        self.assertWarnsMessage(UserWarning, "Expected message", func)

    def test_special_re_chars(self):
        def func1():
            warnings.warn("[.*x+]y?", UserWarning)

        with self.assertWarnsMessage(UserWarning, "[.*x+]y?"):
            func1()


# TODO: Remove when dropping support for PY39.
class AssertNoLogsTest(SimpleTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        logging.config.dictConfig(DEFAULT_LOGGING)
        cls.addClassCleanup(logging.config.dictConfig, settings.LOGGING)

    def setUp(self):
        self.logger = logging.getLogger("django")

    @override_settings(DEBUG=True)
    def test_fails_when_log_emitted(self):
        msg = "Unexpected logs found: ['INFO:django:FAIL!']"
        with self.assertRaisesMessage(AssertionError, msg):
            with self.assertNoLogs("django", "INFO"):
                self.logger.info("FAIL!")

    @override_settings(DEBUG=True)
    def test_text_level(self):
        with self.assertNoLogs("django", "INFO"):
            self.logger.debug("DEBUG logs are ignored.")

    @override_settings(DEBUG=True)
    def test_int_level(self):
        with self.assertNoLogs("django", logging.INFO):
            self.logger.debug("DEBUG logs are ignored.")

    @override_settings(DEBUG=True)
    def test_default_level(self):
        with self.assertNoLogs("django"):
            self.logger.debug("DEBUG logs are ignored.")

    @override_settings(DEBUG=True)
    def test_does_not_hide_other_failures(self):
        msg = "1 != 2"
        with self.assertRaisesMessage(AssertionError, msg):
            with self.assertNoLogs("django"):
                self.assertEqual(1, 2)


class AssertFieldOutputTests(SimpleTestCase):
    def test_assert_field_output(self):
        error_invalid = ["Enter a valid email address."]
        self.assertFieldOutput(
            EmailField, {"a@a.com": "a@a.com"}, {"aaa": error_invalid}
        )
        with self.assertRaises(AssertionError):
            self.assertFieldOutput(
                EmailField,
                {"a@a.com": "a@a.com"},
                {"aaa": error_invalid + ["Another error"]},
            )
        with self.assertRaises(AssertionError):
            self.assertFieldOutput(
                EmailField, {"a@a.com": "Wrong output"}, {"aaa": error_invalid}
            )
        with self.assertRaises(AssertionError):
            self.assertFieldOutput(
                EmailField,
                {"a@a.com": "a@a.com"},
                {"aaa": ["Come on, gimme some well formatted data, dude."]},
            )

    def test_custom_required_message(self):
        class MyCustomField(IntegerField):
            default_error_messages = {
                "required": "This is really required.",
            }

        self.assertFieldOutput(MyCustomField, {}, {}, empty_value=None)


@override_settings(ROOT_URLCONF="test_utils.urls")
class AssertURLEqualTests(SimpleTestCase):
    def test_equal(self):
        valid_tests = (
            ("http://example.com/?", "http://example.com/"),
            ("http://example.com/?x=1&", "http://example.com/?x=1"),
            ("http://example.com/?x=1&y=2", "http://example.com/?y=2&x=1"),
            ("http://example.com/?x=1&y=2", "http://example.com/?y=2&x=1"),
            (
                "http://example.com/?x=1&y=2&a=1&a=2",
                "http://example.com/?a=1&a=2&y=2&x=1",
            ),
            ("/path/to/?x=1&y=2&z=3", "/path/to/?z=3&y=2&x=1"),
            ("?x=1&y=2&z=3", "?z=3&y=2&x=1"),
            ("/test_utils/no_template_used/", reverse_lazy("no_template_used")),
        )
        for url1, url2 in valid_tests:
            with self.subTest(url=url1):
                self.assertURLEqual(url1, url2)

    def test_not_equal(self):
        invalid_tests = (
            # Protocol must be the same.
            ("http://example.com/", "https://example.com/"),
            ("http://example.com/?x=1&x=2", "https://example.com/?x=2&x=1"),
            ("http://example.com/?x=1&y=bar&x=2", "https://example.com/?y=bar&x=2&x=1"),
            # Parameters of the same name must be in the same order.
            ("/path/to?a=1&a=2", "/path/to/?a=2&a=1"),
        )
        for url1, url2 in invalid_tests:
            with self.subTest(url=url1), self.assertRaises(AssertionError):
                self.assertURLEqual(url1, url2)

    def test_message(self):
        msg = (
            "Expected 'http://example.com/?x=1&x=2' to equal "
            "'https://example.com/?x=2&x=1'"
        )
        with self.assertRaisesMessage(AssertionError, msg):
            self.assertURLEqual(
                "http://example.com/?x=1&x=2", "https://example.com/?x=2&x=1"
            )

    def test_msg_prefix(self):
        msg = (
            "Prefix: Expected 'http://example.com/?x=1&x=2' to equal "
            "'https://example.com/?x=2&x=1'"
        )
        with self.assertRaisesMessage(AssertionError, msg):
            self.assertURLEqual(
                "http://example.com/?x=1&x=2",
                "https://example.com/?x=2&x=1",
                msg_prefix="Prefix: ",
            )


class TestForm(Form):
    field = CharField()

    def clean_field(self):
        value = self.cleaned_data.get("field", "")
        if value == "invalid":
            raise ValidationError("invalid value")
        return value

    def clean(self):
        if self.cleaned_data.get("field") == "invalid_non_field":
            raise ValidationError("non-field error")
        return self.cleaned_data

    @classmethod
    def _get_cleaned_form(cls, field_value):
        form = cls({"field": field_value})
        form.full_clean()
        return form

    @classmethod
    def valid(cls):
        return cls._get_cleaned_form("valid")

    @classmethod
    def invalid(cls, nonfield=False):
        return cls._get_cleaned_form("invalid_non_field" if nonfield else "invalid")


class TestFormset(formset_factory(TestForm)):
    @classmethod
    def _get_cleaned_formset(cls, field_value):
        formset = cls(
            {
                "form-TOTAL_FORMS": "1",
                "form-INITIAL_FORMS": "0",
                "form-0-field": field_value,
            }
        )
        formset.full_clean()
        return formset

    @classmethod
    def valid(cls):
        return cls._get_cleaned_formset("valid")

    @classmethod
    def invalid(cls, nonfield=False, nonform=False):
        if nonform:
            formset = cls({}, error_messages={"missing_management_form": "error"})
            formset.full_clean()
            return formset
        return cls._get_cleaned_formset("invalid_non_field" if nonfield else "invalid")


class AssertFormErrorTests(SimpleTestCase):
    @ignore_warnings(category=RemovedInDjango50Warning)
    def test_non_client_response(self):
        msg = (
            "assertFormError() is only usable on responses fetched using the "
            "Django test Client."
        )
        response = HttpResponse()
        with self.assertRaisesMessage(ValueError, msg):
            self.assertFormError(response, "form", "field", "invalid value")

    @ignore_warnings(category=RemovedInDjango50Warning)
    def test_response_with_no_context(self):
        msg = "Response did not use any contexts to render the response"
        response = mock.Mock(context=[])
        with self.assertRaisesMessage(AssertionError, msg):
            self.assertFormError(response, "form", "field", "invalid value")
        msg_prefix = "Custom prefix"
        with self.assertRaisesMessage(AssertionError, f"{msg_prefix}: {msg}"):
            self.assertFormError(
                response,
                "form",
                "field",
                "invalid value",
                msg_prefix=msg_prefix,
            )

    @ignore_warnings(category=RemovedInDjango50Warning)
    def test_form_not_in_context(self):
        msg = "The form 'form' was not used to render the response"
        response = mock.Mock(context=[{}])
        with self.assertRaisesMessage(AssertionError, msg):
            self.assertFormError(response, "form", "field", "invalid value")
        msg_prefix = "Custom prefix"
        with self.assertRaisesMessage(AssertionError, f"{msg_prefix}: {msg}"):
            self.assertFormError(
                response, "form", "field", "invalid value", msg_prefix=msg_prefix
            )

    def test_single_error(self):
        self.assertFormError(TestForm.invalid(), "field", "invalid value")

    def test_error_list(self):
        self.assertFormError(TestForm.invalid(), "field", ["invalid value"])

    def test_empty_errors_valid_form(self):
        self.assertFormError(TestForm.valid(), "field", [])

    def test_empty_errors_valid_form_non_field_errors(self):
        self.assertFormError(TestForm.valid(), None, [])

    def test_field_not_in_form(self):
        msg = (
            "The form <TestForm bound=True, valid=False, fields=(field)> does not "
            "contain the field 'other_field'."
        )
        with self.assertRaisesMessage(AssertionError, msg):
            self.assertFormError(TestForm.invalid(), "other_field", "invalid value")
        msg_prefix = "Custom prefix"
        with self.assertRaisesMessage(AssertionError, f"{msg_prefix}: {msg}"):
            self.assertFormError(
                TestForm.invalid(),
                "other_field",
                "invalid value",
                msg_prefix=msg_prefix,
            )

    def test_field_with_no_errors(self):
        msg = (
            "The errors of field 'field' on form <TestForm bound=True, valid=True, "
            "fields=(field)> don't match."
        )
        with self.assertRaisesMessage(AssertionError, msg) as ctx:
            self.assertFormError(TestForm.valid(), "field", "invalid value")
        self.assertIn("[] != ['invalid value']", str(ctx.exception))
        msg_prefix = "Custom prefix"
        with self.assertRaisesMessage(AssertionError, f"{msg_prefix}: {msg}"):
            self.assertFormError(
                TestForm.valid(), "field", "invalid value", msg_prefix=msg_prefix
            )

    def test_field_with_different_error(self):
        msg = (
            "The errors of field 'field' on form <TestForm bound=True, valid=False, "
            "fields=(field)> don't match."
        )
        with self.assertRaisesMessage(AssertionError, msg) as ctx:
            self.assertFormError(TestForm.invalid(), "field", "other error")
        self.assertIn("['invalid value'] != ['other error']", str(ctx.exception))
        msg_prefix = "Custom prefix"
        with self.assertRaisesMessage(AssertionError, f"{msg_prefix}: {msg}"):
            self.assertFormError(
                TestForm.invalid(), "field", "other error", msg_prefix=msg_prefix
            )

    def test_unbound_form(self):
        msg = (
            "The form <TestForm bound=False, valid=Unknown, fields=(field)> is not "
            "bound, it will never have any errors."
        )
        with self.assertRaisesMessage(AssertionError, msg):
            self.assertFormError(TestForm(), "field", [])
        msg_prefix = "Custom prefix"
        with self.assertRaisesMessage(AssertionError, f"{msg_prefix}: {msg}"):
            self.assertFormError(TestForm(), "field", [], msg_prefix=msg_prefix)

    def test_empty_errors_invalid_form(self):
        msg = (
            "The errors of field 'field' on form <TestForm bound=True, valid=False, "
            "fields=(field)> don't match."
        )
        with self.assertRaisesMessage(AssertionError, msg) as ctx:
            self.assertFormError(TestForm.invalid(), "field", [])
        self.assertIn("['invalid value'] != []", str(ctx.exception))

    def test_non_field_errors(self):
        self.assertFormError(TestForm.invalid(nonfield=True), None, "non-field error")

    def test_different_non_field_errors(self):
        msg = (
            "The non-field errors of form <TestForm bound=True, valid=False, "
            "fields=(field)> don't match."
        )
        with self.assertRaisesMessage(AssertionError, msg) as ctx:
            self.assertFormError(
                TestForm.invalid(nonfield=True), None, "other non-field error"
            )
        self.assertIn(
            "['non-field error'] != ['other non-field error']", str(ctx.exception)
        )
        msg_prefix = "Custom prefix"
        with self.assertRaisesMessage(AssertionError, f"{msg_prefix}: {msg}"):
            self.assertFormError(
                TestForm.invalid(nonfield=True),
                None,
                "other non-field error",
                msg_prefix=msg_prefix,
            )


class AssertFormSetErrorTests(SimpleTestCase):
    @ignore_warnings(category=RemovedInDjango50Warning)
    def test_non_client_response(self):
        msg = (
            "assertFormSetError() is only usable on responses fetched using "
            "the Django test Client."
        )
        response = HttpResponse()
        with self.assertRaisesMessage(ValueError, msg):
            self.assertFormSetError(response, "formset", 0, "field", "invalid value")

    @ignore_warnings(category=RemovedInDjango50Warning)
    def test_response_with_no_context(self):
        msg = "Response did not use any contexts to render the response"
        response = mock.Mock(context=[])
        with self.assertRaisesMessage(AssertionError, msg):
            self.assertFormSetError(response, "formset", 0, "field", "invalid value")

    @ignore_warnings(category=RemovedInDjango50Warning)
    def test_formset_not_in_context(self):
        msg = "The formset 'formset' was not used to render the response"
        response = mock.Mock(context=[{}])
        with self.assertRaisesMessage(AssertionError, msg):
            self.assertFormSetError(response, "formset", 0, "field", "invalid value")
        msg_prefix = "Custom prefix"
        with self.assertRaisesMessage(AssertionError, f"{msg_prefix}: {msg}"):
            self.assertFormSetError(
                response, "formset", 0, "field", "invalid value", msg_prefix=msg_prefix
            )

    def test_rename_assertformseterror_deprecation_warning(self):
        msg = "assertFormsetError() is deprecated in favor of assertFormSetError()."
        with self.assertRaisesMessage(RemovedInDjango51Warning, msg):
            self.assertFormsetError()

    @ignore_warnings(category=RemovedInDjango51Warning)
    def test_deprecated_assertformseterror(self):
        self.assertFormsetError(TestFormset.invalid(), 0, "field", "invalid value")

    def test_single_error(self):
        self.assertFormSetError(TestFormset.invalid(), 0, "field", "invalid value")

    def test_error_list(self):
        self.assertFormSetError(TestFormset.invalid(), 0, "field", ["invalid value"])

    def test_empty_errors_valid_formset(self):
        self.assertFormSetError(TestFormset.valid(), 0, "field", [])

    def test_multiple_forms(self):
        formset = TestFormset(
            {
                "form-TOTAL_FORMS": "2",
                "form-INITIAL_FORMS": "0",
                "form-0-field": "valid",
                "form-1-field": "invalid",
            }
        )
        formset.full_clean()
        self.assertFormSetError(formset, 0, "field", [])
        self.assertFormSetError(formset, 1, "field", ["invalid value"])

    def test_field_not_in_form(self):
        msg = (
            "The form 0 of formset <TestFormset: bound=True valid=False total_forms=1> "
            "does not contain the field 'other_field'."
        )
        with self.assertRaisesMessage(AssertionError, msg):
            self.assertFormSetError(
                TestFormset.invalid(), 0, "other_field", "invalid value"
            )
        msg_prefix = "Custom prefix"
        with self.assertRaisesMessage(AssertionError, f"{msg_prefix}: {msg}"):
            self.assertFormSetError(
                TestFormset.invalid(),
                0,
                "other_field",
                "invalid value",
                msg_prefix=msg_prefix,
            )

    def test_field_with_no_errors(self):
        msg = (
            "The errors of field 'field' on form 0 of formset <TestFormset: bound=True "
            "valid=True total_forms=1> don't match."
        )
        with self.assertRaisesMessage(AssertionError, msg) as ctx:
            self.assertFormSetError(TestFormset.valid(), 0, "field", "invalid value")
        self.assertIn("[] != ['invalid value']", str(ctx.exception))
        msg_prefix = "Custom prefix"
        with self.assertRaisesMessage(AssertionError, f"{msg_prefix}: {msg}"):
            self.assertFormSetError(
                TestFormset.valid(), 0, "field", "invalid value", msg_prefix=msg_prefix
            )

    def test_field_with_different_error(self):
        msg = (
            "The errors of field 'field' on form 0 of formset <TestFormset: bound=True "
            "valid=False total_forms=1> don't match."
        )
        with self.assertRaisesMessage(AssertionError, msg) as ctx:
            self.assertFormSetError(TestFormset.invalid(), 0, "field", "other error")
        self.assertIn("['invalid value'] != ['other error']", str(ctx.exception))
        msg_prefix = "Custom prefix"
        with self.assertRaisesMessage(AssertionError, f"{msg_prefix}: {msg}"):
            self.assertFormSetError(
                TestFormset.invalid(), 0, "field", "other error", msg_prefix=msg_prefix
            )

    def test_unbound_formset(self):
        msg = (
            "The formset <TestFormset: bound=False valid=Unknown total_forms=1> is not "
            "bound, it will never have any errors."
        )
        with self.assertRaisesMessage(AssertionError, msg):
            self.assertFormSetError(TestFormset(), 0, "field", [])

    def test_empty_errors_invalid_formset(self):
        msg = (
            "The errors of field 'field' on form 0 of formset <TestFormset: bound=True "
            "valid=False total_forms=1> don't match."
        )
        with self.assertRaisesMessage(AssertionError, msg) as ctx:
            self.assertFormSetError(TestFormset.invalid(), 0, "field", [])
        self.assertIn("['invalid value'] != []", str(ctx.exception))

    def test_non_field_errors(self):
        self.assertFormSetError(
            TestFormset.invalid(nonfield=True), 0, None, "non-field error"
        )

    def test_different_non_field_errors(self):
        msg = (
            "The non-field errors of form 0 of formset <TestFormset: bound=True "
            "valid=False total_forms=1> don't match."
        )
        with self.assertRaisesMessage(AssertionError, msg) as ctx:
            self.assertFormSetError(
                TestFormset.invalid(nonfield=True), 0, None, "other non-field error"
            )
        self.assertIn(
            "['non-field error'] != ['other non-field error']", str(ctx.exception)
        )
        msg_prefix = "Custom prefix"
        with self.assertRaisesMessage(AssertionError, f"{msg_prefix}: {msg}"):
            self.assertFormSetError(
                TestFormset.invalid(nonfield=True),
                0,
                None,
                "other non-field error",
                msg_prefix=msg_prefix,
            )

    def test_no_non_field_errors(self):
        msg = (
            "The non-field errors of form 0 of formset <TestFormset: bound=True "
            "valid=False total_forms=1> don't match."
        )
        with self.assertRaisesMessage(AssertionError, msg) as ctx:
            self.assertFormSetError(TestFormset.invalid(), 0, None, "non-field error")
        self.assertIn("[] != ['non-field error']", str(ctx.exception))
        msg_prefix = "Custom prefix"
        with self.assertRaisesMessage(AssertionError, f"{msg_prefix}: {msg}"):
            self.assertFormSetError(
                TestFormset.invalid(), 0, None, "non-field error", msg_prefix=msg_prefix
            )

    def test_non_form_errors(self):
        self.assertFormSetError(TestFormset.invalid(nonform=True), None, None, "error")

    def test_different_non_form_errors(self):
        msg = (
            "The non-form errors of formset <TestFormset: bound=True valid=False "
            "total_forms=0> don't match."
        )
        with self.assertRaisesMessage(AssertionError, msg) as ctx:
            self.assertFormSetError(
                TestFormset.invalid(nonform=True), None, None, "other error"
            )
        self.assertIn("['error'] != ['other error']", str(ctx.exception))
        msg_prefix = "Custom prefix"
        with self.assertRaisesMessage(AssertionError, f"{msg_prefix}: {msg}"):
            self.assertFormSetError(
                TestFormset.invalid(nonform=True),
                None,
                None,
                "other error",
                msg_prefix=msg_prefix,
            )

    def test_no_non_form_errors(self):
        msg = (
            "The non-form errors of formset <TestFormset: bound=True valid=False "
            "total_forms=1> don't match."
        )
        with self.assertRaisesMessage(AssertionError, msg) as ctx:
            self.assertFormSetError(TestFormset.invalid(), None, None, "error")
        self.assertIn("[] != ['error']", str(ctx.exception))
        msg_prefix = "Custom prefix"
        with self.assertRaisesMessage(AssertionError, f"{msg_prefix}: {msg}"):
            self.assertFormSetError(
                TestFormset.invalid(),
                None,
                None,
                "error",
                msg_prefix=msg_prefix,
            )

    def test_non_form_errors_with_field(self):
        msg = "You must use field=None with form_index=None."
        with self.assertRaisesMessage(ValueError, msg):
            self.assertFormSetError(
                TestFormset.invalid(nonform=True), None, "field", "error"
            )

    def test_form_index_too_big(self):
        msg = (
            "The formset <TestFormset: bound=True valid=False total_forms=1> only has "
            "1 form."
        )
        with self.assertRaisesMessage(AssertionError, msg):
            self.assertFormSetError(TestFormset.invalid(), 2, "field", "error")

    def test_form_index_too_big_plural(self):
        formset = TestFormset(
            {
                "form-TOTAL_FORMS": "2",
                "form-INITIAL_FORMS": "0",
                "form-0-field": "valid",
                "form-1-field": "valid",
            }
        )
        formset.full_clean()
        msg = (
            "The formset <TestFormset: bound=True valid=True total_forms=2> only has 2 "
            "forms."
        )
        with self.assertRaisesMessage(AssertionError, msg):
            self.assertFormSetError(formset, 2, "field", "error")


# RemovedInDjango50Warning
class AssertFormErrorDeprecationTests(SimpleTestCase):
    """
    Exhaustively test all possible combinations of args/kwargs for the old
    signature.
    """

    @ignore_warnings(category=RemovedInDjango50Warning)
    def test_assert_form_error_errors_none(self):
        msg = (
            "The errors of field 'field' on form <TestForm bound=True, valid=False, "
            "fields=(field)> don't match."
        )
        with self.assertRaisesMessage(AssertionError, msg):
            self.assertFormError(TestForm.invalid(), "field", None)

    def test_assert_form_error_errors_none_warning(self):
        msg = (
            "Passing errors=None to assertFormError() is deprecated, use "
            "errors=[] instead."
        )
        with self.assertWarnsMessage(RemovedInDjango50Warning, msg):
            self.assertFormError(TestForm.valid(), "field", None)

    def _assert_form_error_old_api_cases(self, form, field, errors, msg_prefix):
        response = mock.Mock(context=[{"form": TestForm.invalid()}])
        return (
            ((response, form, field, errors), {}),
            ((response, form, field, errors, msg_prefix), {}),
            ((response, form, field, errors), {"msg_prefix": msg_prefix}),
            ((response, form, field), {"errors": errors}),
            ((response, form, field), {"errors": errors, "msg_prefix": msg_prefix}),
            ((response, form), {"field": field, "errors": errors}),
            (
                (response, form),
                {"field": field, "errors": errors, "msg_prefix": msg_prefix},
            ),
            ((response,), {"form": form, "field": field, "errors": errors}),
            (
                (response,),
                {
                    "form": form,
                    "field": field,
                    "errors": errors,
                    "msg_prefix": msg_prefix,
                },
            ),
            (
                (),
                {"response": response, "form": form, "field": field, "errors": errors},
            ),
            (
                (),
                {
                    "response": response,
                    "form": form,
                    "field": field,
                    "errors": errors,
                    "msg_prefix": msg_prefix,
                },
            ),
        )

    def test_assert_form_error_old_api(self):
        deprecation_msg = (
            "Passing response to assertFormError() is deprecated. Use the form object "
            "directly: assertFormError(response.context['form'], 'field', ...)"
        )
        for args, kwargs in self._assert_form_error_old_api_cases(
            form="form",
            field="field",
            errors=["invalid value"],
            msg_prefix="Custom prefix",
        ):
            with self.subTest(args=args, kwargs=kwargs):
                with self.assertWarnsMessage(RemovedInDjango50Warning, deprecation_msg):
                    self.assertFormError(*args, **kwargs)

    @ignore_warnings(category=RemovedInDjango50Warning)
    def test_assert_form_error_old_api_assertion_error(self):
        for args, kwargs in self._assert_form_error_old_api_cases(
            form="form",
            field="field",
            errors=["other error"],
            msg_prefix="Custom prefix",
        ):
            with self.subTest(args=args, kwargs=kwargs):
                with self.assertRaises(AssertionError):
                    self.assertFormError(*args, **kwargs)

    @ignore_warnings(category=RemovedInDjango50Warning)
    def test_assert_formset_error_errors_none(self):
        msg = (
            "The errors of field 'field' on form 0 of formset <TestFormset: bound=True "
            "valid=False total_forms=1> don't match."
        )
        with self.assertRaisesMessage(AssertionError, msg):
            self.assertFormSetError(TestFormset.invalid(), 0, "field", None)

    def test_assert_formset_error_errors_none_warning(self):
        msg = (
            "Passing errors=None to assertFormSetError() is deprecated, use "
            "errors=[] instead."
        )
        with self.assertWarnsMessage(RemovedInDjango50Warning, msg):
            self.assertFormSetError(TestFormset.valid(), 0, "field", None)

    def _assert_formset_error_old_api_cases(
        self, formset, form_index, field, errors, msg_prefix
    ):
        response = mock.Mock(context=[{"formset": TestFormset.invalid()}])
        return (
            ((response, formset, form_index, field, errors), {}),
            ((response, formset, form_index, field, errors, msg_prefix), {}),
            (
                (response, formset, form_index, field, errors),
                {"msg_prefix": msg_prefix},
            ),
            ((response, formset, form_index, field), {"errors": errors}),
            (
                (response, formset, form_index, field),
                {"errors": errors, "msg_prefix": msg_prefix},
            ),
            ((response, formset, form_index), {"field": field, "errors": errors}),
            (
                (response, formset, form_index),
                {"field": field, "errors": errors, "msg_prefix": msg_prefix},
            ),
            (
                (response, formset),
                {"form_index": form_index, "field": field, "errors": errors},
            ),
            (
                (response, formset),
                {
                    "form_index": form_index,
                    "field": field,
                    "errors": errors,
                    "msg_prefix": msg_prefix,
                },
            ),
            (
                (response,),
                {
                    "formset": formset,
                    "form_index": form_index,
                    "field": field,
                    "errors": errors,
                },
            ),
            (
                (response,),
                {
                    "formset": formset,
                    "form_index": form_index,
                    "field": field,
                    "errors": errors,
                    "msg_prefix": msg_prefix,
                },
            ),
            (
                (),
                {
                    "response": response,
                    "formset": formset,
                    "form_index": form_index,
                    "field": field,
                    "errors": errors,
                },
            ),
            (
                (),
                {
                    "response": response,
                    "formset": formset,
                    "form_index": form_index,
                    "field": field,
                    "errors": errors,
                    "msg_prefix": msg_prefix,
                },
            ),
        )

    def test_assert_formset_error_old_api(self):
        deprecation_msg = (
            "Passing response to assertFormSetError() is deprecated. Use the formset "
            "object directly: assertFormSetError(response.context['formset'], 0, ...)"
        )
        for args, kwargs in self._assert_formset_error_old_api_cases(
            formset="formset",
            form_index=0,
            field="field",
            errors=["invalid value"],
            msg_prefix="Custom prefix",
        ):
            with self.subTest(args=args, kwargs=kwargs):
                with self.assertWarnsMessage(RemovedInDjango50Warning, deprecation_msg):
                    self.assertFormSetError(*args, **kwargs)

    @ignore_warnings(category=RemovedInDjango50Warning)
    def test_assert_formset_error_old_api_assertion_error(self):
        for args, kwargs in self._assert_formset_error_old_api_cases(
            formset="formset",
            form_index=0,
            field="field",
            errors=["other error"],
            msg_prefix="Custom prefix",
        ):
            with self.subTest(args=args, kwargs=kwargs):
                with self.assertRaises(AssertionError):
                    self.assertFormSetError(*args, **kwargs)


class FirstUrls:
    urlpatterns = [path("first/", empty_response, name="first")]


class SecondUrls:
    urlpatterns = [path("second/", empty_response, name="second")]


class SetupTestEnvironmentTests(SimpleTestCase):
    def test_setup_test_environment_calling_more_than_once(self):
        with self.assertRaisesMessage(
            RuntimeError, "setup_test_environment() was already called"
        ):
            setup_test_environment()

    def test_allowed_hosts(self):
        for type_ in (list, tuple):
            with self.subTest(type_=type_):
                allowed_hosts = type_("*")
                with mock.patch("django.test.utils._TestState") as x:
                    del x.saved_data
                    with self.settings(ALLOWED_HOSTS=allowed_hosts):
                        setup_test_environment()
                        self.assertEqual(settings.ALLOWED_HOSTS, ["*", "testserver"])


class OverrideSettingsTests(SimpleTestCase):
    # #21518 -- If neither override_settings nor a setting_changed receiver
    # clears the URL cache between tests, then one of test_first or
    # test_second will fail.

    @override_settings(ROOT_URLCONF=FirstUrls)
    def test_urlconf_first(self):
        reverse("first")

    @override_settings(ROOT_URLCONF=SecondUrls)
    def test_urlconf_second(self):
        reverse("second")

    def test_urlconf_cache(self):
        with self.assertRaises(NoReverseMatch):
            reverse("first")
        with self.assertRaises(NoReverseMatch):
            reverse("second")

        with override_settings(ROOT_URLCONF=FirstUrls):
            self.client.get(reverse("first"))
            with self.assertRaises(NoReverseMatch):
                reverse("second")

            with override_settings(ROOT_URLCONF=SecondUrls):
                with self.assertRaises(NoReverseMatch):
                    reverse("first")
                self.client.get(reverse("second"))

            self.client.get(reverse("first"))
            with self.assertRaises(NoReverseMatch):
                reverse("second")

        with self.assertRaises(NoReverseMatch):
            reverse("first")
        with self.assertRaises(NoReverseMatch):
            reverse("second")

    def test_override_media_root(self):
        """
        Overriding the MEDIA_ROOT setting should be reflected in the
        base_location attribute of django.core.files.storage.default_storage.
        """
        self.assertEqual(default_storage.base_location, "")
        with self.settings(MEDIA_ROOT="test_value"):
            self.assertEqual(default_storage.base_location, "test_value")

    def test_override_media_url(self):
        """
        Overriding the MEDIA_URL setting should be reflected in the
        base_url attribute of django.core.files.storage.default_storage.
        """
        self.assertEqual(default_storage.base_location, "")
        with self.settings(MEDIA_URL="/test_value/"):
            self.assertEqual(default_storage.base_url, "/test_value/")

    def test_override_file_upload_permissions(self):
        """
        Overriding the FILE_UPLOAD_PERMISSIONS setting should be reflected in
        the file_permissions_mode attribute of
        django.core.files.storage.default_storage.
        """
        self.assertEqual(default_storage.file_permissions_mode, 0o644)
        with self.settings(FILE_UPLOAD_PERMISSIONS=0o777):
            self.assertEqual(default_storage.file_permissions_mode, 0o777)

    def test_override_file_upload_directory_permissions(self):
        """
        Overriding the FILE_UPLOAD_DIRECTORY_PERMISSIONS setting should be
        reflected in the directory_permissions_mode attribute of
        django.core.files.storage.default_storage.
        """
        self.assertIsNone(default_storage.directory_permissions_mode)
        with self.settings(FILE_UPLOAD_DIRECTORY_PERMISSIONS=0o777):
            self.assertEqual(default_storage.directory_permissions_mode, 0o777)

    def test_override_database_routers(self):
        """
        Overriding DATABASE_ROUTERS should update the base router.
        """
        test_routers = [object()]
        with self.settings(DATABASE_ROUTERS=test_routers):
            self.assertEqual(router.routers, test_routers)

    def test_override_static_url(self):
        """
        Overriding the STATIC_URL setting should be reflected in the
        base_url attribute of
        django.contrib.staticfiles.storage.staticfiles_storage.
        """
        with self.settings(STATIC_URL="/test/"):
            self.assertEqual(staticfiles_storage.base_url, "/test/")

    def test_override_static_root(self):
        """
        Overriding the STATIC_ROOT setting should be reflected in the
        location attribute of
        django.contrib.staticfiles.storage.staticfiles_storage.
        """
        with self.settings(STATIC_ROOT="/tmp/test"):
            self.assertEqual(staticfiles_storage.location, os.path.abspath("/tmp/test"))

    def test_override_staticfiles_storage(self):
        """
        Overriding the STORAGES setting should be reflected in
        the value of django.contrib.staticfiles.storage.staticfiles_storage.
        """
        new_class = "ManifestStaticFilesStorage"
        new_storage = "django.contrib.staticfiles.storage." + new_class
        with self.settings(
            STORAGES={STATICFILES_STORAGE_ALIAS: {"BACKEND": new_storage}}
        ):
            self.assertEqual(staticfiles_storage.__class__.__name__, new_class)

    def test_override_staticfiles_finders(self):
        """
        Overriding the STATICFILES_FINDERS setting should be reflected in
        the return value of django.contrib.staticfiles.finders.get_finders.
        """
        current = get_finders()
        self.assertGreater(len(list(current)), 1)
        finders = ["django.contrib.staticfiles.finders.FileSystemFinder"]
        with self.settings(STATICFILES_FINDERS=finders):
            self.assertEqual(len(list(get_finders())), len(finders))

    def test_override_staticfiles_dirs(self):
        """
        Overriding the STATICFILES_DIRS setting should be reflected in
        the locations attribute of the
        django.contrib.staticfiles.finders.FileSystemFinder instance.
        """
        finder = get_finder("django.contrib.staticfiles.finders.FileSystemFinder")
        test_path = "/tmp/test"
        expected_location = ("", test_path)
        self.assertNotIn(expected_location, finder.locations)
        with self.settings(STATICFILES_DIRS=[test_path]):
            finder = get_finder("django.contrib.staticfiles.finders.FileSystemFinder")
            self.assertIn(expected_location, finder.locations)


@skipUnlessDBFeature("supports_transactions")
class TestBadSetUpTestData(TestCase):
    """
    An exception in setUpTestData() shouldn't leak a transaction which would
    cascade across the rest of the test suite.
    """

    class MyException(Exception):
        pass

    @classmethod
    def setUpClass(cls):
        try:
            super().setUpClass()
        except cls.MyException:
            cls._in_atomic_block = connection.in_atomic_block

    @classmethod
    def tearDownClass(Cls):
        # override to avoid a second cls._rollback_atomics() which would fail.
        # Normal setUpClass() methods won't have exception handling so this
        # method wouldn't typically be run.
        pass

    @classmethod
    def setUpTestData(cls):
        # Simulate a broken setUpTestData() method.
        raise cls.MyException()

    def test_failure_in_setUpTestData_should_rollback_transaction(self):
        # setUpTestData() should call _rollback_atomics() so that the
        # transaction doesn't leak.
        self.assertFalse(self._in_atomic_block)


@skipUnlessDBFeature("supports_transactions")
class CaptureOnCommitCallbacksTests(TestCase):
    databases = {"default", "other"}
    callback_called = False

    def enqueue_callback(self, using="default"):
        def hook():
            self.callback_called = True

        transaction.on_commit(hook, using=using)

    def test_no_arguments(self):
        with self.captureOnCommitCallbacks() as callbacks:
            self.enqueue_callback()

        self.assertEqual(len(callbacks), 1)
        self.assertIs(self.callback_called, False)
        callbacks[0]()
        self.assertIs(self.callback_called, True)

    def test_using(self):
        with self.captureOnCommitCallbacks(using="other") as callbacks:
            self.enqueue_callback(using="other")

        self.assertEqual(len(callbacks), 1)
        self.assertIs(self.callback_called, False)
        callbacks[0]()
        self.assertIs(self.callback_called, True)

    def test_different_using(self):
        with self.captureOnCommitCallbacks(using="default") as callbacks:
            self.enqueue_callback(using="other")

        self.assertEqual(callbacks, [])

    def test_execute(self):
        with self.captureOnCommitCallbacks(execute=True) as callbacks:
            self.enqueue_callback()

        self.assertEqual(len(callbacks), 1)
        self.assertIs(self.callback_called, True)

    def test_pre_callback(self):
        def pre_hook():
            pass

        transaction.on_commit(pre_hook, using="default")
        with self.captureOnCommitCallbacks() as callbacks:
            self.enqueue_callback()

        self.assertEqual(len(callbacks), 1)
        self.assertNotEqual(callbacks[0], pre_hook)

    def test_with_rolled_back_savepoint(self):
        with self.captureOnCommitCallbacks() as callbacks:
            try:
                with transaction.atomic():
                    self.enqueue_callback()
                    raise IntegrityError
            except IntegrityError:
                # Inner transaction.atomic() has been rolled back.
                pass

        self.assertEqual(callbacks, [])

    def test_execute_recursive(self):
        with self.captureOnCommitCallbacks(execute=True) as callbacks:
            transaction.on_commit(self.enqueue_callback)

        self.assertEqual(len(callbacks), 2)
        self.assertIs(self.callback_called, True)

    def test_execute_tree(self):
        """
        A visualisation of the callback tree tested. Each node is expected to
        be visited only once:

        └─branch_1
          ├─branch_2
          │ ├─leaf_1
          │ └─leaf_2
          └─leaf_3
        """
        branch_1_call_counter = 0
        branch_2_call_counter = 0
        leaf_1_call_counter = 0
        leaf_2_call_counter = 0
        leaf_3_call_counter = 0

        def leaf_1():
            nonlocal leaf_1_call_counter
            leaf_1_call_counter += 1

        def leaf_2():
            nonlocal leaf_2_call_counter
            leaf_2_call_counter += 1

        def leaf_3():
            nonlocal leaf_3_call_counter
            leaf_3_call_counter += 1

        def branch_1():
            nonlocal branch_1_call_counter
            branch_1_call_counter += 1
            transaction.on_commit(branch_2)
            transaction.on_commit(leaf_3)

        def branch_2():
            nonlocal branch_2_call_counter
            branch_2_call_counter += 1
            transaction.on_commit(leaf_1)
            transaction.on_commit(leaf_2)

        with self.captureOnCommitCallbacks(execute=True) as callbacks:
            transaction.on_commit(branch_1)

        self.assertEqual(branch_1_call_counter, 1)
        self.assertEqual(branch_2_call_counter, 1)
        self.assertEqual(leaf_1_call_counter, 1)
        self.assertEqual(leaf_2_call_counter, 1)
        self.assertEqual(leaf_3_call_counter, 1)

        self.assertEqual(callbacks, [branch_1, branch_2, leaf_3, leaf_1, leaf_2])

    def test_execute_robust(self):
        class MyException(Exception):
            pass

        def hook():
            self.callback_called = True
            raise MyException("robust callback")

        with self.assertLogs("django.test", "ERROR") as cm:
            with self.captureOnCommitCallbacks(execute=True) as callbacks:
                transaction.on_commit(hook, robust=True)

        self.assertEqual(len(callbacks), 1)
        self.assertIs(self.callback_called, True)

        log_record = cm.records[0]
        self.assertEqual(
            log_record.getMessage(),
            "Error calling CaptureOnCommitCallbacksTests.test_execute_robust.<locals>."
            "hook in on_commit() (robust callback).",
        )
        self.assertIsNotNone(log_record.exc_info)
        raised_exception = log_record.exc_info[1]
        self.assertIsInstance(raised_exception, MyException)
        self.assertEqual(str(raised_exception), "robust callback")


class DisallowedDatabaseQueriesTests(SimpleTestCase):
    def test_disallowed_database_connections(self):
        expected_message = (
            "Database connections to 'default' are not allowed in SimpleTestCase "
            "subclasses. Either subclass TestCase or TransactionTestCase to "
            "ensure proper test isolation or add 'default' to "
            "test_utils.tests.DisallowedDatabaseQueriesTests.databases to "
            "silence this failure."
        )
        with self.assertRaisesMessage(DatabaseOperationForbidden, expected_message):
            connection.connect()
        with self.assertRaisesMessage(DatabaseOperationForbidden, expected_message):
            connection.temporary_connection()

    def test_disallowed_database_queries(self):
        expected_message = (
            "Database queries to 'default' are not allowed in SimpleTestCase "
            "subclasses. Either subclass TestCase or TransactionTestCase to "
            "ensure proper test isolation or add 'default' to "
            "test_utils.tests.DisallowedDatabaseQueriesTests.databases to "
            "silence this failure."
        )
        with self.assertRaisesMessage(DatabaseOperationForbidden, expected_message):
            Car.objects.first()

    def test_disallowed_database_chunked_cursor_queries(self):
        expected_message = (
            "Database queries to 'default' are not allowed in SimpleTestCase "
            "subclasses. Either subclass TestCase or TransactionTestCase to "
            "ensure proper test isolation or add 'default' to "
            "test_utils.tests.DisallowedDatabaseQueriesTests.databases to "
            "silence this failure."
        )
        with self.assertRaisesMessage(DatabaseOperationForbidden, expected_message):
            next(Car.objects.iterator())


class AllowedDatabaseQueriesTests(SimpleTestCase):
    databases = {"default"}

    def test_allowed_database_queries(self):
        Car.objects.first()

    def test_allowed_database_chunked_cursor_queries(self):
        next(Car.objects.iterator(), None)


class DatabaseAliasTests(SimpleTestCase):
    def setUp(self):
        self.addCleanup(setattr, self.__class__, "databases", self.databases)

    def test_no_close_match(self):
        self.__class__.databases = {"void"}
        message = (
            "test_utils.tests.DatabaseAliasTests.databases refers to 'void' which is "
            "not defined in settings.DATABASES."
        )
        with self.assertRaisesMessage(ImproperlyConfigured, message):
            self._validate_databases()

    def test_close_match(self):
        self.__class__.databases = {"defualt"}
        message = (
            "test_utils.tests.DatabaseAliasTests.databases refers to 'defualt' which "
            "is not defined in settings.DATABASES. Did you mean 'default'?"
        )
        with self.assertRaisesMessage(ImproperlyConfigured, message):
            self._validate_databases()

    def test_match(self):
        self.__class__.databases = {"default", "other"}
        self.assertEqual(self._validate_databases(), frozenset({"default", "other"}))

    def test_all(self):
        self.__class__.databases = "__all__"
        self.assertEqual(self._validate_databases(), frozenset(connections))


@isolate_apps("test_utils", attr_name="class_apps")
class IsolatedAppsTests(SimpleTestCase):
    def test_installed_apps(self):
        self.assertEqual(
            [app_config.label for app_config in self.class_apps.get_app_configs()],
            ["test_utils"],
        )

    def test_class_decoration(self):
        class ClassDecoration(models.Model):
            pass

        self.assertEqual(ClassDecoration._meta.apps, self.class_apps)

    @isolate_apps("test_utils", kwarg_name="method_apps")
    def test_method_decoration(self, method_apps):
        class MethodDecoration(models.Model):
            pass

        self.assertEqual(MethodDecoration._meta.apps, method_apps)

    def test_context_manager(self):
        with isolate_apps("test_utils") as context_apps:

            class ContextManager(models.Model):
                pass

        self.assertEqual(ContextManager._meta.apps, context_apps)

    @isolate_apps("test_utils", kwarg_name="method_apps")
    def test_nested(self, method_apps):
        class MethodDecoration(models.Model):
            pass

        with isolate_apps("test_utils") as context_apps:

            class ContextManager(models.Model):
                pass

            with isolate_apps("test_utils") as nested_context_apps:

                class NestedContextManager(models.Model):
                    pass

        self.assertEqual(MethodDecoration._meta.apps, method_apps)
        self.assertEqual(ContextManager._meta.apps, context_apps)
        self.assertEqual(NestedContextManager._meta.apps, nested_context_apps)


class DoNothingDecorator(TestContextDecorator):
    def enable(self):
        pass

    def disable(self):
        pass


class TestContextDecoratorTests(SimpleTestCase):
    @mock.patch.object(DoNothingDecorator, "disable")
    def test_exception_in_setup(self, mock_disable):
        """An exception is setUp() is reraised after disable() is called."""

        class ExceptionInSetUp(unittest.TestCase):
            def setUp(self):
                raise NotImplementedError("reraised")

        decorator = DoNothingDecorator()
        decorated_test_class = decorator.__call__(ExceptionInSetUp)()
        self.assertFalse(mock_disable.called)
        with self.assertRaisesMessage(NotImplementedError, "reraised"):
            decorated_test_class.setUp()
        decorated_test_class.doCleanups()
        self.assertTrue(mock_disable.called)

    def test_cleanups_run_after_tearDown(self):
        calls = []

        class SaveCallsDecorator(TestContextDecorator):
            def enable(self):
                calls.append("enable")

            def disable(self):
                calls.append("disable")

        class AddCleanupInSetUp(unittest.TestCase):
            def setUp(self):
                calls.append("setUp")
                self.addCleanup(lambda: calls.append("cleanup"))

        decorator = SaveCallsDecorator()
        decorated_test_class = decorator.__call__(AddCleanupInSetUp)()
        decorated_test_class.setUp()
        decorated_test_class.tearDown()
        decorated_test_class.doCleanups()
        self.assertEqual(calls, ["enable", "setUp", "cleanup", "disable"])
