# coding: utf-8
import misc

regressions = ur"""
Format string interpolation should work with *_lazy objects.

>>> from django.utils.translation import ugettext, ugettext_lazy, activate, deactivate, gettext_lazy
>>> s = ugettext_lazy('Add %(name)s')
>>> d = {'name': 'Ringo'}
>>> s % d
u'Add Ringo'
>>> activate('de')
>>> s % d
u'Ringo hinzuf\xfcgen'
>>> activate('pl')
>>> s % d
u'Dodaj Ringo'
>>> deactivate()

It should be possible to compare *_lazy objects.

>>> s1 = ugettext_lazy('Add %(name)s')
>>> s == s1
True
>>> s2 = gettext_lazy('Add %(name)s')
>>> s3 = gettext_lazy('Add %(name)s')
>>> s2 == s3
True
>>> s == s2
True
>>> s4 = ugettext_lazy('Some other string')
>>> s == s4
False

unicode(string_concat(...)) should not raise a TypeError - #4796

>>> import django.utils.translation
>>> reload(django.utils.translation)
<module 'django.utils.translation' from ...>
>>> unicode(django.utils.translation.string_concat("dja", "ngo"))
u'django'

Translating a string requiring no auto-escaping shouldn't change the "safe"
status.

>>> from django.utils.safestring import mark_safe, SafeString
>>> s = mark_safe('Password')
>>> type(s)
<class 'django.utils.safestring.SafeString'>
>>> activate('de')
>>> type(ugettext(s))
<class 'django.utils.safestring.SafeUnicode'>
>>> deactivate()

>>> SafeString('a') + s
'aPassword'
>>> s + SafeString('a')
'Passworda'
>>> s + mark_safe('a')
'Passworda'
>>> mark_safe('a') + s
'aPassword'
>>> mark_safe('a') + mark_safe('s')
'as'
>>> print s
Password

Localization of dates and numbers

>>> import datetime
>>> import decimal
>>> from django.utils.formats import getformat, date_format, number_format, localize
>>> from django import template
>>> from django import forms
>>> from django.forms.extras import SelectDateWidget

>>> n = decimal.Decimal('66666.666')
>>> f = 99999.999
>>> d = datetime.date(2009, 12, 31)
>>> dt = datetime.datetime(2009, 12, 31, 20, 50)
>>> ctxt = template.Context({'n': n, 'd': d, 'dt': dt, 'f': f})
>>> class I18nForm(forms.Form):
...     decimal_field = forms.DecimalField()
...     float_field = forms.FloatField()
...     date_field = forms.DateField()
...     datetime_field = forms.DateTimeField()
...     time_field = forms.TimeField()

Locale independent

>>> number_format(n, decimal_sep='.', decimal_pos=2, grouping=3, thousand_sep=',')
'66,666.66'
>>> number_format(n, decimal_sep='A', decimal_pos=1, grouping=1, thousand_sep='B')
'6B6B6B6B6BA6'

English locale

>>> activate('en')
>>> getformat('DATE_FORMAT')
'N j, Y'
>>> getformat('FIRST_DAY_OF_WEEK')
0
>>> getformat('DECIMAL_SEPARATOR')
'.'
>>> date_format(d)
'December 31, 2009'
>>> date_format(d, 'YEAR_MONTH_FORMAT')
'December 2009'
>>> date_format(d, 'SHORT_DATETIME_FORMAT')
'12/31/2009 8:50 p.m.'
>>> localize('No localizable')
'No localizable'
>>> localize(n)
'66666.666'
>>> localize(f)
'99999.999'
>>> localize(d)
'December 31, 2009'
>>> localize(dt)
'December 31, 2009, 8:50 p.m.'
>>> template.Template('{{ n }}').render(ctxt)
'66666.666'
>>> template.Template('{{ f }}').render(ctxt)
'99999.999'
>>> template.Template('{{ d }}').render(ctxt)
'December 31, 2009'
>>> template.Template('{{ dt }}').render(ctxt)
'December 31, 2009, 8:50 p.m.'
>>> template.Template('{{ n|floatformat:2 }}').render(ctxt)
'66666.66'
>>> template.Template('{{ f|floatformat }}').render(ctxt)
'99999.9'
>>> template.Template('{{ d|date:"SHORT_DATE_FORMAT" }}').render(ctxt)
'12/31/2009'
>>> template.Template('{{ dt|date:"SHORT_DATETIME_FORMAT" }}').render(ctxt)
'12/31/2009 8:50 p.m.'
>>> form = I18nForm({'decimal_field': u'66666.666', 'float_field': u'99999.999', 'date_field': u'12/31/2009', 'datetime_field': u'12/31/2009 20:50', 'time_field': u'20:50'})
>>> form.cleaned_data['decimal_field']
decimal.Decimal('66666.666')
>>> form.cleaned_data['float_field']
99999.999
>>> form.cleaned_data['date_field']
datetime.date(2009, 12, 31)
>>> form.cleaned_data['datetime_field']
datetime.datetime(2009, 12, 31, 20, 50)
>>> form.cleaned_data['time_field']
datetime.time(20, 50)
>>> SelectDateWidget().render('mydate', datetime.date(2009, 12, 31))
u'<select name="mydate_month" id="id_mydate_month">\n<option value="1">January</option>\n<option value="2">February</option>\n<option value="3">March</option>\n<option value="4">April</option>\n<option value="5">May</option>\n<option value="6">June</option>\n<option value="7">July</option>\n<option value="8">August</option>\n<option value="9">September</option>\n<option value="10">October</option>\n<option value="11">November</option>\n<option value="12" selected="selected">December</option>\n</select>\n<select name="mydate_day" id="id_mydate_day">\n<option value="1">1</option>\n<option value="2">2</option>\n<option value="3">3</option>\n<option value="4">4</option>\n<option value="5">5</option>\n<option value="6">6</option>\n<option value="7">7</option>\n<option value="8">8</option>\n<option value="9">9</option>\n<option value="10">10</option>\n<option value="11">11</option>\n<option value="12">12</option>\n<option value="13">13</option>\n<option value="14">14</option>\n<option value="15">15</option>\n<option value="16">16</option>\n<option value="17">17</option>\n<option value="18">18</option>\n<option value="19">19</option>\n<option value="20">20</option>\n<option value="21">21</option>\n<option value="22">22</option>\n<option value="23">23</option>\n<option value="24">24</option>\n<option value="25">25</option>\n<option value="26">26</option>\n<option value="27">27</option>\n<option value="28">28</option>\n<option value="29">29</option>\n<option value="30">30</option>\n<option value="31" selected="selected">31</option>\n</select>\n<select name="mydate_year" id="id_mydate_year">\n<option value="2009" selected="selected">2009</option>\n<option value="2010">2010</option>\n<option value="2011">2011</option>\n<option value="2012">2012</option>\n<option value="2013">2013</option>\n<option value="2014">2014</option>\n<option value="2015">2015</option>\n<option value="2016">2016</option>\n<option value="2017">2017</option>\n<option value="2018">2018</option>\n</select>'

Catalan locale

>>> activate('ca')
>>> getformat('DATE_FORMAT')
'j \de N \de Y'
>>> getformat('FIRST_DAY_OF_WEEK')
1
>>> getformat('DECIMAL_SEPARATOR')
','
>>> date_format(d)
'31 de desembre de 2009'
>>> date_format(d, 'YEAR_MONTH_FORMAT')
'desembre de 2009'
>>> date_format(d, 'SHORT_DATETIME_FORMAT')
'31/12/2009 20:50'
>>> localize('No localizable')
'No localizable'
>>> localize(n)
'66.666,666'
>>> localize(f)
'99.999,999'
>>> localize(d)
'31 de desembre de 2009'
>>> localize(dt)
'31 de desembre de 2009 a les 20:50'
>>> tplt.render(ctxt)
'66.666,666 # 99.999,999 # 6 de juliol de 2009 # 6 de juliol de 2009 a les 20:50'
>>> template.Template('{{ n }}').render(ctxt)
'66666,666'
>>> template.Template('{{ f }}').render(ctxt)
'99999,999'
>>> template.Template('{{ d }}').render(ctxt)
'31 de desembre de 2009'
>>> template.Template('{{ dt }}').render(ctxt)
'31 de desembre de 2009 a les 20:50'
>>> template.Template('{{ n|floatformat:2 }}').render(ctxt)
'66666,66'
>>> template.Template('{{ f|floatformat }}').render(ctxt)
'99999,9'
>>> template.Template('{{ d|date:"SHORT_DATE_FORMAT" }}').render(ctxt)
'31/12/2009'
>>> template.Template('{{ dt|date:"SHORT_DATETIME_FORMAT" }}').render(ctxt)
'31/12/2009 20:50'
>>> form = I18nForm({'decimal_field': u'66666,666', 'float_field': u'99999,999', 'date_field': u'31/12/2009', 'datetime_field': u'31/12/2009 20:50', 'time_field': u'20:50'})
>>> form.cleaned_data['decimal_field']
decimal.Decimal('66666.666')
>>> form.cleaned_data['float_field']
99999.999
>>> form.cleaned_data['date_field']
datetime.date(2009, 12, 31)
>>> form.cleaned_data['datetime_field']
datetime.datetime(2009, 12, 31, 20, 50)
>>> form.cleaned_data['time_field']
datetime.time(20, 50)
>>> SelectDateWidget().render('mydate', datetime.date(2009, 12, 31))
u'<select name="mydate_day" id="id_mydate_day">\n<option value="1">1</option>\n<option value="2">2</option>\n<option value="3">3</option>\n<option value="4">4</option>\n<option value="5">5</option>\n<option value="6">6</option>\n<option value="7">7</option>\n<option value="8">8</option>\n<option value="9">9</option>\n<option value="10">10</option>\n<option value="11">11</option>\n<option value="12">12</option>\n<option value="13">13</option>\n<option value="14">14</option>\n<option value="15">15</option>\n<option value="16">16</option>\n<option value="17">17</option>\n<option value="18">18</option>\n<option value="19">19</option>\n<option value="20">20</option>\n<option value="21">21</option>\n<option value="22">22</option>\n<option value="23">23</option>\n<option value="24">24</option>\n<option value="25">25</option>\n<option value="26">26</option>\n<option value="27">27</option>\n<option value="28">28</option>\n<option value="29">29</option>\n<option value="30">30</option>\n<option value="31" selected="selected">31</option>\n</select>\n<select name="mydate_month" id="id_mydate_month">\n<option value="1">January</option>\n<option value="2">February</option>\n<option value="3">March</option>\n<option value="4">April</option>\n<option value="5">May</option>\n<option value="6">June</option>\n<option value="7">July</option>\n<option value="8">August</option>\n<option value="9">September</option>\n<option value="10">October</option>\n<option value="11">November</option>\n<option value="12" selected="selected">December</option>\n</select>\n<select name="mydate_year" id="id_mydate_year">\n<option value="2009" selected="selected">2009</option>\n<option value="2010">2010</option>\n<option value="2011">2011</option>\n<option value="2012">2012</option>\n<option value="2013">2013</option>\n<option value="2014">2014</option>\n<option value="2015">2015</option>\n<option value="2016">2016</option>\n<option value="2017">2017</option>\n<option value="2018">2018</option>\n</select>'

"""

__test__ = {
    'regressions': regressions,
    'misc': misc.tests,
}
