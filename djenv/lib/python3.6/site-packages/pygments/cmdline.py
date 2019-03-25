# -*- coding: utf-8 -*-
"""
    pygments.cmdline
    ~~~~~~~~~~~~~~~~

    Command line interface.

    :copyright: Copyright 2006-2017 by the Pygments team, see AUTHORS.
    :license: BSD, see LICENSE for details.
"""

from __future__ import print_function

import os
import sys
import getopt
from textwrap import dedent

from pygments import __version__, highlight
from pygments.util import ClassNotFound, OptionError, docstring_headline, \
    guess_decode, guess_decode_from_terminal, terminal_encoding
from pygments.lexers import get_all_lexers, get_lexer_by_name, guess_lexer, \
    load_lexer_from_file, get_lexer_for_filename, find_lexer_class_for_filename
from pygments.lexers.special import TextLexer
from pygments.formatters.latex import LatexEmbeddedLexer, LatexFormatter
from pygments.formatters import get_all_formatters, get_formatter_by_name, \
    load_formatter_from_file, get_formatter_for_filename, find_formatter_class
from pygments.formatters.terminal import TerminalFormatter
from pygments.formatters.terminal256 import Terminal256Formatter
from pygments.filters import get_all_filters, find_filter_class
from pygments.styles import get_all_styles, get_style_by_name


USAGE = """\
Usage: %s [-l <lexer> | -g] [-F <filter>[:<options>]] [-f <formatter>]
          [-O <options>] [-P <option=value>] [-s] [-v] [-x] [-o <outfile>] [<infile>]

       %s -S <style> -f <formatter> [-a <arg>] [-O <options>] [-P <option=value>]
       %s -L [<which> ...]
       %s -N <filename>
       %s -H <type> <name>
       %s -h | -V

Highlight the input file and write the result to <outfile>.

If no input file is given, use stdin, if -o is not given, use stdout.

If -s is passed, lexing will be done in "streaming" mode, reading and
highlighting one line at a time.  This will only work properly with
lexers that have no constructs spanning multiple lines!

<lexer> is a lexer name (query all lexer names with -L). If -l is not
given, the lexer is guessed from the extension of the input file name
(this obviously doesn't work if the input is stdin).  If -g is passed,
attempt to guess the lexer from the file contents, or pass through as
plain text if this fails (this can work for stdin).

Likewise, <formatter> is a formatter name, and will be guessed from
the extension of the output file name. If no output file is given,
the terminal formatter will be used by default.

The additional option -x allows custom lexers and formatters to be
loaded from a .py file relative to the current working directory. For
example, ``-l ./customlexer.py -x``. By default, this option expects a
file with a class named CustomLexer or CustomFormatter; you can also
specify your own class name with a colon (``-l ./lexer.py:MyLexer``).
Users should be very careful not to use this option with untrusted files,
because it will import and run them.

With the -O option, you can give the lexer and formatter a comma-
separated list of options, e.g. ``-O bg=light,python=cool``.

The -P option adds lexer and formatter options like the -O option, but
you can only give one option per -P. That way, the option value may
contain commas and equals signs, which it can't with -O, e.g.
``-P "heading=Pygments, the Python highlighter".

With the -F option, you can add filters to the token stream, you can
give options in the same way as for -O after a colon (note: there must
not be spaces around the colon).

The -O, -P and -F options can be given multiple times.

With the -S option, print out style definitions for style <style>
for formatter <formatter>. The argument given by -a is formatter
dependent.

The -L option lists lexers, formatters, styles or filters -- set
`which` to the thing you want to list (e.g. "styles"), or omit it to
list everything.

The -N option guesses and prints out a lexer name based solely on
the given filename. It does not take input or highlight anything.
If no specific lexer can be determined "text" is returned.

The -H option prints detailed help for the object <name> of type <type>,
where <type> is one of "lexer", "formatter" or "filter".

The -s option processes lines one at a time until EOF, rather than
waiting to process the entire file.  This only works for stdin, and
is intended for streaming input such as you get from 'tail -f'.
Example usage: "tail -f sql.log | pygmentize -s -l sql"

The -v option prints a detailed traceback on unhandled exceptions,
which is useful for debugging and bug reports.

The -h option prints this help.
The -V option prints the package version.
"""


def _parse_options(o_strs):
    opts = {}
    if not o_strs:
        return opts
    for o_str in o_strs:
        if not o_str.strip():
            continue
        o_args = o_str.split(',')
        for o_arg in o_args:
            o_arg = o_arg.strip()
            try:
                o_key, o_val = o_arg.split('=', 1)
                o_key = o_key.strip()
                o_val = o_val.strip()
            except ValueError:
                opts[o_arg] = True
            else:
                opts[o_key] = o_val
    return opts


def _parse_filters(f_strs):
    filters = []
    if not f_strs:
        return filters
    for f_str in f_strs:
        if ':' in f_str:
            fname, fopts = f_str.split(':', 1)
            filters.append((fname, _parse_options([fopts])))
        else:
            filters.append((f_str, {}))
    return filters


def _print_help(what, name):
    try:
        if what == 'lexer':
            cls = get_lexer_by_name(name)
            print("Help on the %s lexer:" % cls.name)
            print(dedent(cls.__doc__))
        elif what == 'formatter':
            cls = find_formatter_class(name)
            print("Help on the %s formatter:" % cls.name)
            print(dedent(cls.__doc__))
        elif what == 'filter':
            cls = find_filter_class(name)
            print("Help on the %s filter:" % name)
            print(dedent(cls.__doc__))
        return 0
    except (AttributeError, ValueError):
        print("%s not found!" % what, file=sys.stderr)
        return 1


def _print_list(what):
    if what == 'lexer':
        print()
        print("Lexers:")
        print("~~~~~~~")

        info = []
        for fullname, names, exts, _ in get_all_lexers():
            tup = (', '.join(names)+':', fullname,
                   exts and '(filenames ' + ', '.join(exts) + ')' or '')
            info.append(tup)
        info.sort()
        for i in info:
            print(('* %s\n    %s %s') % i)

    elif what == 'formatter':
        print()
        print("Formatters:")
        print("~~~~~~~~~~~")

        info = []
        for cls in get_all_formatters():
            doc = docstring_headline(cls)
            tup = (', '.join(cls.aliases) + ':', doc, cls.filenames and
                   '(filenames ' + ', '.join(cls.filenames) + ')' or '')
            info.append(tup)
        info.sort()
        for i in info:
            print(('* %s\n    %s %s') % i)

    elif what == 'filter':
        print()
        print("Filters:")
        print("~~~~~~~~")

        for name in get_all_filters():
            cls = find_filter_class(name)
            print("* " + name + ':')
            print("    %s" % docstring_headline(cls))

    elif what == 'style':
        print()
        print("Styles:")
        print("~~~~~~~")

        for name in get_all_styles():
            cls = get_style_by_name(name)
            print("* " + name + ':')
            print("    %s" % docstring_headline(cls))


def main_inner(popts, args, usage):
    opts = {}
    O_opts = []
    P_opts = []
    F_opts = []
    for opt, arg in popts:
        if opt == '-O':
            O_opts.append(arg)
        elif opt == '-P':
            P_opts.append(arg)
        elif opt == '-F':
            F_opts.append(arg)
        opts[opt] = arg

    if opts.pop('-h', None) is not None:
        print(usage)
        return 0

    if opts.pop('-V', None) is not None:
        print('Pygments version %s, (c) 2006-2017 by Georg Brandl.' % __version__)
        return 0

    # handle ``pygmentize -L``
    L_opt = opts.pop('-L', None)
    if L_opt is not None:
        if opts:
            print(usage, file=sys.stderr)
            return 2

        # print version
        main(['', '-V'])
        if not args:
            args = ['lexer', 'formatter', 'filter', 'style']
        for arg in args:
            _print_list(arg.rstrip('s'))
        return 0

    # handle ``pygmentize -H``
    H_opt = opts.pop('-H', None)
    if H_opt is not None:
        if opts or len(args) != 2:
            print(usage, file=sys.stderr)
            return 2

        what, name = args  # pylint: disable=unbalanced-tuple-unpacking
        if what not in ('lexer', 'formatter', 'filter'):
            print(usage, file=sys.stderr)
            return 2

        return _print_help(what, name)

    # parse -O options
    parsed_opts = _parse_options(O_opts)
    opts.pop('-O', None)

    # parse -P options
    for p_opt in P_opts:
        try:
            name, value = p_opt.split('=', 1)
        except ValueError:
            parsed_opts[p_opt] = True
        else:
            parsed_opts[name] = value
    opts.pop('-P', None)

    # encodings
    inencoding = parsed_opts.get('inencoding', parsed_opts.get('encoding'))
    outencoding = parsed_opts.get('outencoding', parsed_opts.get('encoding'))

    # handle ``pygmentize -N``
    infn = opts.pop('-N', None)
    if infn is not None:
        lexer = find_lexer_class_for_filename(infn)
        if lexer is None:
            lexer = TextLexer

        print(lexer.aliases[0])
        return 0

    # handle ``pygmentize -S``
    S_opt = opts.pop('-S', None)
    a_opt = opts.pop('-a', None)
    if S_opt is not None:
        f_opt = opts.pop('-f', None)
        if not f_opt:
            print(usage, file=sys.stderr)
            return 2
        if opts or args:
            print(usage, file=sys.stderr)
            return 2

        try:
            parsed_opts['style'] = S_opt
            fmter = get_formatter_by_name(f_opt, **parsed_opts)
        except ClassNotFound as err:
            print(err, file=sys.stderr)
            return 1

        print(fmter.get_style_defs(a_opt or ''))
        return 0

    # if no -S is given, -a is not allowed
    if a_opt is not None:
        print(usage, file=sys.stderr)
        return 2

    # parse -F options
    F_opts = _parse_filters(F_opts)
    opts.pop('-F', None)

    allow_custom_lexer_formatter = False
    # -x: allow custom (eXternal) lexers and formatters
    if opts.pop('-x', None) is not None:
        allow_custom_lexer_formatter = True

    # select lexer
    lexer = None

    # given by name?
    lexername = opts.pop('-l', None)
    if lexername:
        # custom lexer, located relative to user's cwd
        if allow_custom_lexer_formatter and '.py' in lexername:
            try:
                if ':' in lexername:
                    filename, name = lexername.rsplit(':', 1)
                    lexer = load_lexer_from_file(filename, name,
                                                 **parsed_opts)
                else:
                    lexer = load_lexer_from_file(lexername, **parsed_opts)
            except ClassNotFound as err:
                print('Error:', err, file=sys.stderr)
                return 1
        else:
            try:
                lexer = get_lexer_by_name(lexername, **parsed_opts)
            except (OptionError, ClassNotFound) as err:
                print('Error:', err, file=sys.stderr)
                return 1

    # read input code
    code = None

    if args:
        if len(args) > 1:
            print(usage, file=sys.stderr)
            return 2

        if '-s' in opts:
            print('Error: -s option not usable when input file specified',
                  file=sys.stderr)
            return 2

        infn = args[0]
        try:
            with open(infn, 'rb') as infp:
                code = infp.read()
        except Exception as err:
            print('Error: cannot read infile:', err, file=sys.stderr)
            return 1
        if not inencoding:
            code, inencoding = guess_decode(code)

        # do we have to guess the lexer?
        if not lexer:
            try:
                lexer = get_lexer_for_filename(infn, code, **parsed_opts)
            except ClassNotFound as err:
                if '-g' in opts:
                    try:
                        lexer = guess_lexer(code, **parsed_opts)
                    except ClassNotFound:
                        lexer = TextLexer(**parsed_opts)
                else:
                    print('Error:', err, file=sys.stderr)
                    return 1
            except OptionError as err:
                print('Error:', err, file=sys.stderr)
                return 1

    elif '-s' not in opts:  # treat stdin as full file (-s support is later)
        # read code from terminal, always in binary mode since we want to
        # decode ourselves and be tolerant with it
        if sys.version_info > (3,):
            # Python 3: we have to use .buffer to get a binary stream
            code = sys.stdin.buffer.read()
        else:
            code = sys.stdin.read()
        if not inencoding:
            code, inencoding = guess_decode_from_terminal(code, sys.stdin)
            # else the lexer will do the decoding
        if not lexer:
            try:
                lexer = guess_lexer(code, **parsed_opts)
            except ClassNotFound:
                lexer = TextLexer(**parsed_opts)

    else:  # -s option needs a lexer with -l
        if not lexer:
            print('Error: when using -s a lexer has to be selected with -l',
                  file=sys.stderr)
            return 2

    # process filters
    for fname, fopts in F_opts:
        try:
            lexer.add_filter(fname, **fopts)
        except ClassNotFound as err:
            print('Error:', err, file=sys.stderr)
            return 1

    # select formatter
    outfn = opts.pop('-o', None)
    fmter = opts.pop('-f', None)
    if fmter:
        # custom formatter, located relative to user's cwd
        if allow_custom_lexer_formatter and '.py' in fmter:
            try:
                if ':' in fmter:
                    file, fmtername = fmter.rsplit(':', 1)
                    fmter = load_formatter_from_file(file, fmtername,
                                                     **parsed_opts)
                else:
                    fmter = load_formatter_from_file(fmter, **parsed_opts)
            except ClassNotFound as err:
                print('Error:', err, file=sys.stderr)
                return 1
        else:
            try:
                fmter = get_formatter_by_name(fmter, **parsed_opts)
            except (OptionError, ClassNotFound) as err:
                print('Error:', err, file=sys.stderr)
                return 1

    if outfn:
        if not fmter:
            try:
                fmter = get_formatter_for_filename(outfn, **parsed_opts)
            except (OptionError, ClassNotFound) as err:
                print('Error:', err, file=sys.stderr)
                return 1
        try:
            outfile = open(outfn, 'wb')
        except Exception as err:
            print('Error: cannot open outfile:', err, file=sys.stderr)
            return 1
    else:
        if not fmter:
            if '256' in os.environ.get('TERM', ''):
                fmter = Terminal256Formatter(**parsed_opts)
            else:
                fmter = TerminalFormatter(**parsed_opts)
        if sys.version_info > (3,):
            # Python 3: we have to use .buffer to get a binary stream
            outfile = sys.stdout.buffer
        else:
            outfile = sys.stdout

    # determine output encoding if not explicitly selected
    if not outencoding:
        if outfn:
            # output file? use lexer encoding for now (can still be None)
            fmter.encoding = inencoding
        else:
            # else use terminal encoding
            fmter.encoding = terminal_encoding(sys.stdout)

    # provide coloring under Windows, if possible
    if not outfn and sys.platform in ('win32', 'cygwin') and \
       fmter.name in ('Terminal', 'Terminal256'):  # pragma: no cover
        # unfortunately colorama doesn't support binary streams on Py3
        if sys.version_info > (3,):
            from pygments.util import UnclosingTextIOWrapper
            outfile = UnclosingTextIOWrapper(outfile, encoding=fmter.encoding)
            fmter.encoding = None
        try:
            import colorama.initialise
        except ImportError:
            pass
        else:
            outfile = colorama.initialise.wrap_stream(
                outfile, convert=None, strip=None, autoreset=False, wrap=True)

    # When using the LaTeX formatter and the option `escapeinside` is
    # specified, we need a special lexer which collects escaped text
    # before running the chosen language lexer.
    escapeinside = parsed_opts.get('escapeinside', '')
    if len(escapeinside) == 2 and isinstance(fmter, LatexFormatter):
        left = escapeinside[0]
        right = escapeinside[1]
        lexer = LatexEmbeddedLexer(left, right, lexer)

    # ... and do it!
    if '-s' not in opts:
        # process whole input as per normal...
        highlight(code, lexer, fmter, outfile)
        return 0
    else:
        # line by line processing of stdin (eg: for 'tail -f')...
        try:
            while 1:
                if sys.version_info > (3,):
                    # Python 3: we have to use .buffer to get a binary stream
                    line = sys.stdin.buffer.readline()
                else:
                    line = sys.stdin.readline()
                if not line:
                    break
                if not inencoding:
                    line = guess_decode_from_terminal(line, sys.stdin)[0]
                highlight(line, lexer, fmter, outfile)
                if hasattr(outfile, 'flush'):
                    outfile.flush()
            return 0
        except KeyboardInterrupt:  # pragma: no cover
            return 0


def main(args=sys.argv):
    """
    Main command line entry point.
    """
    usage = USAGE % ((args[0],) * 6)

    try:
        popts, args = getopt.getopt(args[1:], "l:f:F:o:O:P:LS:a:N:vhVHgsx")
    except getopt.GetoptError:
        print(usage, file=sys.stderr)
        return 2

    try:
        return main_inner(popts, args, usage)
    except Exception:
        if '-v' in dict(popts):
            print(file=sys.stderr)
            print('*' * 65, file=sys.stderr)
            print('An unhandled exception occurred while highlighting.',
                  file=sys.stderr)
            print('Please report the whole traceback to the issue tracker at',
                  file=sys.stderr)
            print('<https://bitbucket.org/birkenfeld/pygments-main/issues>.',
                  file=sys.stderr)
            print('*' * 65, file=sys.stderr)
            print(file=sys.stderr)
            raise
        import traceback
        info = traceback.format_exception(*sys.exc_info())
        msg = info[-1].strip()
        if len(info) >= 3:
            # extract relevant file and position info
            msg += '\n   (f%s)' % info[-2].split('\n')[0].strip()[1:]
        print(file=sys.stderr)
        print('*** Error while highlighting:', file=sys.stderr)
        print(msg, file=sys.stderr)
        print('*** If this is a bug you want to report, please rerun with -v.',
              file=sys.stderr)
        return 1
