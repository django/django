# -*- coding: utf-8 -*-
import datetime
import time
import unittest
from django.conf import settings
from django.forms import *
from django.forms.extras import SelectDateWidget
from django.forms.util import ErrorList
from django.utils import translation
from django.utils.encoding import force_unicode
from django.utils.encoding import smart_unicode
from error_messages import AssertFormErrorsMixin

class GetDate(Form):
    mydate = DateField(widget=SelectDateWidget)

class FormsExtraTestCase(unittest.TestCase, AssertFormErrorsMixin):
    ###############
    # Extra stuff #
    ###############

    # The forms library comes with some extra, higher-level Field and Widget
    def test_selectdate(self):
        w = SelectDateWidget(years=('2007','2008','2009','2010','2011','2012','2013','2014','2015','2016'))
        self.assertEqual(w.render('mydate', ''), """<select name="mydate_month" id="id_mydate_month">
<option value="0">---</option>
<option value="1">January</option>
<option value="2">February</option>
<option value="3">March</option>
<option value="4">April</option>
<option value="5">May</option>
<option value="6">June</option>
<option value="7">July</option>
<option value="8">August</option>
<option value="9">September</option>
<option value="10">October</option>
<option value="11">November</option>
<option value="12">December</option>
</select>
<select name="mydate_day" id="id_mydate_day">
<option value="0">---</option>
<option value="1">1</option>
<option value="2">2</option>
<option value="3">3</option>
<option value="4">4</option>
<option value="5">5</option>
<option value="6">6</option>
<option value="7">7</option>
<option value="8">8</option>
<option value="9">9</option>
<option value="10">10</option>
<option value="11">11</option>
<option value="12">12</option>
<option value="13">13</option>
<option value="14">14</option>
<option value="15">15</option>
<option value="16">16</option>
<option value="17">17</option>
<option value="18">18</option>
<option value="19">19</option>
<option value="20">20</option>
<option value="21">21</option>
<option value="22">22</option>
<option value="23">23</option>
<option value="24">24</option>
<option value="25">25</option>
<option value="26">26</option>
<option value="27">27</option>
<option value="28">28</option>
<option value="29">29</option>
<option value="30">30</option>
<option value="31">31</option>
</select>
<select name="mydate_year" id="id_mydate_year">
<option value="0">---</option>
<option value="2007">2007</option>
<option value="2008">2008</option>
<option value="2009">2009</option>
<option value="2010">2010</option>
<option value="2011">2011</option>
<option value="2012">2012</option>
<option value="2013">2013</option>
<option value="2014">2014</option>
<option value="2015">2015</option>
<option value="2016">2016</option>
</select>""")
        self.assertEqual(w.render('mydate', None), w.render('mydate', ''))

        self.assertEqual(w.render('mydate', '2010-04-15'), """<select name="mydate_month" id="id_mydate_month">
<option value="1">January</option>
<option value="2">February</option>
<option value="3">March</option>
<option value="4" selected="selected">April</option>
<option value="5">May</option>
<option value="6">June</option>
<option value="7">July</option>
<option value="8">August</option>
<option value="9">September</option>
<option value="10">October</option>
<option value="11">November</option>
<option value="12">December</option>
</select>
<select name="mydate_day" id="id_mydate_day">
<option value="1">1</option>
<option value="2">2</option>
<option value="3">3</option>
<option value="4">4</option>
<option value="5">5</option>
<option value="6">6</option>
<option value="7">7</option>
<option value="8">8</option>
<option value="9">9</option>
<option value="10">10</option>
<option value="11">11</option>
<option value="12">12</option>
<option value="13">13</option>
<option value="14">14</option>
<option value="15" selected="selected">15</option>
<option value="16">16</option>
<option value="17">17</option>
<option value="18">18</option>
<option value="19">19</option>
<option value="20">20</option>
<option value="21">21</option>
<option value="22">22</option>
<option value="23">23</option>
<option value="24">24</option>
<option value="25">25</option>
<option value="26">26</option>
<option value="27">27</option>
<option value="28">28</option>
<option value="29">29</option>
<option value="30">30</option>
<option value="31">31</option>
</select>
<select name="mydate_year" id="id_mydate_year">
<option value="2007">2007</option>
<option value="2008">2008</option>
<option value="2009">2009</option>
<option value="2010" selected="selected">2010</option>
<option value="2011">2011</option>
<option value="2012">2012</option>
<option value="2013">2013</option>
<option value="2014">2014</option>
<option value="2015">2015</option>
<option value="2016">2016</option>
</select>""")

        # Accepts a datetime or a string:
        self.assertEqual(w.render('mydate', datetime.date(2010, 4, 15)), w.render('mydate', '2010-04-15'))

        # Invalid dates still render the failed date:
        self.assertEqual(w.render('mydate', '2010-02-31'), """<select name="mydate_month" id="id_mydate_month">
<option value="1">January</option>
<option value="2" selected="selected">February</option>
<option value="3">March</option>
<option value="4">April</option>
<option value="5">May</option>
<option value="6">June</option>
<option value="7">July</option>
<option value="8">August</option>
<option value="9">September</option>
<option value="10">October</option>
<option value="11">November</option>
<option value="12">December</option>
</select>
<select name="mydate_day" id="id_mydate_day">
<option value="1">1</option>
<option value="2">2</option>
<option value="3">3</option>
<option value="4">4</option>
<option value="5">5</option>
<option value="6">6</option>
<option value="7">7</option>
<option value="8">8</option>
<option value="9">9</option>
<option value="10">10</option>
<option value="11">11</option>
<option value="12">12</option>
<option value="13">13</option>
<option value="14">14</option>
<option value="15">15</option>
<option value="16">16</option>
<option value="17">17</option>
<option value="18">18</option>
<option value="19">19</option>
<option value="20">20</option>
<option value="21">21</option>
<option value="22">22</option>
<option value="23">23</option>
<option value="24">24</option>
<option value="25">25</option>
<option value="26">26</option>
<option value="27">27</option>
<option value="28">28</option>
<option value="29">29</option>
<option value="30">30</option>
<option value="31" selected="selected">31</option>
</select>
<select name="mydate_year" id="id_mydate_year">
<option value="2007">2007</option>
<option value="2008">2008</option>
<option value="2009">2009</option>
<option value="2010" selected="selected">2010</option>
<option value="2011">2011</option>
<option value="2012">2012</option>
<option value="2013">2013</option>
<option value="2014">2014</option>
<option value="2015">2015</option>
<option value="2016">2016</option>
</select>""")

        # Using a SelectDateWidget in a form:
        w = SelectDateWidget(years=('2007','2008','2009','2010','2011','2012','2013','2014','2015','2016'), required=False)
        self.assertEqual(w.render('mydate', ''), """<select name="mydate_month" id="id_mydate_month">
<option value="0">---</option>
<option value="1">January</option>
<option value="2">February</option>
<option value="3">March</option>
<option value="4">April</option>
<option value="5">May</option>
<option value="6">June</option>
<option value="7">July</option>
<option value="8">August</option>
<option value="9">September</option>
<option value="10">October</option>
<option value="11">November</option>
<option value="12">December</option>
</select>
<select name="mydate_day" id="id_mydate_day">
<option value="0">---</option>
<option value="1">1</option>
<option value="2">2</option>
<option value="3">3</option>
<option value="4">4</option>
<option value="5">5</option>
<option value="6">6</option>
<option value="7">7</option>
<option value="8">8</option>
<option value="9">9</option>
<option value="10">10</option>
<option value="11">11</option>
<option value="12">12</option>
<option value="13">13</option>
<option value="14">14</option>
<option value="15">15</option>
<option value="16">16</option>
<option value="17">17</option>
<option value="18">18</option>
<option value="19">19</option>
<option value="20">20</option>
<option value="21">21</option>
<option value="22">22</option>
<option value="23">23</option>
<option value="24">24</option>
<option value="25">25</option>
<option value="26">26</option>
<option value="27">27</option>
<option value="28">28</option>
<option value="29">29</option>
<option value="30">30</option>
<option value="31">31</option>
</select>
<select name="mydate_year" id="id_mydate_year">
<option value="0">---</option>
<option value="2007">2007</option>
<option value="2008">2008</option>
<option value="2009">2009</option>
<option value="2010">2010</option>
<option value="2011">2011</option>
<option value="2012">2012</option>
<option value="2013">2013</option>
<option value="2014">2014</option>
<option value="2015">2015</option>
<option value="2016">2016</option>
</select>""")
        self.assertEqual(w.render('mydate', '2010-04-15'), """<select name="mydate_month" id="id_mydate_month">
<option value="0">---</option>
<option value="1">January</option>
<option value="2">February</option>
<option value="3">March</option>
<option value="4" selected="selected">April</option>
<option value="5">May</option>
<option value="6">June</option>
<option value="7">July</option>
<option value="8">August</option>
<option value="9">September</option>
<option value="10">October</option>
<option value="11">November</option>
<option value="12">December</option>
</select>
<select name="mydate_day" id="id_mydate_day">
<option value="0">---</option>
<option value="1">1</option>
<option value="2">2</option>
<option value="3">3</option>
<option value="4">4</option>
<option value="5">5</option>
<option value="6">6</option>
<option value="7">7</option>
<option value="8">8</option>
<option value="9">9</option>
<option value="10">10</option>
<option value="11">11</option>
<option value="12">12</option>
<option value="13">13</option>
<option value="14">14</option>
<option value="15" selected="selected">15</option>
<option value="16">16</option>
<option value="17">17</option>
<option value="18">18</option>
<option value="19">19</option>
<option value="20">20</option>
<option value="21">21</option>
<option value="22">22</option>
<option value="23">23</option>
<option value="24">24</option>
<option value="25">25</option>
<option value="26">26</option>
<option value="27">27</option>
<option value="28">28</option>
<option value="29">29</option>
<option value="30">30</option>
<option value="31">31</option>
</select>
<select name="mydate_year" id="id_mydate_year">
<option value="0">---</option>
<option value="2007">2007</option>
<option value="2008">2008</option>
<option value="2009">2009</option>
<option value="2010" selected="selected">2010</option>
<option value="2011">2011</option>
<option value="2012">2012</option>
<option value="2013">2013</option>
<option value="2014">2014</option>
<option value="2015">2015</option>
<option value="2016">2016</option>
</select>""")

        a = GetDate({'mydate_month':'4', 'mydate_day':'1', 'mydate_year':'2008'})
        self.assertTrue(a.is_valid())
        self.assertEqual(a.cleaned_data['mydate'], datetime.date(2008, 4, 1))

        # As with any widget that implements get_value_from_datadict,
        # we must be prepared to accept the input from the "as_hidden"
        # rendering as well.

        self.assertEqual(a['mydate'].as_hidden(), '<input type="hidden" name="mydate" value="2008-4-1" id="id_mydate" />')

        b = GetDate({'mydate':'2008-4-1'})
        self.assertTrue(b.is_valid())
        self.assertEqual(b.cleaned_data['mydate'], datetime.date(2008, 4, 1))

        # Invalid dates shouldn't be allowed
        c = GetDate({'mydate_month':'2', 'mydate_day':'31', 'mydate_year':'2010'})
        self.assertFalse(c.is_valid())
        self.assertEqual(c.errors, {'mydate': [u'Enter a valid date.']})

        # label tag is correctly associated with month dropdown
        d = GetDate({'mydate_month':'1', 'mydate_day':'1', 'mydate_year':'2010'})
        self.assertTrue('<label for="id_mydate_month">' in d.as_p())

    def test_multiwidget(self):
        # MultiWidget and MultiValueField #############################################
        # MultiWidgets are widgets composed of other widgets. They are usually
        # combined with MultiValueFields - a field that is composed of other fields.
        # MulitWidgets can themselved be composed of other MultiWidgets.
        # SplitDateTimeWidget is one example of a MultiWidget.

        class ComplexMultiWidget(MultiWidget):
            def __init__(self, attrs=None):
                widgets = (
                    TextInput(),
                    SelectMultiple(choices=(('J', 'John'), ('P', 'Paul'), ('G', 'George'), ('R', 'Ringo'))),
                    SplitDateTimeWidget(),
                )
                super(ComplexMultiWidget, self).__init__(widgets, attrs)

            def decompress(self, value):
                if value:
                    data = value.split(',')
                    return [data[0], data[1], datetime.datetime(*time.strptime(data[2], "%Y-%m-%d %H:%M:%S")[0:6])]
                return [None, None, None]

            def format_output(self, rendered_widgets):
                return u'\n'.join(rendered_widgets)

        w = ComplexMultiWidget()
        self.assertEqual(w.render('name', 'some text,JP,2007-04-25 06:24:00'), """<input type="text" name="name_0" value="some text" />
<select multiple="multiple" name="name_1">
<option value="J" selected="selected">John</option>
<option value="P" selected="selected">Paul</option>
<option value="G">George</option>
<option value="R">Ringo</option>
</select>
<input type="text" name="name_2_0" value="2007-04-25" /><input type="text" name="name_2_1" value="06:24:00" />""")

        class ComplexField(MultiValueField):
            def __init__(self, required=True, widget=None, label=None, initial=None):
                fields = (
                    CharField(),
                    MultipleChoiceField(choices=(('J', 'John'), ('P', 'Paul'), ('G', 'George'), ('R', 'Ringo'))),
                    SplitDateTimeField()
                )
                super(ComplexField, self).__init__(fields, required, widget, label, initial)

            def compress(self, data_list):
                if data_list:
                    return '%s,%s,%s' % (data_list[0],''.join(data_list[1]),data_list[2])
                return None

        f = ComplexField(widget=w)
        self.assertEqual(f.clean(['some text', ['J','P'], ['2007-04-25','6:24:00']]), u'some text,JP,2007-04-25 06:24:00')
        self.assertFormErrors([u'Select a valid choice. X is not one of the available choices.'], f.clean, ['some text',['X'], ['2007-04-25','6:24:00']])

        # If insufficient data is provided, None is substituted
        self.assertFormErrors([u'This field is required.'], f.clean, ['some text',['JP']])

        class ComplexFieldForm(Form):
            field1 = ComplexField(widget=w)

        f = ComplexFieldForm()
        self.assertEqual(f.as_table(), """<tr><th><label for="id_field1_0">Field1:</label></th><td><input type="text" name="field1_0" id="id_field1_0" />
<select multiple="multiple" name="field1_1" id="id_field1_1">
<option value="J">John</option>
<option value="P">Paul</option>
<option value="G">George</option>
<option value="R">Ringo</option>
</select>
<input type="text" name="field1_2_0" id="id_field1_2_0" /><input type="text" name="field1_2_1" id="id_field1_2_1" /></td></tr>""")

        f = ComplexFieldForm({'field1_0':'some text','field1_1':['J','P'], 'field1_2_0':'2007-04-25', 'field1_2_1':'06:24:00'})
        self.assertEqual(f.as_table(), """<tr><th><label for="id_field1_0">Field1:</label></th><td><input type="text" name="field1_0" value="some text" id="id_field1_0" />
<select multiple="multiple" name="field1_1" id="id_field1_1">
<option value="J" selected="selected">John</option>
<option value="P" selected="selected">Paul</option>
<option value="G">George</option>
<option value="R">Ringo</option>
</select>
<input type="text" name="field1_2_0" value="2007-04-25" id="id_field1_2_0" /><input type="text" name="field1_2_1" value="06:24:00" id="id_field1_2_1" /></td></tr>""")

        self.assertEqual(f.cleaned_data['field1'], u'some text,JP,2007-04-25 06:24:00')

    def test_ipaddress(self):
        f = IPAddressField()
        self.assertFormErrors([u'This field is required.'], f.clean, '')
        self.assertFormErrors([u'This field is required.'], f.clean, None)
        self.assertEqual(f.clean('127.0.0.1'), u'127.0.0.1')
        self.assertFormErrors([u'Enter a valid IPv4 address.'], f.clean, 'foo')
        self.assertFormErrors([u'Enter a valid IPv4 address.'], f.clean, '127.0.0.')
        self.assertFormErrors([u'Enter a valid IPv4 address.'], f.clean, '1.2.3.4.5')
        self.assertFormErrors([u'Enter a valid IPv4 address.'], f.clean, '256.125.1.5')

        f = IPAddressField(required=False)
        self.assertEqual(f.clean(''), u'')
        self.assertEqual(f.clean(None), u'')
        self.assertEqual(f.clean('127.0.0.1'), u'127.0.0.1')
        self.assertFormErrors([u'Enter a valid IPv4 address.'], f.clean, 'foo')
        self.assertFormErrors([u'Enter a valid IPv4 address.'], f.clean, '127.0.0.')
        self.assertFormErrors([u'Enter a valid IPv4 address.'], f.clean, '1.2.3.4.5')
        self.assertFormErrors([u'Enter a valid IPv4 address.'], f.clean, '256.125.1.5')

    def test_smart_unicode(self):
        class Test:
            def __str__(self):
               return 'ŠĐĆŽćžšđ'

        class TestU:
            def __str__(self):
               return 'Foo'
            def __unicode__(self):
               return u'\u0160\u0110\u0106\u017d\u0107\u017e\u0161\u0111'

        self.assertEqual(smart_unicode(Test()), u'\u0160\u0110\u0106\u017d\u0107\u017e\u0161\u0111')
        self.assertEqual(smart_unicode(TestU()), u'\u0160\u0110\u0106\u017d\u0107\u017e\u0161\u0111')
        self.assertEqual(smart_unicode(1), u'1')
        self.assertEqual(smart_unicode('foo'), u'foo')

    def test_accessing_clean(self):
        class UserForm(Form):
            username = CharField(max_length=10)
            password = CharField(widget=PasswordInput)

            def clean(self):
                data = self.cleaned_data

                if not self.errors:
                    data['username'] = data['username'].lower()

                return data

        f = UserForm({'username': 'SirRobin', 'password': 'blue'})
        self.assertTrue(f.is_valid())
        self.assertEqual(f.cleaned_data['username'], u'sirrobin')

    def test_overriding_errorlist(self):
        class DivErrorList(ErrorList):
            def __unicode__(self):
                return self.as_divs()

            def as_divs(self):
                if not self: return u''
                return u'<div class="errorlist">%s</div>' % ''.join([u'<div class="error">%s</div>' % force_unicode(e) for e in self])

        class CommentForm(Form):
            name = CharField(max_length=50, required=False)
            email = EmailField()
            comment = CharField()

        data = dict(email='invalid')
        f = CommentForm(data, auto_id=False, error_class=DivErrorList)
        self.assertEqual(f.as_p(), """<p>Name: <input type="text" name="name" maxlength="50" /></p>
<div class="errorlist"><div class="error">Enter a valid e-mail address.</div></div>
<p>Email: <input type="text" name="email" value="invalid" /></p>
<div class="errorlist"><div class="error">This field is required.</div></div>
<p>Comment: <input type="text" name="comment" /></p>""")

    def test_multipart_encoded_form(self):
        class FormWithoutFile(Form):
            username = CharField()

        class FormWithFile(Form):
            username = CharField()
            file = FileField()

        class FormWithImage(Form):
            image = ImageField()

        self.assertFalse(FormWithoutFile().is_multipart())
        self.assertTrue(FormWithFile().is_multipart())
        self.assertTrue(FormWithImage().is_multipart())


class FormsExtraL10NTestCase(unittest.TestCase):
    def setUp(self):
        super(FormsExtraL10NTestCase, self).setUp()
        self.old_use_l10n = getattr(settings, 'USE_L10N', False)
        settings.USE_L10N = True
        translation.activate('nl')

    def tearDown(self):
        translation.deactivate()
        settings.USE_L10N = self.old_use_l10n
        super(FormsExtraL10NTestCase, self).tearDown()

    def test_l10n(self):
        w = SelectDateWidget(years=('2007','2008','2009','2010','2011','2012','2013','2014','2015','2016'), required=False)
        self.assertEqual(w.value_from_datadict({'date_year': '2010', 'date_month': '8', 'date_day': '13'}, {}, 'date'), '13-08-2010')

        self.assertEqual(w.render('date', '13-08-2010'), """<select name="date_day" id="id_date_day">
<option value="0">---</option>
<option value="1">1</option>
<option value="2">2</option>
<option value="3">3</option>
<option value="4">4</option>
<option value="5">5</option>
<option value="6">6</option>
<option value="7">7</option>
<option value="8">8</option>
<option value="9">9</option>
<option value="10">10</option>
<option value="11">11</option>
<option value="12">12</option>
<option value="13" selected="selected">13</option>
<option value="14">14</option>
<option value="15">15</option>
<option value="16">16</option>
<option value="17">17</option>
<option value="18">18</option>
<option value="19">19</option>
<option value="20">20</option>
<option value="21">21</option>
<option value="22">22</option>
<option value="23">23</option>
<option value="24">24</option>
<option value="25">25</option>
<option value="26">26</option>
<option value="27">27</option>
<option value="28">28</option>
<option value="29">29</option>
<option value="30">30</option>
<option value="31">31</option>
</select>
<select name="date_month" id="id_date_month">
<option value="0">---</option>
<option value="1">januari</option>
<option value="2">februari</option>
<option value="3">maart</option>
<option value="4">april</option>
<option value="5">mei</option>
<option value="6">juni</option>
<option value="7">juli</option>
<option value="8" selected="selected">augustus</option>
<option value="9">september</option>
<option value="10">oktober</option>
<option value="11">november</option>
<option value="12">december</option>
</select>
<select name="date_year" id="id_date_year">
<option value="0">---</option>
<option value="2007">2007</option>
<option value="2008">2008</option>
<option value="2009">2009</option>
<option value="2010" selected="selected">2010</option>
<option value="2011">2011</option>
<option value="2012">2012</option>
<option value="2013">2013</option>
<option value="2014">2014</option>
<option value="2015">2015</option>
<option value="2016">2016</option>
</select>""")

        # Years before 1900 work
        w = SelectDateWidget(years=('1899',))
        self.assertEqual(w.value_from_datadict({'date_year': '1899', 'date_month': '8', 'date_day': '13'}, {}, 'date'), '13-08-1899')

    def test_l10n_invalid_date_in(self):
        # Invalid dates shouldn't be allowed
        a = GetDate({'mydate_month':'2', 'mydate_day':'31', 'mydate_year':'2010'})
        self.assertFalse(a.is_valid())
        # 'Geef een geldige datum op.' = 'Enter a valid date.'
        self.assertEqual(a.errors, {'mydate': [u'Geef een geldige datum op.']})

    def test_form_label_association(self):
        # label tag is correctly associated with first rendered dropdown
        a = GetDate({'mydate_month':'1', 'mydate_day':'1', 'mydate_year':'2010'})
        self.assertTrue('<label for="id_mydate_day">' in a.as_p())
