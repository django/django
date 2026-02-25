from django.template import Context, Template, TemplateSyntaxError
from django.test import TestCase


class CSPNonceNodeTests(TestCase):

    def test_with_context(self):
        context = Context({"csp_nonce": "testNonce123"})
        self.assertHTMLEqual(
            Template("<script {% csp_nonce %}></script>").render(context),
            '<script nonce="testNonce123"></script>',
        )

    def test_without_context(self):
        context = Context({})
        self.assertHTMLEqual(
            Template("<script {% csp_nonce %}></script>").render(context),
            "<script></script>",
        )

    def test_variable_does_not_exist(self):
        context = Context({"csp_nonce": 12345})
        self.assertRaises(
            ValueError,
            lambda: Template("<script {% csp_nonce doesNotExist %}></script>").render(
                context
            ),
        )

    def test_invalid_type(self):
        context = Context({"csp_nonce": 12345, "notAFormMedia": "sth. else"})
        self.assertRaises(
            TypeError,
            lambda: Template("<script {% csp_nonce notAFormMedia %}></script>").render(
                context
            ),
        )

    def test_too_many_arguments(self):
        self.assertRaises(
            TemplateSyntaxError,
            lambda: Template("<script {% csp_nonce a b %}></script>").render(
                Context({})
            ),
        )
