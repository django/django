#!/usr/bin/env python
#
# This python file contains utility scripts to manage Django translations.
# It has to be run inside the django git root directory.
#
# The following commands are available:
#
# * update_catalogs: check for new strings in core and contrib catalogs, and
#                    output how much strings are new/changed.
#
# * lang_stats: output statistics for each catalog/language combination
#
# * fetch: fetch translations from transifex.com
#
# Each command support the --languages and --resources options to limit their
# operation to the specified language or resource. For example, to get stats
# for Spanish in contrib.admin, run:
#
#  $ python scripts/manage_translations.py lang_stats --language=es --resources=admin

import os
from optparse import OptionParser
from subprocess import call, Popen, PIPE

from django.core.management import call_command


HAVE_JS = ['admin']

def _get_locale_dirs(include_core=True):
    """
    Return a tuple (contrib name, absolute path) for all locale directories,
    optionally including the django core catalog.
    """
    contrib_dir = os.path.join(os.getcwd(), 'django', 'contrib')
    dirs = []
    for contrib_name in os.listdir(contrib_dir):
        path = os.path.join(contrib_dir, contrib_name, 'locale')
        if os.path.isdir(path):
            dirs.append((contrib_name, path))
            if contrib_name in HAVE_JS:
                dirs.append(("%s-js" % contrib_name, path))
    if include_core:
        dirs.insert(0, ('core', os.path.join(os.getcwd(), 'django', 'conf', 'locale')))
    return dirs

def _tx_resource_for_name(name):
    """ Return the Transifex resource name """
    if name == 'core':
        return "django-core.core"
    else:
        return "django-core.contrib-%s" % name

def _check_diff(cat_name, base_path):
    """
    Output the approximate number of changed/added strings in the en catalog.
    """
    po_path = '%(path)s/en/LC_MESSAGES/django%(ext)s.po' % {
        'path': base_path, 'ext': 'js' if cat_name.endswith('-js') else ''}
    p = Popen("git diff -U0 %s | egrep -v '^@@|^[-+]#|^..POT-Creation' | wc -l" % po_path,
              stdout=PIPE, stderr=PIPE, shell=True)
    output, errors = p.communicate()
    num_changes = int(output.strip()) - 4
    print("%d changed/added messages in '%s' catalog." % (num_changes, cat_name))


def update_catalogs(resources=None, languages=None):
    """
    Update the en/LC_MESSAGES/django.po (main and contrib) files with
    new/updated translatable strings.
    """
    contrib_dirs = _get_locale_dirs(include_core=False)

    os.chdir(os.path.join(os.getcwd(), 'django'))
    print("Updating main en catalog")
    call_command('makemessages', locale='en')
    _check_diff('core', os.path.join(os.getcwd(), 'conf', 'locale'))

    # Contrib catalogs
    for name, dir_ in contrib_dirs:
        if resources and not name in resources:
            continue
        os.chdir(os.path.join(dir_, '..'))
        print("Updating en catalog in %s" % dir_)
        if name.endswith('-js'):
            call_command('makemessages', locale='en', domain='djangojs')
        else:
            call_command('makemessages', locale='en')
        _check_diff(name, dir_)


def lang_stats(resources=None, languages=None):
    """
    Output language statistics of committed translation files for each
    Django catalog.
    If resources is provided, it should be a list of translation resource to
    limit the output (e.g. ['core', 'gis']).
    """
    locale_dirs = _get_locale_dirs()

    for name, dir_ in locale_dirs:
        if resources and not name in resources:
            continue
        print("\nShowing translations stats for '%s':" % name) 
        langs = sorted([d for d in os.listdir(dir_) if not d.startswith('_')])
        for lang in langs:
            if languages and not lang in languages:
                continue
            # TODO: merge first with the latest en catalog
            p = Popen("msgfmt -vc -o /dev/null %(path)s/%(lang)s/LC_MESSAGES/django%(ext)s.po" % {
                'path': dir_, 'lang': lang, 'ext': 'js' if name.endswith('-js') else ''},
                stdout=PIPE, stderr=PIPE, shell=True)
            output, errors = p.communicate()
            if p.returncode == 0:
                # msgfmt output stats on stderr
                print("%s: %s" % (lang, errors.strip()))
            else:
                print("Errors happened when checking %s translation for %s:\n%s" % (
                    lang, name, errors))


def fetch(resources=None, languages=None):
    """
    Fetch translations from Transifex, wrap long lines, generate mo files.
    """
    locale_dirs = _get_locale_dirs()
    errors = []

    for name, dir_ in locale_dirs:
        if resources and not name in resources:
            continue

        # Transifex pull
        if languages is None:
            call('tx pull -r %(res)s -a -f' % {'res': _tx_resource_for_name(name)}, shell=True)
            languages = sorted([d for d in os.listdir(dir_) if not d.startswith('_')])
        else:
            for lang in languages:
                call('tx pull -r %(res)s -f -l %(lang)s' % {
                    'res': _tx_resource_for_name(name), 'lang': lang}, shell=True)

        # msgcat to wrap lines and msgfmt for compilation of .mo file
        for lang in languages:
            po_path = '%(path)s/%(lang)s/LC_MESSAGES/django%(ext)s.po' % {
                'path': dir_, 'lang': lang, 'ext': 'js' if name.endswith('-js') else ''}
            call('msgcat -o %s %s' % (po_path, po_path), shell=True)
            res = call('msgfmt -c -o %s.mo %s' % (po_path[:-3], po_path), shell=True)
            if res != 0:
                errors.append((name, lang))
    if errors:
        print("\nWARNING: Errors have occurred in following cases:")
        for resource, lang in errors:
            print("\tResource %s for language %s" % (resource, lang))
        exit(1)


if __name__ == "__main__":
    RUNABLE_SCRIPTS = ('update_catalogs', 'lang_stats', 'fetch')

    parser = OptionParser(usage="usage: %prog [options] cmd")
    parser.add_option("-r", "--resources", action='append',
        help="limit operation to the specified resources")
    parser.add_option("-l", "--languages", action='append',
        help="limit operation to the specified languages")
    options, args = parser.parse_args()

    if not args:
        parser.print_usage()
        exit(1)

    if args[0] in RUNABLE_SCRIPTS:
        eval(args[0])(options.resources, options.languages)
    else:
        print("Available commands are: %s" % ", ".join(RUNABLE_SCRIPTS))
