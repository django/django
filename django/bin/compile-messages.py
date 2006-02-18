#!/usr/bin/env python

import os
import sys
import getopt

def compile_messages():
    basedir = None

    if os.path.isdir(os.path.join('conf', 'locale')):
        basedir = os.path.abspath(os.path.join('conf', 'locale'))
    elif os.path.isdir('locale'):
        basedir = os.path.abspath('locale')
    else:
        print "this script should be run from the django svn tree or your project or app tree"
        sys.exit(1)

    for (dirpath, dirnames, filenames) in os.walk(basedir):
        for f in filenames:
            if f.endswith('.po'):
                sys.stderr.write('processing file %s in %s\n' % (f, dirpath))
                pf = os.path.splitext(os.path.join(dirpath, f))[0]
                cmd = 'msgfmt -o "%s.mo" "%s.po"' % (pf, pf)
                os.system(cmd)

if __name__ == "__main__":
    compile_messages()
