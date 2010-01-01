import sys
import decimal
import datetime

from django.template import Template, Context
from django.conf import settings
from django.utils.formats import get_format, date_format, time_format, number_format, localize, localize_input
from django.utils.numberformat import format
from django.test import TestCase, client
from django.utils.translation import ugettext, ugettext_lazy, activate, deactivate, gettext_lazy, to_locale

from forms import I18nForm, SelectDateForm, SelectDateWidget, CompanyForm


class TranslationTests(TestCase):

    def test_lazy_objects(self):
        """
        Format string interpolation should work with *_lazy objects.
        """
        s = ugettext_lazy('Add %(name)s')
        d = {'name': 'Ringo'}
        self.assertEqual(u'Add Ringo', s % d)
        activate('de')
        try:
            self.assertEqual(u'Ringo hinzuf\xfcgen', s % d)
            activate('pl')
            self.assertEqual(u'Dodaj Ringo', s % d)
        finally:
            deactivate()

        # It should be possible to compare *_lazy objects.
        s1 = ugettext_lazy('Add %(name)s')
        self.assertEqual(True, s == s1)
        s2 = gettext_lazy('Add %(name)s')
        s3 = gettext_lazy('Add %(name)s')
        self.assertEqual(True, s2 == s3)
        self.assertEqual(True, s == s2)
        s4 = ugettext_lazy('Some other string')
        self.assertEqual(False, s == s4)

    def test_string_concat(self):
        """
        unicode(string_concat(...)) should not raise a TypeError - #4796
        """
        import django.utils.translation
        self.assertEqual(django.utils.translation, reload(django.utils.translation))
        self.assertEqual(u'django', unicode(django.utils.translation.string_concat("dja", "ngo")))

    def test_safe_status(self):
        """
        Translating a string requiring no auto-escaping shouldn't change the "safe" status.
        """
        from django.utils.safestring import mark_safe, SafeString, SafeUnicode
        s = mark_safe('Password')
        self.assertEqual(SafeString, type(s))
        activate('de')
        try:
            self.assertEqual(SafeUnicode, type(ugettext(s)))
        finally:
            deactivate()
        self.assertEqual('aPassword', SafeString('a') + s)
        self.assertEqual('Passworda', s + SafeString('a'))
        self.assertEqual('Passworda', s + mark_safe('a'))
        self.assertEqual('aPassword', mark_safe('a') + s)
        self.assertEqual('as', mark_safe('a') + mark_safe('s'))

    def test_maclines(self):
        """
        Translations on files with mac or dos end of lines will be converted
        to unix eof in .po catalogs, and they have to match when retrieved
        """
        from django.utils.translation.trans_real import translation
        ca_translation = translation('ca')
        ca_translation._catalog[u'Mac\nEOF\n'] = u'Catalan Mac\nEOF\n'
        ca_translation._catalog[u'Win\nEOF\n'] = u'Catalan Win\nEOF\n'
        activate('ca')
        try:
            self.assertEqual(u'Catalan Mac\nEOF\n', ugettext(u'Mac\rEOF\r'))
            self.assertEqual(u'Catalan Win\nEOF\n', ugettext(u'Win\r\nEOF\r\n'))
        finally:
            deactivate()

    def test_to_locale(self):
        """
        Tests the to_locale function and the special case of Serbian Latin
        (refs #12230 and r11299)
        """
        self.assertEqual(to_locale('en-us'), 'en_US')
        self.assertEqual(to_locale('sr-lat'), 'sr_Lat')

    def test_to_language(self):
        """
        Test the to_language function
        """
        from django.utils.translation.trans_real import to_language
        self.assertEqual(to_language('en_US'), 'en-us')
        self.assertEqual(to_language('sr_Lat'), 'sr-lat')


class FormattingTests(TestCase):

    def setUp(self):
        self._use_i18n = settings.USE_I18N
        self._use_l10n = settings.USE_L10N
        self._use_thousand_separator = settings.USE_THOUSAND_SEPARATOR
        self.n = decimal.Decimal('66666.666')
        self.f = 99999.999
        self.d = datetime.date(2009, 12, 31)
        self.dt = datetime.datetime(2009, 12, 31, 20, 50)
        self.t = datetime.time(10, 15, 48)
        self.ctxt = Context({
            'n': self.n,
            't': self.t,
            'd': self.d,
            'dt': self.dt,
            'f': self.f
        })

    def tearDown(self):
        # Restore defaults
        settings.USE_I18N = self._use_i18n
        settings.USE_L10N = self._use_l10n
        settings.USE_THOUSAND_SEPARATOR = self._use_thousand_separator

    def test_locale_independent(self):
        """
        Localization of numbers
        """
        settings.USE_L10N = True
        settings.USE_THOUSAND_SEPARATOR = False
        self.assertEqual(u'66666.66', format(self.n, decimal_sep='.', decimal_pos=2, grouping=3, thousand_sep=','))
        self.assertEqual(u'66666A6', format(self.n, decimal_sep='A', decimal_pos=1, grouping=1, thousand_sep='B'))

        settings.USE_THOUSAND_SEPARATOR = True
        self.assertEqual(u'66,666.66', format(self.n, decimal_sep='.', decimal_pos=2, grouping=3, thousand_sep=','))
        self.assertEqual(u'6B6B6B6B6A6', format(self.n, decimal_sep='A', decimal_pos=1, grouping=1, thousand_sep='B'))
        self.assertEqual(u'-66666.6', format(-66666.666, decimal_sep='.', decimal_pos=1))
        self.assertEqual(u'-66666.0', format(int('-66666'), decimal_sep='.', decimal_pos=1))

    def test_l10n_disabled(self):
        """
        Catalan locale with format i18n disabled translations will be used,
        but not formats
        """
        settings.USE_L10N = False
        activate('ca')
        try:
            self.assertEqual('N j, Y', get_format('DATE_FORMAT'))
            self.assertEqual(0, get_format('FIRST_DAY_OF_WEEK'))
            self.assertEqual('.', get_format('DECIMAL_SEPARATOR'))
            self.assertEqual(u'10:15 a.m.', time_format(self.t))
            self.assertEqual(u'des. 31, 2009', date_format(self.d))
            self.assertEqual(u'desembre 2009', date_format(self.d, 'YEAR_MONTH_FORMAT'))
            self.assertEqual(u'12/31/2009 8:50 p.m.', date_format(self.dt, 'SHORT_DATETIME_FORMAT'))
            self.assertEqual('No localizable', localize('No localizable'))
            self.assertEqual(decimal.Decimal('66666.666'), localize(self.n))
            self.assertEqual(99999.999, localize(self.f))
            self.assertEqual(datetime.date(2009, 12, 31), localize(self.d))
            self.assertEqual(datetime.datetime(2009, 12, 31, 20, 50), localize(self.dt))
            self.assertEqual(u'66666.666', Template('{{ n }}').render(self.ctxt))
            self.assertEqual(u'99999.999', Template('{{ f }}').render(self.ctxt))
            self.assertEqual(u'2009-12-31', Template('{{ d }}').render(self.ctxt))
            self.assertEqual(u'2009-12-31 20:50:00', Template('{{ dt }}').render(self.ctxt))
            self.assertEqual(u'66666.67', Template('{{ n|floatformat:2 }}').render(self.ctxt))
            self.assertEqual(u'100000.0', Template('{{ f|floatformat }}').render(self.ctxt))
            self.assertEqual(u'10:15 a.m.', Template('{{ t|time:"TIME_FORMAT" }}').render(self.ctxt))
            self.assertEqual(u'12/31/2009', Template('{{ d|date:"SHORT_DATE_FORMAT" }}').render(self.ctxt))
            self.assertEqual(u'12/31/2009 8:50 p.m.', Template('{{ dt|date:"SHORT_DATETIME_FORMAT" }}').render(self.ctxt))

            form = I18nForm({
                'decimal_field': u'66666,666',
                'float_field': u'99999,999',
                'date_field': u'31/12/2009',
                'datetime_field': u'31/12/2009 20:50',
                'time_field': u'20:50'
            })
            self.assertEqual(False, form.is_valid())
            self.assertEqual([u'Introdu\xefu un n\xfamero.'], form.errors['float_field'])
            self.assertEqual([u'Introdu\xefu un n\xfamero.'], form.errors['decimal_field'])
            self.assertEqual([u'Introdu\xefu una data v\xe0lida.'], form.errors['date_field'])
            self.assertEqual([u'Introdu\xefu una data/hora v\xe0lides.'], form.errors['datetime_field'])

            form2 = SelectDateForm({
                'date_field_month': u'12',
                'date_field_day': u'31',
                'date_field_year': u'2009'
            })
            self.assertEqual(True, form2.is_valid())
            self.assertEqual(datetime.date(2009, 12, 31), form2.cleaned_data['date_field'])
            self.assertEqual(
                u'<select name="mydate_month" id="id_mydate_month">\n<option value="1">gener</option>\n<option value="2">febrer</option>\n<option value="3">mar\xe7</option>\n<option value="4">abril</option>\n<option value="5">maig</option>\n<option value="6">juny</option>\n<option value="7">juliol</option>\n<option value="8">agost</option>\n<option value="9">setembre</option>\n<option value="10">octubre</option>\n<option value="11">novembre</option>\n<option value="12" selected="selected">desembre</option>\n</select>\n<select name="mydate_day" id="id_mydate_day">\n<option value="1">1</option>\n<option value="2">2</option>\n<option value="3">3</option>\n<option value="4">4</option>\n<option value="5">5</option>\n<option value="6">6</option>\n<option value="7">7</option>\n<option value="8">8</option>\n<option value="9">9</option>\n<option value="10">10</option>\n<option value="11">11</option>\n<option value="12">12</option>\n<option value="13">13</option>\n<option value="14">14</option>\n<option value="15">15</option>\n<option value="16">16</option>\n<option value="17">17</option>\n<option value="18">18</option>\n<option value="19">19</option>\n<option value="20">20</option>\n<option value="21">21</option>\n<option value="22">22</option>\n<option value="23">23</option>\n<option value="24">24</option>\n<option value="25">25</option>\n<option value="26">26</option>\n<option value="27">27</option>\n<option value="28">28</option>\n<option value="29">29</option>\n<option value="30">30</option>\n<option value="31" selected="selected">31</option>\n</select>\n<select name="mydate_year" id="id_mydate_year">\n<option value="2009" selected="selected">2009</option>\n<option value="2010">2010</option>\n<option value="2011">2011</option>\n<option value="2012">2012</option>\n<option value="2013">2013</option>\n<option value="2014">2014</option>\n<option value="2015">2015</option>\n<option value="2016">2016</option>\n<option value="2017">2017</option>\n<option value="2018">2018</option>\n</select>',
                SelectDateWidget(years=range(2009, 2019)).render('mydate', datetime.date(2009, 12, 31))
            )
        finally:
            deactivate()

    def test_l10n_enabled(self):
        """
        Catalan locale
        """
        settings.USE_L10N = True
        activate('ca')
        try:
            self.assertEqual('j \de F \de Y', get_format('DATE_FORMAT'))
            self.assertEqual(1, get_format('FIRST_DAY_OF_WEEK'))
            self.assertEqual(',', get_format('DECIMAL_SEPARATOR'))
            self.assertEqual(u'10:15:48', time_format(self.t))
            self.assertEqual(u'31 de desembre de 2009', date_format(self.d))
            self.assertEqual(u'desembre del 2009', date_format(self.d, 'YEAR_MONTH_FORMAT'))
            self.assertEqual(u'31/12/2009 20:50', date_format(self.dt, 'SHORT_DATETIME_FORMAT'))
            self.assertEqual('No localizable', localize('No localizable'))

            settings.USE_THOUSAND_SEPARATOR = True
            self.assertEqual(u'66.666,666', localize(self.n))
            self.assertEqual(u'99.999,999', localize(self.f))

            settings.USE_THOUSAND_SEPARATOR = False
            self.assertEqual(u'66666,666', localize(self.n))
            self.assertEqual(u'99999,999', localize(self.f))
            self.assertEqual(u'31 de desembre de 2009', localize(self.d))
            self.assertEqual(u'31 de desembre de 2009 a les 20:50', localize(self.dt))

            settings.USE_THOUSAND_SEPARATOR = True
            self.assertEqual(u'66.666,666', Template('{{ n }}').render(self.ctxt))
            self.assertEqual(u'99.999,999', Template('{{ f }}').render(self.ctxt))

            settings.USE_THOUSAND_SEPARATOR = False
            self.assertEqual(u'66666,666', Template('{{ n }}').render(self.ctxt))
            self.assertEqual(u'99999,999', Template('{{ f }}').render(self.ctxt))
            self.assertEqual(u'31 de desembre de 2009', Template('{{ d }}').render(self.ctxt))
            self.assertEqual(u'31 de desembre de 2009 a les 20:50', Template('{{ dt }}').render(self.ctxt))
            self.assertEqual(u'66666,67', Template('{{ n|floatformat:2 }}').render(self.ctxt))
            self.assertEqual(u'100000,0', Template('{{ f|floatformat }}').render(self.ctxt))
            self.assertEqual(u'10:15:48', Template('{{ t|time:"TIME_FORMAT" }}').render(self.ctxt))
            self.assertEqual(u'31/12/2009', Template('{{ d|date:"SHORT_DATE_FORMAT" }}').render(self.ctxt))
            self.assertEqual(u'31/12/2009 20:50', Template('{{ dt|date:"SHORT_DATETIME_FORMAT" }}').render(self.ctxt))

            form3 = I18nForm({
                'decimal_field': u'66666,666',
                'float_field': u'99999,999',
                'date_field': u'31/12/2009',
                'datetime_field': u'31/12/2009 20:50',
                'time_field': u'20:50'
            })
            self.assertEqual(True, form3.is_valid())
            self.assertEqual(decimal.Decimal('66666.666'), form3.cleaned_data['decimal_field'])
            self.assertEqual(99999.999, form3.cleaned_data['float_field'])
            self.assertEqual(datetime.date(2009, 12, 31), form3.cleaned_data['date_field'])
            self.assertEqual(datetime.datetime(2009, 12, 31, 20, 50), form3.cleaned_data['datetime_field'])
            self.assertEqual(datetime.time(20, 50), form3.cleaned_data['time_field'])

            form4 = SelectDateForm({
                'date_field_month': u'12',
                'date_field_day': u'31',
                'date_field_year': u'2009'
            })
            self.assertEqual(True, form4.is_valid())
            self.assertEqual(datetime.date(2009, 12, 31), form4.cleaned_data['date_field'])
            self.assertEqual(
                u'<select name="mydate_day" id="id_mydate_day">\n<option value="1">1</option>\n<option value="2">2</option>\n<option value="3">3</option>\n<option value="4">4</option>\n<option value="5">5</option>\n<option value="6">6</option>\n<option value="7">7</option>\n<option value="8">8</option>\n<option value="9">9</option>\n<option value="10">10</option>\n<option value="11">11</option>\n<option value="12">12</option>\n<option value="13">13</option>\n<option value="14">14</option>\n<option value="15">15</option>\n<option value="16">16</option>\n<option value="17">17</option>\n<option value="18">18</option>\n<option value="19">19</option>\n<option value="20">20</option>\n<option value="21">21</option>\n<option value="22">22</option>\n<option value="23">23</option>\n<option value="24">24</option>\n<option value="25">25</option>\n<option value="26">26</option>\n<option value="27">27</option>\n<option value="28">28</option>\n<option value="29">29</option>\n<option value="30">30</option>\n<option value="31" selected="selected">31</option>\n</select>\n<select name="mydate_month" id="id_mydate_month">\n<option value="1">gener</option>\n<option value="2">febrer</option>\n<option value="3">mar\xe7</option>\n<option value="4">abril</option>\n<option value="5">maig</option>\n<option value="6">juny</option>\n<option value="7">juliol</option>\n<option value="8">agost</option>\n<option value="9">setembre</option>\n<option value="10">octubre</option>\n<option value="11">novembre</option>\n<option value="12" selected="selected">desembre</option>\n</select>\n<select name="mydate_year" id="id_mydate_year">\n<option value="2009" selected="selected">2009</option>\n<option value="2010">2010</option>\n<option value="2011">2011</option>\n<option value="2012">2012</option>\n<option value="2013">2013</option>\n<option value="2014">2014</option>\n<option value="2015">2015</option>\n<option value="2016">2016</option>\n<option value="2017">2017</option>\n<option value="2018">2018</option>\n</select>',
                SelectDateWidget(years=range(2009, 2019)).render('mydate', datetime.date(2009, 12, 31))
            )
        finally:
            deactivate()

        # English locale

        settings.USE_L10N = True
        activate('en')
        try:
            self.assertEqual('N j, Y', get_format('DATE_FORMAT'))
            self.assertEqual(0, get_format('FIRST_DAY_OF_WEEK'))
            self.assertEqual('.', get_format('DECIMAL_SEPARATOR'))
            self.assertEqual(u'Dec. 31, 2009', date_format(self.d))
            self.assertEqual(u'December 2009', date_format(self.d, 'YEAR_MONTH_FORMAT'))
            self.assertEqual(u'12/31/2009 8:50 p.m.', date_format(self.dt, 'SHORT_DATETIME_FORMAT'))
            self.assertEqual('No localizable', localize('No localizable'))

            settings.USE_THOUSAND_SEPARATOR = True
            self.assertEqual(u'66,666.666', localize(self.n))
            self.assertEqual(u'99,999.999', localize(self.f))

            settings.USE_THOUSAND_SEPARATOR = False
            self.assertEqual(u'66666.666', localize(self.n))
            self.assertEqual(u'99999.999', localize(self.f))
            self.assertEqual(u'Dec. 31, 2009', localize(self.d))
            self.assertEqual(u'Dec. 31, 2009, 8:50 p.m.', localize(self.dt))

            settings.USE_THOUSAND_SEPARATOR = True
            self.assertEqual(u'66,666.666', Template('{{ n }}').render(self.ctxt))
            self.assertEqual(u'99,999.999', Template('{{ f }}').render(self.ctxt))

            settings.USE_THOUSAND_SEPARATOR = False
            self.assertEqual(u'66666.666', Template('{{ n }}').render(self.ctxt))
            self.assertEqual(u'99999.999', Template('{{ f }}').render(self.ctxt))
            self.assertEqual(u'Dec. 31, 2009', Template('{{ d }}').render(self.ctxt))
            self.assertEqual(u'Dec. 31, 2009, 8:50 p.m.', Template('{{ dt }}').render(self.ctxt))
            self.assertEqual(u'66666.67', Template('{{ n|floatformat:2 }}').render(self.ctxt))
            self.assertEqual(u'100000.0', Template('{{ f|floatformat }}').render(self.ctxt))
            self.assertEqual(u'12/31/2009', Template('{{ d|date:"SHORT_DATE_FORMAT" }}').render(self.ctxt))
            self.assertEqual(u'12/31/2009 8:50 p.m.', Template('{{ dt|date:"SHORT_DATETIME_FORMAT" }}').render(self.ctxt))

            form5 = I18nForm({
                'decimal_field': u'66666.666',
                'float_field': u'99999.999',
                'date_field': u'12/31/2009',
                'datetime_field': u'12/31/2009 20:50',
                'time_field': u'20:50'
            })
            self.assertEqual(True, form5.is_valid())
            self.assertEqual(decimal.Decimal('66666.666'), form5.cleaned_data['decimal_field'])
            self.assertEqual(99999.999, form5.cleaned_data['float_field'])
            self.assertEqual(datetime.date(2009, 12, 31), form5.cleaned_data['date_field'])
            self.assertEqual(datetime.datetime(2009, 12, 31, 20, 50), form5.cleaned_data['datetime_field'])
            self.assertEqual(datetime.time(20, 50), form5.cleaned_data['time_field'])

            form6 = SelectDateForm({
                'date_field_month': u'12',
                'date_field_day': u'31',
                'date_field_year': u'2009'
            })
            self.assertEqual(True, form6.is_valid())
            self.assertEqual(datetime.date(2009, 12, 31), form6.cleaned_data['date_field'])
            self.assertEqual(
                u'<select name="mydate_month" id="id_mydate_month">\n<option value="1">January</option>\n<option value="2">February</option>\n<option value="3">March</option>\n<option value="4">April</option>\n<option value="5">May</option>\n<option value="6">June</option>\n<option value="7">July</option>\n<option value="8">August</option>\n<option value="9">September</option>\n<option value="10">October</option>\n<option value="11">November</option>\n<option value="12" selected="selected">December</option>\n</select>\n<select name="mydate_day" id="id_mydate_day">\n<option value="1">1</option>\n<option value="2">2</option>\n<option value="3">3</option>\n<option value="4">4</option>\n<option value="5">5</option>\n<option value="6">6</option>\n<option value="7">7</option>\n<option value="8">8</option>\n<option value="9">9</option>\n<option value="10">10</option>\n<option value="11">11</option>\n<option value="12">12</option>\n<option value="13">13</option>\n<option value="14">14</option>\n<option value="15">15</option>\n<option value="16">16</option>\n<option value="17">17</option>\n<option value="18">18</option>\n<option value="19">19</option>\n<option value="20">20</option>\n<option value="21">21</option>\n<option value="22">22</option>\n<option value="23">23</option>\n<option value="24">24</option>\n<option value="25">25</option>\n<option value="26">26</option>\n<option value="27">27</option>\n<option value="28">28</option>\n<option value="29">29</option>\n<option value="30">30</option>\n<option value="31" selected="selected">31</option>\n</select>\n<select name="mydate_year" id="id_mydate_year">\n<option value="2009" selected="selected">2009</option>\n<option value="2010">2010</option>\n<option value="2011">2011</option>\n<option value="2012">2012</option>\n<option value="2013">2013</option>\n<option value="2014">2014</option>\n<option value="2015">2015</option>\n<option value="2016">2016</option>\n<option value="2017">2017</option>\n<option value="2018">2018</option>\n</select>',
                SelectDateWidget(years=range(2009, 2019)).render('mydate', datetime.date(2009, 12, 31))
            )
        finally:
            deactivate()

    def test_sub_locales(self):
        """
        Check if sublocales fall back to the main locale
        """
        settings.USE_L10N = True
        activate('de-at')
        settings.USE_THOUSAND_SEPARATOR = True
        try:
            self.assertEqual(u'66.666,666', Template('{{ n }}').render(self.ctxt))
        finally:
            deactivate()

        activate('es-us')
        try:
            self.assertEqual(u'31 de diciembre de 2009', date_format(self.d))
        finally:
            deactivate()

    def test_localized_input(self):
        """
        Tests if form input is correctly localized
        """
        settings.USE_L10N = True
        activate('de-at')
        try:
            form6 = CompanyForm({
                'name': u'acme',
                'date_added': datetime.datetime(2009, 12, 31, 6, 0, 0),
            })
            form6.save()
            self.assertEqual(True, form6.is_valid())
            self.assertEqual(
                form6.as_ul(),
                u'<li><label for="id_name">Name:</label> <input id="id_name" type="text" name="name" value="acme" maxlength="50" /></li>\n<li><label for="id_date_added">Date added:</label> <input type="text" name="date_added" value="31.12.2009 06:00:00" id="id_date_added" /></li>'
            )
            self.assertEqual(localize_input(datetime.datetime(2009, 12, 31, 6, 0, 0)), '31.12.2009 06:00:00')
            self.assertEqual(datetime.datetime(2009, 12, 31, 6, 0, 0), form6.cleaned_data['date_added'])
        finally:
            deactivate()

class MiscTests(TestCase):

    def test_parse_spec_http_header(self):
        """
        Testing HTTP header parsing. First, we test that we can parse the
        values according to the spec (and that we extract all the pieces in
        the right order).
        """
        from django.utils.translation.trans_real import parse_accept_lang_header
        p = parse_accept_lang_header
        # Good headers.
        self.assertEqual([('de', 1.0)], p('de'))
        self.assertEqual([('en-AU', 1.0)], p('en-AU'))
        self.assertEqual([('*', 1.0)], p('*;q=1.00'))
        self.assertEqual([('en-AU', 0.123)], p('en-AU;q=0.123'))
        self.assertEqual([('en-au', 0.10000000000000001)], p('en-au;q=0.1'))
        self.assertEqual([('en-au', 1.0)], p('en-au;q=1.0'))
        self.assertEqual([('da', 1.0), ('en', 0.5), ('en-gb', 0.25)], p('da, en-gb;q=0.25, en;q=0.5'))
        self.assertEqual([('en-au-xx', 1.0)], p('en-au-xx'))
        self.assertEqual([('de', 1.0), ('en-au', 0.75), ('en-us', 0.5), ('en', 0.25), ('es', 0.125), ('fa', 0.125)], p('de,en-au;q=0.75,en-us;q=0.5,en;q=0.25,es;q=0.125,fa;q=0.125'))
        self.assertEqual([('*', 1.0)], p('*'))
        self.assertEqual([('de', 1.0)], p('de;q=0.'))
        self.assertEqual([], p(''))

        # Bad headers; should always return [].
        self.assertEqual([], p('en-gb;q=1.0000'))
        self.assertEqual([], p('en;q=0.1234'))
        self.assertEqual([], p('en;q=.2'))
        self.assertEqual([], p('abcdefghi-au'))
        self.assertEqual([], p('**'))
        self.assertEqual([], p('en,,gb'))
        self.assertEqual([], p('en-au;q=0.1.0'))
        self.assertEqual([], p('XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXZ,en'))
        self.assertEqual([], p('da, en-gb;q=0.8, en;q=0.7,#'))
        self.assertEqual([], p('de;q=2.0'))
        self.assertEqual([], p('de;q=0.a'))
        self.assertEqual([], p(''))

    def test_parse_literal_http_header(self):
        """
        Now test that we parse a literal HTTP header correctly.
        """
        from django.utils.translation.trans_real import get_language_from_request
        g = get_language_from_request
        from django.http import HttpRequest
        r = HttpRequest
        r.COOKIES = {}
        r.META = {'HTTP_ACCEPT_LANGUAGE': 'pt-br'}
        self.assertEqual('pt-br', g(r))

        r.META = {'HTTP_ACCEPT_LANGUAGE': 'pt'}
        self.assertEqual('pt', g(r))

        r.META = {'HTTP_ACCEPT_LANGUAGE': 'es,de'}
        self.assertEqual('es', g(r))

        r.META = {'HTTP_ACCEPT_LANGUAGE': 'es-ar,de'}
        self.assertEqual('es-ar', g(r))

        # Python 2.3 and 2.4 return slightly different results for completely
        # bogus locales, so we omit this test for that anything below 2.4.
        # It's relatively harmless in any cases (GIGO). This also means this
        # won't be executed on Jython currently, but life's like that
        # sometimes. (On those platforms, passing in a truly bogus locale
        # will get you the default locale back.)
        if sys.version_info >= (2, 5):
            # This test assumes there won't be a Django translation to a US
            # variation of the Spanish language, a safe assumption. When the
            # user sets it as the preferred language, the main 'es'
            # translation should be selected instead.
            r.META = {'HTTP_ACCEPT_LANGUAGE': 'es-us'}
            self.assertEqual(g(r), 'es')

        # This tests the following scenario: there isn't a main language (zh)
        # translation of Django but there is a translation to variation (zh_CN)
        # the user sets zh-cn as the preferred language, it should be selected
        # by Django without falling back nor ignoring it.
        r.META = {'HTTP_ACCEPT_LANGUAGE': 'zh-cn,de'}
        self.assertEqual(g(r), 'zh-cn')
