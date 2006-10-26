#!/usr/bin/env python

import os
import sys

def compile_messages():
    basedir = None

    if os.path.isdir(os.path.join('conf', 'locale')):
        basedir = os.path.abspath(os.path.join('conf', 'locale'))
    elif os.path.isdir('locale'):
        basedir = os.path.abspath('locale')
    else:
        print "This script should be run from the Django SVN tree or your project or app tree."
        sys.exit(1)

    for dirpath, dirnames, filenames in os.walk(basedir):
        for f in filenames:
            if f.endswith('.po'):
                sys.stderr.write('processing file %s in %s\n' % (f, dirpath))
                pf = os.path.splitext(os.path.join(dirpath, f))[0]
                # Store the names of the .mo and .po files in an environment
                # variable, rather than doing a string replacement into the
                # command, so that we can take advantage of shell quoting, to
                # quote any malicious characters/escaping.
                # See http://cyberelk.net/tim/articles/cmdline/ar01s02.html
                os.environ['djangocompilemo'] = pf + '.mo'
                os.environ['djangocompilepo'] = pf + '.po'
                if sys.platform == 'win32': # Different shell-variable syntax
                    cmd = 'msgfmt -o "%djangocompilemo%" "%djangocompilepo%"'
                else:
                    cmd = 'msgfmt -o "$djangocompilemo" "$djangocompilepo"'
                os.system(cmd)

if __name__ == "__main__":
    compile_messages()
