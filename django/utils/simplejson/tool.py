r"""Using simplejson from the shell to validate and
pretty-print::

    $ echo '{"json":"obj"}' | python -msimplejson.tool
    {
        "json": "obj"
    }
    $ echo '{ 1.2:3.4}' | python -msimplejson.tool
    Expecting property name: line 1 column 2 (char 2)
"""
from django.utils import simplejson

def main():
    import sys
    if len(sys.argv) == 1:
        infile = sys.stdin
        outfile = sys.stdout
    elif len(sys.argv) == 2:
        infile = open(sys.argv[1], 'rb')
        outfile = sys.stdout
    elif len(sys.argv) == 3:
        infile = open(sys.argv[1], 'rb')
        outfile = open(sys.argv[2], 'wb')
    else:
        raise SystemExit("%s [infile [outfile]]" % (sys.argv[0],))
    try:
        obj = simplejson.load(infile)
    except ValueError, e:
        raise SystemExit(e)
    simplejson.dump(obj, outfile, sort_keys=True, indent=4)
    outfile.write('\n')


if __name__ == '__main__':
    main()
