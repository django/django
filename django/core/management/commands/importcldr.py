import sys
import os
import re
from optparse import make_option, OptionParser

from django.core.management.base import LabelCommand, CommandError

try:
    from lxml import etree
except ImportError:
    raise CommandError('You need to install `python-lxml` to run this script')

FORMATS_FILE_NAME = 'formats.py'
FORMATS_FILE_HEADER = '''# -*- encoding: utf-8 -*-
# This file is distributed under the same license as the Django package.
#

'''

def quote(nodes, name,  locale, previous):
    if len(nodes):
        return "'%s'" % unicode(nodes[0].text).replace("'", "\\'")
    else:
        return None

def convert_time(nodes, name,  locale, previous):
    SPECIAL_CHARS = ('a', 'A', 'b', 'B', 'd', 'D', 'f', 'F', 'g', 'G', 'h',
        'H', 'i', 'I', 'j', 'l', 'L', 'm', 'M', 'n', 'N', 'O', 'P', 'r',
        's', 'S', 't', 'T', 'U', 'w', 'W', 'y', 'Y', 'z', 'Z')
    FORMAT_STR_MAP = ( # not using a dict, because we have to apply formats in order
        ('dd', 'd'),
        ('d', 'j'),
        ('MMMM', 'F'),
        ('MMM', 'M'),
        ('MM', 'm'),
        ('M', 'n'),
        ('yyyy', 'Y'),
        ('yy', 'y'),
        ('y', 'Y'),
        ('hh', 'h'),
        ('h', 'g'),
        ('HH', 'H'),
        ('H', 'G'),
        ('mm', 'i'),
        ('ss', 's'),
        ('a', 'A'),
        ('LLLL', 'F'),
    )
    if len(nodes):
        original = nodes[0].text
        result = ''
        for cnt, segment in enumerate(original.split("'")):
            if cnt % 2:
                for char in SPECIAL_CHARS:
                    segment = segment.replace(char, '\\%s' % char)
                result += segment
            else:
                while segment:
                    found = False
                    for src, dst in FORMAT_STR_MAP:
                        if segment[0:len(src)] == src:
                            result += dst
                            segment = segment[len(src):]
                            found = True
                            break
                    if not found:
                        result += segment[0]
                        segment = segment[1:]

        return "'%s'" % result
    else:
        return None

def datetime(nodes, name, locale, previous):
    result = None
    if len(nodes) and 'DATE_FORMAT' in previous and 'TIME_FORMAT' in previous:
        result = nodes[0].text
        result = result.replace('{0}', previous['TIME_FORMAT'][1:-1])
        if name == 'SHORT_DATETIME_FORMAT' and 'SHORT_DATE_FORMAT' in previous:
            result = result.replace('{1}', previous['SHORT_DATE_FORMAT'][1:-1])
        else:
            result = result.replace('{1}', previous['DATE_FORMAT'][1:-1])
    if result:
        return "'%s'" % result
    else:
        return None

FORMATS_MAP = [
    {
        'name': 'DATE_FORMAT',
        'file': os.path.join('common', 'main', '%(locale)s.xml'),
        'pattern': "/ldml/dates/calendars/calendar[@type='gregorian']/dateFormats/dateFormatLength[@type='long']/dateFormat/pattern",
        'conversion': convert_time,
    },
    {
        'name': 'TIME_FORMAT',
        'file': os.path.join('common', 'main', '%(locale)s.xml'),
        'pattern': "/ldml/dates/calendars/calendar[@type='gregorian']/timeFormats/timeFormatLength[@type='medium']/timeFormat/pattern",
        'conversion': convert_time,
    },
    {
        'name': 'DATETIME_FORMAT',
        'file': os.path.join('common', 'main', '%(locale)s.xml'),
        'pattern': "/ldml/dates/calendars/calendar[@type='gregorian']/dateTimeFormats/dateTimeFormatLength[@type='long']/dateTimeFormat/pattern",
        'conversion': datetime,
    },
    {
        'name': 'YEAR_MONTH_FORMAT',
        'file': os.path.join('common', 'main', '%(locale)s.xml'),
        'pattern': "/ldml/dates/calendars/calendar[@type='gregorian']/dateTimeFormats/availableFormats/dateFormatItem[@id='yMMMM']",
        'conversion': convert_time,
    },
    {
        'name': 'MONTH_DAY_FORMAT',
        'file': os.path.join('common', 'main', '%(locale)s.xml'),
        'pattern': "/ldml/dates/calendars/calendar[@type='gregorian']/dateTimeFormats/availableFormats/dateFormatItem[@id='MMMMd']",
        'conversion': convert_time,
    },
    {
        'name': 'SHORT_DATE_FORMAT',
        'file': os.path.join('common', 'main', '%(locale)s.xml'),
        'pattern': "/ldml/dates/calendars/calendar[@type='gregorian']/dateFormats/dateFormatLength[@type='medium']/dateFormat/pattern",
        'conversion': convert_time,
    },
    {
        'name': 'SHORT_DATETIME_FORMAT',
        'file': os.path.join('common', 'main', '%(locale)s.xml'),
        'pattern': "/ldml/dates/calendars/calendar[@type='gregorian']/dateTimeFormats/dateTimeFormatLength[@type='short']/dateTimeFormat/pattern",
        'conversion': datetime,
    },
    {'name': 'FIRST_DAY_OF_WEEK'},
    {'name': 'DATE_INPUT_FORMATS'},
    {'name': 'TIME_INPUT_FORMATS'},
    {'name': 'DATETIME_INPUT_FORMATS'},
    {
        'name': 'DECIMAL_SEPARATOR',
        'file': os.path.join('common', 'main', '%(locale)s.xml'),
        'pattern': "/ldml/numbers/symbols/decimal",
        'conversion': quote,
    },
    {
        'name': 'THOUSAND_SEPARATOR',
        'file': os.path.join('common', 'main', '%(locale)s.xml'),
        'pattern': "/ldml/numbers/symbols/group",
        'conversion': quote,
    },
    {'name': 'NUMBER_GROUPING'},
]
"""
"""

def get_locales(django_locale_dir, locale=None):
    if locale:
        yield locale
    else:
        locale_re = re.compile('[a-z]{2}(_[A-Z]{2})?')
        for locale in os.listdir(django_locale_dir):
            if locale_re.match(locale):
                yield locale

def import_cldr(cldr_dir, locale=None, overwrite=False):
    """
    For every locale defined in Django, get from the CLDR locale file all
    settings defined in output_structure, and write the result to the 
    locale directories on Django.
    """
    if not os.path.isdir(cldr_dir):
        raise Exception, "Specified CLDR directory '%s' does not exist" % cldr_dir

    import django
    django_locale_dir = os.path.join(os.path.dirname(django.__file__), 'conf', 'locale')

    for locale in get_locales(django_locale_dir, locale):
        output_filename = os.path.join(django_locale_dir, locale, FORMATS_FILE_NAME)
        if os.path.isfile(output_filename) and not overwrite:
            print "'%s' locale already exists. Skipping" % locale
        else:
            result = {}
            output_file = open(output_filename, 'w')
            output_file.write(FORMATS_FILE_HEADER)
            for format in FORMATS_MAP:
                if 'file' in format:
                    cldr_file = os.path.join(cldr_dir, format['file'] % dict(locale=locale))
                    tree = etree.parse(cldr_file) # TODO: error control
                    try:
                        original_value = tree.xpath(format['pattern'])
                    except IndexError:
                        output_file.write('# %s = \n' % (format['name']))
                    else:
                        value = format['conversion'](original_value, format['name'], locale, result)
                        if value:
                            output_file.write('%s = %s\n' % (format['name'], value.encode('utf8')))
                            result[format['name']] = value
                        else:
                            output_file.write('# %s = \n' % (format['name']))
                else:
                    output_file.write('# %s = \n' % (format['name']))
            output_file.close()

            init_filename = os.path.join(django_locale_dir, locale, '__init__.py')
            open(init_filename, 'a').close()

class Command(LabelCommand):
    option_list = LabelCommand.option_list + (
        make_option('--locale', '-l', dest='locale',
            help='The locale to process. Default is to process all.'),
    ) + (
        make_option('--overwite', '-o', action='store_true', dest='overwrite',
            help='Wheter to overwrite format definitions of locales that already have one.'),
    )
    help = 'Creates format definition files for locales, importing data from the CLDR.'
    args = '[cldrpath]'
    label = 'CLDR path'
    requires_model_validation = False
    can_import_settings = False

    def handle_label(self, cldrpath, **options):
        locale = options.get('locale')
        overwrite = options.get('overwrite')
        import_cldr(cldrpath, locale, overwrite)

