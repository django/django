# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.core.files.uploadedfile import SimpleUploadedFile
from django.forms import (
    BooleanField, CharField, ChoiceField, DateField, DateTimeField,
    DecimalField, EmailField, FileField, FloatField, Form,
    GenericIPAddressField, IntegerField, IPAddressField, ModelChoiceField,
    ModelMultipleChoiceField, MultipleChoiceField, RegexField,
    SplitDateTimeField, TimeField, URLField, ValidationError, utils,
)
from django.test import TestCase, ignore_warnings
from django.utils.deprecation import RemovedInDjango19Warning
from django.utils.encoding import python_2_unicode_compatible
from django.utils.safestring import mark_safe


class AssertFormErrorsMixin(object):
    def assertFormErrors(self, expected, the_callable, *args, **kwargs):
        try:
            the_callable(*args, **kwargs)
            self.fail("Testing the 'clean' method on %s failed to raise a ValidationError.")
        except ValidationError as e:
            self.assertEqual(e.messages, expected)


class FormsErrorMessagesTestCase(TestCase, AssertFormErrorsMixin):
    def test_charfield(self):
        e = {
            'required': 'REQUIRED',
            'min_length': 'LENGTH %(show_value)s, MIN LENGTH %(limit_value)s',
            'max_length': 'LENGTH %(show_value)s, MAX LENGTH %(limit_value)s',
        }
        f = CharField(min_length=5, max_length=10, error_messages=e)
        self.assertFormErrors(['REQUIRED'], f.clean, '')
        self.assertFormErrors(['LENGTH 4, MIN LENGTH 5'], f.clean, '1234')
        self.assertFormErrors(['LENGTH 11, MAX LENGTH 10'], f.clean, '12345678901')

    def test_integerfield(self):
        e = {
            'required': 'REQUIRED',
            'invalid': 'INVALID',
            'min_value': 'MIN VALUE IS %(limit_value)s',
            'max_value': 'MAX VALUE IS %(limit_value)s',
        }
        f = IntegerField(min_value=5, max_value=10, error_messages=e)
        self.assertFormErrors(['REQUIRED'], f.clean, '')
        self.assertFormErrors(['INVALID'], f.clean, 'abc')
        self.assertFormErrors(['MIN VALUE IS 5'], f.clean, '4')
        self.assertFormErrors(['MAX VALUE IS 10'], f.clean, '11')

    def test_floatfield(self):
        e = {
            'required': 'REQUIRED',
            'invalid': 'INVALID',
            'min_value': 'MIN VALUE IS %(limit_value)s',
            'max_value': 'MAX VALUE IS %(limit_value)s',
        }
        f = FloatField(min_value=5, max_value=10, error_messages=e)
        self.assertFormErrors(['REQUIRED'], f.clean, '')
        self.assertFormErrors(['INVALID'], f.clean, 'abc')
        self.assertFormErrors(['MIN VALUE IS 5'], f.clean, '4')
        self.assertFormErrors(['MAX VALUE IS 10'], f.clean, '11')

    def test_decimalfield(self):
        e = {
            'required': 'REQUIRED',
            'invalid': 'INVALID',
            'min_value': 'MIN VALUE IS %(limit_value)s',
            'max_value': 'MAX VALUE IS %(limit_value)s',
            'max_digits': 'MAX DIGITS IS %(max)s',
            'max_decimal_places': 'MAX DP IS %(max)s',
            'max_whole_digits': 'MAX DIGITS BEFORE DP IS %(max)s',
        }
        f = DecimalField(min_value=5, max_value=10, error_messages=e)
        self.assertFormErrors(['REQUIRED'], f.clean, '')
        self.assertFormErrors(['INVALID'], f.clean, 'abc')
        self.assertFormErrors(['MIN VALUE IS 5'], f.clean, '4')
        self.assertFormErrors(['MAX VALUE IS 10'], f.clean, '11')

        f2 = DecimalField(max_digits=4, decimal_places=2, error_messages=e)
        self.assertFormErrors(['MAX DIGITS IS 4'], f2.clean, '123.45')
        self.assertFormErrors(['MAX DP IS 2'], f2.clean, '1.234')
        self.assertFormErrors(['MAX DIGITS BEFORE DP IS 2'], f2.clean, '123.4')

    def test_datefield(self):
        e = {
            'required': 'REQUIRED',
            'invalid': 'INVALID',
        }
        f = DateField(error_messages=e)
        self.assertFormErrors(['REQUIRED'], f.clean, '')
        self.assertFormErrors(['INVALID'], f.clean, 'abc')

    def test_timefield(self):
        e = {
            'required': 'REQUIRED',
            'invalid': 'INVALID',
        }
        f = TimeField(error_messages=e)
        self.assertFormErrors(['REQUIRED'], f.clean, '')
        self.assertFormErrors(['INVALID'], f.clean, 'abc')

    def test_datetimefield(self):
        e = {
            'required': 'REQUIRED',
            'invalid': 'INVALID',
        }
        f = DateTimeField(error_messages=e)
        self.assertFormErrors(['REQUIRED'], f.clean, '')
        self.assertFormErrors(['INVALID'], f.clean, 'abc')

    def test_regexfield(self):
        e = {
            'required': 'REQUIRED',
            'invalid': 'INVALID',
            'min_length': 'LENGTH %(show_value)s, MIN LENGTH %(limit_value)s',
            'max_length': 'LENGTH %(show_value)s, MAX LENGTH %(limit_value)s',
        }
        f = RegexField(r'^[0-9]+$', min_length=5, max_length=10, error_messages=e)
        self.assertFormErrors(['REQUIRED'], f.clean, '')
        self.assertFormErrors(['INVALID'], f.clean, 'abcde')
        self.assertFormErrors(['LENGTH 4, MIN LENGTH 5'], f.clean, '1234')
        self.assertFormErrors(['LENGTH 11, MAX LENGTH 10'], f.clean, '12345678901')

    def test_emailfield(self):
        e = {
            'required': 'REQUIRED',
            'invalid': 'INVALID',
            'min_length': 'LENGTH %(show_value)s, MIN LENGTH %(limit_value)s',
            'max_length': 'LENGTH %(show_value)s, MAX LENGTH %(limit_value)s',
        }
        f = EmailField(min_length=8, max_length=10, error_messages=e)
        self.assertFormErrors(['REQUIRED'], f.clean, '')
        self.assertFormErrors(['INVALID'], f.clean, 'abcdefgh')
        self.assertFormErrors(['LENGTH 7, MIN LENGTH 8'], f.clean, 'a@b.com')
        self.assertFormErrors(['LENGTH 11, MAX LENGTH 10'], f.clean, 'aye@bee.com')

    def test_filefield(self):
        e = {
            'required': 'REQUIRED',
            'invalid': 'INVALID',
            'missing': 'MISSING',
            'empty': 'EMPTY FILE',
        }
        f = FileField(error_messages=e)
        self.assertFormErrors(['REQUIRED'], f.clean, '')
        self.assertFormErrors(['INVALID'], f.clean, 'abc')
        self.assertFormErrors(['EMPTY FILE'], f.clean, SimpleUploadedFile('name', None))
        self.assertFormErrors(['EMPTY FILE'], f.clean, SimpleUploadedFile('name', ''))

    def test_urlfield(self):
        e = {
            'required': 'REQUIRED',
            'invalid': 'INVALID',
            'max_length': '"%(value)s" has more than %(limit_value)d characters.',
        }
        f = URLField(error_messages=e, max_length=17)
        self.assertFormErrors(['REQUIRED'], f.clean, '')
        self.assertFormErrors(['INVALID'], f.clean, 'abc.c')
        self.assertFormErrors(['"http://djangoproject.com" has more than 17 characters.'], f.clean, 'djangoproject.com')

    def test_booleanfield(self):
        e = {
            'required': 'REQUIRED',
        }
        f = BooleanField(error_messages=e)
        self.assertFormErrors(['REQUIRED'], f.clean, '')

    def test_choicefield(self):
        e = {
            'required': 'REQUIRED',
            'invalid_choice': '%(value)s IS INVALID CHOICE',
        }
        f = ChoiceField(choices=[('a', 'aye')], error_messages=e)
        self.assertFormErrors(['REQUIRED'], f.clean, '')
        self.assertFormErrors(['b IS INVALID CHOICE'], f.clean, 'b')

    def test_multiplechoicefield(self):
        e = {
            'required': 'REQUIRED',
            'invalid_choice': '%(value)s IS INVALID CHOICE',
            'invalid_list': 'NOT A LIST',
        }
        f = MultipleChoiceField(choices=[('a', 'aye')], error_messages=e)
        self.assertFormErrors(['REQUIRED'], f.clean, '')
        self.assertFormErrors(['NOT A LIST'], f.clean, 'b')
        self.assertFormErrors(['b IS INVALID CHOICE'], f.clean, ['b'])

    def test_splitdatetimefield(self):
        e = {
            'required': 'REQUIRED',
            'invalid_date': 'INVALID DATE',
            'invalid_time': 'INVALID TIME',
        }
        f = SplitDateTimeField(error_messages=e)
        self.assertFormErrors(['REQUIRED'], f.clean, '')
        self.assertFormErrors(['INVALID DATE', 'INVALID TIME'], f.clean, ['a', 'b'])

    @ignore_warnings(category=RemovedInDjango19Warning)
    def test_ipaddressfield(self):
        e = {
            'required': 'REQUIRED',
            'invalid': 'INVALID IP ADDRESS',
        }
        f = IPAddressField(error_messages=e)
        self.assertFormErrors(['REQUIRED'], f.clean, '')
        self.assertFormErrors(['INVALID IP ADDRESS'], f.clean, '127.0.0')

    def test_generic_ipaddressfield(self):
        e = {
            'required': 'REQUIRED',
            'invalid': 'INVALID IP ADDRESS',
        }
        f = GenericIPAddressField(error_messages=e)
        self.assertFormErrors(['REQUIRED'], f.clean, '')
        self.assertFormErrors(['INVALID IP ADDRESS'], f.clean, '127.0.0')

    def test_subclassing_errorlist(self):
        class TestForm(Form):
            first_name = CharField()
            last_name = CharField()
            birthday = DateField()

            def clean(self):
                raise ValidationError("I like to be awkward.")

        @python_2_unicode_compatible
        class CustomErrorList(utils.ErrorList):
            def __str__(self):
                return self.as_divs()

            def as_divs(self):
                if not self:
                    return ''
                return mark_safe('<div class="error">%s</div>' % ''.join('<p>%s</p>' % e for e in self))

        # This form should print errors the default way.
        form1 = TestForm({'first_name': 'John'})
        self.assertHTMLEqual(str(form1['last_name'].errors), '<ul class="errorlist"><li>This field is required.</li></ul>')
        self.assertHTMLEqual(str(form1.errors['__all__']), '<ul class="errorlist nonfield"><li>I like to be awkward.</li></ul>')

        # This one should wrap error groups in the customized way.
        form2 = TestForm({'first_name': 'John'}, error_class=CustomErrorList)
        self.assertHTMLEqual(str(form2['last_name'].errors), '<div class="error"><p>This field is required.</p></div>')
        self.assertHTMLEqual(str(form2.errors['__all__']), '<div class="error"><p>I like to be awkward.</p></div>')


class ModelChoiceFieldErrorMessagesTestCase(TestCase, AssertFormErrorsMixin):
    def test_modelchoicefield(self):
        # Create choices for the model choice field tests below.
        from forms_tests.models import ChoiceModel
        ChoiceModel.objects.create(pk=1, name='a')
        ChoiceModel.objects.create(pk=2, name='b')
        ChoiceModel.objects.create(pk=3, name='c')

        # ModelChoiceField
        e = {
            'required': 'REQUIRED',
            'invalid_choice': 'INVALID CHOICE',
        }
        f = ModelChoiceField(queryset=ChoiceModel.objects.all(), error_messages=e)
        self.assertFormErrors(['REQUIRED'], f.clean, '')
        self.assertFormErrors(['INVALID CHOICE'], f.clean, '4')

        # ModelMultipleChoiceField
        e = {
            'required': 'REQUIRED',
            'invalid_choice': '%(value)s IS INVALID CHOICE',
            'list': 'NOT A LIST OF VALUES',
        }
        f = ModelMultipleChoiceField(queryset=ChoiceModel.objects.all(), error_messages=e)
        self.assertFormErrors(['REQUIRED'], f.clean, '')
        self.assertFormErrors(['NOT A LIST OF VALUES'], f.clean, '3')
        self.assertFormErrors(['4 IS INVALID CHOICE'], f.clean, ['4'])
