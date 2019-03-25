# -*- coding: utf-8 -*-
"""
    sphinx.cmd.build
    ~~~~~~~~~~~~~~~~

    Build documentation from a provided source.

    :copyright: Copyright 2007-2019 by the Sphinx team, see AUTHORS.
    :license: BSD, see LICENSE for details.
"""
from __future__ import print_function

import argparse
import locale
import multiprocessing
import os
import sys
import traceback

from docutils.utils import SystemMessage
from six import text_type, binary_type

import sphinx.locale
from sphinx import __display_version__, package_dir
from sphinx.application import Sphinx
from sphinx.errors import SphinxError
from sphinx.locale import __
from sphinx.util import Tee, format_exception_cut_frames, save_traceback
from sphinx.util.console import red, nocolor, color_terminal  # type: ignore
from sphinx.util.docutils import docutils_namespace, patch_docutils
from sphinx.util.pycompat import terminal_safe

if False:
    # For type annotation
    from typing import Any, IO, List, Union  # NOQA


def handle_exception(app, args, exception, stderr=sys.stderr):
    # type: (Sphinx, Any, Union[Exception, KeyboardInterrupt], IO) -> None
    if args.pdb:
        import pdb
        print(red(__('Exception occurred while building, starting debugger:')),
              file=stderr)
        traceback.print_exc()
        pdb.post_mortem(sys.exc_info()[2])
    else:
        print(file=stderr)
        if args.verbosity or args.traceback:
            traceback.print_exc(None, stderr)
            print(file=stderr)
        if isinstance(exception, KeyboardInterrupt):
            print(__('interrupted!'), file=stderr)
        elif isinstance(exception, SystemMessage):
            print(red(__('reST markup error:')), file=stderr)
            print(terminal_safe(exception.args[0]), file=stderr)
        elif isinstance(exception, SphinxError):
            print(red('%s:' % exception.category), file=stderr)
            print(terminal_safe(text_type(exception)), file=stderr)
        elif isinstance(exception, UnicodeError):
            print(red(__('Encoding error:')), file=stderr)
            print(terminal_safe(text_type(exception)), file=stderr)
            tbpath = save_traceback(app)
            print(red(__('The full traceback has been saved in %s, if you want '
                         'to report the issue to the developers.') % tbpath),
                  file=stderr)
        elif isinstance(exception, RuntimeError) and 'recursion depth' in str(exception):
            print(red(__('Recursion error:')), file=stderr)
            print(terminal_safe(text_type(exception)), file=stderr)
            print(file=stderr)
            print(__('This can happen with very large or deeply nested source '
                     'files.  You can carefully increase the default Python '
                     'recursion limit of 1000 in conf.py with e.g.:'), file=stderr)
            print(__('    import sys; sys.setrecursionlimit(1500)'), file=stderr)
        else:
            print(red(__('Exception occurred:')), file=stderr)
            print(format_exception_cut_frames().rstrip(), file=stderr)
            tbpath = save_traceback(app)
            print(red(__('The full traceback has been saved in %s, if you '
                         'want to report the issue to the developers.') % tbpath),
                  file=stderr)
            print(__('Please also report this if it was a user error, so '
                     'that a better error message can be provided next time.'),
                  file=stderr)
            print(__('A bug report can be filed in the tracker at '
                     '<https://github.com/sphinx-doc/sphinx/issues>. Thanks!'),
                  file=stderr)


def jobs_argument(value):
    # type: (str) -> int
    """
    Special type to handle 'auto' flags passed to 'sphinx-build' via -j flag. Can
    be expanded to handle other special scaling requests, such as setting job count
    to cpu_count.
    """
    if value == 'auto':
        return multiprocessing.cpu_count()
    else:
        jobs = int(value)
        if jobs <= 0:
            raise argparse.ArgumentTypeError(__('job number should be a positive number'))
        else:
            return jobs


def get_parser():
    # type: () -> argparse.ArgumentParser
    parser = argparse.ArgumentParser(
        usage='%(prog)s [OPTIONS] SOURCEDIR OUTPUTDIR [FILENAMES...]',
        epilog=__('For more information, visit <http://sphinx-doc.org/>.'),
        description=__("""
Generate documentation from source files.

sphinx-build generates documentation from the files in SOURCEDIR and places it
in OUTPUTDIR. It looks for 'conf.py' in SOURCEDIR for the configuration
settings.  The 'sphinx-quickstart' tool may be used to generate template files,
including 'conf.py'

sphinx-build can create documentation in different formats. A format is
selected by specifying the builder name on the command line; it defaults to
HTML. Builders can also perform other tasks related to documentation
processing.

By default, everything that is outdated is built. Output only for selected
files can be built by specifying individual filenames.
"""))

    parser.add_argument('--version', action='version', dest='show_version',
                        version='%%(prog)s %s' % __display_version__)

    parser.add_argument('sourcedir',
                        help=__('path to documentation source files'))
    parser.add_argument('outputdir',
                        help=__('path to output directory'))
    parser.add_argument('filenames', nargs='*',
                        help=__('a list of specific files to rebuild. Ignored '
                                'if -a is specified'))

    group = parser.add_argument_group(__('general options'))
    group.add_argument('-b', metavar='BUILDER', dest='builder',
                       default='html',
                       help=__('builder to use (default: html)'))
    group.add_argument('-a', action='store_true', dest='force_all',
                       help=__('write all files (default: only write new and '
                               'changed files)'))
    group.add_argument('-E', action='store_true', dest='freshenv',
                       help=__('don\'t use a saved environment, always read '
                               'all files'))
    group.add_argument('-d', metavar='PATH', dest='doctreedir',
                       help=__('path for the cached environment and doctree '
                               'files (default: OUTPUTDIR/.doctrees)'))
    group.add_argument('-j', metavar='N', default=1, type=jobs_argument, dest='jobs',
                       help=__('build in parallel with N processes where '
                               'possible (special value "auto" will set N to cpu-count)'))
    group = parser.add_argument_group('build configuration options')
    group.add_argument('-c', metavar='PATH', dest='confdir',
                       help=__('path where configuration file (conf.py) is '
                               'located (default: same as SOURCEDIR)'))
    group.add_argument('-C', action='store_true', dest='noconfig',
                       help=__('use no config file at all, only -D options'))
    group.add_argument('-D', metavar='setting=value', action='append',
                       dest='define', default=[],
                       help=__('override a setting in configuration file'))
    group.add_argument('-A', metavar='name=value', action='append',
                       dest='htmldefine', default=[],
                       help=__('pass a value into HTML templates'))
    group.add_argument('-t', metavar='TAG', action='append',
                       dest='tags', default=[],
                       help=__('define tag: include "only" blocks with TAG'))
    group.add_argument('-n', action='store_true', dest='nitpicky',
                       help=__('nit-picky mode, warn about all missing '
                               'references'))

    group = parser.add_argument_group(__('console output options'))
    group.add_argument('-v', action='count', dest='verbosity', default=0,
                       help=__('increase verbosity (can be repeated)'))
    group.add_argument('-q', action='store_true', dest='quiet',
                       help=__('no output on stdout, just warnings on stderr'))
    group.add_argument('-Q', action='store_true', dest='really_quiet',
                       help=__('no output at all, not even warnings'))
    group.add_argument('--color', action='store_const', const='yes',
                       default='auto',
                       help=__('do emit colored output (default: auto-detect)'))
    group.add_argument('-N', '--no-color', dest='color', action='store_const',
                       const='no',
                       help=__('do not emit colored output (default: '
                               'auto-detect)'))
    group.add_argument('-w', metavar='FILE', dest='warnfile',
                       help=__('write warnings (and errors) to given file'))
    group.add_argument('-W', action='store_true', dest='warningiserror',
                       help=__('turn warnings into errors'))
    group.add_argument('--keep-going', action='store_true', dest='keep_going',
                       help=__("With -W, Keep going when getting warnings"))
    group.add_argument('-T', action='store_true', dest='traceback',
                       help=__('show full traceback on exception'))
    group.add_argument('-P', action='store_true', dest='pdb',
                       help=__('run Pdb on exception'))

    return parser


def make_main(argv=sys.argv[1:]):  # type: ignore
    # type: (List[unicode]) -> int
    """Sphinx build "make mode" entry."""
    from sphinx.cmd import make_mode
    return make_mode.run_make_mode(argv[1:])


def build_main(argv=sys.argv[1:]):  # type: ignore
    # type: (List[unicode]) -> int
    """Sphinx build "main" command-line entry."""

    parser = get_parser()
    args = parser.parse_args(argv)

    if args.noconfig:
        args.confdir = None
    elif not args.confdir:
        args.confdir = args.sourcedir

    if not args.doctreedir:
        args.doctreedir = os.path.join(args.outputdir, '.doctrees')

    # handle remaining filename arguments
    filenames = args.filenames
    missing_files = []
    for filename in filenames:
        if not os.path.isfile(filename):
            missing_files.append(filename)
    if missing_files:
        parser.error(__('cannot find files %r') % missing_files)

    # likely encoding used for command-line arguments
    try:
        locale = __import__('locale')  # due to submodule of the same name
        likely_encoding = locale.getpreferredencoding()
    except Exception:
        likely_encoding = None

    if args.force_all and filenames:
        parser.error(__('cannot combine -a option and filenames'))

    if args.color == 'no' or (args.color == 'auto' and not color_terminal()):
        nocolor()

    status = sys.stdout
    warning = sys.stderr
    error = sys.stderr

    if args.quiet:
        status = None

    if args.really_quiet:
        status = warning = None

    if warning and args.warnfile:
        try:
            warnfp = open(args.warnfile, 'w')
        except Exception as exc:
            parser.error(__('cannot open warning file %r: %s') % (
                args.warnfile, exc))
        warning = Tee(warning, warnfp)  # type: ignore
        error = warning

    confoverrides = {}
    for val in args.define:
        try:
            key, val = val.split('=', 1)
        except ValueError:
            parser.error(__('-D option argument must be in the form name=value'))
        if likely_encoding and isinstance(val, binary_type):
            try:
                val = val.decode(likely_encoding)
            except UnicodeError:
                pass
        confoverrides[key] = val

    for val in args.htmldefine:
        try:
            key, val = val.split('=')
        except ValueError:
            parser.error(__('-A option argument must be in the form name=value'))
        try:
            val = int(val)
        except ValueError:
            if likely_encoding and isinstance(val, binary_type):
                try:
                    val = val.decode(likely_encoding)
                except UnicodeError:
                    pass
        confoverrides['html_context.%s' % key] = val

    if args.nitpicky:
        confoverrides['nitpicky'] = True

    app = None
    try:
        confdir = args.confdir or args.sourcedir
        with patch_docutils(confdir), docutils_namespace():
            app = Sphinx(args.sourcedir, args.confdir, args.outputdir,
                         args.doctreedir, args.builder, confoverrides, status,
                         warning, args.freshenv, args.warningiserror,
                         args.tags, args.verbosity, args.jobs, args.keep_going)
            app.build(args.force_all, filenames)
            return app.statuscode
    except (Exception, KeyboardInterrupt) as exc:
        handle_exception(app, args, exc, error)
        return 2


def main(argv=sys.argv[1:]):  # type: ignore
    # type: (List[unicode]) -> int
    sphinx.locale.setlocale(locale.LC_ALL, '')
    sphinx.locale.init_console(os.path.join(package_dir, 'locale'), 'sphinx')

    if argv[:1] == ['-M']:
        return make_main(argv)
    else:
        return build_main(argv)


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))  # type: ignore
