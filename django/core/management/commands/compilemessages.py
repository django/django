from __future__ import unicode_literals

import os
from optparse import make_option

from django.core.management.base import BaseCommand, CommandError
from django.utils._os import upath
from django.utils.translation.trans_real import (compile_message_file,
                                                TranslationError)


def compile_messages(stdout, locale=None):
    basedirs = [os.path.join('conf', 'locale'), 'locale']
    if os.environ.get('DJANGO_SETTINGS_MODULE'):
        from django.conf import settings
        basedirs.extend([upath(path) for path in settings.LOCALE_PATHS])

    # Gather existing directories.
    basedirs = set(map(os.path.abspath, filter(os.path.isdir, basedirs)))

    if not basedirs:
        raise CommandError("This script should be run from the Django Git checkout or your project or app tree, or with the settings module specified.")

    for basedir in basedirs:
        if locale:
            dirs = [os.path.join(basedir, l, 'LC_MESSAGES') for l in locale]
        else:
            dirs = [basedir]
        for ldir in dirs:
            for dirpath, dirnames, filenames in os.walk(ldir):
                for f in filenames:
                    if not f.endswith('.po'):
                        continue
                    stdout.write('processing file %s in %s\n' % (f, dirpath))
                    fn = os.path.join(dirpath, f)
                    try:
                        compile_message_file(fn)
                    except TranslationError as ex:
                        raise CommandError(ex.msg)


class Command(BaseCommand):
    option_list = BaseCommand.option_list + (
        make_option('--locale', '-l', dest='locale', action='append',
                    help='locale(s) to process (e.g. de_AT). Default is to process all. Can be used multiple times.'),
    )
    help = 'Compiles .po files to .mo files for use with builtin gettext support.'

    requires_system_checks = False
    leave_locale_alone = True

    def handle(self, **options):
        locale = options.get('locale')
        compile_messages(self.stdout, locale=locale)
