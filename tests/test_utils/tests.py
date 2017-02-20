import os
import sys
import unittest
from io import StringIO

from django.conf.urls import url
from django.contrib.staticfiles.finders import get_finder, get_finders
from django.contrib.staticfiles.storage import staticfiles_storage
from django.core.files.storage import default_storage
from django.db import connection, models, router
from django.forms import EmailField, IntegerField
from django.http import HttpResponse
from django.template.loader import render_to_string
from django.test import (
    SimpleTestCase, TestCase, skipIfDBFeature, skipUnlessDBFeature,
)
from django.test.html import HTMLParseError, parse_html
from django.test.utils import (
    CaptureQueriesContext, isolate_apps, override_settings,
    setup_test_environment,
)
from django.urls import NoReverseMatch, reverse

from .models import Car, Person, PossessedCar
from .views import empty_response


class SkippingTestCase(SimpleTestCase):
    def _assert_skipping(self, func, expected_exc):
        # We cannot simply use assertRaises because a SkipTest exception will go unnoticed
        try:
            func()
        except expected_exc:
            pass
        except Exception as e:
            self.fail("No %s exception should have been raised for %s." % (
                e.__class__.__name__, func.__name__))

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


class SkippingClassTestCase(SimpleTestCase):
    def test_skip_class_unless_db_feature(self):
        @skipUnlessDBFeature("__class__")
        class NotSkippedTests(unittest.TestCase):
            def test_dummy(self):
                return

        @skipUnlessDBFeature("missing")
        @skipIfDBFeature("__class__")
        class SkippedTests(unittest.TestCase):
            def test_will_be_skipped(self):
                self.fail("We should never arrive here.")

        @skipIfDBFeature("__dict__")
        class SkippedTestsSubclass(SkippedTests):
            pass

        test_suite = unittest.TestSuite()
        test_suite.addTest(NotSkippedTests('test_dummy'))
        try:
            test_suite.addTest(SkippedTests('test_will_be_skipped'))
            test_suite.addTest(SkippedTestsSubclass('test_will_be_skipped'))
        except unittest.SkipTest:
            self.fail("SkipTest should not be raised at this stage")
        result = unittest.TextTestRunner(stream=StringIO()).run(test_suite)
        self.assertEqual(result.testsRun, 3)
        self.assertEqual(len(result.skipped), 2)
        self.assertEqual(result.skipped[0][1], 'Database has feature(s) __class__')
        self.assertEqual(result.skipped[1][1], 'Database has feature(s) __class__')


@override_settings(ROOT_URLCONF='test_utils.urls')
class AssertNumQueriesTests(TestCase):

    def test_assert_num_queries(self):
        def test_func():
            raise ValueError

        with self.assertRaises(ValueError):
            self.assertNumQueries(2, test_func)

    def test_assert_num_queries_with_client(self):
        person = Person.objects.create(name='test')

        self.assertNumQueries(
            1,
            self.client.get,
            "/test_utils/get_person/%s/" % person.pk
        )

        self.assertNumQueries(
            1,
            self.client.get,
            "/test_utils/get_person/%s/" % person.pk
        )

        def test_func():
            self.client.get("/test_utils/get_person/%s/" % person.pk)
            self.client.get("/test_utils/get_person/%s/" % person.pk)
        self.assertNumQueries(2, test_func)


class AssertQuerysetEqualTests(TestCase):
    def setUp(self):
        self.p1 = Person.objects.create(name='p1')
        self.p2 = Person.objects.create(name='p2')

    def test_ordered(self):
        self.assertQuerysetEqual(
            Person.objects.all().order_by('name'),
            [repr(self.p1), repr(self.p2)]
        )

    def test_unordered(self):
        self.assertQuerysetEqual(
            Person.objects.all().order_by('name'),
            [repr(self.p2), repr(self.p1)],
            ordered=False
        )

    def test_transform(self):
        self.assertQuerysetEqual(
            Person.objects.all().order_by('name'),
            [self.p1.pk, self.p2.pk],
            transform=lambda x: x.pk
        )

    def test_undefined_order(self):
        # Using an unordered queryset with more than one ordered value
        # is an error.
        with self.assertRaises(ValueError):
            self.assertQuerysetEqual(
                Person.objects.all(),
                [repr(self.p1), repr(self.p2)]
            )
        # No error for one value.
        self.assertQuerysetEqual(
            Person.objects.filter(name='p1'),
            [repr(self.p1)]
        )

    def test_repeated_values(self):
        """
        assertQuerysetEqual checks the number of appearance of each item
        when used with option ordered=False.
        """
        batmobile = Car.objects.create(name='Batmobile')
        k2000 = Car.objects.create(name='K 2000')
        PossessedCar.objects.bulk_create([
            PossessedCar(car=batmobile, belongs_to=self.p1),
            PossessedCar(car=batmobile, belongs_to=self.p1),
            PossessedCar(car=k2000, belongs_to=self.p1),
            PossessedCar(car=k2000, belongs_to=self.p1),
            PossessedCar(car=k2000, belongs_to=self.p1),
            PossessedCar(car=k2000, belongs_to=self.p1),
        ])
        with self.assertRaises(AssertionError):
            self.assertQuerysetEqual(
                self.p1.cars.all(),
                [repr(batmobile), repr(k2000)],
                ordered=False
            )
        self.assertQuerysetEqual(
            self.p1.cars.all(),
            [repr(batmobile)] * 2 + [repr(k2000)] * 4,
            ordered=False
        )


@override_settings(ROOT_URLCONF='test_utils.urls')
class CaptureQueriesContextManagerTests(TestCase):

    def setUp(self):
        self.person_pk = str(Person.objects.create(name='test').pk)

    def test_simple(self):
        with CaptureQueriesContext(connection) as captured_queries:
            Person.objects.get(pk=self.person_pk)
        self.assertEqual(len(captured_queries), 1)
        self.assertIn(self.person_pk, captured_queries[0]['sql'])

        with CaptureQueriesContext(connection) as captured_queries:
            pass
        self.assertEqual(0, len(captured_queries))

    def test_within(self):
        with CaptureQueriesContext(connection) as captured_queries:
            Person.objects.get(pk=self.person_pk)
            self.assertEqual(len(captured_queries), 1)
            self.assertIn(self.person_pk, captured_queries[0]['sql'])

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
        self.assertIn(self.person_pk, captured_queries[0]['sql'])

        with CaptureQueriesContext(connection) as captured_queries:
            self.client.get("/test_utils/get_person/%s/" % self.person_pk)
        self.assertEqual(len(captured_queries), 1)
        self.assertIn(self.person_pk, captured_queries[0]['sql'])

        with CaptureQueriesContext(connection) as captured_queries:
            self.client.get("/test_utils/get_person/%s/" % self.person_pk)
            self.client.get("/test_utils/get_person/%s/" % self.person_pk)
        self.assertEqual(len(captured_queries), 2)
        self.assertIn(self.person_pk, captured_queries[0]['sql'])
        self.assertIn(self.person_pk, captured_queries[1]['sql'])


@override_settings(ROOT_URLCONF='test_utils.urls')
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
        with self.assertRaises(AssertionError) as exc_info:
            with self.assertNumQueries(2):
                Person.objects.count()
        self.assertIn("1 queries executed, 2 expected", str(exc_info.exception))
        self.assertIn("Captured queries were", str(exc_info.exception))

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


@override_settings(ROOT_URLCONF='test_utils.urls')
class AssertTemplateUsedContextManagerTests(SimpleTestCase):

    def test_usage(self):
        with self.assertTemplateUsed('template_used/base.html'):
            render_to_string('template_used/base.html')

        with self.assertTemplateUsed(template_name='template_used/base.html'):
            render_to_string('template_used/base.html')

        with self.assertTemplateUsed('template_used/base.html'):
            render_to_string('template_used/include.html')

        with self.assertTemplateUsed('template_used/base.html'):
            render_to_string('template_used/extends.html')

        with self.assertTemplateUsed('template_used/base.html'):
            render_to_string('template_used/base.html')
            render_to_string('template_used/base.html')

    def test_nested_usage(self):
        with self.assertTemplateUsed('template_used/base.html'):
            with self.assertTemplateUsed('template_used/include.html'):
                render_to_string('template_used/include.html')

        with self.assertTemplateUsed('template_used/extends.html'):
            with self.assertTemplateUsed('template_used/base.html'):
                render_to_string('template_used/extends.html')

        with self.assertTemplateUsed('template_used/base.html'):
            with self.assertTemplateUsed('template_used/alternative.html'):
                render_to_string('template_used/alternative.html')
            render_to_string('template_used/base.html')

        with self.assertTemplateUsed('template_used/base.html'):
            render_to_string('template_used/extends.html')
            with self.assertTemplateNotUsed('template_used/base.html'):
                render_to_string('template_used/alternative.html')
            render_to_string('template_used/base.html')

    def test_not_used(self):
        with self.assertTemplateNotUsed('template_used/base.html'):
            pass
        with self.assertTemplateNotUsed('template_used/alternative.html'):
            pass

    def test_error_message(self):
        msg = 'template_used/base.html was not rendered. No template was rendered.'
        with self.assertRaisesMessage(AssertionError, msg):
            with self.assertTemplateUsed('template_used/base.html'):
                pass

        with self.assertRaisesMessage(AssertionError, msg):
            with self.assertTemplateUsed(template_name='template_used/base.html'):
                pass

        msg2 = (
            'template_used/base.html was not rendered. Following templates '
            'were rendered: template_used/alternative.html'
        )
        with self.assertRaisesMessage(AssertionError, msg2):
            with self.assertTemplateUsed('template_used/base.html'):
                render_to_string('template_used/alternative.html')

        with self.assertRaisesMessage(AssertionError, 'No templates used to render the response'):
            response = self.client.get('/test_utils/no_template_used/')
            self.assertTemplateUsed(response, 'template_used/base.html')

    def test_failure(self):
        with self.assertRaises(TypeError):
            with self.assertTemplateUsed():
                pass

        with self.assertRaises(AssertionError):
            with self.assertTemplateUsed(''):
                pass

        with self.assertRaises(AssertionError):
            with self.assertTemplateUsed(''):
                render_to_string('template_used/base.html')

        with self.assertRaises(AssertionError):
            with self.assertTemplateUsed(template_name=''):
                pass

        with self.assertRaises(AssertionError):
            with self.assertTemplateUsed('template_used/base.html'):
                render_to_string('template_used/alternative.html')

    def test_assert_used_on_http_response(self):
        response = HttpResponse()
        error_msg = (
            'assertTemplateUsed() and assertTemplateNotUsed() are only '
            'usable on responses fetched using the Django test Client.'
        )
        with self.assertRaisesMessage(ValueError, error_msg):
            self.assertTemplateUsed(response, 'template.html')

        with self.assertRaisesMessage(ValueError, error_msg):
            self.assertTemplateNotUsed(response, 'template.html')


class HTMLEqualTests(SimpleTestCase):
    def test_html_parser(self):
        element = parse_html('<div><p>Hello</p></div>')
        self.assertEqual(len(element.children), 1)
        self.assertEqual(element.children[0].name, 'p')
        self.assertEqual(element.children[0].children[0], 'Hello')

        parse_html('<p>')
        parse_html('<p attr>')
        dom = parse_html('<p>foo')
        self.assertEqual(len(dom.children), 1)
        self.assertEqual(dom.name, 'p')
        self.assertEqual(dom[0], 'foo')

    def test_parse_html_in_script(self):
        parse_html('<script>var a = "<p" + ">";</script>')
        parse_html('''
            <script>
            var js_sha_link='<p>***</p>';
            </script>
        ''')

        # script content will be parsed to text
        dom = parse_html('''
            <script><p>foo</p> '</scr'+'ipt>' <span>bar</span></script>
        ''')
        self.assertEqual(len(dom.children), 1)
        self.assertEqual(dom.children[0], "<p>foo</p> '</scr'+'ipt>' <span>bar</span>")

    def test_self_closing_tags(self):
        self_closing_tags = (
            'br', 'hr', 'input', 'img', 'meta', 'spacer', 'link', 'frame',
            'base', 'col',
        )
        for tag in self_closing_tags:
            dom = parse_html('<p>Hello <%s> world</p>' % tag)
            self.assertEqual(len(dom.children), 3)
            self.assertEqual(dom[0], 'Hello')
            self.assertEqual(dom[1].name, tag)
            self.assertEqual(dom[2], 'world')

            dom = parse_html('<p>Hello <%s /> world</p>' % tag)
            self.assertEqual(len(dom.children), 3)
            self.assertEqual(dom[0], 'Hello')
            self.assertEqual(dom[1].name, tag)
            self.assertEqual(dom[2], 'world')

    def test_simple_equal_html(self):
        self.assertHTMLEqual('', '')
        self.assertHTMLEqual('<p></p>', '<p></p>')
        self.assertHTMLEqual('<p></p>', ' <p> </p> ')
        self.assertHTMLEqual(
            '<div><p>Hello</p></div>',
            '<div><p>Hello</p></div>')
        self.assertHTMLEqual(
            '<div><p>Hello</p></div>',
            '<div> <p>Hello</p> </div>')
        self.assertHTMLEqual(
            '<div>\n<p>Hello</p></div>',
            '<div><p>Hello</p></div>\n')
        self.assertHTMLEqual(
            '<div><p>Hello\nWorld !</p></div>',
            '<div><p>Hello World\n!</p></div>')
        self.assertHTMLEqual(
            '<div><p>Hello\nWorld !</p></div>',
            '<div><p>Hello World\n!</p></div>')
        self.assertHTMLEqual(
            '<p>Hello  World   !</p>',
            '<p>Hello World\n\n!</p>')
        self.assertHTMLEqual('<p> </p>', '<p></p>')
        self.assertHTMLEqual('<p/>', '<p></p>')
        self.assertHTMLEqual('<p />', '<p></p>')
        self.assertHTMLEqual('<input checked>', '<input checked="checked">')
        self.assertHTMLEqual('<p>Hello', '<p> Hello')
        self.assertHTMLEqual('<p>Hello</p>World', '<p>Hello</p> World')

    def test_ignore_comments(self):
        self.assertHTMLEqual(
            '<div>Hello<!-- this is a comment --> World!</div>',
            '<div>Hello World!</div>')

    def test_unequal_html(self):
        self.assertHTMLNotEqual('<p>Hello</p>', '<p>Hello!</p>')
        self.assertHTMLNotEqual('<p>foo&#20;bar</p>', '<p>foo&nbsp;bar</p>')
        self.assertHTMLNotEqual('<p>foo bar</p>', '<p>foo &nbsp;bar</p>')
        self.assertHTMLNotEqual('<p>foo nbsp</p>', '<p>foo &nbsp;</p>')
        self.assertHTMLNotEqual('<p>foo #20</p>', '<p>foo &#20;</p>')
        self.assertHTMLNotEqual(
            '<p><span>Hello</span><span>World</span></p>',
            '<p><span>Hello</span>World</p>')
        self.assertHTMLNotEqual(
            '<p><span>Hello</span>World</p>',
            '<p><span>Hello</span><span>World</span></p>')

    def test_attributes(self):
        self.assertHTMLEqual(
            '<input type="text" id="id_name" />',
            '<input id="id_name" type="text" />')
        self.assertHTMLEqual(
            '''<input type='text' id="id_name" />''',
            '<input id="id_name" type="text" />')
        self.assertHTMLNotEqual(
            '<input type="text" id="id_name" />',
            '<input type="password" id="id_name" />')

    def test_complex_examples(self):
        self.assertHTMLEqual(
            """<tr><th><label for="id_first_name">First name:</label></th>
<td><input type="text" name="first_name" value="John" id="id_first_name" /></td></tr>
<tr><th><label for="id_last_name">Last name:</label></th>
<td><input type="text" id="id_last_name" name="last_name" value="Lennon" /></td></tr>
<tr><th><label for="id_birthday">Birthday:</label></th>
<td><input type="text" value="1940-10-9" name="birthday" id="id_birthday" /></td></tr>""",
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
        """)

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
        </html>""", """
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
        </html>""")

    def test_html_contain(self):
        # equal html contains each other
        dom1 = parse_html('<p>foo')
        dom2 = parse_html('<p>foo</p>')
        self.assertIn(dom1, dom2)
        self.assertIn(dom2, dom1)

        dom2 = parse_html('<div><p>foo</p></div>')
        self.assertIn(dom1, dom2)
        self.assertNotIn(dom2, dom1)

        self.assertNotIn('<p>foo</p>', dom2)
        self.assertIn('foo', dom2)

        # when a root element is used ...
        dom1 = parse_html('<p>foo</p><p>bar</p>')
        dom2 = parse_html('<p>foo</p><p>bar</p>')
        self.assertIn(dom1, dom2)
        dom1 = parse_html('<p>foo</p>')
        self.assertIn(dom1, dom2)
        dom1 = parse_html('<p>bar</p>')
        self.assertIn(dom1, dom2)
        dom1 = parse_html('<div><p>foo</p><p>bar</p></div>')
        self.assertIn(dom2, dom1)

    def test_count(self):
        # equal html contains each other one time
        dom1 = parse_html('<p>foo')
        dom2 = parse_html('<p>foo</p>')
        self.assertEqual(dom1.count(dom2), 1)
        self.assertEqual(dom2.count(dom1), 1)

        dom2 = parse_html('<p>foo</p><p>bar</p>')
        self.assertEqual(dom2.count(dom1), 1)

        dom2 = parse_html('<p>foo foo</p><p>foo</p>')
        self.assertEqual(dom2.count('foo'), 3)

        dom2 = parse_html('<p class="bar">foo</p>')
        self.assertEqual(dom2.count('bar'), 0)
        self.assertEqual(dom2.count('class'), 0)
        self.assertEqual(dom2.count('p'), 0)
        self.assertEqual(dom2.count('o'), 2)

        dom2 = parse_html('<p>foo</p><p>foo</p>')
        self.assertEqual(dom2.count(dom1), 2)

        dom2 = parse_html('<div><p>foo<input type=""></p><p>foo</p></div>')
        self.assertEqual(dom2.count(dom1), 1)

        dom2 = parse_html('<div><div><p>foo</p></div></div>')
        self.assertEqual(dom2.count(dom1), 1)

        dom2 = parse_html('<p>foo<p>foo</p></p>')
        self.assertEqual(dom2.count(dom1), 1)

        dom2 = parse_html('<p>foo<p>bar</p></p>')
        self.assertEqual(dom2.count(dom1), 0)

        # html with a root element contains the same html with no root element
        dom1 = parse_html('<p>foo</p><p>bar</p>')
        dom2 = parse_html('<div><p>foo</p><p>bar</p></div>')
        self.assertEqual(dom2.count(dom1), 1)

    def test_parsing_errors(self):
        with self.assertRaises(AssertionError):
            self.assertHTMLEqual('<p>', '')
        with self.assertRaises(AssertionError):
            self.assertHTMLEqual('', '<p>')
        error_msg = (
            "First argument is not valid HTML:\n"
            "('Unexpected end tag `div` (Line 1, Column 6)', (1, 6))"
        ) if sys.version_info >= (3, 5) else (
            "First argument is not valid HTML:\n"
            "Unexpected end tag `div` (Line 1, Column 6), at line 1, column 7"
        )
        with self.assertRaisesMessage(AssertionError, error_msg):
            self.assertHTMLEqual('< div></ div>', '<div></div>')
        with self.assertRaises(HTMLParseError):
            parse_html('</p>')

    def test_contains_html(self):
        response = HttpResponse('''<body>
        This is a form: <form action="" method="get">
            <input type="text" name="Hello" />
        </form></body>''')

        self.assertNotContains(response, "<input name='Hello' type='text'>")
        self.assertContains(response, '<form action="" method="get">')

        self.assertContains(response, "<input name='Hello' type='text'>", html=True)
        self.assertNotContains(response, '<form action="" method="get">', html=True)

        invalid_response = HttpResponse('''<body <bad>>''')

        with self.assertRaises(AssertionError):
            self.assertContains(invalid_response, '<p></p>')

        with self.assertRaises(AssertionError):
            self.assertContains(response, '<p "whats" that>')

    def test_unicode_handling(self):
        response = HttpResponse('<p class="help">Some help text for the title (with unicode ŠĐĆŽćžšđ)</p>')
        self.assertContains(
            response,
            '<p class="help">Some help text for the title (with unicode ŠĐĆŽćžšđ)</p>',
            html=True
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

        msg = '''{xml1} != {xml2}
- <elem attr1='a' />
+ <elem attr2='b' attr1='a' />
?      ++++++++++
'''.format(xml1=repr(xml1), xml2=repr(xml2))

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


class SkippingExtraTests(TestCase):
    fixtures = ['should_not_be_loaded.json']

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


class AssertFieldOutputTests(SimpleTestCase):

    def test_assert_field_output(self):
        error_invalid = ['Enter a valid email address.']
        self.assertFieldOutput(EmailField, {'a@a.com': 'a@a.com'}, {'aaa': error_invalid})
        with self.assertRaises(AssertionError):
            self.assertFieldOutput(EmailField, {'a@a.com': 'a@a.com'}, {'aaa': error_invalid + ['Another error']})
        with self.assertRaises(AssertionError):
            self.assertFieldOutput(EmailField, {'a@a.com': 'Wrong output'}, {'aaa': error_invalid})
        with self.assertRaises(AssertionError):
            self.assertFieldOutput(
                EmailField, {'a@a.com': 'a@a.com'}, {'aaa': ['Come on, gimme some well formatted data, dude.']}
            )

    def test_custom_required_message(self):
        class MyCustomField(IntegerField):
            default_error_messages = {
                'required': 'This is really required.',
            }
        self.assertFieldOutput(MyCustomField, {}, {}, empty_value=None)


class FirstUrls:
    urlpatterns = [url(r'first/$', empty_response, name='first')]


class SecondUrls:
    urlpatterns = [url(r'second/$', empty_response, name='second')]


class SetupTestEnvironmentTests(SimpleTestCase):

    def test_setup_test_environment_calling_more_than_once(self):
        with self.assertRaisesMessage(RuntimeError, "setup_test_environment() was already called"):
            setup_test_environment()


class OverrideSettingsTests(SimpleTestCase):

    # #21518 -- If neither override_settings nor a setting_changed receiver
    # clears the URL cache between tests, then one of test_first or
    # test_second will fail.

    @override_settings(ROOT_URLCONF=FirstUrls)
    def test_urlconf_first(self):
        reverse('first')

    @override_settings(ROOT_URLCONF=SecondUrls)
    def test_urlconf_second(self):
        reverse('second')

    def test_urlconf_cache(self):
        with self.assertRaises(NoReverseMatch):
            reverse('first')
        with self.assertRaises(NoReverseMatch):
            reverse('second')

        with override_settings(ROOT_URLCONF=FirstUrls):
            self.client.get(reverse('first'))
            with self.assertRaises(NoReverseMatch):
                reverse('second')

            with override_settings(ROOT_URLCONF=SecondUrls):
                with self.assertRaises(NoReverseMatch):
                    reverse('first')
                self.client.get(reverse('second'))

            self.client.get(reverse('first'))
            with self.assertRaises(NoReverseMatch):
                reverse('second')

        with self.assertRaises(NoReverseMatch):
            reverse('first')
        with self.assertRaises(NoReverseMatch):
            reverse('second')

    def test_override_media_root(self):
        """
        Overriding the MEDIA_ROOT setting should be reflected in the
        base_location attribute of django.core.files.storage.default_storage.
        """
        self.assertEqual(default_storage.base_location, '')
        with self.settings(MEDIA_ROOT='test_value'):
            self.assertEqual(default_storage.base_location, 'test_value')

    def test_override_media_url(self):
        """
        Overriding the MEDIA_URL setting should be reflected in the
        base_url attribute of django.core.files.storage.default_storage.
        """
        self.assertEqual(default_storage.base_location, '')
        with self.settings(MEDIA_URL='/test_value/'):
            self.assertEqual(default_storage.base_url, '/test_value/')

    def test_override_file_upload_permissions(self):
        """
        Overriding the FILE_UPLOAD_PERMISSIONS setting should be reflected in
        the file_permissions_mode attribute of
        django.core.files.storage.default_storage.
        """
        self.assertIsNone(default_storage.file_permissions_mode)
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
        Overriding DATABASE_ROUTERS should update the master router.
        """
        test_routers = (object(),)
        with self.settings(DATABASE_ROUTERS=test_routers):
            self.assertSequenceEqual(router.routers, test_routers)

    def test_override_static_url(self):
        """
        Overriding the STATIC_URL setting should be reflected in the
        base_url attribute of
        django.contrib.staticfiles.storage.staticfiles_storage.
        """
        with self.settings(STATIC_URL='/test/'):
            self.assertEqual(staticfiles_storage.base_url, '/test/')

    def test_override_static_root(self):
        """
        Overriding the STATIC_ROOT setting should be reflected in the
        location attribute of
        django.contrib.staticfiles.storage.staticfiles_storage.
        """
        with self.settings(STATIC_ROOT='/tmp/test'):
            self.assertEqual(staticfiles_storage.location, os.path.abspath('/tmp/test'))

    def test_override_staticfiles_storage(self):
        """
        Overriding the STATICFILES_STORAGE setting should be reflected in
        the value of django.contrib.staticfiles.storage.staticfiles_storage.
        """
        new_class = 'CachedStaticFilesStorage'
        new_storage = 'django.contrib.staticfiles.storage.' + new_class
        with self.settings(STATICFILES_STORAGE=new_storage):
            self.assertEqual(staticfiles_storage.__class__.__name__, new_class)

    def test_override_staticfiles_finders(self):
        """
        Overriding the STATICFILES_FINDERS setting should be reflected in
        the return value of django.contrib.staticfiles.finders.get_finders.
        """
        current = get_finders()
        self.assertGreater(len(list(current)), 1)
        finders = ['django.contrib.staticfiles.finders.FileSystemFinder']
        with self.settings(STATICFILES_FINDERS=finders):
            self.assertEqual(len(list(get_finders())), len(finders))

    def test_override_staticfiles_dirs(self):
        """
        Overriding the STATICFILES_DIRS setting should be reflected in
        the locations attribute of the
        django.contrib.staticfiles.finders.FileSystemFinder instance.
        """
        finder = get_finder('django.contrib.staticfiles.finders.FileSystemFinder')
        test_path = '/tmp/test'
        expected_location = ('', test_path)
        self.assertNotIn(expected_location, finder.locations)
        with self.settings(STATICFILES_DIRS=[test_path]):
            finder = get_finder('django.contrib.staticfiles.finders.FileSystemFinder')
            self.assertIn(expected_location, finder.locations)


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


class DisallowedDatabaseQueriesTests(SimpleTestCase):
    def test_disallowed_database_queries(self):
        expected_message = (
            "Database queries aren't allowed in SimpleTestCase. "
            "Either use TestCase or TransactionTestCase to ensure proper test isolation or "
            "set DisallowedDatabaseQueriesTests.allow_database_queries to True to silence this failure."
        )
        with self.assertRaisesMessage(AssertionError, expected_message):
            Car.objects.first()


class DisallowedDatabaseQueriesChunkedCursorsTests(SimpleTestCase):
    def test_disallowed_database_queries(self):
        expected_message = (
            "Database queries aren't allowed in SimpleTestCase. Either use "
            "TestCase or TransactionTestCase to ensure proper test isolation or "
            "set DisallowedDatabaseQueriesChunkedCursorsTests.allow_database_queries "
            "to True to silence this failure."
        )
        with self.assertRaisesMessage(AssertionError, expected_message):
            next(Car.objects.iterator())


class AllowedDatabaseQueriesTests(SimpleTestCase):
    allow_database_queries = True

    def test_allowed_database_queries(self):
        Car.objects.first()


@isolate_apps('test_utils', attr_name='class_apps')
class IsolatedAppsTests(SimpleTestCase):
    def test_installed_apps(self):
        self.assertEqual([app_config.label for app_config in self.class_apps.get_app_configs()], ['test_utils'])

    def test_class_decoration(self):
        class ClassDecoration(models.Model):
            pass
        self.assertEqual(ClassDecoration._meta.apps, self.class_apps)

    @isolate_apps('test_utils', kwarg_name='method_apps')
    def test_method_decoration(self, method_apps):
        class MethodDecoration(models.Model):
            pass
        self.assertEqual(MethodDecoration._meta.apps, method_apps)

    def test_context_manager(self):
        with isolate_apps('test_utils') as context_apps:
            class ContextManager(models.Model):
                pass
        self.assertEqual(ContextManager._meta.apps, context_apps)

    @isolate_apps('test_utils', kwarg_name='method_apps')
    def test_nested(self, method_apps):
        class MethodDecoration(models.Model):
            pass
        with isolate_apps('test_utils') as context_apps:
            class ContextManager(models.Model):
                pass
            with isolate_apps('test_utils') as nested_context_apps:
                class NestedContextManager(models.Model):
                    pass
        self.assertEqual(MethodDecoration._meta.apps, method_apps)
        self.assertEqual(ContextManager._meta.apps, context_apps)
        self.assertEqual(NestedContextManager._meta.apps, nested_context_apps)
