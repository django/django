from __future__ import unicode_literals

import codecs
import os
from optparse import make_option

from django.core.management.base import BaseCommand, CommandError
from django.core.management.utils import find_command, popen_wrapper
from django.utils._os import npath, upath


def has_bom(fn):
    with open(fn, 'rb') as f:
        sample = f.read(4)
    return sample[:3] == b'\xef\xbb\xbf' or \
        sample.startswith(codecs.BOM_UTF16_LE) or \
        sample.startswith(codecs.BOM_UTF16_BE)


def is_writable(path):
    # Known side effect: updating file access/modified time to current time if
    # it is writable.
    try:
        with open(path, 'a'):
            os.utime(path, None)
    except (IOError, OSError):
        return False
    return True


class Command(BaseCommand):
    option_list = BaseCommand.option_list + (
        make_option('--locale', '-l', dest='locale', action='append',
                    help='locale(s) to process (e.g. de_AT). Default is to process all. Can be used multiple times.'),
    )
    help = 'Compiles .po files to .mo files for use with builtin gettext support.'

    requires_system_checks = False
    leave_locale_alone = True

    program = 'msgfmt'
    program_options = ['--check-format']

    def handle(self, **options):
        locale = options.get('locale')
        self.verbosity = int(options.get('verbosity'))

        if find_command(self.program) is None:
            raise CommandError("Can't find %s. Make sure you have GNU gettext "
                               "tools 0.15 or newer installed." % self.program)

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
            if has_bom(po_path):
                raise CommandError("The %s file has a BOM (Byte Order Mark). "
                                   "Django only supports .po files encoded in "
                                   "UTF-8 and without any BOM." % po_path)
            base_path = os.path.splitext(po_path)[0]

            # Check writability on first location
            if i == 0 and not is_writable(npath(base_path + '.mo')):
                self.stderr.write("The po files under %s are in a seemingly not "
                                  "writable location. mo files will not be updated/created." % dirpath)
                return

            args = [self.program] + self.program_options + ['-o',
                    npath(base_path + '.mo'), npath(base_path + '.po')]
            output, errors, status = popen_wrapper(args)
            if status:
                if errors:
                    msg = "Execution of %s failed: %s" % (self.program, errors)
                else:
                    msg = "Execution of %s failed" % self.program
                raise CommandError(msg)
