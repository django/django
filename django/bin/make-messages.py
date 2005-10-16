#!/usr/bin/python

import re
import os
import sys
import getopt

basedir = None

if os.path.isdir(os.path.join('conf', 'locale')):
    basedir = os.path.abspath(os.path.join('conf', 'locale'))
elif os.path.isdir('locale'):
    basedir = os.path.abspath('locale')
else:
    print "this script should be run from the django svn tree or your project or app tree"
    sys.exit(1)

(opts, args) = getopt.getopt(sys.argv[1:], 'l:d:v')

lang = None
domain = 'django'
verbose = False

for o, v in opts:
    if o == '-l':
        lang = v
    elif o == '-d':
        domain = v
    elif o == '-v':
        verbose = True

if lang is None or domain is None:
    print "usage: make-messages.py -l <language>"
    sys.exit(1)

basedir = os.path.join(basedir, lang, 'LC_MESSAGES')
if not os.path.isdir(basedir):
    os.makedirs(basedir)

dot_re = re.compile('\S')
def blank(src):
    return dot_re.sub('p', src)

def templateize(src):
    o = []
    going = 1
    while going:
        start = src.find('{')
        if start >= 0 and src[start+1] in ('{', '%'):
            o.append(blank(src[:start]))
            end = src.find(src[start+1] == '{' and '}}' or '%}', start)
            if end >= 0:
                o.append(src[start:end+2])
                src = src[end+2:]
            else:
                o.append(blank(src[start:]))
                going = 0
        else:
            o.append(blank(src))
            going = 0
    return ''.join(o)

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

