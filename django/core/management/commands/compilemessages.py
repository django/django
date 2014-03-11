from __future__ import unicode_literals

import os
from optparse import make_option

from django.core.management.base import BaseCommand, CommandError
from django.utils._os import upath
from django.utils.translation.trans_real import (compile_message_file,
                                                TranslationError, TranslationWritableError)

class Command(BaseCommand):
    option_list = BaseCommand.option_list + (
        make_option('--locale', '-l', dest='locale', action='append',
                    help='locale(s) to process (e.g. de_AT). Default is to process all. Can be used multiple times.'),
    )
    help = 'Compiles .po files to .mo files for use with builtin gettext support.'

    requires_system_checks = False
    leave_locale_alone = True
    program = 'msgfmt'

    def handle(self, **options):
        locale = options.get('locale')
        self.verbosity = int(options.get('verbosity'))

        basedirs = [os.path.join('conf', 'locale'), 'locale']
        if os.environ.get('DJANGO_SETTINGS_MODULE'):
            from django.conf import settings
            basedirs.extend([upath(path) for path in settings.LOCALE_PATHS])

        # Gather existing directories.
        basedirs = set(map(os.path.abspath, filter(os.path.isdir, basedirs)))

        if not basedirs:
            raise CommandError("This script should be run from the Django Git "
                               "checkout or your project or app tree, or with "
                               "the settings module specified.")

        for basedir in basedirs:
            if locale:
                dirs = [os.path.join(basedir, l, 'LC_MESSAGES') for l in locale]
            else:
                dirs = [basedir]
            locations = []
            for ldir in dirs:
                for dirpath, dirnames, filenames in os.walk(ldir):
                    locations.extend((dirpath, f) for f in filenames if f.endswith('.po'))
            if locations:
                self.compile_messages(locations)

    def compile_messages(self, locations):
        """
        Locations is a list of tuples: [(directory, file), ...]
        """
        for i, (dirpath, f) in enumerate(locations):
            if self.verbosity > 0:
                self.stdout.write('processing file %s in %s\n' % (f, dirpath))
            po_path = os.path.join(dirpath, f)
            try:
                compile_message_file(po_path)
            except TranslationWritableError as writable_err:
                self.stderr.write(writable_err.args[0])
            except TranslationError as trans_err:
                raise CommandError(trans_err.args[0])

