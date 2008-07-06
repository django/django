import os
import sys
from optparse import make_option
from django.core.management.base import BaseCommand
from django.core.management.color import no_style

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
        raise CommandError("This script should be run from the Django SVN tree or your project or app tree, or with the settings module specified.")

    for basedir in basedirs:
        if locale:
            basedir = os.path.join(basedir, locale, 'LC_MESSAGES')
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


class Command(BaseCommand):
    option_list = BaseCommand.option_list + (
        make_option('--locale', '-l', dest='locale',
            help='The locale to process. Default is to process all.'),
    )
    help = 'Compiles .po files to .mo files for use with builtin gettext support.'

    requires_model_validation = False
    can_import_settings = False

    def handle(self, **options):
        locale = options.get('locale')
        compile_messages(locale)
