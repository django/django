from __future__ import unicode_literals

import codecs
import os
from optparse import make_option

from django.core.management.base import BaseCommand, CommandError
from django.core.management.utils import find_command, popen_wrapper
from django.utils._os import npath

def has_bom(fn):
    with open(fn, 'rb') as f:
        sample = f.read(4)
    return sample[:3] == b'\xef\xbb\xbf' or \
            sample.startswith(codecs.BOM_UTF16_LE) or \
            sample.startswith(codecs.BOM_UTF16_BE)

def compile_messages(stdout, locale=None):
    program = 'msgfmt'
    if find_command(program) is None:
        raise CommandError("Can't find %s. Make sure you have GNU gettext tools 0.15 or newer installed." % program)

    basedirs = [os.path.join('conf', 'locale'), 'locale']
    if os.environ.get('DJANGO_SETTINGS_MODULE'):
        from django.conf import settings
        basedirs.extend(settings.LOCALE_PATHS)

    # Gather existing directories.
    basedirs = set(map(os.path.abspath, filter(os.path.isdir, basedirs)))

    if not basedirs:
        raise CommandError("This script should be run from the Django Git checkout or your project or app tree, or with the settings module specified.")

    for basedir in basedirs:
        if locale:
            dirs = [os.path.join(basedir, l, 'LC_MESSAGES') for l in (locale if isinstance(locale, list) else [locale])]
        else:
            dirs = [basedir]
        for ldir in dirs:
            for dirpath, dirnames, filenames in os.walk(ldir):
                for f in filenames:
                    if not f.endswith('.po'):
                        continue
                    stdout.write('processing file %s in %s\n' % (f, dirpath))
                    fn = os.path.join(dirpath, f)
                    if has_bom(fn):
                        raise CommandError("The %s file has a BOM (Byte Order Mark). Django only supports .po files encoded in UTF-8 and without any BOM." % fn)
                    pf = os.path.splitext(fn)[0]
                    args = [program, '--check-format', '-o', npath(pf + '.mo'), npath(pf + '.po')]
                    output, errors, status = popen_wrapper(args)
                    if status:
                        if errors:
                            msg = "Execution of %s failed: %s" % (program, errors)
                        else:
                            msg = "Execution of %s failed" % program
                        raise CommandError(msg)


class Command(BaseCommand):
    option_list = BaseCommand.option_list + (
        make_option('--locale', '-l', dest='locale', action='append',
                    help='locale(s) to process (e.g. de_AT). Default is to process all. Can be used multiple times, accepts a comma-separated list of locale names.'),
    )
    help = 'Compiles .po files to .mo files for use with builtin gettext support.'

    requires_model_validation = False
    leave_locale_alone = True

    def handle(self, **options):
        locale = options.get('locale')
        compile_messages(self.stdout, locale=locale)
