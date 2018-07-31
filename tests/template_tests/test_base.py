from django.template import Context, Template, VariableDoesNotExist
from django.test import SimpleTestCase
from django.utils.translation import gettext_lazy


class TemplateTests(SimpleTestCase):
    def test_lazy_template_string(self):
        template_string = gettext_lazy('lazy string')
        self.assertEqual(Template(template_string).render(Context()), template_string)


class VariableDoesNotExistTests(SimpleTestCase):
    def test_str(self):
        exc = VariableDoesNotExist(msg='Failed lookup in %r', params=({'foo': 'bar'},))
        self.assertEqual(str(exc), "Failed lookup in {'foo': 'bar'}")
