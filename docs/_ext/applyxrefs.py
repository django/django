"""Adds xref targets to the top of files."""

import sys
import os

testing = False

DONT_TOUCH = (
        './index.txt',
        )

def target_name(fn):
    if fn.endswith('.txt'):
        fn = fn[:-4]
    return '_' + fn.lstrip('./').replace('/', '-')

def process_file(fn, lines):
    lines.insert(0, '\n')
    lines.insert(0, '.. %s:\n' % target_name(fn))
    try:
        with open(fn, 'w') as fp:
            fp.writelines(lines)
    except IOError:
        print("Can't open %s for writing. Not touching it." % fn)

def has_target(fn):
    try:
        with open(fn, 'r') as fp:
            lines = fp.readlines()
    except IOError:
        print("Can't open or read %s. Not touching it." % fn)
        return (True, None)

    #print fn, len(lines)
    if len(lines) < 1:
        print("Not touching empty file %s." % fn)
        return (True, None)
    if lines[0].startswith('.. _'):
        return (True, None)
    return (False, lines)

def main(argv=None):
    if argv is None:
        argv = sys.argv

    if len(argv) == 1:
        argv.extend('.')

    files = []
    for root in argv[1:]:
        for (dirpath, dirnames, filenames) in os.walk(root):
            files.extend([(dirpath, f) for f in filenames])
    files.sort()
    files = [os.path.join(p, fn) for p, fn in files if fn.endswith('.txt')]
    #print files

    for fn in files:
        if fn in DONT_TOUCH:
            print("Skipping blacklisted file %s." % fn)
            continue

        target_found, lines = has_target(fn)
        if not target_found:
            if testing:
                print('%s: %s' % (fn, lines[0]))
            else:
                print("Adding xref to %s" % fn)
                process_file(fn, lines)
        else:
            print("Skipping %s: already has a xref" % fn)

if __name__ == '__main__':
    sys.exit(main())
