from django.test import SimpleTestCase

from ..utils import setup


class JsonScriptTests(SimpleTestCase):
    @setup({"json-tag01": '{{ value|json_script:"test_id" }}'})
    def test_basic(self):
        output = self.engine.render_to_string(
            "json-tag01", {"value": {"a": "testing\r\njson 'string\" <b>escaping</b>"}}
        )
        self.assertEqual(
            output,
            '<script id="test_id" type="application/json">'
            '{"a":"testing\\r\\njson \'string\\" '
            '\\u003Cb\\u003Eescaping\\u003C/b\\u003E"}'
            "</script>",
        )

    @setup({"json-tag02": "{{ value|json_script }}"})
    def test_without_id(self):
        output = self.engine.render_to_string("json-tag02", {"value": {}})
        self.assertEqual(output, '<script type="application/json">{}</script>')

    @setup({"json-tag03": '{{ val|json_script:"el" }}'})
    def test_non_ascii(self):
        self.assertHTMLEqual(
            self.engine.render_to_string("json-tag03", {"val": {"hello": "привет"}}),
            '<script id="el" type="application/json">{"hello":"привет"}</script>',
        )
