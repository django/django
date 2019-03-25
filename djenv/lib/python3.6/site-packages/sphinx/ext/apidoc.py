# -*- coding: utf-8 -*-
"""
    sphinx.ext.apidoc
    ~~~~~~~~~~~~~~~~~

    Parses a directory tree looking for Python modules and packages and creates
    ReST files appropriately to create code documentation with Sphinx.  It also
    creates a modules index (named modules.<suffix>).

    This is derived from the "sphinx-autopackage" script, which is:
    Copyright 2008 Société des arts technologiques (SAT),
    https://sat.qc.ca/

    :copyright: Copyright 2007-2019 by the Sphinx team, see AUTHORS.
    :license: BSD, see LICENSE for details.
"""

from __future__ import print_function

import argparse
import glob
import locale
import os
import sys
from fnmatch import fnmatch
from os import path

from six import binary_type

import sphinx.locale
from sphinx import __display_version__, package_dir
from sphinx.cmd.quickstart import EXTENSIONS
from sphinx.locale import __
from sphinx.util import rst
from sphinx.util.osutil import FileAvoidWrite, ensuredir, walk

if False:
    # For type annotation
    from typing import Any, List, Tuple  # NOQA

# automodule options
if 'SPHINX_APIDOC_OPTIONS' in os.environ:
    OPTIONS = os.environ['SPHINX_APIDOC_OPTIONS'].split(',')
else:
    OPTIONS = [
        'members',
        'undoc-members',
        # 'inherited-members', # disabled because there's a bug in sphinx
        'show-inheritance',
    ]

INITPY = '__init__.py'
PY_SUFFIXES = set(['.py', '.pyx'])


def makename(package, module):
    # type: (unicode, unicode) -> unicode
    """Join package and module with a dot."""
    # Both package and module can be None/empty.
    if package:
        name = package
        if module:
            name += '.' + module
    else:
        name = module
    return name


def write_file(name, text, opts):
    # type: (unicode, unicode, Any) -> None
    """Write the output file for module/package <name>."""
    fname = path.join(opts.destdir, '%s.%s' % (name, opts.suffix))
    if opts.dryrun:
        print(__('Would create file %s.') % fname)
        return
    if not opts.force and path.isfile(fname):
        print(__('File %s already exists, skipping.') % fname)
    else:
        print(__('Creating file %s.') % fname)
        with FileAvoidWrite(fname) as f:
            f.write(text)


def format_heading(level, text, escape=True):
    # type: (int, unicode, bool) -> unicode
    """Create a heading of <level> [1, 2 or 3 supported]."""
    if escape:
        text = rst.escape(text)
    underlining = ['=', '-', '~', ][level - 1] * len(text)
    return '%s\n%s\n\n' % (text, underlining)


def format_directive(module, package=None):
    # type: (unicode, unicode) -> unicode
    """Create the automodule directive and add the options."""
    directive = '.. automodule:: %s\n' % makename(package, module)
    for option in OPTIONS:
        directive += '    :%s:\n' % option
    return directive


def create_module_file(package, module, opts):
    # type: (unicode, unicode, Any) -> None
    """Build the text of the file and write the file."""
    if not opts.noheadings:
        text = format_heading(1, '%s module' % module)
    else:
        text = ''
    # text += format_heading(2, ':mod:`%s` Module' % module)
    text += format_directive(module, package)
    write_file(makename(package, module), text, opts)


def create_package_file(root, master_package, subroot, py_files, opts, subs, is_namespace, excludes=[]):  # NOQA
    # type: (unicode, unicode, unicode, List[unicode], Any, List[unicode], bool, List[unicode]) -> None  # NOQA
    """Build the text of the file and write the file."""
    text = format_heading(1, ('%s package' if not is_namespace else "%s namespace")
                          % makename(master_package, subroot))

    if opts.modulefirst and not is_namespace:
        text += format_directive(subroot, master_package)
        text += '\n'

    # build a list of directories that are szvpackages (contain an INITPY file)
    # and also checks the INITPY file is not empty, or there are other python
    # source files in that folder.
    # (depending on settings - but shall_skip() takes care of that)
    subs = [sub for sub in subs if not
            shall_skip(path.join(root, sub, INITPY), opts, excludes)]
    # if there are some package directories, add a TOC for theses subpackages
    if subs:
        text += format_heading(2, 'Subpackages')
        text += '.. toctree::\n\n'
        for sub in subs:
            text += '    %s.%s\n' % (makename(master_package, subroot), sub)
        text += '\n'

    submods = [path.splitext(sub)[0] for sub in py_files
               if not shall_skip(path.join(root, sub), opts, excludes) and
               sub != INITPY]
    if submods:
        text += format_heading(2, 'Submodules')
        if opts.separatemodules:
            text += '.. toctree::\n\n'
            for submod in submods:
                modfile = makename(master_package, makename(subroot, submod))
                text += '   %s\n' % modfile

                # generate separate file for this module
                if not opts.noheadings:
                    filetext = format_heading(1, '%s module' % modfile)
                else:
                    filetext = ''
                filetext += format_directive(makename(subroot, submod),
                                             master_package)
                write_file(modfile, filetext, opts)
        else:
            for submod in submods:
                modfile = makename(master_package, makename(subroot, submod))
                if not opts.noheadings:
                    text += format_heading(2, '%s module' % modfile)
                text += format_directive(makename(subroot, submod),
                                         master_package)
                text += '\n'
        text += '\n'

    if not opts.modulefirst and not is_namespace:
        text += format_heading(2, 'Module contents')
        text += format_directive(subroot, master_package)

    write_file(makename(master_package, subroot), text, opts)


def create_modules_toc_file(modules, opts, name='modules'):
    # type: (List[unicode], Any, unicode) -> None
    """Create the module's index."""
    text = format_heading(1, '%s' % opts.header, escape=False)
    text += '.. toctree::\n'
    text += '   :maxdepth: %s\n\n' % opts.maxdepth

    modules.sort()
    prev_module = ''  # type: unicode
    for module in modules:
        # look if the module is a subpackage and, if yes, ignore it
        if module.startswith(prev_module + '.'):
            continue
        prev_module = module
        text += '   %s\n' % module

    write_file(name, text, opts)


def shall_skip(module, opts, excludes=[]):
    # type: (unicode, Any, List[unicode]) -> bool
    """Check if we want to skip this module."""
    # skip if the file doesn't exist and not using implicit namespaces
    if not opts.implicit_namespaces and not path.exists(module):
        return True

    # Are we a package (here defined as __init__.py, not the folder in itself)
    if os.path.basename(module) == INITPY:
        # Yes, check if we have any non-excluded modules at all here
        all_skipped = True
        basemodule = path.dirname(module)
        for submodule in glob.glob(path.join(basemodule, '*.py')):
            if not is_excluded(path.join(basemodule, submodule), excludes):
                # There's a non-excluded module here, we won't skip
                all_skipped = False
        if all_skipped:
            return True

    # skip if it has a "private" name and this is selected
    filename = path.basename(module)
    if filename != '__init__.py' and filename.startswith('_') and \
       not opts.includeprivate:
        return True
    return False


def recurse_tree(rootpath, excludes, opts):
    # type: (unicode, List[unicode], Any) -> List[unicode]
    """
    Look for every file in the directory tree and create the corresponding
    ReST files.
    """
    followlinks = getattr(opts, 'followlinks', False)
    includeprivate = getattr(opts, 'includeprivate', False)
    implicit_namespaces = getattr(opts, 'implicit_namespaces', False)

    # check if the base directory is a package and get its name
    if INITPY in os.listdir(rootpath) or implicit_namespaces:
        root_package = rootpath.split(path.sep)[-1]
    else:
        # otherwise, the base is a directory with packages
        root_package = None

    toplevels = []
    for root, subs, files in walk(rootpath, followlinks=followlinks):
        # document only Python module files (that aren't excluded)
        py_files = sorted(f for f in files
                          if path.splitext(f)[1] in PY_SUFFIXES and
                          not is_excluded(path.join(root, f), excludes))
        is_pkg = INITPY in py_files
        is_namespace = INITPY not in py_files and implicit_namespaces
        if is_pkg:
            py_files.remove(INITPY)
            py_files.insert(0, INITPY)
        elif root != rootpath:
            # only accept non-package at toplevel unless using implicit namespaces
            if not implicit_namespaces:
                del subs[:]
                continue
        # remove hidden ('.') and private ('_') directories, as well as
        # excluded dirs
        if includeprivate:
            exclude_prefixes = ('.',)  # type: Tuple[unicode, ...]
        else:
            exclude_prefixes = ('.', '_')
        subs[:] = sorted(sub for sub in subs if not sub.startswith(exclude_prefixes) and
                         not is_excluded(path.join(root, sub), excludes))

        if is_pkg or is_namespace:
            # we are in a package with something to document
            if subs or len(py_files) > 1 or not shall_skip(path.join(root, INITPY), opts):
                subpackage = root[len(rootpath):].lstrip(path.sep).\
                    replace(path.sep, '.')
                # if this is not a namespace or
                # a namespace and there is something there to document
                if not is_namespace or len(py_files) > 0:
                    create_package_file(root, root_package, subpackage,
                                        py_files, opts, subs, is_namespace, excludes)
                    toplevels.append(makename(root_package, subpackage))
        else:
            # if we are at the root level, we don't require it to be a package
            assert root == rootpath and root_package is None
            for py_file in py_files:
                if not shall_skip(path.join(rootpath, py_file), opts):
                    module = path.splitext(py_file)[0]
                    create_module_file(root_package, module, opts)
                    toplevels.append(module)

    return toplevels


def is_excluded(root, excludes):
    # type: (unicode, List[unicode]) -> bool
    """Check if the directory is in the exclude list.

    Note: by having trailing slashes, we avoid common prefix issues, like
          e.g. an exclude "foo" also accidentally excluding "foobar".
    """
    for exclude in excludes:
        if fnmatch(root, exclude):
            return True
    return False


def get_parser():
    # type: () -> argparse.ArgumentParser
    parser = argparse.ArgumentParser(
        usage='%(prog)s [OPTIONS] -o <OUTPUT_PATH> <MODULE_PATH> '
              '[EXCLUDE_PATTERN, ...]',
        epilog=__('For more information, visit <http://sphinx-doc.org/>.'),
        description=__("""
Look recursively in <MODULE_PATH> for Python modules and packages and create
one reST file with automodule directives per package in the <OUTPUT_PATH>.

The <EXCLUDE_PATTERN>s can be file and/or directory patterns that will be
excluded from generation.

Note: By default this script will not overwrite already created files."""))

    parser.add_argument('--version', action='version', dest='show_version',
                        version='%%(prog)s %s' % __display_version__)

    parser.add_argument('module_path',
                        help=__('path to module to document'))
    parser.add_argument('exclude_pattern', nargs='*',
                        help=__('fnmatch-style file and/or directory patterns '
                                'to exclude from generation'))

    parser.add_argument('-o', '--output-dir', action='store', dest='destdir',
                        required=True,
                        help=__('directory to place all output'))
    parser.add_argument('-d', '--maxdepth', action='store', dest='maxdepth',
                        type=int, default=4,
                        help=__('maximum depth of submodules to show in the TOC '
                                '(default: 4)'))
    parser.add_argument('-f', '--force', action='store_true', dest='force',
                        help=__('overwrite existing files'))
    parser.add_argument('-l', '--follow-links', action='store_true',
                        dest='followlinks', default=False,
                        help=__('follow symbolic links. Powerful when combined '
                                'with collective.recipe.omelette.'))
    parser.add_argument('-n', '--dry-run', action='store_true', dest='dryrun',
                        help=__('run the script without creating files'))
    parser.add_argument('-e', '--separate', action='store_true',
                        dest='separatemodules',
                        help=__('put documentation for each module on its own page'))
    parser.add_argument('-P', '--private', action='store_true',
                        dest='includeprivate',
                        help=__('include "_private" modules'))
    parser.add_argument('--tocfile', action='store', dest='tocfile', default='modules',
                        help=__("filename of table of contents (default: modules)"))
    parser.add_argument('-T', '--no-toc', action='store_false', dest='tocfile',
                        help=__("don't create a table of contents file"))
    parser.add_argument('-E', '--no-headings', action='store_true',
                        dest='noheadings',
                        help=__("don't create headings for the module/package "
                                "packages (e.g. when the docstrings already "
                                "contain them)"))
    parser.add_argument('-M', '--module-first', action='store_true',
                        dest='modulefirst',
                        help=__('put module documentation before submodule '
                                'documentation'))
    parser.add_argument('--implicit-namespaces', action='store_true',
                        dest='implicit_namespaces',
                        help=__('interpret module paths according to PEP-0420 '
                                'implicit namespaces specification'))
    parser.add_argument('-s', '--suffix', action='store', dest='suffix',
                        default='rst',
                        help=__('file suffix (default: rst)'))
    parser.add_argument('-F', '--full', action='store_true', dest='full',
                        help=__('generate a full project with sphinx-quickstart'))
    parser.add_argument('-a', '--append-syspath', action='store_true',
                        dest='append_syspath',
                        help=__('append module_path to sys.path, used when --full is given'))
    parser.add_argument('-H', '--doc-project', action='store', dest='header',
                        help=__('project name (default: root module name)'))
    parser.add_argument('-A', '--doc-author', action='store', dest='author',
                        help=__('project author(s), used when --full is given'))
    parser.add_argument('-V', '--doc-version', action='store', dest='version',
                        help=__('project version, used when --full is given'))
    parser.add_argument('-R', '--doc-release', action='store', dest='release',
                        help=__('project release, used when --full is given, '
                                'defaults to --doc-version'))

    group = parser.add_argument_group(__('extension options'))
    for ext in EXTENSIONS:
        group.add_argument('--ext-%s' % ext, action='append_const',
                           const='sphinx.ext.%s' % ext, dest='extensions',
                           help=__('enable %s extension') % ext)

    return parser


def main(argv=sys.argv[1:]):
    # type: (List[str]) -> int
    """Parse and check the command line arguments."""
    sphinx.locale.setlocale(locale.LC_ALL, '')
    sphinx.locale.init_console(os.path.join(package_dir, 'locale'), 'sphinx')

    parser = get_parser()
    args = parser.parse_args(argv)

    rootpath = path.abspath(args.module_path)

    # normalize opts

    if args.header is None:
        args.header = rootpath.split(path.sep)[-1]
    if args.suffix.startswith('.'):
        args.suffix = args.suffix[1:]
    if not path.isdir(rootpath):
        print(__('%s is not a directory.') % rootpath, file=sys.stderr)
        sys.exit(1)
    if not args.dryrun:
        ensuredir(args.destdir)
    excludes = [path.abspath(exclude) for exclude in args.exclude_pattern]
    modules = recurse_tree(rootpath, excludes, args)

    if args.full:
        from sphinx.cmd import quickstart as qs
        modules.sort()
        prev_module = ''  # type: unicode
        text = ''
        for module in modules:
            if module.startswith(prev_module + '.'):
                continue
            prev_module = module
            text += '   %s\n' % module
        d = dict(
            path = args.destdir,
            sep = False,
            dot = '_',
            project = args.header,
            author = args.author or 'Author',
            version = args.version or '',
            release = args.release or args.version or '',
            suffix = '.' + args.suffix,
            master = 'index',
            epub = True,
            extensions = ['sphinx.ext.autodoc', 'sphinx.ext.viewcode',
                          'sphinx.ext.todo'],
            makefile = True,
            batchfile = True,
            make_mode = True,
            mastertocmaxdepth = args.maxdepth,
            mastertoctree = text,
            language = 'en',
            module_path = rootpath,
            append_syspath = args.append_syspath,
        )
        if args.extensions:
            d['extensions'].extend(args.extensions)

        if isinstance(args.header, binary_type):
            d['project'] = d['project'].decode('utf-8')
        if isinstance(args.author, binary_type):
            d['author'] = d['author'].decode('utf-8')
        if isinstance(args.version, binary_type):
            d['version'] = d['version'].decode('utf-8')
        if isinstance(args.release, binary_type):
            d['release'] = d['release'].decode('utf-8')

        if not args.dryrun:
            qs.generate(d, silent=True, overwrite=args.force)
    elif args.tocfile:
        create_modules_toc_file(modules, args, args.tocfile)

    return 0


# So program can be started with "python -m sphinx.apidoc ..."
if __name__ == "__main__":
    main()
