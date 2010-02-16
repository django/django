import fnmatch
import glob
import os
import re
import sys
from itertools import dropwhile
from optparse import make_option
from subprocess import PIPE, Popen

from django.core.management.base import CommandError, BaseCommand
from django.utils.text import get_text_list

pythonize_re = re.compile(r'(?:^|\n)\s*//')
plural_forms_re = re.compile(r'^(?P<value>"Plural-Forms.+?\\n")\s*$', re.MULTILINE | re.DOTALL)

def handle_extensions(extensions=('html',)):
    """
    organizes multiple extensions that are separated with commas or passed by
    using --extension/-e multiple times.

    for example: running 'django-admin makemessages -e js,txt -e xhtml -a'
    would result in a extension list: ['.js', '.txt', '.xhtml']

    >>> handle_extensions(['.html', 'html,js,py,py,py,.py', 'py,.py'])
    ['.html', '.js']
    >>> handle_extensions(['.html, txt,.tpl'])
    ['.html', '.tpl', '.txt']
    """
    ext_list = []
    for ext in extensions:
        ext_list.extend(ext.replace(' ','').split(','))
    for i, ext in enumerate(ext_list):
        if not ext.startswith('.'):
            ext_list[i] = '.%s' % ext_list[i]

    # we don't want *.py files here because of the way non-*.py files
    # are handled in make_messages() (they are copied to file.ext.py files to
    # trick xgettext to parse them as Python files)
    return set([x for x in ext_list if x != '.py'])

def _popen(cmd):
    """
    Friendly wrapper around Popen for Windows
    """
    p = Popen(cmd, shell=True, stdout=PIPE, stderr=PIPE, close_fds=os.name != 'nt', universal_newlines=True)
    return p.communicate()

def walk(root, topdown=True, onerror=None, followlinks=False):
    """
    A version of os.walk that can follow symlinks for Python < 2.6
    """
    for dirpath, dirnames, filenames in os.walk(root, topdown, onerror):
        yield (dirpath, dirnames, filenames)
        if followlinks:
            for d in dirnames:
                p = os.path.join(dirpath, d)
                if os.path.islink(p):
                    for link_dirpath, link_dirnames, link_filenames in walk(p):
                        yield (link_dirpath, link_dirnames, link_filenames)

def is_ignored(path, ignore_patterns):
    """
    Helper function to check if the given path should be ignored or not.
    """
    for pattern in ignore_patterns:
        if fnmatch.fnmatchcase(path, pattern):
            return True
    return False

def find_files(root, ignore_patterns, verbosity, symlinks=False):
    """
    Helper function to get all files in the given root.
    """
    all_files = []
    for (dirpath, dirnames, filenames) in walk(".", followlinks=symlinks):
        for f in filenames:
            norm_filepath = os.path.normpath(os.path.join(dirpath, f))
            if is_ignored(norm_filepath, ignore_patterns):
                if verbosity > 1:
                    sys.stdout.write('ignoring file %s in %s\n' % (f, dirpath))
            else:
                all_files.extend([(dirpath, f)])
    all_files.sort()
    return all_files

def copy_plural_forms(msgs, locale, domain, verbosity):
    """
    Copies plural forms header contents from a Django catalog of locale to
    the msgs string, inserting it at the right place. msgs should be the
    contents of a newly created .po file.
    """
    import django
    django_dir = os.path.normpath(os.path.join(os.path.dirname(django.__file__)))
    if domain == 'djangojs':
        domains = ('djangojs', 'django')
    else:
        domains = ('django',)
    for domain in domains:
        django_po = os.path.join(django_dir, 'conf', 'locale', locale, 'LC_MESSAGES', '%s.po' % domain)
        if os.path.exists(django_po):
            m = plural_forms_re.search(open(django_po, 'rU').read())
            if m:
                if verbosity > 1:
                    sys.stderr.write("copying plural forms: %s\n" % m.group('value'))
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


def make_messages(locale=None, domain='django', verbosity='1', all=False,
        extensions=None, symlinks=False, ignore_patterns=[]):
    """
    Uses the locale directory from the Django SVN tree or an application/
    project to process all
    """
    # Need to ensure that the i18n framework is enabled
    from django.conf import settings
    if settings.configured:
        settings.USE_I18N = True
    else:
        settings.configure(USE_I18N = True)

    from django.utils.translation import templatize

    invoked_for_django = False
    if os.path.isdir(os.path.join('conf', 'locale')):
        localedir = os.path.abspath(os.path.join('conf', 'locale'))
        invoked_for_django = True
    elif os.path.isdir('locale'):
        localedir = os.path.abspath('locale')
    else:
        raise CommandError("This script should be run from the Django SVN tree or your project or app tree. If you did indeed run it from the SVN checkout or your project or application, maybe you are just missing the conf/locale (in the django tree) or locale (for project and application) directory? It is not created automatically, you have to create it by hand if you want to enable i18n for your project or application.")

    if domain not in ('django', 'djangojs'):
        raise CommandError("currently makemessages only supports domains 'django' and 'djangojs'")

    if (locale is None and not all) or domain is None:
        # backwards compatible error message
        if not sys.argv[0].endswith("make-messages.py"):
            message = "Type '%s help %s' for usage.\n" % (os.path.basename(sys.argv[0]), sys.argv[1])
        else:
            message = "usage: make-messages.py -l <language>\n   or: make-messages.py -a\n"
        raise CommandError(message)

    # We require gettext version 0.15 or newer.
    output = _popen('xgettext --version')[0]
    match = re.search(r'(?P<major>\d+)\.(?P<minor>\d+)', output)
    if match:
        xversion = (int(match.group('major')), int(match.group('minor')))
        if xversion < (0, 15):
            raise CommandError("Django internationalization requires GNU gettext 0.15 or newer. You are using version %s, please upgrade your gettext toolset." % match.group())

    languages = []
    if locale is not None:
        languages.append(locale)
    elif all:
        locale_dirs = filter(os.path.isdir, glob.glob('%s/*' % localedir))
        languages = [os.path.basename(l) for l in locale_dirs]

    for locale in languages:
        if verbosity > 0:
            print "processing language", locale
        basedir = os.path.join(localedir, locale, 'LC_MESSAGES')
        if not os.path.isdir(basedir):
            os.makedirs(basedir)

        pofile = os.path.join(basedir, '%s.po' % domain)
        potfile = os.path.join(basedir, '%s.pot' % domain)

        if os.path.exists(potfile):
            os.unlink(potfile)

        for dirpath, file in find_files(".", ignore_patterns, verbosity, symlinks=symlinks):
            file_base, file_ext = os.path.splitext(file)
            if domain == 'djangojs' and file_ext in extensions:
                if verbosity > 1:
                    sys.stdout.write('processing file %s in %s\n' % (file, dirpath))
                src = open(os.path.join(dirpath, file), "rU").read()
                src = pythonize_re.sub('\n#', src)
                thefile = '%s.py' % file
                open(os.path.join(dirpath, thefile), "w").write(src)
                cmd = 'xgettext -d %s -L Perl --keyword=gettext_noop --keyword=gettext_lazy --keyword=ngettext_lazy:1,2 --from-code UTF-8 -o - "%s"' % (domain, os.path.join(dirpath, thefile))
                msgs, errors = _popen(cmd)
                if errors:
                    raise CommandError("errors happened while running xgettext on %s\n%s" % (file, errors))
                old = '#: '+os.path.join(dirpath, thefile)[2:]
                new = '#: '+os.path.join(dirpath, file)[2:]
                msgs = msgs.replace(old, new)
                if os.path.exists(potfile):
                    # Strip the header
                    msgs = '\n'.join(dropwhile(len, msgs.split('\n')))
                else:
                    msgs = msgs.replace('charset=CHARSET', 'charset=UTF-8')
                if msgs:
                    open(potfile, 'ab').write(msgs)
                os.unlink(os.path.join(dirpath, thefile))
            elif domain == 'django' and (file_ext == '.py' or file_ext in extensions):
                thefile = file
                if file_ext in extensions:
                    src = open(os.path.join(dirpath, file), "rU").read()
                    thefile = '%s.py' % file
                    try:
                        open(os.path.join(dirpath, thefile), "w").write(templatize(src))
                    except SyntaxError, msg:
                        msg = "%s (file: %s)" % (msg, os.path.join(dirpath, file))
                        raise SyntaxError(msg)
                if verbosity > 1:
                    sys.stdout.write('processing file %s in %s\n' % (file, dirpath))
                cmd = 'xgettext -d %s -L Python --keyword=gettext_noop --keyword=gettext_lazy --keyword=ngettext_lazy:1,2 --keyword=ugettext_noop --keyword=ugettext_lazy --keyword=ungettext_lazy:1,2 --from-code UTF-8 -o - "%s"' % (
                    domain, os.path.join(dirpath, thefile))
                msgs, errors = _popen(cmd)
                if errors:
                    raise CommandError("errors happened while running xgettext on %s\n%s" % (file, errors))

                if thefile != file:
                    old = '#: '+os.path.join(dirpath, thefile)[2:]
                    new = '#: '+os.path.join(dirpath, file)[2:]
                    msgs = msgs.replace(old, new)
                if os.path.exists(potfile):
                    # Strip the header
                    msgs = '\n'.join(dropwhile(len, msgs.split('\n')))
                else:
                    msgs = msgs.replace('charset=CHARSET', 'charset=UTF-8')
                if msgs:
                    open(potfile, 'ab').write(msgs)
                if thefile != file:
                    os.unlink(os.path.join(dirpath, thefile))

        if os.path.exists(potfile):
            msgs, errors = _popen('msguniq --to-code=utf-8 "%s"' % potfile)
            if errors:
                raise CommandError("errors happened while running msguniq\n%s" % errors)
            open(potfile, 'w').write(msgs)
            if os.path.exists(pofile):
                msgs, errors = _popen('msgmerge -q "%s" "%s"' % (pofile, potfile))
                if errors:
                    raise CommandError("errors happened while running msgmerge\n%s" % errors)
            elif not invoked_for_django:
                msgs = copy_plural_forms(msgs, locale, domain, verbosity)
            open(pofile, 'wb').write(msgs)
            os.unlink(potfile)


class Command(BaseCommand):
    option_list = BaseCommand.option_list + (
        make_option('--locale', '-l', default=None, dest='locale',
            help='Creates or updates the message files only for the given locale (e.g. pt_BR).'),
        make_option('--domain', '-d', default='django', dest='domain',
            help='The domain of the message files (default: "django").'),
        make_option('--all', '-a', action='store_true', dest='all',
            default=False, help='Reexamines all source code and templates for new translation strings and updates all message files for all available languages.'),
        make_option('--extension', '-e', dest='extensions',
            help='The file extension(s) to examine (default: ".html", separate multiple extensions with commas, or use -e multiple times)',
            action='append'),
        make_option('--symlinks', '-s', action='store_true', dest='symlinks',
            default=False, help='Follows symlinks to directories when examining source code and templates for translation strings.'),
        make_option('--ignore', '-i', action='append', dest='ignore_patterns',
            default=[], metavar='PATTERN', help='Ignore files or directories matching this glob-style pattern. Use multiple times to ignore more.'),
        make_option('--no-default-ignore', action='store_false', dest='use_default_ignore_patterns',
            default=True, help="Don't ignore the common glob-style patterns 'CVS', '.*' and '*~'."),
    )
    help = "Runs over the entire source tree of the current directory and pulls out all strings marked for translation. It creates (or updates) a message file in the conf/locale (in the django tree) or locale (for project and application) directory."

    requires_model_validation = False
    can_import_settings = False

    def handle(self, *args, **options):
        if len(args) != 0:
            raise CommandError("Command doesn't accept any arguments")

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

        if domain == 'djangojs':
            extensions = handle_extensions(extensions or ['js'])
        else:
            extensions = handle_extensions(extensions or ['html'])

        if verbosity > 1:
            sys.stdout.write('examining files with the extensions: %s\n' % get_text_list(list(extensions), 'and'))

        make_messages(locale, domain, verbosity, process_all, extensions, symlinks, ignore_patterns)
