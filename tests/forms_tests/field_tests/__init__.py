"""
##########
# Fields #
##########

Each Field class does some sort of validation. Each Field has a clean() method,
which either raises django.forms.ValidationError or returns the "clean"
data -- usually a Unicode object, but, in some rare cases, a list.

Each Field's __init__() takes at least these parameters:
    required -- Boolean that specifies whether the field is required.
                True by default.
    widget -- A Widget class, or instance of a Widget class, that should be
              used for this Field when displaying it. Each Field has a default
              Widget that it'll use if you don't specify this. In most cases,
              the default widget is TextInput.
    label -- A verbose name for this field, for use in displaying this field in
             a form. By default, Django will use a "pretty" version of the form
             field name, if the Field is part of a Form.
    initial -- A value to use in this Field's initial display. This value is
               *not* used as a fallback if data isn't given.

Other than that, the Field subclasses have class-specific options for
__init__(). For example, CharField has a max_length option.
"""

from django.forms import Form


class FormFieldAssertionsMixin(object):

    def assertWidgetRendersTo(self, field, to):
        class _Form(Form):
            f = field
        self.assertHTMLEqual(str(_Form()['f']), to)
