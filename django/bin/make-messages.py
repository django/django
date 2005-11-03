#!/usr/bin/python

import re
import os
import sys
import getopt

from django.utils.translation import templateize

localedir = None

if os.path.isdir(os.path.join('conf', 'locale')):
    localedir = os.path.abspath(os.path.join('conf', 'locale'))
elif os.path.isdir('locale'):
    localedir = os.path.abspath('locale')
else:
    print "this script should be run from the django svn tree or your project or app tree"
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

    for (dirpath, dirnames, filenames) in os.walk("."):
        for file in filenames:
            if file.endswith('.py') or file.endswith('.html'):
                thefile = file
                if file.endswith('.html'):
                    src = open(os.path.join(dirpath, file), "rb").read()
                    open(os.path.join(dirpath, '%s.py' % file), "wb").write(templateize(src))
                    thefile = '%s.py' % file
                if verbose: sys.stdout.write('processing file %s in %s\n' % (file, dirpath))
                cmd = 'xgettext %s -d %s -L Python --keyword=gettext_noop --keyword=gettext_lazy --keyword=ngettext_lazy -o - "%s"' % (
                    os.path.exists(potfile) and '--omit-header' or '', domain, os.path.join(dirpath, thefile))
                msgs = os.popen(cmd, 'r').read()
                if thefile != file:
                    old = '#: '+os.path.join(dirpath, thefile)[2:]
                    new = '#: '+os.path.join(dirpath, file)[2:]
                    msgs = msgs.replace(old, new)
                if msgs:
                    open(potfile, 'ab').write(msgs)
                if thefile != file:
                    os.unlink(os.path.join(dirpath, thefile))

    msgs = os.popen('msguniq %s' % potfile, 'r').read()
    open(potfile, 'w').write(msgs)
    if os.path.exists(pofile):
        msgs = os.popen('msgmerge %s %s' % (pofile, potfile), 'r').read()
    open(pofile, 'wb').write(msgs)
    os.unlink(potfile)

