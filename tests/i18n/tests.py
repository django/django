import datetime
import decimal
import gettext as gettext_module
import os
import pickle
import re
from contextlib import contextmanager
from importlib import import_module
from threading import local

from django import forms
from django.conf import settings
from django.conf.locale import LANG_INFO
from django.conf.urls.i18n import i18n_patterns
from django.template import Context, Template
from django.test import (
    RequestFactory, SimpleTestCase, TestCase, ignore_warnings,
    override_settings,
)
from django.utils import translation
from django.utils.deprecation import RemovedInDjango21Warning
from django.utils.formats import (
    date_format, get_format, get_format_modules, iter_format_modules, localize,
    localize_input, reset_format_cache, sanitize_separators, time_format,
)
from django.utils.numberformat import format as nformat
from django.utils.safestring import SafeText, mark_safe
from django.utils.translation import (
    LANGUAGE_SESSION_KEY, activate, check_for_language, deactivate,
    get_language, get_language_bidi, get_language_from_request,
    get_language_info, gettext, gettext_lazy, ngettext, ngettext_lazy,
    npgettext, npgettext_lazy, pgettext, string_concat, to_locale, trans_real,
    ugettext, ugettext_lazy, ungettext, ungettext_lazy,
)

from .forms import CompanyForm, I18nForm, SelectDateForm
from .models import Company, TestModel

here = os.path.dirname(os.path.abspath(__file__))
extended_locale_paths = settings.LOCALE_PATHS + [
    os.path.join(here, 'other', 'locale'),
]


@contextmanager
def patch_formats(lang, **settings):
    from django.utils.formats import _format_cache

    # Populate _format_cache with temporary values
    for key, value in settings.items():
        _format_cache[(key, lang)] = value
    try:
        yield
    finally:
        reset_format_cache()


class TranslationTests(SimpleTestCase):

    @translation.override('de')
    def test_legacy_aliases(self):
        """
        Pre-Django 2.0 aliases with u prefix are still available.
        """
        self.assertEqual(ugettext("Image"), "Bild")
        self.assertEqual(ugettext_lazy("Image"), gettext_lazy("Image"))
        self.assertEqual(ungettext("%d year", "%d years", 0) % 0, "0 Jahre")
        self.assertEqual(
            ungettext_lazy("%d year", "%d years", 0) % 0,
            ngettext_lazy("%d year", "%d years", 0) % 0,
        )

    @translation.override('fr')
    def test_plural(self):
        """
        Test plurals with ngettext. French differs from English in that 0 is singular.
        """
        self.assertEqual(ngettext("%d year", "%d years", 0) % 0, "0 année")
        self.assertEqual(ngettext("%d year", "%d years", 2) % 2, "2 années")
        self.assertEqual(ngettext("%(size)d byte", "%(size)d bytes", 0) % {'size': 0}, "0 octet")
        self.assertEqual(ngettext("%(size)d byte", "%(size)d bytes", 2) % {'size': 2}, "2 octets")

    def test_override(self):
        activate('de')
        try:
            with translation.override('pl'):
                self.assertEqual(get_language(), 'pl')
            self.assertEqual(get_language(), 'de')
            with translation.override(None):
                self.assertIsNone(get_language())
                with translation.override('pl'):
                    pass
                self.assertIsNone(get_language())
            self.assertEqual(get_language(), 'de')
        finally:
            deactivate()

    def test_override_decorator(self):

        @translation.override('pl')
        def func_pl():
            self.assertEqual(get_language(), 'pl')

        @translation.override(None)
        def func_none():
            self.assertIsNone(get_language())

        try:
            activate('de')
            func_pl()
            self.assertEqual(get_language(), 'de')
            func_none()
            self.assertEqual(get_language(), 'de')
        finally:
            deactivate()

    def test_override_exit(self):
        """
        The language restored is the one used when the function was
        called, not the one used when the decorator was initialized (#23381).
        """
        activate('fr')

        @translation.override('pl')
        def func_pl():
            pass
        deactivate()

        try:
            activate('en')
            func_pl()
            self.assertEqual(get_language(), 'en')
        finally:
            deactivate()

    def test_lazy_objects(self):
        """
        Format string interpolation should work with *_lazy objects.
        """
        s = gettext_lazy('Add %(name)s')
        d = {'name': 'Ringo'}
        self.assertEqual('Add Ringo', s % d)
        with translation.override('de', deactivate=True):
            self.assertEqual('Ringo hinzuf\xfcgen', s % d)
            with translation.override('pl'):
                self.assertEqual('Dodaj Ringo', s % d)

        # It should be possible to compare *_lazy objects.
        s1 = gettext_lazy('Add %(name)s')
        self.assertEqual(s, s1)
        s2 = gettext_lazy('Add %(name)s')
        s3 = gettext_lazy('Add %(name)s')
        self.assertEqual(s2, s3)
        self.assertEqual(s, s2)
        s4 = gettext_lazy('Some other string')
        self.assertNotEqual(s, s4)

    def test_lazy_pickle(self):
        s1 = gettext_lazy("test")
        self.assertEqual(str(s1), "test")
        s2 = pickle.loads(pickle.dumps(s1))
        self.assertEqual(str(s2), "test")

    @override_settings(LOCALE_PATHS=extended_locale_paths)
    def test_ngettext_lazy(self):
        simple_with_format = ngettext_lazy('%d good result', '%d good results')
        simple_context_with_format = npgettext_lazy('Exclamation', '%d good result', '%d good results')
        simple_without_format = ngettext_lazy('good result', 'good results')
        with translation.override('de'):
            self.assertEqual(simple_with_format % 1, '1 gutes Resultat')
            self.assertEqual(simple_with_format % 4, '4 guten Resultate')
            self.assertEqual(simple_context_with_format % 1, '1 gutes Resultat!')
            self.assertEqual(simple_context_with_format % 4, '4 guten Resultate!')
            self.assertEqual(simple_without_format % 1, 'gutes Resultat')
            self.assertEqual(simple_without_format % 4, 'guten Resultate')

        complex_nonlazy = ngettext_lazy('Hi %(name)s, %(num)d good result', 'Hi %(name)s, %(num)d good results', 4)
        complex_deferred = ngettext_lazy(
            'Hi %(name)s, %(num)d good result', 'Hi %(name)s, %(num)d good results', 'num'
        )
        complex_context_nonlazy = npgettext_lazy(
            'Greeting', 'Hi %(name)s, %(num)d good result', 'Hi %(name)s, %(num)d good results', 4
        )
        complex_context_deferred = npgettext_lazy(
            'Greeting', 'Hi %(name)s, %(num)d good result', 'Hi %(name)s, %(num)d good results', 'num'
        )
        with translation.override('de'):
            self.assertEqual(complex_nonlazy % {'num': 4, 'name': 'Jim'}, 'Hallo Jim, 4 guten Resultate')
            self.assertEqual(complex_deferred % {'name': 'Jim', 'num': 1}, 'Hallo Jim, 1 gutes Resultat')
            self.assertEqual(complex_deferred % {'name': 'Jim', 'num': 5}, 'Hallo Jim, 5 guten Resultate')
            with self.assertRaisesMessage(KeyError, 'Your dictionary lacks key'):
                complex_deferred % {'name': 'Jim'}
            self.assertEqual(complex_context_nonlazy % {'num': 4, 'name': 'Jim'}, 'Willkommen Jim, 4 guten Resultate')
            self.assertEqual(complex_context_deferred % {'name': 'Jim', 'num': 1}, 'Willkommen Jim, 1 gutes Resultat')
            self.assertEqual(complex_context_deferred % {'name': 'Jim', 'num': 5}, 'Willkommen Jim, 5 guten Resultate')
            with self.assertRaisesMessage(KeyError, 'Your dictionary lacks key'):
                complex_context_deferred % {'name': 'Jim'}

    def test_ngettext_lazy_bool(self):
        self.assertTrue(ngettext_lazy('%d good result', '%d good results'))
        self.assertFalse(ngettext_lazy('', ''))

    def test_ngettext_lazy_pickle(self):
        s1 = ngettext_lazy('%d good result', '%d good results')
        self.assertEqual(s1 % 1, '1 good result')
        self.assertEqual(s1 % 8, '8 good results')
        s2 = pickle.loads(pickle.dumps(s1))
        self.assertEqual(s2 % 1, '1 good result')
        self.assertEqual(s2 % 8, '8 good results')

    @override_settings(LOCALE_PATHS=extended_locale_paths)
    def test_pgettext(self):
        trans_real._active = local()
        trans_real._translations = {}
        with translation.override('de'):
            self.assertEqual(pgettext("unexisting", "May"), "May")
            self.assertEqual(pgettext("month name", "May"), "Mai")
            self.assertEqual(pgettext("verb", "May"), "Kann")
            self.assertEqual(npgettext("search", "%d result", "%d results", 4) % 4, "4 Resultate")

    @ignore_warnings(category=RemovedInDjango21Warning)
    def test_string_concat(self):
        self.assertEqual(str(string_concat('dja', 'ngo')), 'django')

    def test_empty_value(self):
        """Empty value must stay empty after being translated (#23196)."""
        with translation.override('de'):
            self.assertEqual('', gettext(''))
            s = mark_safe('')
            self.assertEqual(s, gettext(s))

    @override_settings(LOCALE_PATHS=extended_locale_paths)
    def test_safe_status(self):
        """
        Translating a string requiring no auto-escaping with gettext or pgettext
        shouldn't change the "safe" status.
        """
        trans_real._active = local()
        trans_real._translations = {}
        s1 = mark_safe('Password')
        s2 = mark_safe('May')
        with translation.override('de', deactivate=True):
            self.assertIs(type(gettext(s1)), SafeText)
            self.assertIs(type(pgettext('month name', s2)), SafeText)
        self.assertEqual('aPassword', SafeText('a') + s1)
        self.assertEqual('Passworda', s1 + SafeText('a'))
        self.assertEqual('Passworda', s1 + mark_safe('a'))
        self.assertEqual('aPassword', mark_safe('a') + s1)
        self.assertEqual('as', mark_safe('a') + mark_safe('s'))

    def test_maclines(self):
        """
        Translations on files with Mac or DOS end of lines will be converted
        to unix EOF in .po catalogs.
        """
        ca_translation = trans_real.translation('ca')
        ca_translation._catalog['Mac\nEOF\n'] = 'Catalan Mac\nEOF\n'
        ca_translation._catalog['Win\nEOF\n'] = 'Catalan Win\nEOF\n'
        with translation.override('ca', deactivate=True):
            self.assertEqual('Catalan Mac\nEOF\n', gettext('Mac\rEOF\r'))
            self.assertEqual('Catalan Win\nEOF\n', gettext('Win\r\nEOF\r\n'))

    def test_to_locale(self):
        tests = (
            ('en', 'en'),
            ('EN', 'en'),
            ('en-us', 'en_US'),
            ('EN-US', 'en_US'),
            # With > 2 characters after the dash.
            ('sr-latn', 'sr_Latn'),
            ('sr-LATN', 'sr_Latn'),
            # With private use subtag (x-informal).
            ('nl-nl-x-informal', 'nl_NL-x-informal'),
            ('NL-NL-X-INFORMAL', 'nl_NL-x-informal'),
            ('sr-latn-x-informal', 'sr_Latn-x-informal'),
            ('SR-LATN-X-INFORMAL', 'sr_Latn-x-informal'),
        )
        for lang, locale in tests:
            with self.subTest(lang=lang):
                self.assertEqual(to_locale(lang), locale)

    def test_to_language(self):
        self.assertEqual(trans_real.to_language('en_US'), 'en-us')
        self.assertEqual(trans_real.to_language('sr_Lat'), 'sr-lat')

    def test_language_bidi(self):
        self.assertIs(get_language_bidi(), False)
        with translation.override(None):
            self.assertIs(get_language_bidi(), False)


class TranslationThreadSafetyTests(SimpleTestCase):

    def setUp(self):
        self._old_language = get_language()
        self._translations = trans_real._translations

        # here we rely on .split() being called inside the _fetch()
        # in trans_real.translation()
        class sideeffect_str(str):
            def split(self, *args, **kwargs):
                res = str.split(self, *args, **kwargs)
                trans_real._translations['en-YY'] = None
                return res

        trans_real._translations = {sideeffect_str('en-XX'): None}

    def tearDown(self):
        trans_real._translations = self._translations
        activate(self._old_language)

    def test_bug14894_translation_activate_thread_safety(self):
        translation_count = len(trans_real._translations)
        # May raise RuntimeError if translation.activate() isn't thread-safe.
        translation.activate('pl')
        # make sure sideeffect_str actually added a new translation
        self.assertLess(translation_count, len(trans_real._translations))


@override_settings(USE_L10N=True)
class FormattingTests(SimpleTestCase):

    def setUp(self):
        super().setUp()
        self.n = decimal.Decimal('66666.666')
        self.f = 99999.999
        self.d = datetime.date(2009, 12, 31)
        self.dt = datetime.datetime(2009, 12, 31, 20, 50)
        self.t = datetime.time(10, 15, 48)
        self.long = 10000
        self.ctxt = Context({
            'n': self.n,
            't': self.t,
            'd': self.d,
            'dt': self.dt,
            'f': self.f,
            'l': self.long,
        })

    def test_all_format_strings(self):
        all_locales = LANG_INFO.keys()
        some_date = datetime.date(2017, 10, 14)
        some_datetime = datetime.datetime(2017, 10, 14, 10, 23)
        for locale in all_locales:
            with self.subTest(locale=locale), translation.override(locale):
                self.assertIn('2017', date_format(some_date))  # Uses DATE_FORMAT by default
                self.assertIn('23', time_format(some_datetime))  # Uses TIME_FORMAT by default
                self.assertIn('2017', date_format(some_datetime, format=get_format('DATETIME_FORMAT')))
                self.assertIn('2017', date_format(some_date, format=get_format('YEAR_MONTH_FORMAT')))
                self.assertIn('14', date_format(some_date, format=get_format('MONTH_DAY_FORMAT')))
                self.assertIn('2017', date_format(some_date, format=get_format('SHORT_DATE_FORMAT')))
                self.assertIn('2017', date_format(some_datetime, format=get_format('SHORT_DATETIME_FORMAT')))

    def test_locale_independent(self):
        """
        Localization of numbers
        """
        with self.settings(USE_THOUSAND_SEPARATOR=False):
            self.assertEqual('66666.66', nformat(self.n, decimal_sep='.', decimal_pos=2, grouping=3, thousand_sep=','))
            self.assertEqual('66666A6', nformat(self.n, decimal_sep='A', decimal_pos=1, grouping=1, thousand_sep='B'))
            self.assertEqual('66666', nformat(self.n, decimal_sep='X', decimal_pos=0, grouping=1, thousand_sep='Y'))

        with self.settings(USE_THOUSAND_SEPARATOR=True):
            self.assertEqual(
                '66,666.66',
                nformat(self.n, decimal_sep='.', decimal_pos=2, grouping=3, thousand_sep=',')
            )
            self.assertEqual(
                '6B6B6B6B6A6',
                nformat(self.n, decimal_sep='A', decimal_pos=1, grouping=1, thousand_sep='B')
            )
            self.assertEqual('-66666.6', nformat(-66666.666, decimal_sep='.', decimal_pos=1))
            self.assertEqual('-66666.0', nformat(int('-66666'), decimal_sep='.', decimal_pos=1))
            self.assertEqual('10000.0', nformat(self.long, decimal_sep='.', decimal_pos=1))
            self.assertEqual(
                '10,00,00,000.00',
                nformat(100000000.00, decimal_sep='.', decimal_pos=2, grouping=(3, 2, 0), thousand_sep=',')
            )
            self.assertEqual(
                '1,0,00,000,0000.00',
                nformat(10000000000.00, decimal_sep='.', decimal_pos=2, grouping=(4, 3, 2, 1, 0), thousand_sep=',')
            )
            self.assertEqual(
                '10000,00,000.00',
                nformat(1000000000.00, decimal_sep='.', decimal_pos=2, grouping=(3, 2, -1), thousand_sep=',')
            )
            # This unusual grouping/force_grouping combination may be triggered by the intcomma filter (#17414)
            self.assertEqual(
                '10000',
                nformat(self.long, decimal_sep='.', decimal_pos=0, grouping=0, force_grouping=True)
            )
            # date filter
            self.assertEqual('31.12.2009 в 20:50', Template('{{ dt|date:"d.m.Y в H:i" }}').render(self.ctxt))
            self.assertEqual('⌚ 10:15', Template('{{ t|time:"⌚ H:i" }}').render(self.ctxt))

    @override_settings(USE_L10N=False)
    def test_l10n_disabled(self):
        """
        Catalan locale with format i18n disabled translations will be used,
        but not formats
        """
        with translation.override('ca', deactivate=True):
            self.maxDiff = 3000
            self.assertEqual('N j, Y', get_format('DATE_FORMAT'))
            self.assertEqual(0, get_format('FIRST_DAY_OF_WEEK'))
            self.assertEqual('.', get_format('DECIMAL_SEPARATOR'))
            self.assertEqual('10:15 a.m.', time_format(self.t))
            self.assertEqual('des. 31, 2009', date_format(self.d))
            self.assertEqual('desembre 2009', date_format(self.d, 'YEAR_MONTH_FORMAT'))
            self.assertEqual('12/31/2009 8:50 p.m.', date_format(self.dt, 'SHORT_DATETIME_FORMAT'))
            self.assertEqual('No localizable', localize('No localizable'))
            self.assertEqual('66666.666', localize(self.n))
            self.assertEqual('99999.999', localize(self.f))
            self.assertEqual('10000', localize(self.long))
            self.assertEqual('des. 31, 2009', localize(self.d))
            self.assertEqual('des. 31, 2009, 8:50 p.m.', localize(self.dt))
            self.assertEqual('66666.666', Template('{{ n }}').render(self.ctxt))
            self.assertEqual('99999.999', Template('{{ f }}').render(self.ctxt))
            self.assertEqual('des. 31, 2009', Template('{{ d }}').render(self.ctxt))
            self.assertEqual('des. 31, 2009, 8:50 p.m.', Template('{{ dt }}').render(self.ctxt))
            self.assertEqual('66666.67', Template('{{ n|floatformat:2 }}').render(self.ctxt))
            self.assertEqual('100000.0', Template('{{ f|floatformat }}').render(self.ctxt))
            self.assertEqual('10:15 a.m.', Template('{{ t|time:"TIME_FORMAT" }}').render(self.ctxt))
            self.assertEqual('12/31/2009', Template('{{ d|date:"SHORT_DATE_FORMAT" }}').render(self.ctxt))
            self.assertEqual(
                '12/31/2009 8:50 p.m.', Template('{{ dt|date:"SHORT_DATETIME_FORMAT" }}').render(self.ctxt)
            )

            form = I18nForm({
                'decimal_field': '66666,666',
                'float_field': '99999,999',
                'date_field': '31/12/2009',
                'datetime_field': '31/12/2009 20:50',
                'time_field': '20:50',
                'integer_field': '1.234',
            })
            self.assertFalse(form.is_valid())
            self.assertEqual(['Introdu\xefu un n\xfamero.'], form.errors['float_field'])
            self.assertEqual(['Introdu\xefu un n\xfamero.'], form.errors['decimal_field'])
            self.assertEqual(['Introdu\xefu una data v\xe0lida.'], form.errors['date_field'])
            self.assertEqual(['Introdu\xefu una data/hora v\xe0lides.'], form.errors['datetime_field'])
            self.assertEqual(['Introdu\xefu un n\xfamero sencer.'], form.errors['integer_field'])

            form2 = SelectDateForm({
                'date_field_month': '12',
                'date_field_day': '31',
                'date_field_year': '2009'
            })
            self.assertTrue(form2.is_valid())
            self.assertEqual(datetime.date(2009, 12, 31), form2.cleaned_data['date_field'])
            self.assertHTMLEqual(
                '<select name="mydate_month" id="id_mydate_month">'
                '<option value="0">---</option>'
                '<option value="1">gener</option>'
                '<option value="2">febrer</option>'
                '<option value="3">mar\xe7</option>'
                '<option value="4">abril</option>'
                '<option value="5">maig</option>'
                '<option value="6">juny</option>'
                '<option value="7">juliol</option>'
                '<option value="8">agost</option>'
                '<option value="9">setembre</option>'
                '<option value="10">octubre</option>'
                '<option value="11">novembre</option>'
                '<option value="12" selected>desembre</option>'
                '</select>'
                '<select name="mydate_day" id="id_mydate_day">'
                '<option value="0">---</option>'
                '<option value="1">1</option>'
                '<option value="2">2</option>'
                '<option value="3">3</option>'
                '<option value="4">4</option>'
                '<option value="5">5</option>'
                '<option value="6">6</option>'
                '<option value="7">7</option>'
                '<option value="8">8</option>'
                '<option value="9">9</option>'
                '<option value="10">10</option>'
                '<option value="11">11</option>'
                '<option value="12">12</option>'
                '<option value="13">13</option>'
                '<option value="14">14</option>'
                '<option value="15">15</option>'
                '<option value="16">16</option>'
                '<option value="17">17</option>'
                '<option value="18">18</option>'
                '<option value="19">19</option>'
                '<option value="20">20</option>'
                '<option value="21">21</option>'
                '<option value="22">22</option>'
                '<option value="23">23</option>'
                '<option value="24">24</option>'
                '<option value="25">25</option>'
                '<option value="26">26</option>'
                '<option value="27">27</option>'
                '<option value="28">28</option>'
                '<option value="29">29</option>'
                '<option value="30">30</option>'
                '<option value="31" selected>31</option>'
                '</select>'
                '<select name="mydate_year" id="id_mydate_year">'
                '<option value="0">---</option>'
                '<option value="2009" selected>2009</option>'
                '<option value="2010">2010</option>'
                '<option value="2011">2011</option>'
                '<option value="2012">2012</option>'
                '<option value="2013">2013</option>'
                '<option value="2014">2014</option>'
                '<option value="2015">2015</option>'
                '<option value="2016">2016</option>'
                '<option value="2017">2017</option>'
                '<option value="2018">2018</option>'
                '</select>',
                forms.SelectDateWidget(years=range(2009, 2019)).render('mydate', datetime.date(2009, 12, 31))
            )

            # We shouldn't change the behavior of the floatformat filter re:
            # thousand separator and grouping when USE_L10N is False even
            # if the USE_THOUSAND_SEPARATOR, NUMBER_GROUPING and
            # THOUSAND_SEPARATOR settings are specified
            with self.settings(USE_THOUSAND_SEPARATOR=True, NUMBER_GROUPING=1, THOUSAND_SEPARATOR='!'):
                self.assertEqual('66666.67', Template('{{ n|floatformat:2 }}').render(self.ctxt))
                self.assertEqual('100000.0', Template('{{ f|floatformat }}').render(self.ctxt))

    def test_false_like_locale_formats(self):
        """
        The active locale's formats take precedence over the default settings
        even if they would be interpreted as False in a conditional test
        (e.g. 0 or empty string) (#16938).
        """
        with translation.override('fr'):
            with self.settings(USE_THOUSAND_SEPARATOR=True, THOUSAND_SEPARATOR='!'):
                self.assertEqual('\xa0', get_format('THOUSAND_SEPARATOR'))
                # Even a second time (after the format has been cached)...
                self.assertEqual('\xa0', get_format('THOUSAND_SEPARATOR'))

            with self.settings(FIRST_DAY_OF_WEEK=0):
                self.assertEqual(1, get_format('FIRST_DAY_OF_WEEK'))
                # Even a second time (after the format has been cached)...
                self.assertEqual(1, get_format('FIRST_DAY_OF_WEEK'))

    def test_l10n_enabled(self):
        self.maxDiff = 3000
        # Catalan locale
        with translation.override('ca', deactivate=True):
            self.assertEqual(r'j \d\e F \d\e Y', get_format('DATE_FORMAT'))
            self.assertEqual(1, get_format('FIRST_DAY_OF_WEEK'))
            self.assertEqual(',', get_format('DECIMAL_SEPARATOR'))
            self.assertEqual('10:15', time_format(self.t))
            self.assertEqual('31 de desembre de 2009', date_format(self.d))
            self.assertEqual('desembre del 2009', date_format(self.d, 'YEAR_MONTH_FORMAT'))
            self.assertEqual('31/12/2009 20:50', date_format(self.dt, 'SHORT_DATETIME_FORMAT'))
            self.assertEqual('No localizable', localize('No localizable'))

            with self.settings(USE_THOUSAND_SEPARATOR=True):
                self.assertEqual('66.666,666', localize(self.n))
                self.assertEqual('99.999,999', localize(self.f))
                self.assertEqual('10.000', localize(self.long))
                self.assertEqual('True', localize(True))

            with self.settings(USE_THOUSAND_SEPARATOR=False):
                self.assertEqual('66666,666', localize(self.n))
                self.assertEqual('99999,999', localize(self.f))
                self.assertEqual('10000', localize(self.long))
                self.assertEqual('31 de desembre de 2009', localize(self.d))
                self.assertEqual('31 de desembre de 2009 a les 20:50', localize(self.dt))

            with self.settings(USE_THOUSAND_SEPARATOR=True):
                self.assertEqual('66.666,666', Template('{{ n }}').render(self.ctxt))
                self.assertEqual('99.999,999', Template('{{ f }}').render(self.ctxt))
                self.assertEqual('10.000', Template('{{ l }}').render(self.ctxt))

            with self.settings(USE_THOUSAND_SEPARATOR=True):
                form3 = I18nForm({
                    'decimal_field': '66.666,666',
                    'float_field': '99.999,999',
                    'date_field': '31/12/2009',
                    'datetime_field': '31/12/2009 20:50',
                    'time_field': '20:50',
                    'integer_field': '1.234',
                })
                self.assertTrue(form3.is_valid())
                self.assertEqual(decimal.Decimal('66666.666'), form3.cleaned_data['decimal_field'])
                self.assertEqual(99999.999, form3.cleaned_data['float_field'])
                self.assertEqual(datetime.date(2009, 12, 31), form3.cleaned_data['date_field'])
                self.assertEqual(datetime.datetime(2009, 12, 31, 20, 50), form3.cleaned_data['datetime_field'])
                self.assertEqual(datetime.time(20, 50), form3.cleaned_data['time_field'])
                self.assertEqual(1234, form3.cleaned_data['integer_field'])

            with self.settings(USE_THOUSAND_SEPARATOR=False):
                self.assertEqual('66666,666', Template('{{ n }}').render(self.ctxt))
                self.assertEqual('99999,999', Template('{{ f }}').render(self.ctxt))
                self.assertEqual('31 de desembre de 2009', Template('{{ d }}').render(self.ctxt))
                self.assertEqual('31 de desembre de 2009 a les 20:50', Template('{{ dt }}').render(self.ctxt))
                self.assertEqual('66666,67', Template('{{ n|floatformat:2 }}').render(self.ctxt))
                self.assertEqual('100000,0', Template('{{ f|floatformat }}').render(self.ctxt))
                self.assertEqual('10:15', Template('{{ t|time:"TIME_FORMAT" }}').render(self.ctxt))
                self.assertEqual('31/12/2009', Template('{{ d|date:"SHORT_DATE_FORMAT" }}').render(self.ctxt))
                self.assertEqual(
                    '31/12/2009 20:50',
                    Template('{{ dt|date:"SHORT_DATETIME_FORMAT" }}').render(self.ctxt)
                )
                self.assertEqual(date_format(datetime.datetime.now(), "DATE_FORMAT"),
                                 Template('{% now "DATE_FORMAT" %}').render(self.ctxt))

            with self.settings(USE_THOUSAND_SEPARATOR=False):
                form4 = I18nForm({
                    'decimal_field': '66666,666',
                    'float_field': '99999,999',
                    'date_field': '31/12/2009',
                    'datetime_field': '31/12/2009 20:50',
                    'time_field': '20:50',
                    'integer_field': '1234',
                })
                self.assertTrue(form4.is_valid())
                self.assertEqual(decimal.Decimal('66666.666'), form4.cleaned_data['decimal_field'])
                self.assertEqual(99999.999, form4.cleaned_data['float_field'])
                self.assertEqual(datetime.date(2009, 12, 31), form4.cleaned_data['date_field'])
                self.assertEqual(datetime.datetime(2009, 12, 31, 20, 50), form4.cleaned_data['datetime_field'])
                self.assertEqual(datetime.time(20, 50), form4.cleaned_data['time_field'])
                self.assertEqual(1234, form4.cleaned_data['integer_field'])

            form5 = SelectDateForm({
                'date_field_month': '12',
                'date_field_day': '31',
                'date_field_year': '2009'
            })
            self.assertTrue(form5.is_valid())
            self.assertEqual(datetime.date(2009, 12, 31), form5.cleaned_data['date_field'])
            self.assertHTMLEqual(
                '<select name="mydate_day" id="id_mydate_day">'
                '<option value="0">---</option>'
                '<option value="1">1</option>'
                '<option value="2">2</option>'
                '<option value="3">3</option>'
                '<option value="4">4</option>'
                '<option value="5">5</option>'
                '<option value="6">6</option>'
                '<option value="7">7</option>'
                '<option value="8">8</option>'
                '<option value="9">9</option>'
                '<option value="10">10</option>'
                '<option value="11">11</option>'
                '<option value="12">12</option>'
                '<option value="13">13</option>'
                '<option value="14">14</option>'
                '<option value="15">15</option>'
                '<option value="16">16</option>'
                '<option value="17">17</option>'
                '<option value="18">18</option>'
                '<option value="19">19</option>'
                '<option value="20">20</option>'
                '<option value="21">21</option>'
                '<option value="22">22</option>'
                '<option value="23">23</option>'
                '<option value="24">24</option>'
                '<option value="25">25</option>'
                '<option value="26">26</option>'
                '<option value="27">27</option>'
                '<option value="28">28</option>'
                '<option value="29">29</option>'
                '<option value="30">30</option>'
                '<option value="31" selected>31</option>'
                '</select>'
                '<select name="mydate_month" id="id_mydate_month">'
                '<option value="0">---</option>'
                '<option value="1">gener</option>'
                '<option value="2">febrer</option>'
                '<option value="3">mar\xe7</option>'
                '<option value="4">abril</option>'
                '<option value="5">maig</option>'
                '<option value="6">juny</option>'
                '<option value="7">juliol</option>'
                '<option value="8">agost</option>'
                '<option value="9">setembre</option>'
                '<option value="10">octubre</option>'
                '<option value="11">novembre</option>'
                '<option value="12" selected>desembre</option>'
                '</select>'
                '<select name="mydate_year" id="id_mydate_year">'
                '<option value="0">---</option>'
                '<option value="2009" selected>2009</option>'
                '<option value="2010">2010</option>'
                '<option value="2011">2011</option>'
                '<option value="2012">2012</option>'
                '<option value="2013">2013</option>'
                '<option value="2014">2014</option>'
                '<option value="2015">2015</option>'
                '<option value="2016">2016</option>'
                '<option value="2017">2017</option>'
                '<option value="2018">2018</option>'
                '</select>',
                forms.SelectDateWidget(years=range(2009, 2019)).render('mydate', datetime.date(2009, 12, 31))
            )

        # Russian locale (with E as month)
        with translation.override('ru', deactivate=True):
            self.assertHTMLEqual(
                '<select name="mydate_day" id="id_mydate_day">'
                '<option value="0">---</option>'
                '<option value="1">1</option>'
                '<option value="2">2</option>'
                '<option value="3">3</option>'
                '<option value="4">4</option>'
                '<option value="5">5</option>'
                '<option value="6">6</option>'
                '<option value="7">7</option>'
                '<option value="8">8</option>'
                '<option value="9">9</option>'
                '<option value="10">10</option>'
                '<option value="11">11</option>'
                '<option value="12">12</option>'
                '<option value="13">13</option>'
                '<option value="14">14</option>'
                '<option value="15">15</option>'
                '<option value="16">16</option>'
                '<option value="17">17</option>'
                '<option value="18">18</option>'
                '<option value="19">19</option>'
                '<option value="20">20</option>'
                '<option value="21">21</option>'
                '<option value="22">22</option>'
                '<option value="23">23</option>'
                '<option value="24">24</option>'
                '<option value="25">25</option>'
                '<option value="26">26</option>'
                '<option value="27">27</option>'
                '<option value="28">28</option>'
                '<option value="29">29</option>'
                '<option value="30">30</option>'
                '<option value="31" selected>31</option>'
                '</select>'
                '<select name="mydate_month" id="id_mydate_month">'
                '<option value="0">---</option>'
                '<option value="1">\u042f\u043d\u0432\u0430\u0440\u044c</option>'
                '<option value="2">\u0424\u0435\u0432\u0440\u0430\u043b\u044c</option>'
                '<option value="3">\u041c\u0430\u0440\u0442</option>'
                '<option value="4">\u0410\u043f\u0440\u0435\u043b\u044c</option>'
                '<option value="5">\u041c\u0430\u0439</option>'
                '<option value="6">\u0418\u044e\u043d\u044c</option>'
                '<option value="7">\u0418\u044e\u043b\u044c</option>'
                '<option value="8">\u0410\u0432\u0433\u0443\u0441\u0442</option>'
                '<option value="9">\u0421\u0435\u043d\u0442\u044f\u0431\u0440\u044c</option>'
                '<option value="10">\u041e\u043a\u0442\u044f\u0431\u0440\u044c</option>'
                '<option value="11">\u041d\u043e\u044f\u0431\u0440\u044c</option>'
                '<option value="12" selected>\u0414\u0435\u043a\u0430\u0431\u0440\u044c</option>'
                '</select>'
                '<select name="mydate_year" id="id_mydate_year">'
                '<option value="0">---</option>'
                '<option value="2009" selected>2009</option>'
                '<option value="2010">2010</option>'
                '<option value="2011">2011</option>'
                '<option value="2012">2012</option>'
                '<option value="2013">2013</option>'
                '<option value="2014">2014</option>'
                '<option value="2015">2015</option>'
                '<option value="2016">2016</option>'
                '<option value="2017">2017</option>'
                '<option value="2018">2018</option>'
                '</select>',
                forms.SelectDateWidget(years=range(2009, 2019)).render('mydate', datetime.date(2009, 12, 31))
            )

        # English locale
        with translation.override('en', deactivate=True):
            self.assertEqual('N j, Y', get_format('DATE_FORMAT'))
            self.assertEqual(0, get_format('FIRST_DAY_OF_WEEK'))
            self.assertEqual('.', get_format('DECIMAL_SEPARATOR'))
            self.assertEqual('Dec. 31, 2009', date_format(self.d))
            self.assertEqual('December 2009', date_format(self.d, 'YEAR_MONTH_FORMAT'))
            self.assertEqual('12/31/2009 8:50 p.m.', date_format(self.dt, 'SHORT_DATETIME_FORMAT'))
            self.assertEqual('No localizable', localize('No localizable'))

            with self.settings(USE_THOUSAND_SEPARATOR=True):
                self.assertEqual('66,666.666', localize(self.n))
                self.assertEqual('99,999.999', localize(self.f))
                self.assertEqual('10,000', localize(self.long))

            with self.settings(USE_THOUSAND_SEPARATOR=False):
                self.assertEqual('66666.666', localize(self.n))
                self.assertEqual('99999.999', localize(self.f))
                self.assertEqual('10000', localize(self.long))
                self.assertEqual('Dec. 31, 2009', localize(self.d))
                self.assertEqual('Dec. 31, 2009, 8:50 p.m.', localize(self.dt))

            with self.settings(USE_THOUSAND_SEPARATOR=True):
                self.assertEqual('66,666.666', Template('{{ n }}').render(self.ctxt))
                self.assertEqual('99,999.999', Template('{{ f }}').render(self.ctxt))
                self.assertEqual('10,000', Template('{{ l }}').render(self.ctxt))

            with self.settings(USE_THOUSAND_SEPARATOR=False):
                self.assertEqual('66666.666', Template('{{ n }}').render(self.ctxt))
                self.assertEqual('99999.999', Template('{{ f }}').render(self.ctxt))
                self.assertEqual('Dec. 31, 2009', Template('{{ d }}').render(self.ctxt))
                self.assertEqual('Dec. 31, 2009, 8:50 p.m.', Template('{{ dt }}').render(self.ctxt))
                self.assertEqual('66666.67', Template('{{ n|floatformat:2 }}').render(self.ctxt))
                self.assertEqual('100000.0', Template('{{ f|floatformat }}').render(self.ctxt))
                self.assertEqual('12/31/2009', Template('{{ d|date:"SHORT_DATE_FORMAT" }}').render(self.ctxt))
                self.assertEqual(
                    '12/31/2009 8:50 p.m.',
                    Template('{{ dt|date:"SHORT_DATETIME_FORMAT" }}').render(self.ctxt)
                )

            form5 = I18nForm({
                'decimal_field': '66666.666',
                'float_field': '99999.999',
                'date_field': '12/31/2009',
                'datetime_field': '12/31/2009 20:50',
                'time_field': '20:50',
                'integer_field': '1234',
            })
            self.assertTrue(form5.is_valid())
            self.assertEqual(decimal.Decimal('66666.666'), form5.cleaned_data['decimal_field'])
            self.assertEqual(99999.999, form5.cleaned_data['float_field'])
            self.assertEqual(datetime.date(2009, 12, 31), form5.cleaned_data['date_field'])
            self.assertEqual(datetime.datetime(2009, 12, 31, 20, 50), form5.cleaned_data['datetime_field'])
            self.assertEqual(datetime.time(20, 50), form5.cleaned_data['time_field'])
            self.assertEqual(1234, form5.cleaned_data['integer_field'])

            form6 = SelectDateForm({
                'date_field_month': '12',
                'date_field_day': '31',
                'date_field_year': '2009'
            })
            self.assertTrue(form6.is_valid())
            self.assertEqual(datetime.date(2009, 12, 31), form6.cleaned_data['date_field'])
            self.assertHTMLEqual(
                '<select name="mydate_month" id="id_mydate_month">'
                '<option value="0">---</option>'
                '<option value="1">January</option>'
                '<option value="2">February</option>'
                '<option value="3">March</option>'
                '<option value="4">April</option>'
                '<option value="5">May</option>'
                '<option value="6">June</option>'
                '<option value="7">July</option>'
                '<option value="8">August</option>'
                '<option value="9">September</option>'
                '<option value="10">October</option>'
                '<option value="11">November</option>'
                '<option value="12" selected>December</option>'
                '</select>'
                '<select name="mydate_day" id="id_mydate_day">'
                '<option value="0">---</option>'
                '<option value="1">1</option>'
                '<option value="2">2</option>'
                '<option value="3">3</option>'
                '<option value="4">4</option>'
                '<option value="5">5</option>'
                '<option value="6">6</option>'
                '<option value="7">7</option>'
                '<option value="8">8</option>'
                '<option value="9">9</option>'
                '<option value="10">10</option>'
                '<option value="11">11</option>'
                '<option value="12">12</option>'
                '<option value="13">13</option>'
                '<option value="14">14</option>'
                '<option value="15">15</option>'
                '<option value="16">16</option>'
                '<option value="17">17</option>'
                '<option value="18">18</option>'
                '<option value="19">19</option>'
                '<option value="20">20</option>'
                '<option value="21">21</option>'
                '<option value="22">22</option>'
                '<option value="23">23</option>'
                '<option value="24">24</option>'
                '<option value="25">25</option>'
                '<option value="26">26</option>'
                '<option value="27">27</option>'
                '<option value="28">28</option>'
                '<option value="29">29</option>'
                '<option value="30">30</option>'
                '<option value="31" selected>31</option>'
                '</select>'
                '<select name="mydate_year" id="id_mydate_year">'
                '<option value="0">---</option>'
                '<option value="2009" selected>2009</option>'
                '<option value="2010">2010</option>'
                '<option value="2011">2011</option>'
                '<option value="2012">2012</option>'
                '<option value="2013">2013</option>'
                '<option value="2014">2014</option>'
                '<option value="2015">2015</option>'
                '<option value="2016">2016</option>'
                '<option value="2017">2017</option>'
                '<option value="2018">2018</option>'
                '</select>',
                forms.SelectDateWidget(years=range(2009, 2019)).render('mydate', datetime.date(2009, 12, 31))
            )

    def test_sub_locales(self):
        """
        Check if sublocales fall back to the main locale
        """
        with self.settings(USE_THOUSAND_SEPARATOR=True):
            with translation.override('de-at', deactivate=True):
                self.assertEqual('66.666,666', Template('{{ n }}').render(self.ctxt))
            with translation.override('es-us', deactivate=True):
                self.assertEqual('31 de Diciembre de 2009', date_format(self.d))

    def test_localized_input(self):
        """
        Tests if form input is correctly localized
        """
        self.maxDiff = 1200
        with translation.override('de-at', deactivate=True):
            form6 = CompanyForm({
                'name': 'acme',
                'date_added': datetime.datetime(2009, 12, 31, 6, 0, 0),
                'cents_paid': decimal.Decimal('59.47'),
                'products_delivered': 12000,
            })
            self.assertTrue(form6.is_valid())
            self.assertHTMLEqual(
                form6.as_ul(),
                '<li><label for="id_name">Name:</label>'
                '<input id="id_name" type="text" name="name" value="acme" maxlength="50" required /></li>'
                '<li><label for="id_date_added">Date added:</label>'
                '<input type="text" name="date_added" value="31.12.2009 06:00:00" id="id_date_added" required /></li>'
                '<li><label for="id_cents_paid">Cents paid:</label>'
                '<input type="text" name="cents_paid" value="59,47" id="id_cents_paid" required /></li>'
                '<li><label for="id_products_delivered">Products delivered:</label>'
                '<input type="text" name="products_delivered" value="12000" id="id_products_delivered" required />'
                '</li>'
            )
            self.assertEqual(localize_input(datetime.datetime(2009, 12, 31, 6, 0, 0)), '31.12.2009 06:00:00')
            self.assertEqual(datetime.datetime(2009, 12, 31, 6, 0, 0), form6.cleaned_data['date_added'])
            with self.settings(USE_THOUSAND_SEPARATOR=True):
                # Checking for the localized "products_delivered" field
                self.assertInHTML(
                    '<input type="text" name="products_delivered" '
                    'value="12.000" id="id_products_delivered" required />',
                    form6.as_ul()
                )

    def test_localized_input_func(self):
        with self.settings(USE_THOUSAND_SEPARATOR=True):
            self.assertEqual(localize_input(True), 'True')

    def test_sanitize_separators(self):
        """
        Tests django.utils.formats.sanitize_separators.
        """
        # Non-strings are untouched
        self.assertEqual(sanitize_separators(123), 123)

        with translation.override('ru', deactivate=True):
            # Russian locale has non-breaking space (\xa0) as thousand separator
            # Usual space is accepted too when sanitizing inputs
            with self.settings(USE_THOUSAND_SEPARATOR=True):
                self.assertEqual(sanitize_separators('1\xa0234\xa0567'), '1234567')
                self.assertEqual(sanitize_separators('77\xa0777,777'), '77777.777')
                self.assertEqual(sanitize_separators('12 345'), '12345')
                self.assertEqual(sanitize_separators('77 777,777'), '77777.777')
            with self.settings(USE_THOUSAND_SEPARATOR=True, USE_L10N=False):
                self.assertEqual(sanitize_separators('12\xa0345'), '12\xa0345')

        with self.settings(USE_THOUSAND_SEPARATOR=True):
            with patch_formats(get_language(), THOUSAND_SEPARATOR='.', DECIMAL_SEPARATOR=','):
                self.assertEqual(sanitize_separators('10.234'), '10234')
                # Suspicion that user entered dot as decimal separator (#22171)
                self.assertEqual(sanitize_separators('10.10'), '10.10')

        with self.settings(USE_L10N=False, DECIMAL_SEPARATOR=','):
            self.assertEqual(sanitize_separators('1001,10'), '1001.10')
            self.assertEqual(sanitize_separators('1001.10'), '1001.10')

        with self.settings(
            USE_L10N=False, DECIMAL_SEPARATOR=',', USE_THOUSAND_SEPARATOR=True,
            THOUSAND_SEPARATOR='.'
        ):
            self.assertEqual(sanitize_separators('1.001,10'), '1001.10')
            self.assertEqual(sanitize_separators('1001,10'), '1001.10')
            self.assertEqual(sanitize_separators('1001.10'), '1001.10')
            self.assertEqual(sanitize_separators('1,001.10'), '1.001.10')  # Invalid output

    def test_iter_format_modules(self):
        """
        Tests the iter_format_modules function.
        """
        # Importing some format modules so that we can compare the returned
        # modules with these expected modules
        default_mod = import_module('django.conf.locale.de.formats')
        test_mod = import_module('i18n.other.locale.de.formats')
        test_mod2 = import_module('i18n.other2.locale.de.formats')

        with translation.override('de-at', deactivate=True):
            # Should return the correct default module when no setting is set
            self.assertEqual(list(iter_format_modules('de')), [default_mod])

            # When the setting is a string, should return the given module and
            # the default module
            self.assertEqual(
                list(iter_format_modules('de', 'i18n.other.locale')),
                [test_mod, default_mod])

            # When setting is a list of strings, should return the given
            # modules and the default module
            self.assertEqual(
                list(iter_format_modules('de', ['i18n.other.locale', 'i18n.other2.locale'])),
                [test_mod, test_mod2, default_mod])

    def test_iter_format_modules_stability(self):
        """
        Tests the iter_format_modules function always yields format modules in
        a stable and correct order in presence of both base ll and ll_CC formats.
        """
        en_format_mod = import_module('django.conf.locale.en.formats')
        en_gb_format_mod = import_module('django.conf.locale.en_GB.formats')
        self.assertEqual(list(iter_format_modules('en-gb')), [en_gb_format_mod, en_format_mod])

    def test_get_format_modules_lang(self):
        with translation.override('de', deactivate=True):
            self.assertEqual('.', get_format('DECIMAL_SEPARATOR', lang='en'))

    def test_get_format_modules_stability(self):
        with self.settings(FORMAT_MODULE_PATH='i18n.other.locale'):
            with translation.override('de', deactivate=True):
                old = "%r" % get_format_modules(reverse=True)
                new = "%r" % get_format_modules(reverse=True)  # second try
                self.assertEqual(new, old, 'Value returned by get_formats_modules() must be preserved between calls.')

    def test_localize_templatetag_and_filter(self):
        """
        Tests the {% localize %} templatetag
        """
        context = Context({'value': 3.14})
        template1 = Template(
            '{% load l10n %}{% localize %}{{ value }}{% endlocalize %};'
            '{% localize on %}{{ value }}{% endlocalize %}'
        )
        template2 = Template("{% load l10n %}{{ value }};{% localize off %}{{ value }};{% endlocalize %}{{ value }}")
        template3 = Template('{% load l10n %}{{ value }};{{ value|unlocalize }}')
        template4 = Template('{% load l10n %}{{ value }};{{ value|localize }}')
        output1 = '3,14;3,14'
        output2 = '3,14;3.14;3,14'
        output3 = '3,14;3.14'
        output4 = '3.14;3,14'
        with translation.override('de', deactivate=True):
            with self.settings(USE_L10N=False):
                self.assertEqual(template1.render(context), output1)
                self.assertEqual(template4.render(context), output4)
            with self.settings(USE_L10N=True):
                self.assertEqual(template1.render(context), output1)
                self.assertEqual(template2.render(context), output2)
                self.assertEqual(template3.render(context), output3)

    def test_localized_as_text_as_hidden_input(self):
        """
        Tests if form input with 'as_hidden' or 'as_text' is correctly localized. Ticket #18777
        """
        self.maxDiff = 1200

        with translation.override('de-at', deactivate=True):
            template = Template('{% load l10n %}{{ form.date_added }}; {{ form.cents_paid }}')
            template_as_text = Template('{% load l10n %}{{ form.date_added.as_text }}; {{ form.cents_paid.as_text }}')
            template_as_hidden = Template(
                '{% load l10n %}{{ form.date_added.as_hidden }}; {{ form.cents_paid.as_hidden }}'
            )
            form = CompanyForm({
                'name': 'acme',
                'date_added': datetime.datetime(2009, 12, 31, 6, 0, 0),
                'cents_paid': decimal.Decimal('59.47'),
                'products_delivered': 12000,
            })
            context = Context({'form': form})
            self.assertTrue(form.is_valid())

            self.assertHTMLEqual(
                template.render(context),
                '<input id="id_date_added" name="date_added" type="text" value="31.12.2009 06:00:00" required />;'
                '<input id="id_cents_paid" name="cents_paid" type="text" value="59,47" required />'
            )
            self.assertHTMLEqual(
                template_as_text.render(context),
                '<input id="id_date_added" name="date_added" type="text" value="31.12.2009 06:00:00" required />;'
                ' <input id="id_cents_paid" name="cents_paid" type="text" value="59,47" required />'
            )
            self.assertHTMLEqual(
                template_as_hidden.render(context),
                '<input id="id_date_added" name="date_added" type="hidden" value="31.12.2009 06:00:00" />;'
                '<input id="id_cents_paid" name="cents_paid" type="hidden" value="59,47" />'
            )

    def test_format_arbitrary_settings(self):
        self.assertEqual(get_format('DEBUG'), 'DEBUG')

    def test_get_custom_format(self):
        with self.settings(FORMAT_MODULE_PATH='i18n.other.locale'):
            with translation.override('fr', deactivate=True):
                self.assertEqual('d/m/Y CUSTOM', get_format('CUSTOM_DAY_FORMAT'))

    def test_admin_javascript_supported_input_formats(self):
        """
        The first input format for DATE_INPUT_FORMATS, TIME_INPUT_FORMATS, and
        DATETIME_INPUT_FORMATS must not contain %f since that's unsupported by
        the admin's time picker widget.
        """
        regex = re.compile('%([^BcdHImMpSwxXyY%])')
        for language_code, language_name in settings.LANGUAGES:
            for format_name in ('DATE_INPUT_FORMATS', 'TIME_INPUT_FORMATS', 'DATETIME_INPUT_FORMATS'):
                with self.subTest(language=language_code, format=format_name):
                    formatter = get_format(format_name, lang=language_code)[0]
                    self.assertEqual(
                        regex.findall(formatter), [],
                        "%s locale's %s uses an unsupported format code." % (language_code, format_name)
                    )


class MiscTests(SimpleTestCase):

    def setUp(self):
        super().setUp()
        self.rf = RequestFactory()

    @override_settings(LANGUAGE_CODE='de')
    def test_english_fallback(self):
        """
        With a non-English LANGUAGE_CODE and if the active language is English
        or one of its variants, the untranslated string should be returned
        (instead of falling back to LANGUAGE_CODE) (See #24413).
        """
        self.assertEqual(gettext("Image"), "Bild")
        with translation.override('en'):
            self.assertEqual(gettext("Image"), "Image")
        with translation.override('en-us'):
            self.assertEqual(gettext("Image"), "Image")
        with translation.override('en-ca'):
            self.assertEqual(gettext("Image"), "Image")

    def test_parse_spec_http_header(self):
        """
        Testing HTTP header parsing. First, we test that we can parse the
        values according to the spec (and that we extract all the pieces in
        the right order).
        """
        p = trans_real.parse_accept_lang_header
        # Good headers.
        self.assertEqual([('de', 1.0)], p('de'))
        self.assertEqual([('en-au', 1.0)], p('en-AU'))
        self.assertEqual([('es-419', 1.0)], p('es-419'))
        self.assertEqual([('*', 1.0)], p('*;q=1.00'))
        self.assertEqual([('en-au', 0.123)], p('en-AU;q=0.123'))
        self.assertEqual([('en-au', 0.5)], p('en-au;q=0.5'))
        self.assertEqual([('en-au', 1.0)], p('en-au;q=1.0'))
        self.assertEqual([('da', 1.0), ('en', 0.5), ('en-gb', 0.25)], p('da, en-gb;q=0.25, en;q=0.5'))
        self.assertEqual([('en-au-xx', 1.0)], p('en-au-xx'))
        self.assertEqual(
            [('de', 1.0), ('en-au', 0.75), ('en-us', 0.5), ('en', 0.25), ('es', 0.125), ('fa', 0.125)],
            p('de,en-au;q=0.75,en-us;q=0.5,en;q=0.25,es;q=0.125,fa;q=0.125')
        )
        self.assertEqual([('*', 1.0)], p('*'))
        self.assertEqual([('de', 0.0)], p('de;q=0.'))
        self.assertEqual([('en', 1.0), ('*', 0.5)], p('en; q=1.0, * ; q=0.5'))
        self.assertEqual([('en', 1.0)], p('en; q=1,'))
        self.assertEqual([], p(''))

        # Bad headers; should always return [].
        self.assertEqual([], p('en-gb;q=1.0000'))
        self.assertEqual([], p('en;q=0.1234'))
        self.assertEqual([], p('en;q=.2'))
        self.assertEqual([], p('abcdefghi-au'))
        self.assertEqual([], p('**'))
        self.assertEqual([], p('en,,gb'))
        self.assertEqual([], p('en-au;q=0.1.0'))
        self.assertEqual(
            [],
            p('XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXZ,en')
        )
        self.assertEqual([], p('da, en-gb;q=0.8, en;q=0.7,#'))
        self.assertEqual([], p('de;q=2.0'))
        self.assertEqual([], p('de;q=0.a'))
        self.assertEqual([], p('12-345'))
        self.assertEqual([], p(''))
        self.assertEqual([], p('en;q=1e0'))

    def test_parse_literal_http_header(self):
        """
        Now test that we parse a literal HTTP header correctly.
        """
        g = get_language_from_request
        r = self.rf.get('/')
        r.COOKIES = {}
        r.META = {'HTTP_ACCEPT_LANGUAGE': 'pt-br'}
        self.assertEqual('pt-br', g(r))

        r.META = {'HTTP_ACCEPT_LANGUAGE': 'pt'}
        self.assertEqual('pt', g(r))

        r.META = {'HTTP_ACCEPT_LANGUAGE': 'es,de'}
        self.assertEqual('es', g(r))

        r.META = {'HTTP_ACCEPT_LANGUAGE': 'es-ar,de'}
        self.assertEqual('es-ar', g(r))

        # This test assumes there won't be a Django translation to a US
        # variation of the Spanish language, a safe assumption. When the
        # user sets it as the preferred language, the main 'es'
        # translation should be selected instead.
        r.META = {'HTTP_ACCEPT_LANGUAGE': 'es-us'}
        self.assertEqual(g(r), 'es')

        # This tests the following scenario: there isn't a main language (zh)
        # translation of Django but there is a translation to variation (zh-hans)
        # the user sets zh-hans as the preferred language, it should be selected
        # by Django without falling back nor ignoring it.
        r.META = {'HTTP_ACCEPT_LANGUAGE': 'zh-hans,de'}
        self.assertEqual(g(r), 'zh-hans')

        r.META = {'HTTP_ACCEPT_LANGUAGE': 'NL'}
        self.assertEqual('nl', g(r))

        r.META = {'HTTP_ACCEPT_LANGUAGE': 'fy'}
        self.assertEqual('fy', g(r))

        r.META = {'HTTP_ACCEPT_LANGUAGE': 'ia'}
        self.assertEqual('ia', g(r))

        r.META = {'HTTP_ACCEPT_LANGUAGE': 'sr-latn'}
        self.assertEqual('sr-latn', g(r))

        r.META = {'HTTP_ACCEPT_LANGUAGE': 'zh-hans'}
        self.assertEqual('zh-hans', g(r))

        r.META = {'HTTP_ACCEPT_LANGUAGE': 'zh-hant'}
        self.assertEqual('zh-hant', g(r))

    @override_settings(
        LANGUAGES=[
            ('en', 'English'),
            ('zh-hans', 'Simplified Chinese'),
            ('zh-hant', 'Traditional Chinese'),
        ]
    )
    def test_support_for_deprecated_chinese_language_codes(self):
        """
        Some browsers (Firefox, IE, etc.) use deprecated language codes. As these
        language codes will be removed in Django 1.9, these will be incorrectly
        matched. For example zh-tw (traditional) will be interpreted as zh-hans
        (simplified), which is wrong. So we should also accept these deprecated
        language codes.

        refs #18419 -- this is explicitly for browser compatibility
        """
        g = get_language_from_request
        r = self.rf.get('/')
        r.COOKIES = {}
        r.META = {'HTTP_ACCEPT_LANGUAGE': 'zh-cn,en'}
        self.assertEqual(g(r), 'zh-hans')

        r.META = {'HTTP_ACCEPT_LANGUAGE': 'zh-tw,en'}
        self.assertEqual(g(r), 'zh-hant')

    def test_special_fallback_language(self):
        """
        Some languages may have special fallbacks that don't follow the simple
        'fr-ca' -> 'fr' logic (notably Chinese codes).
        """
        r = self.rf.get('/')
        r.COOKIES = {}
        r.META = {'HTTP_ACCEPT_LANGUAGE': 'zh-my,en'}
        self.assertEqual(get_language_from_request(r), 'zh-hans')

    def test_parse_language_cookie(self):
        """
        Now test that we parse language preferences stored in a cookie correctly.
        """
        g = get_language_from_request
        r = self.rf.get('/')
        r.COOKIES = {settings.LANGUAGE_COOKIE_NAME: 'pt-br'}
        r.META = {}
        self.assertEqual('pt-br', g(r))

        r.COOKIES = {settings.LANGUAGE_COOKIE_NAME: 'pt'}
        r.META = {}
        self.assertEqual('pt', g(r))

        r.COOKIES = {settings.LANGUAGE_COOKIE_NAME: 'es'}
        r.META = {'HTTP_ACCEPT_LANGUAGE': 'de'}
        self.assertEqual('es', g(r))

        # This test assumes there won't be a Django translation to a US
        # variation of the Spanish language, a safe assumption. When the
        # user sets it as the preferred language, the main 'es'
        # translation should be selected instead.
        r.COOKIES = {settings.LANGUAGE_COOKIE_NAME: 'es-us'}
        r.META = {}
        self.assertEqual(g(r), 'es')

        # This tests the following scenario: there isn't a main language (zh)
        # translation of Django but there is a translation to variation (zh-hans)
        # the user sets zh-hans as the preferred language, it should be selected
        # by Django without falling back nor ignoring it.
        r.COOKIES = {settings.LANGUAGE_COOKIE_NAME: 'zh-hans'}
        r.META = {'HTTP_ACCEPT_LANGUAGE': 'de'}
        self.assertEqual(g(r), 'zh-hans')

    @override_settings(
        LANGUAGES=[
            ('en', 'English'),
            ('de', 'German'),
            ('de-at', 'Austrian German'),
            ('pl', 'Polish'),
        ],
    )
    def test_get_language_from_path_real(self):
        g = trans_real.get_language_from_path
        self.assertEqual(g('/pl/'), 'pl')
        self.assertEqual(g('/pl'), 'pl')
        self.assertIsNone(g('/xyz/'))
        self.assertEqual(g('/en/'), 'en')
        self.assertEqual(g('/en-gb/'), 'en')
        self.assertEqual(g('/de/'), 'de')
        self.assertEqual(g('/de-at/'), 'de-at')
        self.assertEqual(g('/de-ch/'), 'de')
        self.assertIsNone(g('/de-simple-page/'))

    def test_get_language_from_path_null(self):
        from django.utils.translation.trans_null import get_language_from_path as g
        self.assertIsNone(g('/pl/'))
        self.assertIsNone(g('/pl'))
        self.assertIsNone(g('/xyz/'))

    def test_cache_resetting(self):
        """
        After setting LANGUAGE, the cache should be cleared and languages
        previously valid should not be used (#14170).
        """
        g = get_language_from_request
        r = self.rf.get('/')
        r.COOKIES = {}
        r.META = {'HTTP_ACCEPT_LANGUAGE': 'pt-br'}
        self.assertEqual('pt-br', g(r))
        with self.settings(LANGUAGES=[('en', 'English')]):
            self.assertNotEqual('pt-br', g(r))

    def test_i18n_patterns_returns_list(self):
        with override_settings(USE_I18N=False):
            self.assertIsInstance(i18n_patterns([]), list)
        with override_settings(USE_I18N=True):
            self.assertIsInstance(i18n_patterns([]), list)


class ResolutionOrderI18NTests(SimpleTestCase):

    def setUp(self):
        super().setUp()
        activate('de')

    def tearDown(self):
        deactivate()
        super().tearDown()

    def assertGettext(self, msgid, msgstr):
        result = gettext(msgid)
        self.assertIn(
            msgstr, result,
            "The string '%s' isn't in the translation of '%s'; the actual result is '%s'."
            % (msgstr, msgid, result)
        )


class AppResolutionOrderI18NTests(ResolutionOrderI18NTests):

    @override_settings(LANGUAGE_CODE='de')
    def test_app_translation(self):
        # Original translation.
        self.assertGettext('Date/time', 'Datum/Zeit')

        # Different translation.
        with self.modify_settings(INSTALLED_APPS={'append': 'i18n.resolution'}):
            # Force refreshing translations.
            activate('de')

            # Doesn't work because it's added later in the list.
            self.assertGettext('Date/time', 'Datum/Zeit')

            with self.modify_settings(INSTALLED_APPS={'remove': 'django.contrib.admin.apps.SimpleAdminConfig'}):
                # Force refreshing translations.
                activate('de')

                # Unless the original is removed from the list.
                self.assertGettext('Date/time', 'Datum/Zeit (APP)')


@override_settings(LOCALE_PATHS=extended_locale_paths)
class LocalePathsResolutionOrderI18NTests(ResolutionOrderI18NTests):

    def test_locale_paths_translation(self):
        self.assertGettext('Time', 'LOCALE_PATHS')

    def test_locale_paths_override_app_translation(self):
        with self.settings(INSTALLED_APPS=['i18n.resolution']):
            self.assertGettext('Time', 'LOCALE_PATHS')


class DjangoFallbackResolutionOrderI18NTests(ResolutionOrderI18NTests):

    def test_django_fallback(self):
        self.assertEqual(gettext('Date/time'), 'Datum/Zeit')


class TestModels(TestCase):
    def test_lazy(self):
        tm = TestModel()
        tm.save()

    def test_safestr(self):
        c = Company(cents_paid=12, products_delivered=1)
        c.name = SafeText('Iñtërnâtiônàlizætiøn1')
        c.save()


class TestLanguageInfo(SimpleTestCase):
    def test_localized_language_info(self):
        li = get_language_info('de')
        self.assertEqual(li['code'], 'de')
        self.assertEqual(li['name_local'], 'Deutsch')
        self.assertEqual(li['name'], 'German')
        self.assertIs(li['bidi'], False)

    def test_unknown_language_code(self):
        with self.assertRaisesMessage(KeyError, "Unknown language code xx"):
            get_language_info('xx')
        with translation.override('xx'):
            # A language with no translation catalogs should fallback to the
            # untranslated string.
            self.assertEqual(gettext("Title"), "Title")

    def test_unknown_only_country_code(self):
        li = get_language_info('de-xx')
        self.assertEqual(li['code'], 'de')
        self.assertEqual(li['name_local'], 'Deutsch')
        self.assertEqual(li['name'], 'German')
        self.assertIs(li['bidi'], False)

    def test_unknown_language_code_and_country_code(self):
        with self.assertRaisesMessage(KeyError, "Unknown language code xx-xx and xx"):
            get_language_info('xx-xx')

    def test_fallback_language_code(self):
        """
        get_language_info return the first fallback language info if the lang_info
        struct does not contain the 'name' key.
        """
        li = get_language_info('zh-my')
        self.assertEqual(li['code'], 'zh-hans')
        li = get_language_info('zh-hans')
        self.assertEqual(li['code'], 'zh-hans')


@override_settings(
    USE_I18N=True,
    LANGUAGES=[
        ('en', 'English'),
        ('fr', 'French'),
    ],
    MIDDLEWARE=[
        'django.middleware.locale.LocaleMiddleware',
        'django.middleware.common.CommonMiddleware',
    ],
    ROOT_URLCONF='i18n.urls',
)
class LocaleMiddlewareTests(TestCase):

    def test_streaming_response(self):
        # Regression test for #5241
        response = self.client.get('/fr/streaming/')
        self.assertContains(response, "Oui/Non")
        response = self.client.get('/en/streaming/')
        self.assertContains(response, "Yes/No")

    @override_settings(
        MIDDLEWARE=[
            'django.contrib.sessions.middleware.SessionMiddleware',
            'django.middleware.locale.LocaleMiddleware',
            'django.middleware.common.CommonMiddleware',
        ],
    )
    def test_language_not_saved_to_session(self):
        """
        The Current language isno' automatically saved to the session on every
        request (#21473).
        """
        self.client.get('/fr/simple/')
        self.assertNotIn(LANGUAGE_SESSION_KEY, self.client.session)


@override_settings(
    USE_I18N=True,
    LANGUAGES=[
        ('en', 'English'),
        ('de', 'German'),
        ('fr', 'French'),
    ],
    MIDDLEWARE=[
        'django.middleware.locale.LocaleMiddleware',
        'django.middleware.common.CommonMiddleware',
    ],
    ROOT_URLCONF='i18n.urls_default_unprefixed',
    LANGUAGE_CODE='en',
)
class UnprefixedDefaultLanguageTests(SimpleTestCase):
    def test_default_lang_without_prefix(self):
        """
        With i18n_patterns(..., prefix_default_language=False), the default
        language (settings.LANGUAGE_CODE) should be accessible without a prefix.
        """
        response = self.client.get('/simple/')
        self.assertEqual(response.content, b'Yes')

    def test_other_lang_with_prefix(self):
        response = self.client.get('/fr/simple/')
        self.assertEqual(response.content, b'Oui')

    def test_unprefixed_language_other_than_accept_language(self):
        response = self.client.get('/simple/', HTTP_ACCEPT_LANGUAGE='fr')
        self.assertEqual(response.content, b'Yes')

    def test_page_with_dash(self):
        # A page starting with /de* shouldn't match the 'de' language code.
        response = self.client.get('/de-simple-page/')
        self.assertEqual(response.content, b'Yes')

    def test_no_redirect_on_404(self):
        """
        A request for a nonexistent URL shouldn't cause a redirect to
        /<defaut_language>/<request_url> when prefix_default_language=False and
        /<default_language>/<request_url> has a URL match (#27402).
        """
        # A match for /group1/group2/ must exist for this to act as a
        # regression test.
        response = self.client.get('/group1/group2/')
        self.assertEqual(response.status_code, 200)

        response = self.client.get('/nonexistent/')
        self.assertEqual(response.status_code, 404)


@override_settings(
    USE_I18N=True,
    LANGUAGES=[
        ('bg', 'Bulgarian'),
        ('en-us', 'English'),
        ('pt-br', 'Portuguese (Brazil)'),
    ],
    MIDDLEWARE=[
        'django.middleware.locale.LocaleMiddleware',
        'django.middleware.common.CommonMiddleware',
    ],
    ROOT_URLCONF='i18n.urls'
)
class CountrySpecificLanguageTests(SimpleTestCase):

    def setUp(self):
        super().setUp()
        self.rf = RequestFactory()

    def test_check_for_language(self):
        self.assertTrue(check_for_language('en'))
        self.assertTrue(check_for_language('en-us'))
        self.assertTrue(check_for_language('en-US'))
        self.assertTrue(check_for_language('be'))
        self.assertTrue(check_for_language('be@latin'))
        self.assertTrue(check_for_language('sr-RS@latin'))
        self.assertTrue(check_for_language('sr-RS@12345'))
        self.assertFalse(check_for_language('en-ü'))
        self.assertFalse(check_for_language('en\x00'))
        self.assertFalse(check_for_language(None))
        self.assertFalse(check_for_language('be@ '))
        # Specifying encoding is not supported (Django enforces UTF-8)
        self.assertFalse(check_for_language('tr-TR.UTF-8'))
        self.assertFalse(check_for_language('tr-TR.UTF8'))
        self.assertFalse(check_for_language('de-DE.utf-8'))

    def test_get_language_from_request(self):
        # issue 19919
        r = self.rf.get('/')
        r.COOKIES = {}
        r.META = {'HTTP_ACCEPT_LANGUAGE': 'en-US,en;q=0.8,bg;q=0.6,ru;q=0.4'}
        lang = get_language_from_request(r)
        self.assertEqual('en-us', lang)
        r = self.rf.get('/')
        r.COOKIES = {}
        r.META = {'HTTP_ACCEPT_LANGUAGE': 'bg-bg,en-US;q=0.8,en;q=0.6,ru;q=0.4'}
        lang = get_language_from_request(r)
        self.assertEqual('bg', lang)

    def test_specific_language_codes(self):
        # issue 11915
        r = self.rf.get('/')
        r.COOKIES = {}
        r.META = {'HTTP_ACCEPT_LANGUAGE': 'pt,en-US;q=0.8,en;q=0.6,ru;q=0.4'}
        lang = get_language_from_request(r)
        self.assertEqual('pt-br', lang)
        r = self.rf.get('/')
        r.COOKIES = {}
        r.META = {'HTTP_ACCEPT_LANGUAGE': 'pt-pt,en-US;q=0.8,en;q=0.6,ru;q=0.4'}
        lang = get_language_from_request(r)
        self.assertEqual('pt-br', lang)


class TranslationFilesMissing(SimpleTestCase):

    def setUp(self):
        super().setUp()
        self.gettext_find_builtin = gettext_module.find

    def tearDown(self):
        gettext_module.find = self.gettext_find_builtin
        super().tearDown()

    def patchGettextFind(self):
        gettext_module.find = lambda *args, **kw: None

    def test_failure_finding_default_mo_files(self):
        '''
        Ensure IOError is raised if the default language is unparseable.
        Refs: #18192
        '''
        self.patchGettextFind()
        trans_real._translations = {}
        with self.assertRaises(IOError):
            activate('en')


class NonDjangoLanguageTests(SimpleTestCase):
    """
    A language non present in default Django languages can still be
    installed/used by a Django project.
    """
    @override_settings(
        USE_I18N=True,
        LANGUAGES=[
            ('en-us', 'English'),
            ('xxx', 'Somelanguage'),
        ],
        LANGUAGE_CODE='xxx',
        LOCALE_PATHS=[os.path.join(here, 'commands', 'locale')],
    )
    def test_non_django_language(self):
        self.assertEqual(get_language(), 'xxx')
        self.assertEqual(gettext("year"), "reay")

    @override_settings(
        USE_I18N=True,
        LANGUAGES=[
            ('en-us', 'English'),
            # xyz language has no locale files
            ('xyz', 'XYZ'),
        ],
    )
    @translation.override('xyz')
    def test_plural_non_django_language(self):
        self.assertEqual(get_language(), 'xyz')
        self.assertEqual(ngettext('year', 'years', 2), 'years')
