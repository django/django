from django.template import Context, Template, Variable, VariableDoesNotExist
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


class VariableTests(SimpleTestCase):
    def test_integer_literals(self):
        self.assertEqual(Variable('999999999999999999999999999').literal, 999999999999999999999999999)

    def test_nonliterals(self):
        """Variable names that aren't resolved as literals."""
        var_names = []
        for var in ('inf', 'infinity', 'iNFiniTy', 'nan'):
            var_names.extend((var, '-' + var, '+' + var))
        for var in var_names:
            with self.subTest(var=var):
                self.assertIsNone(Variable(var).literal)
