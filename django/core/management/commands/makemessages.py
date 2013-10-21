import fnmatch
import glob
import io
import os
import re
import sys
from itertools import dropwhile
from optparse import make_option

import django
from django.core.management.base import CommandError, NoArgsCommand
from django.core.management.utils import (handle_extensions, find_command,
    popen_wrapper)
from django.utils.encoding import force_str
from django.utils.functional import total_ordering
from django.utils.text import get_text_list
from django.utils.jslex import prepare_js_for_gettext

plural_forms_re = re.compile(r'^(?P<value>"Plural-Forms.+?\\n")\s*$', re.MULTILINE | re.DOTALL)
STATUS_OK = 0


def check_programs(*programs):
    for program in programs:
        if find_command(program) is None:
            raise CommandError("Can't find %s. Make sure you have GNU "
                    "gettext tools 0.15 or newer installed." % program)


@total_ordering
class TranslatableFile(object):
    def __init__(self, dirpath, file_name):
        self.file = file_name
        self.dirpath = dirpath

    def __repr__(self):
        return "<TranslatableFile: %s>" % os.sep.join([self.dirpath, self.file])

    def __eq__(self, other):
        return self.dirpath == other.dirpath and self.file == other.file

    def __lt__(self, other):
        if self.dirpath == other.dirpath:
            return self.file < other.file
        return self.dirpath < other.dirpath

    def process(self, command, potfile, domain, keep_pot=False):
        """
        Extract translatable literals from self.file for :param domain:
        creating or updating the :param potfile: POT file.

        Uses the xgettext GNU gettext utility.
        """

        from django.utils.translation import templatize

        if command.verbosity > 1:
            command.stdout.write('processing file %s in %s\n' % (self.file, self.dirpath))
        _, file_ext = os.path.splitext(self.file)
        if domain == 'djangojs' and file_ext in command.extensions:
            is_templatized = True
            orig_file = os.path.join(self.dirpath, self.file)
            with open(orig_file) as fp:
                src_data = fp.read()
            src_data = prepare_js_for_gettext(src_data)
            thefile = '%s.c' % self.file
            work_file = os.path.join(self.dirpath, thefile)
            with open(work_file, "w") as fp:
                fp.write(src_data)
            args = [
                'xgettext',
                '-d', domain,
                '--language=C',
                '--keyword=gettext_noop',
                '--keyword=gettext_lazy',
                '--keyword=ngettext_lazy:1,2',
                '--keyword=pgettext:1c,2',
                '--keyword=npgettext:1c,2,3',
                '--from-code=UTF-8',
                '--add-comments=Translators',
                '--output=-'
            ]
            if command.wrap:
                args.append(command.wrap)
            if command.location:
                args.append(command.location)
            args.append(work_file)
        elif domain == 'django' and (file_ext == '.py' or file_ext in command.extensions):
            thefile = self.file
            orig_file = os.path.join(self.dirpath, self.file)
            is_templatized = file_ext in command.extensions
            if is_templatized:
                with open(orig_file, "rU") as fp:
                    src_data = fp.read()
                thefile = '%s.py' % self.file
                content = templatize(src_data, orig_file[2:])
                with open(os.path.join(self.dirpath, thefile), "w") as fp:
                    fp.write(content)
            work_file = os.path.join(self.dirpath, thefile)
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
                '--from-code=UTF-8',
                '--add-comments=Translators',
                '--output=-'
            ]
            if command.wrap:
                args.append(command.wrap)
            if command.location:
                args.append(command.location)
            args.append(work_file)
        else:
            return
        msgs, errors, status = popen_wrapper(args)
        if errors:
            if status != STATUS_OK:
                if is_templatized:
                    os.unlink(work_file)
                if not keep_pot and os.path.exists(potfile):
                    os.unlink(potfile)
                raise CommandError(
                    "errors happened while running xgettext on %s\n%s" %
                    (self.file, errors))
            elif command.verbosity > 0:
                # Print warnings
                command.stdout.write(errors)
        if msgs:
            if is_templatized:
                # Remove '.py' suffix
                if os.name =='nt':
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
    with open(potfile, 'a') as fp:
        fp.write(msgs)


class Command(NoArgsCommand):
    option_list = NoArgsCommand.option_list + (
        make_option('--locale', '-l', default=None, dest='locale', action='append',
            help='Creates or updates the message files for the given locale(s) (e.g. pt_BR). '
                 'Can be used multiple times, accepts a comma-separated list of locale names.'),
        make_option('--domain', '-d', default='django', dest='domain',
            help='The domain of the message files (default: "django").'),
        make_option('--all', '-a', action='store_true', dest='all',
            default=False, help='Updates the message files for all existing locales.'),
        make_option('--extension', '-e', dest='extensions',
            help='The file extension(s) to examine (default: "html,txt", or "js" if the domain is "djangojs"). Separate multiple extensions with commas, or use -e multiple times.',
            action='append'),
        make_option('--symlinks', '-s', action='store_true', dest='symlinks',
            default=False, help='Follows symlinks to directories when examining source code and templates for translation strings.'),
        make_option('--ignore', '-i', action='append', dest='ignore_patterns',
            default=[], metavar='PATTERN', help='Ignore files or directories matching this glob-style pattern. Use multiple times to ignore more.'),
        make_option('--no-default-ignore', action='store_false', dest='use_default_ignore_patterns',
            default=True, help="Don't ignore the common glob-style patterns 'CVS', '.*', '*~' and '*.pyc'."),
        make_option('--no-wrap', action='store_true', dest='no_wrap',
            default=False, help="Don't break long message lines into several lines."),
        make_option('--no-location', action='store_true', dest='no_location',
            default=False, help="Don't write '#: filename:line' lines."),
        make_option('--no-obsolete', action='store_true', dest='no_obsolete',
            default=False, help="Remove obsolete message strings."),
        make_option('--keep-pot', action='store_true', dest='keep_pot',
            default=False, help="Keep .pot file after making messages. Useful when debugging."),
    )
    help = ("Runs over the entire source tree of the current directory and "
"pulls out all strings marked for translation. It creates (or updates) a message "
"file in the conf/locale (in the django tree) or locale (for projects and "
"applications) directory.\n\nYou must run this command with one of either the "
"--locale or --all options.")

    requires_model_validation = False
    leave_locale_alone = True

    def handle_noargs(self, *args, **options):
        locale = options.get('locale')
        self.domain = options.get('domain')
        self.verbosity = int(options.get('verbosity'))
        process_all = options.get('all')
        extensions = options.get('extensions')
        self.symlinks = options.get('symlinks')
        ignore_patterns = options.get('ignore_patterns')
        if options.get('use_default_ignore_patterns'):
            ignore_patterns += ['CVS', '.*', '*~', '*.pyc']
        self.ignore_patterns = list(set(ignore_patterns))
        self.wrap = '--no-wrap' if options.get('no_wrap') else ''
        self.location = '--no-location' if options.get('no_location') else ''
        self.no_obsolete = options.get('no_obsolete')
        self.keep_pot = options.get('keep_pot')

        if self.domain not in ('django', 'djangojs'):
            raise CommandError("currently makemessages only supports domains "
                               "'django' and 'djangojs'")
        if self.domain == 'djangojs':
            exts = extensions if extensions else ['js']
        else:
            exts = extensions if extensions else ['html', 'txt']
        self.extensions = handle_extensions(exts)

        if (locale is None and not process_all) or self.domain is None:
            raise CommandError("Type '%s help %s' for usage information." % (
                                os.path.basename(sys.argv[0]), sys.argv[1]))

        if self.verbosity > 1:
            self.stdout.write('examining files with the extensions: %s\n'
                             % get_text_list(list(self.extensions), 'and'))

        # Need to ensure that the i18n framework is enabled
        from django.conf import settings
        if settings.configured:
            settings.USE_I18N = True
        else:
            settings.configure(USE_I18N = True)

        self.invoked_for_django = False
        if os.path.isdir(os.path.join('conf', 'locale')):
            localedir = os.path.abspath(os.path.join('conf', 'locale'))
            self.invoked_for_django = True
            # Ignoring all contrib apps
            self.ignore_patterns += ['contrib/*']
        elif os.path.isdir('locale'):
            localedir = os.path.abspath('locale')
        else:
            raise CommandError("This script should be run from the Django Git "
                    "tree or your project or app tree. If you did indeed run it "
                    "from the Git checkout or your project or application, "
                    "maybe you are just missing the conf/locale (in the django "
                    "tree) or locale (for project and application) directory? It "
                    "is not created automatically, you have to create it by hand "
                    "if you want to enable i18n for your project or application.")

        check_programs('xgettext')

        potfile = self.build_pot_file(localedir)

        # Build po files for each selected locale
        locales = []
        if locale is not None:
            locales += locale.split(',') if not isinstance(locale, list) else locale
        elif process_all:
            locale_dirs = filter(os.path.isdir, glob.glob('%s/*' % localedir))
            locales = [os.path.basename(l) for l in locale_dirs]

        if locales:
            check_programs('msguniq', 'msgmerge', 'msgattrib')

        try:
            for locale in locales:
                if self.verbosity > 0:
                    self.stdout.write("processing locale %s\n" % locale)
                self.write_po_file(potfile, locale)
        finally:
            if not self.keep_pot and os.path.exists(potfile):
                os.unlink(potfile)

    def build_pot_file(self, localedir):
        file_list = self.find_files(".")

        potfile = os.path.join(localedir, '%s.pot' % str(self.domain))
        if os.path.exists(potfile):
            # Remove a previous undeleted potfile, if any
            os.unlink(potfile)

        for f in file_list:
            try:
                f.process(self, potfile, self.domain, self.keep_pot)
            except UnicodeDecodeError:
                self.stdout.write("UnicodeDecodeError: skipped file %s in %s" % (f.file, f.dirpath))
        return potfile

    def find_files(self, root):
        """
        Helper method to get all files in the given root.
        """

        def is_ignored(path, ignore_patterns):
            """
            Check if the given path should be ignored or not.
            """
            filename = os.path.basename(path)
            ignore = lambda pattern: fnmatch.fnmatchcase(filename, pattern)
            return any(ignore(pattern) for pattern in ignore_patterns)

        dir_suffix = '%s*' % os.sep
        norm_patterns = [p[:-len(dir_suffix)] if p.endswith(dir_suffix) else p for p in self.ignore_patterns]
        all_files = []
        for dirpath, dirnames, filenames in os.walk(root, topdown=True, followlinks=self.symlinks):
            for dirname in dirnames[:]:
                if is_ignored(os.path.normpath(os.path.join(dirpath, dirname)), norm_patterns):
                    dirnames.remove(dirname)
                    if self.verbosity > 1:
                        self.stdout.write('ignoring directory %s\n' % dirname)
            for filename in filenames:
                if is_ignored(os.path.normpath(os.path.join(dirpath, filename)), self.ignore_patterns):
                    if self.verbosity > 1:
                        self.stdout.write('ignoring file %s in %s\n' % (filename, dirpath))
                else:
                    all_files.append(TranslatableFile(dirpath, filename))
        return sorted(all_files)

    def write_po_file(self, potfile, locale):
        """
        Creates or updates the PO file for self.domain and :param locale:.
        Uses contents of the existing :param potfile:.

        Uses mguniq, msgmerge, and msgattrib GNU gettext utilities.
        """
        args = ['msguniq', '--to-code=utf-8']
        if self.wrap:
            args.append(self.wrap)
        if self.location:
            args.append(self.location)
        args.append(potfile)
        msgs, errors, status = popen_wrapper(args)
        if errors:
            if status != STATUS_OK:
                raise CommandError(
                    "errors happened while running msguniq\n%s" % errors)
            elif self.verbosity > 0:
                self.stdout.write(errors)

        basedir = os.path.join(os.path.dirname(potfile), locale, 'LC_MESSAGES')
        if not os.path.isdir(basedir):
            os.makedirs(basedir)
        pofile = os.path.join(basedir, '%s.po' % str(self.domain))

        if os.path.exists(pofile):
            with open(potfile, 'w') as fp:
                fp.write(msgs)
            args = ['msgmerge', '-q']
            if self.wrap:
                args.append(self.wrap)
            if self.location:
                args.append(self.location)
            args.extend([pofile, potfile])
            msgs, errors, status = popen_wrapper(args)
            if errors:
                if status != STATUS_OK:
                    raise CommandError(
                        "errors happened while running msgmerge\n%s" % errors)
                elif self.verbosity > 0:
                    self.stdout.write(errors)
        elif not self.invoked_for_django:
            msgs = self.copy_plural_forms(msgs, locale)
        msgs = msgs.replace(
            "#. #-#-#-#-#  %s.pot (PACKAGE VERSION)  #-#-#-#-#\n" % self.domain, "")
        with open(pofile, 'w') as fp:
            fp.write(msgs)

        if self.no_obsolete:
            args = ['msgattrib', '-o', pofile, '--no-obsolete']
            if self.wrap:
                args.append(self.wrap)
            if self.location:
                args.append(self.location)
            args.append(pofile)
            msgs, errors, status = popen_wrapper(args)
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
        django_dir = os.path.normpath(os.path.join(os.path.dirname(django.__file__)))
        if self.domain == 'djangojs':
            domains = ('djangojs', 'django')
        else:
            domains = ('django',)
        for domain in domains:
            django_po = os.path.join(django_dir, 'conf', 'locale', locale, 'LC_MESSAGES', '%s.po' % domain)
            if os.path.exists(django_po):
                with io.open(django_po, 'rU', encoding='utf-8') as fp:
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
