from django.forms import Media
from django.forms.widgets import Script
from django.template import Context, Template
from django.test import SimpleTestCase, override_settings


@override_settings(STATIC_URL="/static/")
class CspNonceTagTests(SimpleTestCase):
    def test_with_nonce_in_context(self):
        t = Template("<script {% csp_nonce_attr %}></script>")
        result = t.render(Context({"csp_nonce": "abc123"}))
        self.assertEqual(result, '<script nonce="abc123"></script>')

    def test_without_csp_nonce_in_context(self):
        t = Template("<script {% csp_nonce_attr %}></script>")
        result = t.render(Context())
        self.assertEqual(result, "<script ></script>")

    def test_with_csp_nonce_none(self):
        t = Template("<script {% csp_nonce_attr %}></script>")
        result = t.render(Context({"csp_nonce": None}))
        self.assertEqual(result, "<script ></script>")

    def test_nonce_is_escaped(self):
        t = Template("<script {% csp_nonce_attr %}></script>")
        result = t.render(Context({"csp_nonce": '<script>"'}))
        self.assertIn("&lt;", result)
        self.assertNotIn("<script>", result)


@override_settings(STATIC_URL="/static/")
class CspNonceTagWithMediaTests(SimpleTestCase):
    def test_with_nonce_in_context(self):
        media = Media(js=["/path/to/js"])
        t = Template("{% csp_nonce_attr media %}")
        result = t.render(Context({"media": media, "csp_nonce": "abc123"}))
        self.assertHTMLEqual(
            result,
            '<script src="/path/to/js" nonce="abc123"></script>',
        )

    def test_without_csp_nonce_in_context(self):
        media = Media(js=["/path/to/js"])
        t = Template("{% csp_nonce_attr media %}")
        result = t.render(Context({"media": media}))
        self.assertHTMLEqual(result, '<script src="/path/to/js"></script>')

    def test_with_csp_nonce_none(self):
        media = Media(js=["/path/to/js"])
        t = Template("{% csp_nonce_attr media %}")
        result = t.render(Context({"media": media, "csp_nonce": None}))
        self.assertHTMLEqual(result, '<script src="/path/to/js"></script>')

    def test_css_and_js(self):
        media = Media(
            css={"all": ["/path/to/css"]},
            js=["/path/to/js"],
        )
        t = Template("{% csp_nonce_attr media %}")
        result = t.render(Context({"media": media, "csp_nonce": "abc123"}))
        self.assertHTMLEqual(
            result,
            '<link href="/path/to/css" media="all" nonce="abc123" rel="stylesheet">\n'
            '<script src="/path/to/js" nonce="abc123"></script>',
        )

    def test_with_script_object(self):
        media = Media(js=[Script("/path/to/js", integrity="sha256-abc")])
        t = Template("{% csp_nonce_attr media %}")
        result = t.render(Context({"media": media, "csp_nonce": "abc123"}))
        self.assertHTMLEqual(
            result,
            '<script src="/path/to/js" integrity="sha256-abc"'
            ' nonce="abc123"></script>',
        )

    def test_output_is_safe(self):
        media = Media(js=["/path/to/js"])
        t = Template("{% csp_nonce_attr media %}")
        result = t.render(Context({"media": media, "csp_nonce": "abc123"}))
        self.assertIn("<script", result)
        self.assertNotIn("&lt;", result)

    def test_script_with_conflicting_nonce_raises(self):
        media = Media(js=[Script("/path/to/js", nonce="static")])
        t = Template("{% csp_nonce_attr media %}")
        msg = "Script has conflicting attributes: nonce"
        with self.assertRaisesMessage(ValueError, msg):
            t.render(Context({"media": media, "csp_nonce": "abc123"}))
