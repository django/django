# -*- coding: utf-8 -*-
from __future__ import absolute_import, unicode_literals
import warnings

from django.db import connection
from django.forms import EmailField, IntegerField
from django.http import HttpResponse
from django.template.loader import render_to_string
from django.test import SimpleTestCase, TestCase, skipUnlessDBFeature
from django.test.html import HTMLParseError, parse_html
from django.test.utils import CaptureQueriesContext, IgnorePendingDeprecationWarningsMixin
from django.utils import six
from django.utils import unittest
from django.utils.unittest import skip

from .models import Person


class SkippingTestCase(TestCase):
    def test_skip_unless_db_feature(self):
        "A test that might be skipped is actually called."
        # Total hack, but it works, just want an attribute that's always true.
        @skipUnlessDBFeature("__class__")
        def test_func():
            raise ValueError

        self.assertRaises(ValueError, test_func)


class AssertNumQueriesTests(TestCase):
    urls = 'test_utils.urls'

    def test_assert_num_queries(self):
        def test_func():
            raise ValueError

        self.assertRaises(ValueError,
            self.assertNumQueries, 2, test_func
        )

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


class CaptureQueriesContextManagerTests(TestCase):
    urls = 'test_utils.urls'

    def setUp(self):
        self.person_pk = six.text_type(Person.objects.create(name='test').pk)

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


class AssertNumQueriesContextManagerTests(TestCase):
    urls = 'test_utils.urls'

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


class AssertTemplateUsedContextManagerTests(TestCase):
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
        with six.assertRaisesRegex(self, AssertionError, r'^template_used/base\.html'):
            with self.assertTemplateUsed('template_used/base.html'):
                pass

        with six.assertRaisesRegex(self, AssertionError, r'^template_used/base\.html'):
            with self.assertTemplateUsed(template_name='template_used/base.html'):
                pass

        with six.assertRaisesRegex(self, AssertionError, r'^template_used/base\.html.*template_used/alternative\.html$'):
            with self.assertTemplateUsed('template_used/base.html'):
                render_to_string('template_used/alternative.html')

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


class SaveRestoreWarningState(TestCase):
    def test_save_restore_warnings_state(self):
        """
        Ensure save_warnings_state/restore_warnings_state work correctly.
        """
        # In reality this test could be satisfied by many broken implementations
        # of save_warnings_state/restore_warnings_state (e.g. just
        # warnings.resetwarnings()) , but it is difficult to test more.
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", DeprecationWarning)

            self.save_warnings_state()

            class MyWarning(Warning):
                pass

            # Add a filter that causes an exception to be thrown, so we can catch it
            warnings.simplefilter("error", MyWarning)
            self.assertRaises(Warning, lambda: warnings.warn("warn", MyWarning))

            # Now restore.
            self.restore_warnings_state()
            # After restoring, we shouldn't get an exception. But we don't want a
            # warning printed either, so we have to silence the warning.
            warnings.simplefilter("ignore", MyWarning)
            warnings.warn("warn", MyWarning)

            # Remove the filter we just added.
            self.restore_warnings_state()


class HTMLEqualTests(TestCase):
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
        parse_html('<script>var a = "<p" + ">";</script>');
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
        self_closing_tags = ('br' , 'hr', 'input', 'img', 'meta', 'spacer',
            'link', 'frame', 'base', 'col')
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
            <label for="id_first_name">First name:</label></th><td><input type="text" name="first_name" value="John" id="id_first_name" />
        </td></tr>
        <tr><th>
            <label for="id_last_name">Last name:</label></th><td><input type="text" name="last_name" value="Lennon" id="id_last_name" />
        </td></tr>
        <tr><th>
            <label for="id_birthday">Birthday:</label></th><td><input type="text" name="birthday" value="1940-10-9" id="id_birthday" />
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
        self.assertTrue(dom1 in dom2)
        self.assertTrue(dom2 in dom1)

        dom2 = parse_html('<div><p>foo</p></div>')
        self.assertTrue(dom1 in dom2)
        self.assertTrue(dom2 not in dom1)

        self.assertFalse('<p>foo</p>' in dom2)
        self.assertTrue('foo' in dom2)

        # when a root element is used ...
        dom1 = parse_html('<p>foo</p><p>bar</p>')
        dom2 = parse_html('<p>foo</p><p>bar</p>')
        self.assertTrue(dom1 in dom2)
        dom1 = parse_html('<p>foo</p>')
        self.assertTrue(dom1 in dom2)
        dom1 = parse_html('<p>bar</p>')
        self.assertTrue(dom1 in dom2)

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

    def test_parsing_errors(self):
        with self.assertRaises(AssertionError):
            self.assertHTMLEqual('<p>', '')
        with self.assertRaises(AssertionError):
            self.assertHTMLEqual('', '<p>')
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
        self.assertContains(response, '<p class="help">Some help text for the title (with unicode ŠĐĆŽćžšđ)</p>', html=True)


class XMLEqualTests(TestCase):
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


class SkippingExtraTests(TestCase):
    fixtures = ['should_not_be_loaded.json']

    # HACK: This depends on internals of our TestCase subclasses
    def __call__(self, result=None):
        # Detect fixture loading by counting SQL queries, should be zero
        with self.assertNumQueries(0):
            super(SkippingExtraTests, self).__call__(result)

    @skip("Fixture loading should not be performed for skipped tests.")
    def test_fixtures_are_skipped(self):
        pass


class AssertRaisesMsgTest(SimpleTestCase):

    def test_special_re_chars(self):
        """assertRaisesMessage shouldn't interpret RE special chars."""
        def func1():
            raise ValueError("[.*x+]y?")
        self.assertRaisesMessage(ValueError, "[.*x+]y?", func1)


class AssertFieldOutputTests(SimpleTestCase):

    def test_assert_field_output(self):
        error_invalid = ['Enter a valid email address.']
        self.assertFieldOutput(EmailField, {'a@a.com': 'a@a.com'}, {'aaa': error_invalid})
        self.assertRaises(AssertionError, self.assertFieldOutput, EmailField, {'a@a.com': 'a@a.com'}, {'aaa': error_invalid + ['Another error']})
        self.assertRaises(AssertionError, self.assertFieldOutput, EmailField, {'a@a.com': 'Wrong output'}, {'aaa': error_invalid})
        self.assertRaises(AssertionError, self.assertFieldOutput, EmailField, {'a@a.com': 'a@a.com'}, {'aaa': ['Come on, gimme some well formatted data, dude.']})

    def test_custom_required_message(self):
        class MyCustomField(IntegerField):
            default_error_messages = {
                'required': 'This is really required.',
            }
        self.assertFieldOutput(MyCustomField, {}, {}, empty_value=None)


class DoctestNormalizerTest(IgnorePendingDeprecationWarningsMixin, SimpleTestCase):

    def test_normalizer(self):
        from django.test.simple import make_doctest
        suite = make_doctest("test_utils.doctest_output")
        failures = unittest.TextTestRunner(stream=six.StringIO()).run(suite)
        self.assertEqual(failures.failures, [])
