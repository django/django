import fnmatch
import glob
import os
import re
import sys
from itertools import dropwhile
from optparse import make_option
from subprocess import PIPE, Popen

import django
from django.core.management.base import CommandError, NoArgsCommand
from django.utils.text import get_text_list
from django.utils.jslex import prepare_js_for_gettext

plural_forms_re = re.compile(r'^(?P<value>"Plural-Forms.+?\\n")\s*$', re.MULTILINE | re.DOTALL)
STATUS_OK = 0

def handle_extensions(extensions=('html',), ignored=('py',)):
    """
    Organizes multiple extensions that are separated with commas or passed by
    using --extension/-e multiple times. Note that the .py extension is ignored
    here because of the way non-*.py files are handled in make_messages() (they
    are copied to file.ext.py files to trick xgettext to parse them as Python
    files).

    For example: running 'django-admin makemessages -e js,txt -e xhtml -a'
    would result in an extension list: ['.js', '.txt', '.xhtml']

    >>> handle_extensions(['.html', 'html,js,py,py,py,.py', 'py,.py'])
    set(['.html', '.js'])
    >>> handle_extensions(['.html, txt,.tpl'])
    set(['.html', '.tpl', '.txt'])
    """
    ext_list = []
    for ext in extensions:
        ext_list.extend(ext.replace(' ', '').split(','))
    for i, ext in enumerate(ext_list):
        if not ext.startswith('.'):
            ext_list[i] = '.%s' % ext_list[i]
    return set([x for x in ext_list if x.strip('.') not in ignored])

def _popen(cmd):
    """
    Friendly wrapper around Popen for Windows
    """
    p = Popen(cmd, shell=True, stdout=PIPE, stderr=PIPE, close_fds=os.name != 'nt', universal_newlines=True)
    output, errors = p.communicate()
    return output, errors, p.returncode

def find_files(root, ignore_patterns, verbosity, stdout=sys.stdout, symlinks=False):
    """
    Helper function to get all files in the given root.
    """
    dir_suffix = '%s*' % os.sep
    norm_patterns = [p[:-len(dir_suffix)] if p.endswith(dir_suffix) else p for p in ignore_patterns]
    all_files = []
    for dirpath, dirnames, filenames in os.walk(root, topdown=True, followlinks=symlinks):
        for dirname in dirnames[:]:
            if is_ignored(os.path.normpath(os.path.join(dirpath, dirname)), norm_patterns):
                dirnames.remove(dirname)
                if verbosity > 1:
                    stdout.write('ignoring directory %s\n' % dirname)
        for filename in filenames:
            if is_ignored(os.path.normpath(os.path.join(dirpath, filename)), ignore_patterns):
                if verbosity > 1:
                    stdout.write('ignoring file %s in %s\n' % (filename, dirpath))
            else:
                all_files.extend([(dirpath, filename)])
    all_files.sort()
    return all_files

def is_ignored(path, ignore_patterns):
    """
    Helper function to check if the given path should be ignored or not.
    """
    for pattern in ignore_patterns:
        if fnmatch.fnmatchcase(path, pattern):
            return True
    return False

def copy_plural_forms(msgs, locale, domain, verbosity, stdout=sys.stdout):
    """
    Copies plural forms header contents from a Django catalog of locale to
    the msgs string, inserting it at the right place. msgs should be the
    contents of a newly created .po file.
    """
    django_dir = os.path.normpath(os.path.join(os.path.dirname(django.__file__)))
    if domain == 'djangojs':
        domains = ('djangojs', 'django')
    else:
        domains = ('django',)
    for domain in domains:
        django_po = os.path.join(django_dir, 'conf', 'locale', locale, 'LC_MESSAGES', '%s.po' % domain)
        if os.path.exists(django_po):
            with open(django_po, 'rU') as fp:
                m = plural_forms_re.search(fp.read())
            if m:
                if verbosity > 1:
                    stdout.write("copying plural forms: %s\n" % m.group('value'))
                lines = []
                seen = False
                for line in msgs.split('\n'):
                    if not line and not seen:
                        line = '%s\n' % m.group('value')
                        seen = True
                    lines.append(line)
                msgs = '\n'.join(lines)
                break
    return msgs

def write_pot_file(potfile, msgs, file, work_file, is_templatized):
    """
    Write the :param potfile: POT file with the :param msgs: contents,
    previously making sure its format is valid.
    """
    if is_templatized:
        old = '#: ' + work_file[2:]
        new = '#: ' + file[2:]
        msgs = msgs.replace(old, new)
    if os.path.exists(potfile):
        # Strip the header
        msgs = '\n'.join(dropwhile(len, msgs.split('\n')))
    else:
        msgs = msgs.replace('charset=CHARSET', 'charset=UTF-8')
    with open(potfile, 'a') as fp:
        fp.write(msgs)

def process_file(file, dirpath, potfile, domain, verbosity,
                 extensions, wrap, location, stdout=sys.stdout):
    """
    Extract translatable literals from :param file: for :param domain:
    creating or updating the :param potfile: POT file.

    Uses the xgettext GNU gettext utility.
    """

    from django.utils.translation import templatize

    if verbosity > 1:
        stdout.write('processing file %s in %s\n' % (file, dirpath))
    _, file_ext = os.path.splitext(file)
    if domain == 'djangojs' and file_ext in extensions:
        is_templatized = True
        orig_file = os.path.join(dirpath, file)
        with open(orig_file) as fp:
            src_data = fp.read()
        src_data = prepare_js_for_gettext(src_data)
        thefile = '%s.c' % file
        work_file = os.path.join(dirpath, thefile)
        with open(work_file, "w") as fp:
            fp.write(src_data)
        cmd = (
            'xgettext -d %s -L C %s %s --keyword=gettext_noop '
            '--keyword=gettext_lazy --keyword=ngettext_lazy:1,2 '
            '--keyword=pgettext:1c,2 --keyword=npgettext:1c,2,3 '
            '--from-code UTF-8 --add-comments=Translators -o - "%s"' %
            (domain, wrap, location, work_file))
    elif domain == 'django' and (file_ext == '.py' or file_ext in extensions):
        thefile = file
        orig_file = os.path.join(dirpath, file)
        is_templatized = file_ext in extensions
        if is_templatized:
            with open(orig_file, "rU") as fp:
                src_data = fp.read()
            thefile = '%s.py' % file
            content = templatize(src_data, orig_file[2:])
            with open(os.path.join(dirpath, thefile), "w") as fp:
                fp.write(content)
        work_file = os.path.join(dirpath, thefile)
        cmd = (
            'xgettext -d %s -L Python %s %s --keyword=gettext_noop '
            '--keyword=gettext_lazy --keyword=ngettext_lazy:1,2 '
            '--keyword=ugettext_noop --keyword=ugettext_lazy '
            '--keyword=ungettext_lazy:1,2 --keyword=pgettext:1c,2 '
            '--keyword=npgettext:1c,2,3 --keyword=pgettext_lazy:1c,2 '
            '--keyword=npgettext_lazy:1c,2,3 --from-code UTF-8 '
            '--add-comments=Translators -o - "%s"' %
            (domain, wrap, location, work_file))
    else:
        return
    msgs, errors, status = _popen(cmd)
    if errors:
        if status != STATUS_OK:
            if is_templatized:
                os.unlink(work_file)
            if os.path.exists(potfile):
                os.unlink(potfile)
            raise CommandError(
                "errors happened while running xgettext on %s\n%s" %
                (file, errors))
        elif verbosity > 0:
            # Print warnings
            stdout.write(errors)
    if msgs:
        write_pot_file(potfile, msgs, orig_file, work_file, is_templatized)
    if is_templatized:
        os.unlink(work_file)

def write_po_file(pofile, potfile, domain, locale, verbosity, stdout,
                  copy_pforms, wrap, location, no_obsolete):
    """
    Creates of updates the :param pofile: PO file for :param domain: and :param
    locale:.  Uses contents of the existing :param potfile:.

    Uses mguniq, msgmerge, and msgattrib GNU gettext utilities.
    """
    msgs, errors, status = _popen('msguniq %s %s --to-code=utf-8 "%s"' %
                                    (wrap, location, potfile))
    if errors:
        if status != STATUS_OK:
            os.unlink(potfile)
            raise CommandError(
                "errors happened while running msguniq\n%s" % errors)
        elif verbosity > 0:
            stdout.write(errors)

    if os.path.exists(pofile):
        with open(potfile, 'w') as fp:
            fp.write(msgs)
        msgs, errors, status = _popen('msgmerge %s %s -q "%s" "%s"' %
                                        (wrap, location, pofile, potfile))
        if errors:
            if status != STATUS_OK:
                os.unlink(potfile)
                raise CommandError(
                    "errors happened while running msgmerge\n%s" % errors)
            elif verbosity > 0:
                stdout.write(errors)
    elif copy_pforms:
        msgs = copy_plural_forms(msgs, locale, domain, verbosity, stdout)
    msgs = msgs.replace(
        "#. #-#-#-#-#  %s.pot (PACKAGE VERSION)  #-#-#-#-#\n" % domain, "")
    with open(pofile, 'w') as fp:
        fp.write(msgs)
    os.unlink(potfile)
    if no_obsolete:
        msgs, errors, status = _popen(
            'msgattrib %s %s -o "%s" --no-obsolete "%s"' %
            (wrap, location, pofile, pofile))
        if errors:
            if status != STATUS_OK:
                raise CommandError(
                    "errors happened while running msgattrib\n%s" % errors)
            elif verbosity > 0:
                stdout.write(errors)

def make_messages(locale=None, domain='django', verbosity=1, all=False,
        extensions=None, symlinks=False, ignore_patterns=None, no_wrap=False,
        no_location=False, no_obsolete=False, stdout=sys.stdout):
    """
    Uses the ``locale/`` directory from the Django Git tree or an
    application/project to process all files with translatable literals for
    the :param domain: domain and :param locale: locale.
    """
    # Need to ensure that the i18n framework is enabled
    from django.conf import settings
    if settings.configured:
        settings.USE_I18N = True
    else:
        settings.configure(USE_I18N = True)

    if ignore_patterns is None:
        ignore_patterns = []

    invoked_for_django = False
    if os.path.isdir(os.path.join('conf', 'locale')):
        localedir = os.path.abspath(os.path.join('conf', 'locale'))
        invoked_for_django = True
        # Ignoring all contrib apps
        ignore_patterns += ['contrib/*']
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

    if domain not in ('django', 'djangojs'):
        raise CommandError("currently makemessages only supports domains 'django' and 'djangojs'")

    if (locale is None and not all) or domain is None:
        message = "Type '%s help %s' for usage information." % (os.path.basename(sys.argv[0]), sys.argv[1])
        raise CommandError(message)

    # We require gettext version 0.15 or newer.
    output, errors, status = _popen('xgettext --version')
    if status != STATUS_OK:
        raise CommandError("Error running xgettext. Note that Django "
                    "internationalization requires GNU gettext 0.15 or newer.")
    match = re.search(r'(?P<major>\d+)\.(?P<minor>\d+)', output)
    if match:
        xversion = (int(match.group('major')), int(match.group('minor')))
        if xversion < (0, 15):
            raise CommandError("Django internationalization requires GNU "
                    "gettext 0.15 or newer. You are using version %s, please "
                    "upgrade your gettext toolset." % match.group())

    locales = []
    if locale is not None:
        locales.append(str(locale))
    elif all:
        locale_dirs = filter(os.path.isdir, glob.glob('%s/*' % localedir))
        locales = [os.path.basename(l) for l in locale_dirs]

    wrap = '--no-wrap' if no_wrap else ''
    location = '--no-location' if no_location else ''

    for locale in locales:
        if verbosity > 0:
            stdout.write("processing language %s\n" % locale)
        basedir = os.path.join(localedir, locale, 'LC_MESSAGES')
        if not os.path.isdir(basedir):
            os.makedirs(basedir)

        pofile = os.path.join(basedir, '%s.po' % str(domain))
        potfile = os.path.join(basedir, '%s.pot' % str(domain))

        if os.path.exists(potfile):
            os.unlink(potfile)

        for dirpath, file in find_files(".", ignore_patterns, verbosity,
                stdout, symlinks=symlinks):
            process_file(file, dirpath, potfile, domain, verbosity, extensions,
                    wrap, location, stdout)

        if os.path.exists(potfile):
            write_po_file(pofile, potfile, domain, locale, verbosity, stdout,
                    not invoked_for_django, wrap, location, no_obsolete)


class Command(NoArgsCommand):
    option_list = NoArgsCommand.option_list + (
        make_option('--locale', '-l', default=None, dest='locale',
            help='Creates or updates the message files for the given locale (e.g. pt_BR).'),
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
            default=True, help="Don't ignore the common glob-style patterns 'CVS', '.*' and '*~'."),
        make_option('--no-wrap', action='store_true', dest='no_wrap',
            default=False, help="Don't break long message lines into several lines"),
        make_option('--no-location', action='store_true', dest='no_location',
            default=False, help="Don't write '#: filename:line' lines"),
        make_option('--no-obsolete', action='store_true', dest='no_obsolete',
            default=False, help="Remove obsolete message strings"),
    )
    help = ("Runs over the entire source tree of the current directory and "
"pulls out all strings marked for translation. It creates (or updates) a message "
"file in the conf/locale (in the django tree) or locale (for projects and "
"applications) directory.\n\nYou must run this command with one of either the "
"--locale or --all options.")

    requires_model_validation = False
    can_import_settings = False

    def handle_noargs(self, *args, **options):
        locale = options.get('locale')
        domain = options.get('domain')
        verbosity = int(options.get('verbosity'))
        process_all = options.get('all')
        extensions = options.get('extensions')
        symlinks = options.get('symlinks')
        ignore_patterns = options.get('ignore_patterns')
        if options.get('use_default_ignore_patterns'):
            ignore_patterns += ['CVS', '.*', '*~']
        ignore_patterns = list(set(ignore_patterns))
        no_wrap = options.get('no_wrap')
        no_location = options.get('no_location')
        no_obsolete = options.get('no_obsolete')
        if domain == 'djangojs':
            exts = extensions if extensions else ['js']
        else:
            exts = extensions if extensions else ['html', 'txt']
        extensions = handle_extensions(exts)

        if verbosity > 1:
            self.stdout.write('examining files with the extensions: %s\n'
                             % get_text_list(list(extensions), 'and'))

        make_messages(locale, domain, verbosity, process_all, extensions,
            symlinks, ignore_patterns, no_wrap, no_location, no_obsolete, self.stdout)
