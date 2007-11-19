#!/usr/bin/env python

import optparse
import os
import sys

try:
    set
except NameError:
    from sets import Set as set     # For Python 2.3


def compile_messages(locale=None):
    basedirs = (os.path.join('conf', 'locale'), 'locale')
    if os.environ.get('DJANGO_SETTINGS_MODULE'):
        from django.conf import settings
        basedirs += settings.LOCALE_PATHS

    # Gather existing directories.
    basedirs = set(map(os.path.abspath, filter(os.path.isdir, basedirs)))

    if not basedirs:
        print "This script should be run from the Django SVN tree or your project or app tree, or with the settings module specified."
        sys.exit(1)

    for basedir in basedirs:
        if locale:
            basedir = os.path.join(basedir, locale, 'LC_MESSAGES')
        compile_messages_in_dir(basedir)

def compile_messages_in_dir(basedir):
    for dirpath, dirnames, filenames in os.walk(basedir):
        for f in filenames:
            if f.endswith('.po'):
                sys.stderr.write('processing file %s in %s\n' % (f, dirpath))
                pf = os.path.splitext(os.path.join(dirpath, f))[0]
                # Store the names of the .mo and .po files in an environment
                # variable, rather than doing a string replacement into the
                # command, so that we can take advantage of shell quoting, to
                # quote any malicious characters/escaping.
                # See http://cyberelk.net/tim/articles/cmdline/ar01s02.html
                os.environ['djangocompilemo'] = pf + '.mo'
                os.environ['djangocompilepo'] = pf + '.po'
                if sys.platform == 'win32': # Different shell-variable syntax
                    cmd = 'msgfmt --check-format -o "%djangocompilemo%" "%djangocompilepo%"'
                else:
                    cmd = 'msgfmt --check-format -o "$djangocompilemo" "$djangocompilepo"'
                os.system(cmd)

def main():
    parser = optparse.OptionParser()
    parser.add_option('-l', '--locale', dest='locale',
            help="The locale to process. Default is to process all.")
    parser.add_option('--settings',
        help='Python path to settings module, e.g. "myproject.settings". If provided, all LOCALE_PATHS will be processed. If this isn\'t provided, the DJANGO_SETTINGS_MODULE environment variable will be checked as well.')
    options, args = parser.parse_args()
    if len(args):
        parser.error("This program takes no arguments")
    if options.settings:
        os.environ['DJANGO_SETTINGS_MODULE'] = options.settings
    compile_messages(options.locale)

if __name__ == "__main__":
    main()
