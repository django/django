from django.forms.fields import BooleanField
from django.forms.forms import Form
from django.forms.renderers import DjangoTemplates
from django.template import Context, Template
from django.test import SimpleTestCase


class FormRenderer(DjangoTemplates):
    def get_template(self, template_name):
        return super().get_template('forms_tests/custom_checkbox.html')


class CustomCheckboxTest(SimpleTestCase):
    def test_use_custom_template(self):
        class Subscribe(Form):
            accept = BooleanField()
            default_renderer = FormRenderer

        t = Template('{{ form.accept }}')
        html = t.render(Context({'form': Subscribe()}))
        expected = """
        <label><input type="checkbox" name="accept" required id="id_accept">
        Accept</label>
        """
        self.assertHTMLEqual(html, expected)
