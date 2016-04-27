from django import forms


class FormFieldAssertionsMixin(object):

    def assertWidgetRendersTo(self, field, to):
        class Form(forms.Form):
            f = field
        self.assertHTMLEqual(str(Form()['f']), to)
