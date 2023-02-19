from django import forms


class FormFieldAssertionsMixin:
    def assertWidgetRendersTo(self, field, to):
        class Form(forms.Form):
            f = field

        self.assertHTMLEqual(str(Form()["f"].widget), to)
