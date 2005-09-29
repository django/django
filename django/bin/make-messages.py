#!/usr/bin/python

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

(opts, args) = getopt.getopt(sys.argv[1:], 'l:d:')

lang = None
domain = 'django'

for o, v in opts:
    if o == '-l':
        lang = v
    elif o == '-d':
        domain = v

if lang is None or domain is None:
    print "usage: make-messages.py -l <language>"
    sys.exit(1)

basedir = os.path.join(basedir, lang, 'LC_MESSAGES')
if not os.path.isdir(basedir):
    os.makedirs(basedir)

lf = os.path.join(basedir, '%s.po' % domain)

for (dirpath, dirnames, filenames) in os.walk("."):
    for file in filenames:
        if file.endswith('.py') or file.endswith('.html'):
            sys.stderr.write('processing file %s in %s\n' % (file, dirpath))
            if os.path.isfile(lf):
                cmd = 'xgettext -j -d %s -L Python -p %s %s' % (domain, basedir, os.path.join(dirpath, file))
            else:
                cmd = 'xgettext -d %s -L Python -p %s %s' % (domain, basedir, os.path.join(dirpath, file))
            os.system(cmd)

