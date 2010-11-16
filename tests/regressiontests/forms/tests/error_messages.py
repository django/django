# -*- coding: utf-8 -*-
from django.core.files.uploadedfile import SimpleUploadedFile
from django.forms import *
from django.test import TestCase
from django.utils.safestring import mark_safe
from django.utils import unittest

class AssertFormErrorsMixin(object):
    def assertFormErrors(self, expected, the_callable, *args, **kwargs):
        try:
            the_callable(*args, **kwargs)
            self.fail("Testing the 'clean' method on %s failed to raise a ValidationError.")
        except ValidationError, e:
            self.assertEqual(e.messages, expected)


class FormsErrorMessagesTestCase(unittest.TestCase, AssertFormErrorsMixin):
    def test_charfield(self):
        e = {
            'required': 'REQUIRED',
            'min_length': 'LENGTH %(show_value)s, MIN LENGTH %(limit_value)s',
            'max_length': 'LENGTH %(show_value)s, MAX LENGTH %(limit_value)s',
        }
        f = CharField(min_length=5, max_length=10, error_messages=e)
        self.assertFormErrors([u'REQUIRED'], f.clean, '')
        self.assertFormErrors([u'LENGTH 4, MIN LENGTH 5'], f.clean, '1234')
        self.assertFormErrors([u'LENGTH 11, MAX LENGTH 10'], f.clean, '12345678901')

    def test_integerfield(self):
        e = {
            'required': 'REQUIRED',
            'invalid': 'INVALID',
            'min_value': 'MIN VALUE IS %(limit_value)s',
            'max_value': 'MAX VALUE IS %(limit_value)s',
        }
        f = IntegerField(min_value=5, max_value=10, error_messages=e)
        self.assertFormErrors([u'REQUIRED'], f.clean, '')
        self.assertFormErrors([u'INVALID'], f.clean, 'abc')
        self.assertFormErrors([u'MIN VALUE IS 5'], f.clean, '4')
        self.assertFormErrors([u'MAX VALUE IS 10'], f.clean, '11')

    def test_floatfield(self):
        e = {
            'required': 'REQUIRED',
            'invalid': 'INVALID',
            'min_value': 'MIN VALUE IS %(limit_value)s',
            'max_value': 'MAX VALUE IS %(limit_value)s',
        }
        f = FloatField(min_value=5, max_value=10, error_messages=e)
        self.assertFormErrors([u'REQUIRED'], f.clean, '')
        self.assertFormErrors([u'INVALID'], f.clean, 'abc')
        self.assertFormErrors([u'MIN VALUE IS 5'], f.clean, '4')
        self.assertFormErrors([u'MAX VALUE IS 10'], f.clean, '11')

    def test_decimalfield(self):
        e = {
            'required': 'REQUIRED',
            'invalid': 'INVALID',
            'min_value': 'MIN VALUE IS %(limit_value)s',
            'max_value': 'MAX VALUE IS %(limit_value)s',
            'max_digits': 'MAX DIGITS IS %s',
            'max_decimal_places': 'MAX DP IS %s',
            'max_whole_digits': 'MAX DIGITS BEFORE DP IS %s',
        }
        f = DecimalField(min_value=5, max_value=10, error_messages=e)
        self.assertFormErrors([u'REQUIRED'], f.clean, '')
        self.assertFormErrors([u'INVALID'], f.clean, 'abc')
        self.assertFormErrors([u'MIN VALUE IS 5'], f.clean, '4')
        self.assertFormErrors([u'MAX VALUE IS 10'], f.clean, '11')

        f2 = DecimalField(max_digits=4, decimal_places=2, error_messages=e)
        self.assertFormErrors([u'MAX DIGITS IS 4'], f2.clean, '123.45')
        self.assertFormErrors([u'MAX DP IS 2'], f2.clean, '1.234')
        self.assertFormErrors([u'MAX DIGITS BEFORE DP IS 2'], f2.clean, '123.4')

    def test_datefield(self):
        e = {
            'required': 'REQUIRED',
            'invalid': 'INVALID',
        }
        f = DateField(error_messages=e)
        self.assertFormErrors([u'REQUIRED'], f.clean, '')
        self.assertFormErrors([u'INVALID'], f.clean, 'abc')

    def test_timefield(self):
        e = {
            'required': 'REQUIRED',
            'invalid': 'INVALID',
        }
        f = TimeField(error_messages=e)
        self.assertFormErrors([u'REQUIRED'], f.clean, '')
        self.assertFormErrors([u'INVALID'], f.clean, 'abc')

    def test_datetimefield(self):
        e = {
            'required': 'REQUIRED',
            'invalid': 'INVALID',
        }
        f = DateTimeField(error_messages=e)
        self.assertFormErrors([u'REQUIRED'], f.clean, '')
        self.assertFormErrors([u'INVALID'], f.clean, 'abc')

    def test_regexfield(self):
        e = {
            'required': 'REQUIRED',
            'invalid': 'INVALID',
            'min_length': 'LENGTH %(show_value)s, MIN LENGTH %(limit_value)s',
            'max_length': 'LENGTH %(show_value)s, MAX LENGTH %(limit_value)s',
        }
        f = RegexField(r'^\d+$', min_length=5, max_length=10, error_messages=e)
        self.assertFormErrors([u'REQUIRED'], f.clean, '')
        self.assertFormErrors([u'INVALID'], f.clean, 'abcde')
        self.assertFormErrors([u'LENGTH 4, MIN LENGTH 5'], f.clean, '1234')
        self.assertFormErrors([u'LENGTH 11, MAX LENGTH 10'], f.clean, '12345678901')

    def test_emailfield(self):
        e = {
            'required': 'REQUIRED',
            'invalid': 'INVALID',
            'min_length': 'LENGTH %(show_value)s, MIN LENGTH %(limit_value)s',
            'max_length': 'LENGTH %(show_value)s, MAX LENGTH %(limit_value)s',
        }
        f = EmailField(min_length=8, max_length=10, error_messages=e)
        self.assertFormErrors([u'REQUIRED'], f.clean, '')
        self.assertFormErrors([u'INVALID'], f.clean, 'abcdefgh')
        self.assertFormErrors([u'LENGTH 7, MIN LENGTH 8'], f.clean, 'a@b.com')
        self.assertFormErrors([u'LENGTH 11, MAX LENGTH 10'], f.clean, 'aye@bee.com')

    def test_filefield(self):
        e = {
            'required': 'REQUIRED',
            'invalid': 'INVALID',
            'missing': 'MISSING',
            'empty': 'EMPTY FILE',
        }
        f = FileField(error_messages=e)
        self.assertFormErrors([u'REQUIRED'], f.clean, '')
        self.assertFormErrors([u'INVALID'], f.clean, 'abc')
        self.assertFormErrors([u'EMPTY FILE'], f.clean, SimpleUploadedFile('name', None))
        self.assertFormErrors([u'EMPTY FILE'], f.clean, SimpleUploadedFile('name', ''))

    def test_urlfield(self):
        e = {
            'required': 'REQUIRED',
            'invalid': 'INVALID',
            'invalid_link': 'INVALID LINK',
        }
        f = URLField(verify_exists=True, error_messages=e)
        self.assertFormErrors([u'REQUIRED'], f.clean, '')
        self.assertFormErrors([u'INVALID'], f.clean, 'abc.c')
        self.assertFormErrors([u'INVALID LINK'], f.clean, 'http://www.broken.djangoproject.com')

    def test_booleanfield(self):
        e = {
            'required': 'REQUIRED',
        }
        f = BooleanField(error_messages=e)
        self.assertFormErrors([u'REQUIRED'], f.clean, '')

    def test_choicefield(self):
        e = {
            'required': 'REQUIRED',
            'invalid_choice': '%(value)s IS INVALID CHOICE',
        }
        f = ChoiceField(choices=[('a', 'aye')], error_messages=e)
        self.assertFormErrors([u'REQUIRED'], f.clean, '')
        self.assertFormErrors([u'b IS INVALID CHOICE'], f.clean, 'b')

    def test_multiplechoicefield(self):
        e = {
            'required': 'REQUIRED',
            'invalid_choice': '%(value)s IS INVALID CHOICE',
            'invalid_list': 'NOT A LIST',
        }
        f = MultipleChoiceField(choices=[('a', 'aye')], error_messages=e)
        self.assertFormErrors([u'REQUIRED'], f.clean, '')
        self.assertFormErrors([u'NOT A LIST'], f.clean, 'b')
        self.assertFormErrors([u'b IS INVALID CHOICE'], f.clean, ['b'])

    def test_splitdatetimefield(self):
        e = {
            'required': 'REQUIRED',
            'invalid_date': 'INVALID DATE',
            'invalid_time': 'INVALID TIME',
        }
        f = SplitDateTimeField(error_messages=e)
        self.assertFormErrors([u'REQUIRED'], f.clean, '')
        self.assertFormErrors([u'INVALID DATE', u'INVALID TIME'], f.clean, ['a', 'b'])

    def test_ipaddressfield(self):
        e = {
            'required': 'REQUIRED',
            'invalid': 'INVALID IP ADDRESS',
        }
        f = IPAddressField(error_messages=e)
        self.assertFormErrors([u'REQUIRED'], f.clean, '')
        self.assertFormErrors([u'INVALID IP ADDRESS'], f.clean, '127.0.0')

    def test_subclassing_errorlist(self):
        class TestForm(Form):
            first_name = CharField()
            last_name = CharField()
            birthday = DateField()

            def clean(self):
                raise ValidationError("I like to be awkward.")

        class CustomErrorList(util.ErrorList):
            def __unicode__(self):
                return self.as_divs()

            def as_divs(self):
                if not self: return u''
                return mark_safe(u'<div class="error">%s</div>' % ''.join([u'<p>%s</p>' % e for e in self]))

        # This form should print errors the default way.
        form1 = TestForm({'first_name': 'John'})
        self.assertEqual(str(form1['last_name'].errors), '<ul class="errorlist"><li>This field is required.</li></ul>')
        self.assertEqual(str(form1.errors['__all__']), '<ul class="errorlist"><li>I like to be awkward.</li></ul>')

        # This one should wrap error groups in the customized way.
        form2 = TestForm({'first_name': 'John'}, error_class=CustomErrorList)
        self.assertEqual(str(form2['last_name'].errors), '<div class="error"><p>This field is required.</p></div>')
        self.assertEqual(str(form2.errors['__all__']), '<div class="error"><p>I like to be awkward.</p></div>')


class ModelChoiceFieldErrorMessagesTestCase(TestCase, AssertFormErrorsMixin):
    def test_modelchoicefield(self):
        # Create choices for the model choice field tests below.
        from regressiontests.forms.models import ChoiceModel
        c1 = ChoiceModel.objects.create(pk=1, name='a')
        c2 = ChoiceModel.objects.create(pk=2, name='b')
        c3 = ChoiceModel.objects.create(pk=3, name='c')

        # ModelChoiceField
        e = {
            'required': 'REQUIRED',
            'invalid_choice': 'INVALID CHOICE',
        }
        f = ModelChoiceField(queryset=ChoiceModel.objects.all(), error_messages=e)
        self.assertFormErrors([u'REQUIRED'], f.clean, '')
        self.assertFormErrors([u'INVALID CHOICE'], f.clean, '4')

        # ModelMultipleChoiceField
        e = {
            'required': 'REQUIRED',
            'invalid_choice': '%s IS INVALID CHOICE',
            'list': 'NOT A LIST OF VALUES',
        }
        f = ModelMultipleChoiceField(queryset=ChoiceModel.objects.all(), error_messages=e)
        self.assertFormErrors([u'REQUIRED'], f.clean, '')
        self.assertFormErrors([u'NOT A LIST OF VALUES'], f.clean, '3')
        self.assertFormErrors([u'4 IS INVALID CHOICE'], f.clean, ['4'])
