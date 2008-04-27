#!/usr/bin/env python

# Need to ensure that the i18n framework is enabled
from django.conf import settings
settings.configure(USE_I18N = True)

from django.utils.translation import templatize
import re
import os
import sys
import getopt
from itertools import dropwhile

pythonize_re = re.compile(r'\n\s*//')

def make_messages():
    localedir = None

    if os.path.isdir(os.path.join('conf', 'locale')):
        localedir = os.path.abspath(os.path.join('conf', 'locale'))
    elif os.path.isdir('locale'):
        localedir = os.path.abspath('locale')
    else:
        print "This script should be run from the django svn tree or your project or app tree."
        print "If you did indeed run it from the svn checkout or your project or application,"
        print "maybe you are just missing the conf/locale (in the django tree) or locale (for project"
        print "and application) directory?"
        print "make-messages.py doesn't create it automatically, you have to create it by hand if"
        print "you want to enable i18n for your project or application."
        sys.exit(1)

    (opts, args) = getopt.getopt(sys.argv[1:], 'l:d:va')

    lang = None
    domain = 'django'
    verbose = False
    all = False

    for o, v in opts:
        if o == '-l':
            lang = v
        elif o == '-d':
            domain = v
        elif o == '-v':
            verbose = True
        elif o == '-a':
            all = True

    if domain not in ('django', 'djangojs'):
        print "currently make-messages.py only supports domains 'django' and 'djangojs'"
        sys.exit(1)
    if (lang is None and not all) or domain is None:
        print "usage: make-messages.py -l <language>"
        print "   or: make-messages.py -a"
        sys.exit(1)

    languages = []

    if lang is not None:
        languages.append(lang)
    elif all:
        languages = [el for el in os.listdir(localedir) if not el.startswith('.')]

    for lang in languages:

        print "processing language", lang
        basedir = os.path.join(localedir, lang, 'LC_MESSAGES')
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
                if verbose: sys.stdout.write('processing file %s in %s\n' % (file, dirpath))
                src = open(os.path.join(dirpath, file), "rb").read()
                src = pythonize_re.sub('\n#', src)
                open(os.path.join(dirpath, '%s.py' % file), "wb").write(src)
                thefile = '%s.py' % file
                cmd = 'xgettext -d %s -L Perl --keyword=gettext_noop --keyword=gettext_lazy --keyword=ngettext_lazy:1,2 --from-code UTF-8 -o - "%s"' % (domain, os.path.join(dirpath, thefile))
                (stdin, stdout, stderr) = os.popen3(cmd, 't')
                msgs = stdout.read()
                errors = stderr.read()
                if errors:
                    print "errors happened while running xgettext on %s" % file
                    print errors
                    sys.exit(8)
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
                if verbose:
                    sys.stdout.write('processing file %s in %s\n' % (file, dirpath))
                cmd = 'xgettext -d %s -L Python --keyword=gettext_noop --keyword=gettext_lazy --keyword=ngettext_lazy:1,2 --keyword=ugettext_noop --keyword=ugettext_lazy --keyword=ungettext_lazy:1,2 --from-code UTF-8 -o - "%s"' % (
                    domain, os.path.join(dirpath, thefile))
                (stdin, stdout, stderr) = os.popen3(cmd, 't')
                msgs = stdout.read()
                errors = stderr.read()
                if errors:
                    print "errors happened while running xgettext on %s" % file
                    print errors
                    sys.exit(8)
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
                print "errors happened while running msguniq"
                print errors
                sys.exit(8)
            open(potfile, 'w').write(msgs)
            if os.path.exists(pofile):
                (stdin, stdout, stderr) = os.popen3('msgmerge -q "%s" "%s"' % (pofile, potfile), 'b')
                msgs = stdout.read()
                errors = stderr.read()
                if errors:
                    print "errors happened while running msgmerge"
                    print errors
                    sys.exit(8)
            open(pofile, 'wb').write(msgs)
            os.unlink(potfile)

if __name__ == "__main__":
    make_messages()
