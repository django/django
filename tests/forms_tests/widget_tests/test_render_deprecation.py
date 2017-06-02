from django import forms
from django.test import SimpleTestCase
from django.utils.deprecation import RemovedInDjango21Warning


class RenderDeprecationTests(SimpleTestCase):
    def test_custom_widget_renderer_warning(self):
        class CustomWidget1(forms.TextInput):
            def render(self, name, value, attrs=None, renderer=None):
                return super(CustomWidget1, self).render(name, value, attrs, renderer)

        class CustomWidget2(forms.TextInput):
            def render(self, *args, **kwargs):
                return super(CustomWidget2, self).render(*args, **kwargs)

        class CustomWidget3(forms.TextInput):
            def render(self, name, value, attrs=None):
                return super(CustomWidget3, self).render(name, value, attrs)

        class MyForm(forms.Form):
            foo = forms.CharField(widget=CustomWidget1)
            bar = forms.CharField(widget=CustomWidget2)
            baz = forms.CharField(widget=CustomWidget3)

        form = MyForm()
        str(form['foo'])  # No warning.
        str(form['bar'])  # No warning.
        msg = "Add the `renderer` argument to the render() method of <class "
        with self.assertRaisesMessage(RemovedInDjango21Warning, msg):
            str(form['baz'])
