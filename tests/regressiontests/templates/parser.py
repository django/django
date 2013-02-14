"""
Testing some internals of the template processing. These are *not* examples to be copied in user code.
"""
from __future__ import unicode_literals

from django.template import (TokenParser, FilterExpression, Parser, Variable,
    Template, TemplateSyntaxError)
from django.test.utils import override_settings
from django.utils.unittest import TestCase
from django.utils import six


class ParserTests(TestCase):
    def test_token_parsing(self):
        # Tests for TokenParser behavior in the face of quoted strings with
        # spaces.

        p = TokenParser("tag thevar|filter sometag")
        self.assertEqual(p.tagname, "tag")
        self.assertEqual(p.value(), "thevar|filter")
        self.assertTrue(p.more())
        self.assertEqual(p.tag(), "sometag")
        self.assertFalse(p.more())

        p = TokenParser('tag "a value"|filter sometag')
        self.assertEqual(p.tagname, "tag")
        self.assertEqual(p.value(), '"a value"|filter')
        self.assertTrue(p.more())
        self.assertEqual(p.tag(), "sometag")
        self.assertFalse(p.more())

        p = TokenParser("tag 'a value'|filter sometag")
        self.assertEqual(p.tagname, "tag")
        self.assertEqual(p.value(), "'a value'|filter")
        self.assertTrue(p.more())
        self.assertEqual(p.tag(), "sometag")
        self.assertFalse(p.more())

    def test_filter_parsing(self):
        c = {"article": {"section": "News"}}
        p = Parser("")

        def fe_test(s, val):
            self.assertEqual(FilterExpression(s, p).resolve(c), val)

        fe_test("article.section", "News")
        fe_test("article.section|upper", "NEWS")
        fe_test('"News"', "News")
        fe_test("'News'", "News")
        fe_test(r'"Some \"Good\" News"', 'Some "Good" News')
        fe_test(r'"Some \"Good\" News"', 'Some "Good" News')
        fe_test(r"'Some \'Bad\' News'", "Some 'Bad' News")

        fe = FilterExpression(r'"Some \"Good\" News"', p)
        self.assertEqual(fe.filters, [])
        self.assertEqual(fe.var, 'Some "Good" News')

        # Filtered variables should reject access of attributes beginning with
        # underscores.
        self.assertRaises(TemplateSyntaxError,
            FilterExpression, "article._hidden|upper", p
        )

    def test_variable_parsing(self):
        c = {"article": {"section": "News"}}
        self.assertEqual(Variable("article.section").resolve(c), "News")
        self.assertEqual(Variable('"News"').resolve(c), "News")
        self.assertEqual(Variable("'News'").resolve(c), "News")

        # Translated strings are handled correctly.
        self.assertEqual(Variable("_(article.section)").resolve(c), "News")
        self.assertEqual(Variable('_("Good News")').resolve(c), "Good News")
        self.assertEqual(Variable("_('Better News')").resolve(c), "Better News")

        # Escaped quotes work correctly as well.
        self.assertEqual(
            Variable(r'"Some \"Good\" News"').resolve(c), 'Some "Good" News'
        )
        self.assertEqual(
            Variable(r"'Some \'Better\' News'").resolve(c), "Some 'Better' News"
        )

        # Variables should reject access of attributes beginning with
        # underscores.
        self.assertRaises(TemplateSyntaxError,
            Variable, "article._hidden"
        )

    @override_settings(DEBUG=True, TEMPLATE_DEBUG=True)
    def test_compile_filter_error(self):
        # regression test for #19819
        msg = "Could not parse the remainder: '@bar' from 'foo@bar'"
        with six.assertRaisesRegex(self, TemplateSyntaxError, msg) as cm:
            Template("{% if 1 %}{{ foo@bar }}{% endif %}")
        self.assertEqual(cm.exception.django_template_source[1], (10, 23))
