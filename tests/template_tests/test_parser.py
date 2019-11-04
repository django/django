"""
Testing some internals of the template processing. These are *not* examples to be copied in user code.
"""
from django.template import Library, TemplateSyntaxError
from django.template.base import (
    FilterExpression, Parser, Token, TokenType, Variable,
)
from django.template.defaultfilters import register as filter_library
from django.test import SimpleTestCase


class ParserTests(SimpleTestCase):

    def test_token_smart_split(self):
        """
        #7027 -- _() syntax should work with spaces
        """
        token = Token(TokenType.BLOCK, 'sometag _("Page not found") value|yesno:_("yes,no")')
        split = token.split_contents()
        self.assertEqual(split, ["sometag", '_("Page not found")', 'value|yesno:_("yes,no")'])

    def test_filter_parsing(self):
        c = {"article": {"section": "News"}}
        p = Parser("", builtins=[filter_library])

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
        msg = "Variables and attributes may not begin with underscores: 'article._hidden'"
        with self.assertRaisesMessage(TemplateSyntaxError, msg):
            FilterExpression("article._hidden|upper", p)

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
        msg = "Variables and attributes may not begin with underscores: 'article._hidden'"
        with self.assertRaisesMessage(TemplateSyntaxError, msg):
            Variable("article._hidden")

        # Variables should raise on non string type
        with self.assertRaisesMessage(TypeError, "Variable must be a string or number, got <class 'dict'>"):
            Variable({})

    def test_filter_args_count(self):
        parser = Parser("")
        register = Library()

        @register.filter
        def no_arguments(value):
            pass

        @register.filter
        def one_argument(value, arg):
            pass

        @register.filter
        def one_opt_argument(value, arg=False):
            pass

        @register.filter
        def two_arguments(value, arg, arg2):
            pass

        @register.filter
        def two_one_opt_arg(value, arg, arg2=False):
            pass
        parser.add_library(register)
        for expr in (
                '1|no_arguments:"1"',
                '1|two_arguments',
                '1|two_arguments:"1"',
                '1|two_one_opt_arg',
        ):
            with self.assertRaises(TemplateSyntaxError):
                FilterExpression(expr, parser)
        for expr in (
                # Correct number of arguments
                '1|no_arguments',
                '1|one_argument:"1"',
                # One optional
                '1|one_opt_argument',
                '1|one_opt_argument:"1"',
                # Not supplying all
                '1|two_one_opt_arg:"1"',
        ):
            FilterExpression(expr, parser)
