import codecs
import os
import sys
from optparse import make_option
from django.core.management.base import BaseCommand, CommandError

def has_bom(fn):
    f = open(fn, 'r')
    sample = f.read(4)
    return sample[:3] == '\xef\xbb\xbf' or \
            sample.startswith(codecs.BOM_UTF16_LE) or \
            sample.startswith(codecs.BOM_UTF16_BE)

def compile_messages(stderr, locale=None):
    basedirs = [os.path.join('conf', 'locale'), 'locale']
    if os.environ.get('DJANGO_SETTINGS_MODULE'):
        from django.conf import settings
        basedirs.extend(settings.LOCALE_PATHS)

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
                    stderr.write('processing file %s in %s\n' % (f, dirpath))
                    fn = os.path.join(dirpath, f)
                    if has_bom(fn):
                        raise CommandError("The %s file has a BOM (Byte Order Mark). Django only supports .po files encoded in UTF-8 and without any BOM." % fn)
                    pf = os.path.splitext(fn)[0]
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
        compile_messages(self.stderr, locale=locale)
