from __future__ import unicode_literals

import fnmatch
import glob
import io
import os
import re
import sys
from itertools import dropwhile

import django
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.core.management.utils import (
    find_command, handle_extensions, popen_wrapper,
)
from django.utils import six
from django.utils._os import upath
from django.utils.encoding import DEFAULT_LOCALE_ENCODING, force_str
from django.utils.functional import cached_property, total_ordering
from django.utils.jslex import prepare_js_for_gettext
from django.utils.text import get_text_list

plural_forms_re = re.compile(r'^(?P<value>"Plural-Forms.+?\\n")\s*$', re.MULTILINE | re.DOTALL)
STATUS_OK = 0


def check_programs(*programs):
    for program in programs:
        if find_command(program) is None:
            raise CommandError("Can't find %s. Make sure you have GNU "
                    "gettext tools 0.15 or newer installed." % program)


def gettext_popen_wrapper(args, os_err_exc_type=CommandError, stdout_encoding="utf-8"):
    """
    Makes sure text obtained from stdout of gettext utilities is Unicode.
    """
    # This both decodes utf-8 and cleans line endings. Simply using
    # popen_wrapper(universal_newlines=True) doesn't properly handle the
    # encoding. This goes back to popen's flaky support for encoding:
    # https://bugs.python.org/issue6135. This is a solution for #23271, #21928.
    # No need to do anything on Python 2 because it's already a byte-string there.
    manual_io_wrapper = six.PY3 and stdout_encoding != DEFAULT_LOCALE_ENCODING

    stdout, stderr, status_code = popen_wrapper(args, os_err_exc_type=os_err_exc_type,
                                                universal_newlines=not manual_io_wrapper)
    if manual_io_wrapper:
        stdout = io.TextIOWrapper(io.BytesIO(stdout), encoding=stdout_encoding).read()
    if six.PY2:
        stdout = stdout.decode(stdout_encoding)
    return stdout, stderr, status_code


@total_ordering
class TranslatableFile(object):
    def __init__(self, dirpath, file_name, locale_dir):
        self.file = file_name
        self.dirpath = dirpath
        self.locale_dir = locale_dir

    def __repr__(self):
        return "<TranslatableFile: %s>" % os.sep.join([self.dirpath, self.file])

    def __eq__(self, other):
        return self.path == other.path

    def __lt__(self, other):
        return self.path < other.path

    @property
    def path(self):
        return os.path.join(self.dirpath, self.file)

    def process(self, command, domain):
        """
        Extract translatable literals from self.file for :param domain:,
        creating or updating the POT file.

        Uses the xgettext GNU gettext utility.
        """
        from django.utils.translation import templatize

        if command.verbosity > 1:
            command.stdout.write('processing file %s in %s\n' % (self.file, self.dirpath))
        file_ext = os.path.splitext(self.file)[1]
        if domain == 'djangojs':
            orig_file = os.path.join(self.dirpath, self.file)
            work_file = orig_file
            is_templatized = command.gettext_version < (0, 18, 3)
            if is_templatized:
                with io.open(orig_file, 'r', encoding=settings.FILE_CHARSET) as fp:
                    src_data = fp.read()
                src_data = prepare_js_for_gettext(src_data)
                work_file = os.path.join(self.dirpath, '%s.c' % self.file)
                with io.open(work_file, "w", encoding='utf-8') as fp:
                    fp.write(src_data)
            args = [
                'xgettext',
                '-d', domain,
                '--language=%s' % ('C' if is_templatized else 'JavaScript',),
                '--keyword=gettext_noop',
                '--keyword=gettext_lazy',
                '--keyword=ngettext_lazy:1,2',
                '--keyword=pgettext:1c,2',
                '--keyword=npgettext:1c,2,3',
                '--output=-'
            ] + command.xgettext_options
            args.append(work_file)
        elif domain == 'django':
            orig_file = os.path.join(self.dirpath, self.file)
            work_file = orig_file
            is_templatized = file_ext != '.py'
            if is_templatized:
                with io.open(orig_file, encoding=settings.FILE_CHARSET) as fp:
                    src_data = fp.read()
                content = templatize(src_data, orig_file[2:])
                work_file = os.path.join(self.dirpath, '%s.py' % self.file)
                with io.open(work_file, "w", encoding='utf-8') as fp:
                    fp.write(content)
            args = [
                'xgettext',
                '-d', domain,
                '--language=Python',
                '--keyword=gettext_noop',
                '--keyword=gettext_lazy',
                '--keyword=ngettext_lazy:1,2',
                '--keyword=ugettext_noop',
                '--keyword=ugettext_lazy',
                '--keyword=ungettext_lazy:1,2',
                '--keyword=pgettext:1c,2',
                '--keyword=npgettext:1c,2,3',
                '--keyword=pgettext_lazy:1c,2',
                '--keyword=npgettext_lazy:1c,2,3',
                '--output=-'
            ] + command.xgettext_options
            args.append(work_file)
        else:
            return
        msgs, errors, status = gettext_popen_wrapper(args)
        if errors:
            if status != STATUS_OK:
                if is_templatized:
                    os.unlink(work_file)
                raise CommandError(
                    "errors happened while running xgettext on %s\n%s" %
                    (self.file, errors))
            elif command.verbosity > 0:
                # Print warnings
                command.stdout.write(errors)
        if msgs:
            # Write/append messages to pot file
            potfile = os.path.join(self.locale_dir, '%s.pot' % str(domain))
            if is_templatized:
                # Remove '.py' suffix
                if os.name == 'nt':
                    # Preserve '.\' prefix on Windows to respect gettext behavior
                    old = '#: ' + work_file
                    new = '#: ' + orig_file
                else:
                    old = '#: ' + work_file[2:]
                    new = '#: ' + orig_file[2:]
                msgs = msgs.replace(old, new)
            write_pot_file(potfile, msgs)

        if is_templatized:
            os.unlink(work_file)


def write_pot_file(potfile, msgs):
    """
    Write the :param potfile: POT file with the :param msgs: contents,
    previously making sure its format is valid.
    """
    if os.path.exists(potfile):
        # Strip the header
        msgs = '\n'.join(dropwhile(len, msgs.split('\n')))
    else:
        msgs = msgs.replace('charset=CHARSET', 'charset=UTF-8')
    with io.open(potfile, 'a', encoding='utf-8') as fp:
        fp.write(msgs)


class Command(BaseCommand):
    help = ("Runs over the entire source tree of the current directory and "
"pulls out all strings marked for translation. It creates (or updates) a message "
"file in the conf/locale (in the django tree) or locale (for projects and "
"applications) directory.\n\nYou must run this command with one of either the "
"--locale, --exclude or --all options.")

    requires_system_checks = False
    leave_locale_alone = True

    msgmerge_options = ['-q', '--previous']
    msguniq_options = ['--to-code=utf-8']
    msgattrib_options = ['--no-obsolete']
    xgettext_options = ['--from-code=UTF-8', '--add-comments=Translators']

    def add_arguments(self, parser):
        parser.add_argument('--locale', '-l', default=[], dest='locale', action='append',
            help='Creates or updates the message files for the given locale(s) (e.g. pt_BR). '
                 'Can be used multiple times.')
        parser.add_argument('--exclude', '-x', default=[], dest='exclude', action='append',
                    help='Locales to exclude. Default is none. Can be used multiple times.')
        parser.add_argument('--domain', '-d', default='django', dest='domain',
            help='The domain of the message files (default: "django").')
        parser.add_argument('--all', '-a', action='store_true', dest='all',
            default=False, help='Updates the message files for all existing locales.')
        parser.add_argument('--extension', '-e', dest='extensions',
            help='The file extension(s) to examine (default: "html,txt", or "js" '
                 'if the domain is "djangojs"). Separate multiple extensions with '
                 'commas, or use -e multiple times.',
            action='append')
        parser.add_argument('--symlinks', '-s', action='store_true', dest='symlinks',
            default=False, help='Follows symlinks to directories when examining '
                                'source code and templates for translation strings.')
        parser.add_argument('--ignore', '-i', action='append', dest='ignore_patterns',
            default=[], metavar='PATTERN',
            help='Ignore files or directories matching this glob-style pattern. '
                 'Use multiple times to ignore more.')
        parser.add_argument('--no-default-ignore', action='store_false', dest='use_default_ignore_patterns',
            default=True, help="Don't ignore the common glob-style patterns 'CVS', '.*', '*~' and '*.pyc'.")
        parser.add_argument('--no-wrap', action='store_true', dest='no_wrap',
            default=False, help="Don't break long message lines into several lines.")
        parser.add_argument('--no-location', action='store_true', dest='no_location',
            default=False, help="Don't write '#: filename:line' lines.")
        parser.add_argument('--no-obsolete', action='store_true', dest='no_obsolete',
            default=False, help="Remove obsolete message strings.")
        parser.add_argument('--keep-pot', action='store_true', dest='keep_pot',
            default=False, help="Keep .pot file after making messages. Useful when debugging.")

    def handle(self, *args, **options):
        locale = options.get('locale')
        exclude = options.get('exclude')
        self.domain = options.get('domain')
        self.verbosity = options.get('verbosity')
        process_all = options.get('all')
        extensions = options.get('extensions')
        self.symlinks = options.get('symlinks')

        # Need to ensure that the i18n framework is enabled
        if settings.configured:
            settings.USE_I18N = True
        else:
            settings.configure(USE_I18N=True)

        ignore_patterns = options.get('ignore_patterns')
        if options.get('use_default_ignore_patterns'):
            ignore_patterns += ['CVS', '.*', '*~', '*.pyc']
        self.ignore_patterns = list(set(ignore_patterns))

        # Avoid messing with mutable class variables
        if options.get('no_wrap'):
            self.msgmerge_options = self.msgmerge_options[:] + ['--no-wrap']
            self.msguniq_options = self.msguniq_options[:] + ['--no-wrap']
            self.msgattrib_options = self.msgattrib_options[:] + ['--no-wrap']
            self.xgettext_options = self.xgettext_options[:] + ['--no-wrap']
        if options.get('no_location'):
            self.msgmerge_options = self.msgmerge_options[:] + ['--no-location']
            self.msguniq_options = self.msguniq_options[:] + ['--no-location']
            self.msgattrib_options = self.msgattrib_options[:] + ['--no-location']
            self.xgettext_options = self.xgettext_options[:] + ['--no-location']

        self.no_obsolete = options.get('no_obsolete')
        self.keep_pot = options.get('keep_pot')

        if self.domain not in ('django', 'djangojs'):
            raise CommandError("currently makemessages only supports domains "
                               "'django' and 'djangojs'")
        if self.domain == 'djangojs':
            exts = extensions if extensions else ['js']
        else:
            exts = extensions if extensions else ['html', 'txt', 'py']
        self.extensions = handle_extensions(exts)

        if (locale is None and not exclude and not process_all) or self.domain is None:
            raise CommandError("Type '%s help %s' for usage information." % (
                os.path.basename(sys.argv[0]), sys.argv[1]))

        if self.verbosity > 1:
            self.stdout.write('examining files with the extensions: %s\n'
                             % get_text_list(list(self.extensions), 'and'))

        self.invoked_for_django = False
        self.locale_paths = []
        self.default_locale_path = None
        if os.path.isdir(os.path.join('conf', 'locale')):
            self.locale_paths = [os.path.abspath(os.path.join('conf', 'locale'))]
            self.default_locale_path = self.locale_paths[0]
            self.invoked_for_django = True
        else:
            self.locale_paths.extend(list(settings.LOCALE_PATHS))
            # Allow to run makemessages inside an app dir
            if os.path.isdir('locale'):
                self.locale_paths.append(os.path.abspath('locale'))
            if self.locale_paths:
                self.default_locale_path = self.locale_paths[0]
                if not os.path.exists(self.default_locale_path):
                    os.makedirs(self.default_locale_path)

        # Build locale list
        locale_dirs = filter(os.path.isdir, glob.glob('%s/*' % self.default_locale_path))
        all_locales = map(os.path.basename, locale_dirs)

        # Account for excluded locales
        if process_all:
            locales = all_locales
        else:
            locales = locale or all_locales
            locales = set(locales) - set(exclude)

        if locales:
            check_programs('msguniq', 'msgmerge', 'msgattrib')

        check_programs('xgettext')

        try:
            potfiles = self.build_potfiles()

            # Build po files for each selected locale
            for locale in locales:
                if self.verbosity > 0:
                    self.stdout.write("processing locale %s\n" % locale)
                for potfile in potfiles:
                    self.write_po_file(potfile, locale)
        finally:
            if not self.keep_pot:
                self.remove_potfiles()

    @cached_property
    def gettext_version(self):
        # Gettext tools will output system-encoded bytestrings instead of UTF-8,
        # when looking up the version. It's especially a problem on Windows.
        out, err, status = gettext_popen_wrapper(
            ['xgettext', '--version'],
            stdout_encoding=DEFAULT_LOCALE_ENCODING,
        )
        m = re.search(r'(\d+)\.(\d+)\.?(\d+)?', out)
        if m:
            return tuple(int(d) for d in m.groups() if d is not None)
        else:
            raise CommandError("Unable to get gettext version. Is it installed?")

    def build_potfiles(self):
        """
        Build pot files and apply msguniq to them.
        """
        file_list = self.find_files(".")
        self.remove_potfiles()
        for f in file_list:
            try:
                f.process(self, self.domain)
            except UnicodeDecodeError as e:
                self.stdout.write(
                    "UnicodeDecodeError: skipped file %s in %s (reason: %s)" % (
                        f.file,
                        f.dirpath,
                        e,
                    )
                )

        potfiles = []
        for path in self.locale_paths:
            potfile = os.path.join(path, '%s.pot' % str(self.domain))
            if not os.path.exists(potfile):
                continue
            args = ['msguniq'] + self.msguniq_options + [potfile]
            msgs, errors, status = gettext_popen_wrapper(args)
            if errors:
                if status != STATUS_OK:
                    raise CommandError(
                        "errors happened while running msguniq\n%s" % errors)
                elif self.verbosity > 0:
                    self.stdout.write(errors)
            with io.open(potfile, 'w', encoding='utf-8') as fp:
                fp.write(msgs)
            potfiles.append(potfile)
        return potfiles

    def remove_potfiles(self):
        for path in self.locale_paths:
            pot_path = os.path.join(path, '%s.pot' % str(self.domain))
            if os.path.exists(pot_path):
                os.unlink(pot_path)

    def find_files(self, root):
        """
        Helper method to get all files in the given root. Also check that there
        is a matching locale dir for each file.
        """

        def is_ignored(path, ignore_patterns):
            """
            Check if the given path should be ignored or not.
            """
            filename = os.path.basename(path)
            ignore = lambda pattern: (fnmatch.fnmatchcase(filename, pattern) or
                fnmatch.fnmatchcase(path, pattern))
            return any(ignore(pattern) for pattern in ignore_patterns)

        ignore_patterns = [os.path.normcase(p) for p in self.ignore_patterns]
        dir_suffixes = {'%s*' % path_sep for path_sep in {'/', os.sep}}
        norm_patterns = []
        for p in ignore_patterns:
            for dir_suffix in dir_suffixes:
                if p.endswith(dir_suffix):
                    norm_patterns.append(p[:-len(dir_suffix)])
                    break
            else:
                norm_patterns.append(p)

        all_files = []
        ignored_roots = [os.path.normpath(p) for p in (settings.MEDIA_ROOT, settings.STATIC_ROOT) if p]
        for dirpath, dirnames, filenames in os.walk(root, topdown=True, followlinks=self.symlinks):
            for dirname in dirnames[:]:
                if (is_ignored(os.path.normpath(os.path.join(dirpath, dirname)), norm_patterns) or
                        os.path.join(os.path.abspath(dirpath), dirname) in ignored_roots):
                    dirnames.remove(dirname)
                    if self.verbosity > 1:
                        self.stdout.write('ignoring directory %s\n' % dirname)
                elif dirname == 'locale':
                    dirnames.remove(dirname)
                    self.locale_paths.insert(0, os.path.join(os.path.abspath(dirpath), dirname))
            for filename in filenames:
                file_path = os.path.normpath(os.path.join(dirpath, filename))
                file_ext = os.path.splitext(filename)[1]
                if file_ext not in self.extensions or is_ignored(file_path, self.ignore_patterns):
                    if self.verbosity > 1:
                        self.stdout.write('ignoring file %s in %s\n' % (filename, dirpath))
                else:
                    locale_dir = None
                    for path in self.locale_paths:
                        if os.path.abspath(dirpath).startswith(os.path.dirname(path)):
                            locale_dir = path
                            break
                    if not locale_dir:
                        locale_dir = self.default_locale_path
                    if not locale_dir:
                        raise CommandError(
                            "Unable to find a locale path to store translations for file %s" % file_path)
                    all_files.append(TranslatableFile(dirpath, filename, locale_dir))
        return sorted(all_files)

    def write_po_file(self, potfile, locale):
        """
        Creates or updates the PO file for self.domain and :param locale:.
        Uses contents of the existing :param potfile:.

        Uses msgmerge, and msgattrib GNU gettext utilities.
        """
        basedir = os.path.join(os.path.dirname(potfile), locale, 'LC_MESSAGES')
        if not os.path.isdir(basedir):
            os.makedirs(basedir)
        pofile = os.path.join(basedir, '%s.po' % str(self.domain))

        if os.path.exists(pofile):
            args = ['msgmerge'] + self.msgmerge_options + [pofile, potfile]
            msgs, errors, status = gettext_popen_wrapper(args)
            if errors:
                if status != STATUS_OK:
                    raise CommandError(
                        "errors happened while running msgmerge\n%s" % errors)
                elif self.verbosity > 0:
                    self.stdout.write(errors)
        else:
            with io.open(potfile, 'r', encoding='utf-8') as fp:
                msgs = fp.read()
            if not self.invoked_for_django:
                msgs = self.copy_plural_forms(msgs, locale)
        msgs = msgs.replace(
            "#. #-#-#-#-#  %s.pot (PACKAGE VERSION)  #-#-#-#-#\n" % self.domain, "")
        with io.open(pofile, 'w', encoding='utf-8') as fp:
            fp.write(msgs)

        if self.no_obsolete:
            args = ['msgattrib'] + self.msgattrib_options + ['-o', pofile, pofile]
            msgs, errors, status = gettext_popen_wrapper(args)
            if errors:
                if status != STATUS_OK:
                    raise CommandError(
                        "errors happened while running msgattrib\n%s" % errors)
                elif self.verbosity > 0:
                    self.stdout.write(errors)

    def copy_plural_forms(self, msgs, locale):
        """
        Copies plural forms header contents from a Django catalog of locale to
        the msgs string, inserting it at the right place. msgs should be the
        contents of a newly created .po file.
        """
        django_dir = os.path.normpath(os.path.join(os.path.dirname(upath(django.__file__))))
        if self.domain == 'djangojs':
            domains = ('djangojs', 'django')
        else:
            domains = ('django',)
        for domain in domains:
            django_po = os.path.join(django_dir, 'conf', 'locale', locale, 'LC_MESSAGES', '%s.po' % domain)
            if os.path.exists(django_po):
                with io.open(django_po, 'r', encoding='utf-8') as fp:
                    m = plural_forms_re.search(fp.read())
                if m:
                    plural_form_line = force_str(m.group('value'))
                    if self.verbosity > 1:
                        self.stdout.write("copying plural forms: %s\n" % plural_form_line)
                    lines = []
                    found = False
                    for line in msgs.split('\n'):
                        if not found and (not line or plural_forms_re.search(line)):
                            line = '%s\n' % plural_form_line
                            found = True
                        lines.append(line)
                    msgs = '\n'.join(lines)
                    break
        return msgs
