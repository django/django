#!/usr/bin/env python

if __name__ == "__main__":
    import sys
    name = sys.argv[0]
    args = ' '.join(sys.argv[1:])
    print >> sys.stderr, "%s has been moved into django-admin.py" % name
    print >> sys.stderr, 'Please run "django-admin.py makemessages %s" instead.'% args
    print >> sys.stderr
    sys.exit(1)

