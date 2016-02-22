import warnings

from django.http import HttpRequest
from django.template import Template
from django.template.response import TemplateResponse
from django.test import SimpleTestCase


class MyTemplateResponse(TemplateResponse):
    def resolve_template(self, template_name):
        return Template(template_name)


class DeprecationTests(SimpleTestCase):

    def test_template_response(self):
        msg = (
            "TemplateResponse's template argument cannot be a "
            "django.template.Template anymore. It may be a backend-specific "
            "template like those created by get_template()."
        )
        with warnings.catch_warnings(record=True) as warns:
            warnings.simplefilter('always')
            response = TemplateResponse(HttpRequest(), Template('foo'))
        response.render()
        self.assertEqual(response.content, b'foo')
        self.assertEqual(len(warns), 1)
        self.assertEqual(str(warns[0].message), msg)

    def test_custom_template_response(self):
        response = MyTemplateResponse(HttpRequest(), 'baz')
        msg = (
            "MyTemplateResponse.resolve_template() must return a "
            "backend-specific template like those created by get_template(), "
            "not a Template."
        )
        with warnings.catch_warnings(record=True) as warns:
            warnings.simplefilter('always')
            response.render()
        self.assertEqual(response.content, b'baz')
        self.assertEqual(len(warns), 1)
        self.assertEqual(str(warns[0].message), msg)
