# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import datetime

from django.forms import (
    CharField, DateField, EmailField, FileField, Form, GenericIPAddressField,
    HiddenInput, ImageField, IPAddressField, MultipleChoiceField,
    MultiValueField, MultiWidget, PasswordInput, SelectMultiple, SlugField,
    SplitDateTimeField, SplitDateTimeWidget, TextInput, URLField,
)
from django.forms.extras import SelectDateWidget
from django.forms.utils import ErrorList
from django.test import TestCase, ignore_warnings, override_settings
from django.utils import six, translation
from django.utils.dates import MONTHS_AP
from django.utils.deprecation import RemovedInDjango19Warning
from django.utils.encoding import (
    force_text, python_2_unicode_compatible, smart_text,
)

from .test_error_messages import AssertFormErrorsMixin


class GetDate(Form):
    mydate = DateField(widget=SelectDateWidget)


class GetDateShowHiddenInitial(Form):
    mydate = DateField(widget=SelectDateWidget, show_hidden_initial=True)


class FormsExtraTestCase(TestCase, AssertFormErrorsMixin):
    ###############
    # Extra stuff #
    ###############

    # The forms library comes with some extra, higher-level Field and Widget
    def test_selectdate(self):
        self.maxDiff = None
        w = SelectDateWidget(years=('2007', '2008', '2009', '2010', '2011', '2012', '2013', '2014', '2015', '2016'))

        # Rendering the default state.
        self.assertHTMLEqual(w.render('mydate', ''), """<select name="mydate_month" id="id_mydate_month">
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

        # Rendering the None or '' values should yield the same output.
        self.assertHTMLEqual(w.render('mydate', None), w.render('mydate', ''))

        # Rendering a string value.
        self.assertHTMLEqual(w.render('mydate', '2010-04-15'), """<select name="mydate_month" id="id_mydate_month">
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

        # Rendering a datetime value.
        self.assertHTMLEqual(w.render('mydate', datetime.date(2010, 4, 15)), w.render('mydate', '2010-04-15'))

        # Invalid dates should still render the failed date.
        self.assertHTMLEqual(w.render('mydate', '2010-02-31'), """<select name="mydate_month" id="id_mydate_month">
<option value="0">---</option>
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
<option value="31" selected="selected">31</option>
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

        # Rendering with a custom months dict.
        w = SelectDateWidget(months=MONTHS_AP, years=('2013',))
        self.assertHTMLEqual(w.render('mydate', ''), """<select name="mydate_month" id="id_mydate_month">
<option value="0">---</option>
<option value="1">Jan.</option>
<option value="2">Feb.</option>
<option value="3">March</option>
<option value="4">April</option>
<option value="5">May</option>
<option value="6">June</option>
<option value="7">July</option>
<option value="8">Aug.</option>
<option value="9">Sept.</option>
<option value="10">Oct.</option>
<option value="11">Nov.</option>
<option value="12">Dec.</option>
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
<option value="2013">2013</option>
</select>""")

        a = GetDate({'mydate_month': '4', 'mydate_day': '1', 'mydate_year': '2008'})
        self.assertTrue(a.is_valid())
        self.assertEqual(a.cleaned_data['mydate'], datetime.date(2008, 4, 1))

        # As with any widget that implements get_value_from_datadict,
        # we must be prepared to accept the input from the "as_hidden"
        # rendering as well.

        self.assertHTMLEqual(a['mydate'].as_hidden(), '<input type="hidden" name="mydate" value="2008-4-1" id="id_mydate" />')

        b = GetDate({'mydate': '2008-4-1'})
        self.assertTrue(b.is_valid())
        self.assertEqual(b.cleaned_data['mydate'], datetime.date(2008, 4, 1))

        # Invalid dates shouldn't be allowed
        c = GetDate({'mydate_month': '2', 'mydate_day': '31', 'mydate_year': '2010'})
        self.assertFalse(c.is_valid())
        self.assertEqual(c.errors, {'mydate': ['Enter a valid date.']})

        # label tag is correctly associated with month dropdown
        d = GetDate({'mydate_month': '1', 'mydate_day': '1', 'mydate_year': '2010'})
        self.assertIn('<label for="id_mydate_month">', d.as_p())

    def test_selectdate_empty_label(self):
        w = SelectDateWidget(years=('2014',), empty_label='empty_label')

        # Rendering the default state with empty_label setted as string.
        self.assertInHTML('<option value="0">empty_label</option>', w.render('mydate', ''), count=3)

        w = SelectDateWidget(years=('2014',), empty_label=('empty_year', 'empty_month', 'empty_day'))

        # Rendering the default state with empty_label tuple.
        self.assertHTMLEqual(w.render('mydate', ''), """<select name="mydate_month" id="id_mydate_month">
<option value="0">empty_month</option>
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
<option value="0">empty_day</option>
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
<option value="0">empty_year</option>
<option value="2014">2014</option>
</select>""")

        self.assertRaisesMessage(ValueError, 'empty_label list/tuple must have 3 elements.',
            SelectDateWidget, years=('2014',), empty_label=('not enough', 'values'))

    def test_multiwidget(self):
        # MultiWidget and MultiValueField #############################################
        # MultiWidgets are widgets composed of other widgets. They are usually
        # combined with MultiValueFields - a field that is composed of other fields.
        # MulitWidgets can themselves be composed of other MultiWidgets.
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
                    return [data[0], list(data[1]), datetime.datetime.strptime(data[2], "%Y-%m-%d %H:%M:%S")]
                return [None, None, None]

            def format_output(self, rendered_widgets):
                return '\n'.join(rendered_widgets)

        w = ComplexMultiWidget()
        self.assertHTMLEqual(w.render('name', 'some text,JP,2007-04-25 06:24:00'), """<input type="text" name="name_0" value="some text" />
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
                    return '%s,%s,%s' % (data_list[0], ''.join(data_list[1]), data_list[2])
                return None

        f = ComplexField(widget=w)
        self.assertEqual(f.clean(['some text', ['J', 'P'], ['2007-04-25', '6:24:00']]), 'some text,JP,2007-04-25 06:24:00')
        self.assertFormErrors(['Select a valid choice. X is not one of the available choices.'], f.clean, ['some text', ['X'], ['2007-04-25', '6:24:00']])

        # If insufficient data is provided, None is substituted
        self.assertFormErrors(['This field is required.'], f.clean, ['some text', ['JP']])

        # test with no initial data
        self.assertTrue(f.has_changed(None, ['some text', ['J', 'P'], ['2007-04-25', '6:24:00']]))

        # test when the data is the same as initial
        self.assertFalse(f.has_changed('some text,JP,2007-04-25 06:24:00',
            ['some text', ['J', 'P'], ['2007-04-25', '6:24:00']]))

        # test when the first widget's data has changed
        self.assertTrue(f.has_changed('some text,JP,2007-04-25 06:24:00',
            ['other text', ['J', 'P'], ['2007-04-25', '6:24:00']]))

        # test when the last widget's data has changed. this ensures that it is not
        # short circuiting while testing the widgets.
        self.assertTrue(f.has_changed('some text,JP,2007-04-25 06:24:00',
            ['some text', ['J', 'P'], ['2009-04-25', '11:44:00']]))

        class ComplexFieldForm(Form):
            field1 = ComplexField(widget=w)

        f = ComplexFieldForm()
        self.assertHTMLEqual(f.as_table(), """<tr><th><label for="id_field1_0">Field1:</label></th><td><input type="text" name="field1_0" id="id_field1_0" />
<select multiple="multiple" name="field1_1" id="id_field1_1">
<option value="J">John</option>
<option value="P">Paul</option>
<option value="G">George</option>
<option value="R">Ringo</option>
</select>
<input type="text" name="field1_2_0" id="id_field1_2_0" /><input type="text" name="field1_2_1" id="id_field1_2_1" /></td></tr>""")

        f = ComplexFieldForm({'field1_0': 'some text', 'field1_1': ['J', 'P'], 'field1_2_0': '2007-04-25', 'field1_2_1': '06:24:00'})
        self.assertHTMLEqual(f.as_table(), """<tr><th><label for="id_field1_0">Field1:</label></th><td><input type="text" name="field1_0" value="some text" id="id_field1_0" />
<select multiple="multiple" name="field1_1" id="id_field1_1">
<option value="J" selected="selected">John</option>
<option value="P" selected="selected">Paul</option>
<option value="G">George</option>
<option value="R">Ringo</option>
</select>
<input type="text" name="field1_2_0" value="2007-04-25" id="id_field1_2_0" /><input type="text" name="field1_2_1" value="06:24:00" id="id_field1_2_1" /></td></tr>""")

        self.assertEqual(f.cleaned_data['field1'], 'some text,JP,2007-04-25 06:24:00')

    @ignore_warnings(category=RemovedInDjango19Warning)
    def test_ipaddress(self):
        f = IPAddressField()
        self.assertFormErrors(['This field is required.'], f.clean, '')
        self.assertFormErrors(['This field is required.'], f.clean, None)
        self.assertEqual(f.clean(' 127.0.0.1'), '127.0.0.1')
        self.assertFormErrors(['Enter a valid IPv4 address.'], f.clean, 'foo')
        self.assertFormErrors(['Enter a valid IPv4 address.'], f.clean, '127.0.0.')
        self.assertFormErrors(['Enter a valid IPv4 address.'], f.clean, '1.2.3.4.5')
        self.assertFormErrors(['Enter a valid IPv4 address.'], f.clean, '256.125.1.5')

        f = IPAddressField(required=False)
        self.assertEqual(f.clean(''), '')
        self.assertEqual(f.clean(None), '')
        self.assertEqual(f.clean(' 127.0.0.1'), '127.0.0.1')
        self.assertFormErrors(['Enter a valid IPv4 address.'], f.clean, 'foo')
        self.assertFormErrors(['Enter a valid IPv4 address.'], f.clean, '127.0.0.')
        self.assertFormErrors(['Enter a valid IPv4 address.'], f.clean, '1.2.3.4.5')
        self.assertFormErrors(['Enter a valid IPv4 address.'], f.clean, '256.125.1.5')

    def test_generic_ipaddress_invalid_arguments(self):
        self.assertRaises(ValueError, GenericIPAddressField, protocol="hamster")
        self.assertRaises(ValueError, GenericIPAddressField, protocol="ipv4", unpack_ipv4=True)

    def test_generic_ipaddress_as_generic(self):
        # The edge cases of the IPv6 validation code are not deeply tested
        # here, they are covered in the tests for django.utils.ipv6
        f = GenericIPAddressField()
        self.assertFormErrors(['This field is required.'], f.clean, '')
        self.assertFormErrors(['This field is required.'], f.clean, None)
        self.assertEqual(f.clean(' 127.0.0.1 '), '127.0.0.1')
        self.assertFormErrors(['Enter a valid IPv4 or IPv6 address.'], f.clean, 'foo')
        self.assertFormErrors(['Enter a valid IPv4 or IPv6 address.'], f.clean, '127.0.0.')
        self.assertFormErrors(['Enter a valid IPv4 or IPv6 address.'], f.clean, '1.2.3.4.5')
        self.assertFormErrors(['Enter a valid IPv4 or IPv6 address.'], f.clean, '256.125.1.5')
        self.assertEqual(f.clean(' fe80::223:6cff:fe8a:2e8a '), 'fe80::223:6cff:fe8a:2e8a')
        self.assertEqual(f.clean(' 2a02::223:6cff:fe8a:2e8a '), '2a02::223:6cff:fe8a:2e8a')
        self.assertFormErrors(['This is not a valid IPv6 address.'], f.clean, '12345:2:3:4')
        self.assertFormErrors(['This is not a valid IPv6 address.'], f.clean, '1::2:3::4')
        self.assertFormErrors(['This is not a valid IPv6 address.'], f.clean, 'foo::223:6cff:fe8a:2e8a')
        self.assertFormErrors(['This is not a valid IPv6 address.'], f.clean, '1::2:3:4:5:6:7:8')
        self.assertFormErrors(['This is not a valid IPv6 address.'], f.clean, '1:2')

    def test_generic_ipaddress_as_ipv4_only(self):
        f = GenericIPAddressField(protocol="IPv4")
        self.assertFormErrors(['This field is required.'], f.clean, '')
        self.assertFormErrors(['This field is required.'], f.clean, None)
        self.assertEqual(f.clean(' 127.0.0.1 '), '127.0.0.1')
        self.assertFormErrors(['Enter a valid IPv4 address.'], f.clean, 'foo')
        self.assertFormErrors(['Enter a valid IPv4 address.'], f.clean, '127.0.0.')
        self.assertFormErrors(['Enter a valid IPv4 address.'], f.clean, '1.2.3.4.5')
        self.assertFormErrors(['Enter a valid IPv4 address.'], f.clean, '256.125.1.5')
        self.assertFormErrors(['Enter a valid IPv4 address.'], f.clean, 'fe80::223:6cff:fe8a:2e8a')
        self.assertFormErrors(['Enter a valid IPv4 address.'], f.clean, '2a02::223:6cff:fe8a:2e8a')

    def test_generic_ipaddress_as_ipv6_only(self):
        f = GenericIPAddressField(protocol="IPv6")
        self.assertFormErrors(['This field is required.'], f.clean, '')
        self.assertFormErrors(['This field is required.'], f.clean, None)
        self.assertFormErrors(['Enter a valid IPv6 address.'], f.clean, '127.0.0.1')
        self.assertFormErrors(['Enter a valid IPv6 address.'], f.clean, 'foo')
        self.assertFormErrors(['Enter a valid IPv6 address.'], f.clean, '127.0.0.')
        self.assertFormErrors(['Enter a valid IPv6 address.'], f.clean, '1.2.3.4.5')
        self.assertFormErrors(['Enter a valid IPv6 address.'], f.clean, '256.125.1.5')
        self.assertEqual(f.clean(' fe80::223:6cff:fe8a:2e8a '), 'fe80::223:6cff:fe8a:2e8a')
        self.assertEqual(f.clean(' 2a02::223:6cff:fe8a:2e8a '), '2a02::223:6cff:fe8a:2e8a')
        self.assertFormErrors(['This is not a valid IPv6 address.'], f.clean, '12345:2:3:4')
        self.assertFormErrors(['This is not a valid IPv6 address.'], f.clean, '1::2:3::4')
        self.assertFormErrors(['This is not a valid IPv6 address.'], f.clean, 'foo::223:6cff:fe8a:2e8a')
        self.assertFormErrors(['This is not a valid IPv6 address.'], f.clean, '1::2:3:4:5:6:7:8')
        self.assertFormErrors(['This is not a valid IPv6 address.'], f.clean, '1:2')

    def test_generic_ipaddress_as_generic_not_required(self):
        f = GenericIPAddressField(required=False)
        self.assertEqual(f.clean(''), '')
        self.assertEqual(f.clean(None), '')
        self.assertEqual(f.clean('127.0.0.1'), '127.0.0.1')
        self.assertFormErrors(['Enter a valid IPv4 or IPv6 address.'], f.clean, 'foo')
        self.assertFormErrors(['Enter a valid IPv4 or IPv6 address.'], f.clean, '127.0.0.')
        self.assertFormErrors(['Enter a valid IPv4 or IPv6 address.'], f.clean, '1.2.3.4.5')
        self.assertFormErrors(['Enter a valid IPv4 or IPv6 address.'], f.clean, '256.125.1.5')
        self.assertEqual(f.clean(' fe80::223:6cff:fe8a:2e8a '), 'fe80::223:6cff:fe8a:2e8a')
        self.assertEqual(f.clean(' 2a02::223:6cff:fe8a:2e8a '), '2a02::223:6cff:fe8a:2e8a')
        self.assertFormErrors(['This is not a valid IPv6 address.'], f.clean, '12345:2:3:4')
        self.assertFormErrors(['This is not a valid IPv6 address.'], f.clean, '1::2:3::4')
        self.assertFormErrors(['This is not a valid IPv6 address.'], f.clean, 'foo::223:6cff:fe8a:2e8a')
        self.assertFormErrors(['This is not a valid IPv6 address.'], f.clean, '1::2:3:4:5:6:7:8')
        self.assertFormErrors(['This is not a valid IPv6 address.'], f.clean, '1:2')

    def test_generic_ipaddress_normalization(self):
        # Test the normalizing code
        f = GenericIPAddressField()
        self.assertEqual(f.clean(' ::ffff:0a0a:0a0a  '), '::ffff:10.10.10.10')
        self.assertEqual(f.clean(' ::ffff:10.10.10.10  '), '::ffff:10.10.10.10')
        self.assertEqual(f.clean(' 2001:000:a:0000:0:fe:fe:beef  '), '2001:0:a::fe:fe:beef')
        self.assertEqual(f.clean(' 2001::a:0000:0:fe:fe:beef  '), '2001:0:a::fe:fe:beef')

        f = GenericIPAddressField(unpack_ipv4=True)
        self.assertEqual(f.clean(' ::ffff:0a0a:0a0a'), '10.10.10.10')

    def test_slugfield_normalization(self):
        f = SlugField()
        self.assertEqual(f.clean('    aa-bb-cc    '), 'aa-bb-cc')

    def test_urlfield_normalization(self):
        f = URLField()
        self.assertEqual(f.clean('http://example.com/     '), 'http://example.com/')

    def test_smart_text(self):
        class Test:
            if six.PY3:
                def __str__(self):
                    return 'ŠĐĆŽćžšđ'
            else:
                def __str__(self):
                    return 'ŠĐĆŽćžšđ'.encode('utf-8')

        class TestU:
            if six.PY3:
                def __str__(self):
                    return 'ŠĐĆŽćžšđ'

                def __bytes__(self):
                    return b'Foo'
            else:
                def __str__(self):
                    return b'Foo'

                def __unicode__(self):
                    return '\u0160\u0110\u0106\u017d\u0107\u017e\u0161\u0111'

        self.assertEqual(smart_text(Test()), '\u0160\u0110\u0106\u017d\u0107\u017e\u0161\u0111')
        self.assertEqual(smart_text(TestU()), '\u0160\u0110\u0106\u017d\u0107\u017e\u0161\u0111')
        self.assertEqual(smart_text(1), '1')
        self.assertEqual(smart_text('foo'), 'foo')

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
        self.assertEqual(f.cleaned_data['username'], 'sirrobin')

    def test_changing_cleaned_data_nothing_returned(self):
        class UserForm(Form):
            username = CharField(max_length=10)
            password = CharField(widget=PasswordInput)

            def clean(self):
                self.cleaned_data['username'] = self.cleaned_data['username'].lower()
                # don't return anything

        f = UserForm({'username': 'SirRobin', 'password': 'blue'})
        self.assertTrue(f.is_valid())
        self.assertEqual(f.cleaned_data['username'], 'sirrobin')

    def test_changing_cleaned_data_in_clean(self):
        class UserForm(Form):
            username = CharField(max_length=10)
            password = CharField(widget=PasswordInput)

            def clean(self):
                data = self.cleaned_data

                # Return a different dict. We have not changed self.cleaned_data.
                return {
                    'username': data['username'].lower(),
                    'password': 'this_is_not_a_secret',
                }

        f = UserForm({'username': 'SirRobin', 'password': 'blue'})
        self.assertTrue(f.is_valid())
        self.assertEqual(f.cleaned_data['username'], 'sirrobin')

    def test_overriding_errorlist(self):
        @python_2_unicode_compatible
        class DivErrorList(ErrorList):
            def __str__(self):
                return self.as_divs()

            def as_divs(self):
                if not self:
                    return ''
                return '<div class="errorlist">%s</div>' % ''.join('<div class="error">%s</div>' % force_text(e) for e in self)

        class CommentForm(Form):
            name = CharField(max_length=50, required=False)
            email = EmailField()
            comment = CharField()

        data = dict(email='invalid')
        f = CommentForm(data, auto_id=False, error_class=DivErrorList)
        self.assertHTMLEqual(f.as_p(), """<p>Name: <input type="text" name="name" maxlength="50" /></p>
<div class="errorlist"><div class="error">Enter a valid email address.</div></div>
<p>Email: <input type="email" name="email" value="invalid" /></p>
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

    def test_selectdatewidget_required(self):
        class GetNotRequiredDate(Form):
            mydate = DateField(widget=SelectDateWidget, required=False)

        class GetRequiredDate(Form):
            mydate = DateField(widget=SelectDateWidget, required=True)

        self.assertFalse(GetNotRequiredDate().fields['mydate'].widget.is_required)
        self.assertTrue(GetRequiredDate().fields['mydate'].widget.is_required)


@override_settings(USE_L10N=True)
class FormsExtraL10NTestCase(TestCase):
    def setUp(self):
        super(FormsExtraL10NTestCase, self).setUp()
        translation.activate('nl')

    def tearDown(self):
        translation.deactivate()
        super(FormsExtraL10NTestCase, self).tearDown()

    def test_l10n(self):
        w = SelectDateWidget(years=('2007', '2008', '2009', '2010', '2011', '2012', '2013', '2014', '2015', '2016'))
        self.assertEqual(w.value_from_datadict({'date_year': '2010', 'date_month': '8', 'date_day': '13'}, {}, 'date'), '13-08-2010')

        self.assertHTMLEqual(w.render('date', '13-08-2010'), """<select name="date_day" id="id_date_day">
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

    def test_l10n_date_changed(self):
        """
        Ensure that DateField.has_changed() with SelectDateWidget works
        correctly with a localized date format.
        Refs #17165.
        """
        # With Field.show_hidden_initial=False -----------------------
        b = GetDate({
            'mydate_year': '2008',
            'mydate_month': '4',
            'mydate_day': '1',
        }, initial={'mydate': datetime.date(2008, 4, 1)})
        self.assertFalse(b.has_changed())

        b = GetDate({
            'mydate_year': '2008',
            'mydate_month': '4',
            'mydate_day': '2',
        }, initial={'mydate': datetime.date(2008, 4, 1)})
        self.assertTrue(b.has_changed())

        # With Field.show_hidden_initial=True ------------------------
        b = GetDateShowHiddenInitial({
            'mydate_year': '2008',
            'mydate_month': '4',
            'mydate_day': '1',
            'initial-mydate': HiddenInput()._format_value(datetime.date(2008, 4, 1))
        }, initial={'mydate': datetime.date(2008, 4, 1)})
        self.assertFalse(b.has_changed())

        b = GetDateShowHiddenInitial({
            'mydate_year': '2008',
            'mydate_month': '4',
            'mydate_day': '22',
            'initial-mydate': HiddenInput()._format_value(datetime.date(2008, 4, 1))
        }, initial={'mydate': datetime.date(2008, 4, 1)})
        self.assertTrue(b.has_changed())

        b = GetDateShowHiddenInitial({
            'mydate_year': '2008',
            'mydate_month': '4',
            'mydate_day': '22',
            'initial-mydate': HiddenInput()._format_value(datetime.date(2008, 4, 1))
        }, initial={'mydate': datetime.date(2008, 4, 22)})
        self.assertTrue(b.has_changed())

        b = GetDateShowHiddenInitial({
            'mydate_year': '2008',
            'mydate_month': '4',
            'mydate_day': '22',
            'initial-mydate': HiddenInput()._format_value(datetime.date(2008, 4, 22))
        }, initial={'mydate': datetime.date(2008, 4, 1)})
        self.assertFalse(b.has_changed())

    def test_l10n_invalid_date_in(self):
        # Invalid dates shouldn't be allowed
        a = GetDate({'mydate_month': '2', 'mydate_day': '31', 'mydate_year': '2010'})
        self.assertFalse(a.is_valid())
        # 'Geef een geldige datum op.' = 'Enter a valid date.'
        self.assertEqual(a.errors, {'mydate': ['Geef een geldige datum op.']})

    def test_form_label_association(self):
        # label tag is correctly associated with first rendered dropdown
        a = GetDate({'mydate_month': '1', 'mydate_day': '1', 'mydate_year': '2010'})
        self.assertIn('<label for="id_mydate_day">', a.as_p())
