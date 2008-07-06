import re
import os
import sys
from itertools import dropwhile
from optparse import make_option
from django.core.management.base import CommandError, BaseCommand

pythonize_re = re.compile(r'\n\s*//')

def make_messages(locale=None, domain='django', verbosity='1', all=False):
    """
    Uses the locale directory from the Django SVN tree or an application/
    project to process all 
    """
    # Need to ensure that the i18n framework is enabled
    from django.conf import settings
    settings.configure(USE_I18N = True)
    
    from django.utils.translation import templatize

    if os.path.isdir(os.path.join('conf', 'locale')):
        localedir = os.path.abspath(os.path.join('conf', 'locale'))
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

    languages = []
    if locale is not None:
        languages.append(locale)
    elif all:
        languages = [el for el in os.listdir(localedir) if not el.startswith('.')]

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

        all_files = []
        for (dirpath, dirnames, filenames) in os.walk("."):
            all_files.extend([(dirpath, f) for f in filenames])
        all_files.sort()
        for dirpath, file in all_files:
            if domain == 'djangojs' and file.endswith('.js'):
                if verbosity > 1:
                    sys.stdout.write('processing file %s in %s\n' % (file, dirpath))
                src = open(os.path.join(dirpath, file), "rb").read()
                src = pythonize_re.sub('\n#', src)
                open(os.path.join(dirpath, '%s.py' % file), "wb").write(src)
                thefile = '%s.py' % file
                cmd = 'xgettext -d %s -L Perl --keyword=gettext_noop --keyword=gettext_lazy --keyword=ngettext_lazy:1,2 --from-code UTF-8 -o - "%s"' % (domain, os.path.join(dirpath, thefile))
                (stdin, stdout, stderr) = os.popen3(cmd, 't')
                msgs = stdout.read()
                errors = stderr.read()
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
            elif domain == 'django' and (file.endswith('.py') or file.endswith('.html')):
                thefile = file
                if file.endswith('.html'):
                    src = open(os.path.join(dirpath, file), "rb").read()
                    thefile = '%s.py' % file
                    open(os.path.join(dirpath, thefile), "wb").write(templatize(src))
                if verbosity > 1:
                    sys.stdout.write('processing file %s in %s\n' % (file, dirpath))
                cmd = 'xgettext -d %s -L Python --keyword=gettext_noop --keyword=gettext_lazy --keyword=ngettext_lazy:1,2 --keyword=ugettext_noop --keyword=ugettext_lazy --keyword=ungettext_lazy:1,2 --from-code UTF-8 -o - "%s"' % (
                    domain, os.path.join(dirpath, thefile))
                (stdin, stdout, stderr) = os.popen3(cmd, 't')
                msgs = stdout.read()
                errors = stderr.read()
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
            (stdin, stdout, stderr) = os.popen3('msguniq --to-code=utf-8 "%s"' % potfile, 'b')
            msgs = stdout.read()
            errors = stderr.read()
            if errors:
                raise CommandError("errors happened while running msguniq\n%s" % errors)
            open(potfile, 'w').write(msgs)
            if os.path.exists(pofile):
                (stdin, stdout, stderr) = os.popen3('msgmerge -q "%s" "%s"' % (pofile, potfile), 'b')
                msgs = stdout.read()
                errors = stderr.read()
                if errors:
                    raise CommandError("errors happened while running msgmerge\n%s" % errors)
            open(pofile, 'wb').write(msgs)
            os.unlink(potfile)


class Command(BaseCommand):
    option_list = BaseCommand.option_list + (
        make_option('--locale', '-l', default=None, dest='locale',
            help='Creates or updates the message files only for the given locale (e.g. pt_BR).'),
        make_option('--domain', '-d', default='django', dest='domain',
            help='The domain of the message files (default: "django").'),
        make_option('--verbosity', '-v', action='store', dest='verbosity',
            default='1', type='choice', choices=['0', '1', '2'],
            help='Verbosity level; 0=minimal output, 1=normal output, 2=all output'),
        make_option('--all', '-a', action='store_true', dest='all',
            default=False, help='Reexamines all source code and templates for new translation strings and updates all message files for all available languages.'),
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

        make_messages(locale, domain, verbosity, process_all)
