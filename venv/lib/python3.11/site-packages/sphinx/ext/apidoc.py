"""Creates reST files corresponding to Python modules for code documentation.

Parses a directory tree looking for Python modules and packages and creates
ReST files appropriately to create code documentation with Sphinx.  It also
creates a modules index (named modules.<suffix>).

This is derived from the "sphinx-autopackage" script, which is:
Copyright 2008 Société des arts technologiques (SAT),
https://sat.qc.ca/
"""

from __future__ import annotations

import argparse
import fnmatch
import glob
import locale
import os
import re
import sys
from copy import copy
from importlib.machinery import EXTENSION_SUFFIXES
from os import path
from typing import TYPE_CHECKING, Any

import sphinx.locale
from sphinx import __display_version__, package_dir
from sphinx.cmd.quickstart import EXTENSIONS
from sphinx.locale import __
from sphinx.util import logging
from sphinx.util.osutil import FileAvoidWrite, ensuredir
from sphinx.util.template import ReSTRenderer

if TYPE_CHECKING:
    from collections.abc import Generator, Sequence

logger = logging.getLogger(__name__)

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

PY_SUFFIXES = ('.py', '.pyx') + tuple(EXTENSION_SUFFIXES)

template_dir = path.join(package_dir, 'templates', 'apidoc')


def is_initpy(filename: str) -> bool:
    """Check *filename* is __init__ file or not."""
    basename = path.basename(filename)
    return any(
        basename == '__init__' + suffix
        for suffix in sorted(PY_SUFFIXES, key=len, reverse=True)
    )


def module_join(*modnames: str | None) -> str:
    """Join module names with dots."""
    return '.'.join(filter(None, modnames))


def is_packagedir(dirname: str | None = None, files: list[str] | None = None) -> bool:
    """Check given *files* contains __init__ file."""
    if files is None and dirname is None:
        return False

    if files is None:
        files = os.listdir(dirname)
    return any(f for f in files if is_initpy(f))


def write_file(name: str, text: str, opts: Any) -> None:
    """Write the output file for module/package <name>."""
    quiet = getattr(opts, 'quiet', None)

    fname = path.join(opts.destdir, f'{name}.{opts.suffix}')
    if opts.dryrun:
        if not quiet:
            logger.info(__('Would create file %s.'), fname)
        return
    if not opts.force and path.isfile(fname):
        if not quiet:
            logger.info(__('File %s already exists, skipping.'), fname)
    else:
        if not quiet:
            logger.info(__('Creating file %s.'), fname)
        with FileAvoidWrite(fname) as f:
            f.write(text)


def create_module_file(package: str | None, basename: str, opts: Any,
                       user_template_dir: str | None = None) -> None:
    """Build the text of the file and write the file."""
    options = copy(OPTIONS)
    if opts.includeprivate and 'private-members' not in options:
        options.append('private-members')

    qualname = module_join(package, basename)
    context = {
        'show_headings': not opts.noheadings,
        'basename': basename,
        'qualname': qualname,
        'automodule_options': options,
    }
    if user_template_dir is not None:
        template_path = [user_template_dir, template_dir]
    else:
        template_path = [template_dir]
    text = ReSTRenderer(template_path).render('module.rst_t', context)
    write_file(qualname, text, opts)


def create_package_file(root: str, master_package: str | None, subroot: str,
                        py_files: list[str],
                        opts: Any, subs: list[str], is_namespace: bool,
                        excludes: Sequence[re.Pattern[str]] = (),
                        user_template_dir: str | None = None,
                        ) -> None:
    """Build the text of the file and write the file."""
    # build a list of sub packages (directories containing an __init__ file)
    subpackages = [module_join(master_package, subroot, pkgname)
                   for pkgname in subs
                   if not is_skipped_package(path.join(root, pkgname), opts, excludes)]
    # build a list of sub modules
    submodules = [sub.split('.')[0] for sub in py_files
                  if not is_skipped_module(path.join(root, sub), opts, excludes) and
                  not is_initpy(sub)]
    submodules = sorted(set(submodules))
    submodules = [module_join(master_package, subroot, modname)
                  for modname in submodules]
    options = copy(OPTIONS)
    if opts.includeprivate and 'private-members' not in options:
        options.append('private-members')

    pkgname = module_join(master_package, subroot)
    context = {
        'pkgname': pkgname,
        'subpackages': subpackages,
        'submodules': submodules,
        'is_namespace': is_namespace,
        'modulefirst': opts.modulefirst,
        'separatemodules': opts.separatemodules,
        'automodule_options': options,
        'show_headings': not opts.noheadings,
        'maxdepth': opts.maxdepth,
    }
    if user_template_dir is not None:
        template_path = [user_template_dir, template_dir]
    else:
        template_path = [template_dir]
    text = ReSTRenderer(template_path).render('package.rst_t', context)
    write_file(pkgname, text, opts)

    if submodules and opts.separatemodules:
        for submodule in submodules:
            create_module_file(None, submodule, opts, user_template_dir)


def create_modules_toc_file(modules: list[str], opts: Any, name: str = 'modules',
                            user_template_dir: str | None = None) -> None:
    """Create the module's index."""
    modules.sort()
    prev_module = ''
    for module in modules[:]:
        # look if the module is a subpackage and, if yes, ignore it
        if module.startswith(prev_module + '.'):
            modules.remove(module)
        else:
            prev_module = module

    context = {
        'header': opts.header,
        'maxdepth': opts.maxdepth,
        'docnames': modules,
    }
    if user_template_dir is not None:
        template_path = [user_template_dir, template_dir]
    else:
        template_path = [template_dir]
    text = ReSTRenderer(template_path).render('toc.rst_t', context)
    write_file(name, text, opts)


def is_skipped_package(dirname: str, opts: Any,
                       excludes: Sequence[re.Pattern[str]] = ()) -> bool:
    """Check if we want to skip this module."""
    if not path.isdir(dirname):
        return False

    files = glob.glob(path.join(dirname, '*.py'))
    regular_package = any(f for f in files if is_initpy(f))
    if not regular_package and not opts.implicit_namespaces:
        # *dirname* is not both a regular package and an implicit namespace package
        return True

    # Check there is some showable module inside package
    return all(is_excluded(path.join(dirname, f), excludes) for f in files)


def is_skipped_module(filename: str, opts: Any, _excludes: Sequence[re.Pattern[str]]) -> bool:
    """Check if we want to skip this module."""
    if not path.exists(filename):
        # skip if the file doesn't exist
        return True
    if path.basename(filename).startswith('_') and not opts.includeprivate:
        # skip if the module has a "private" name
        return True
    return False


def walk(rootpath: str, excludes: Sequence[re.Pattern[str]], opts: Any,
         ) -> Generator[tuple[str, list[str], list[str]], None, None]:
    """Walk through the directory and list files and subdirectories up."""
    followlinks = getattr(opts, 'followlinks', False)
    includeprivate = getattr(opts, 'includeprivate', False)

    for root, subs, files in os.walk(rootpath, followlinks=followlinks):
        # document only Python module files (that aren't excluded)
        files = sorted(f for f in files
                       if f.endswith(PY_SUFFIXES) and
                       not is_excluded(path.join(root, f), excludes))

        # remove hidden ('.') and private ('_') directories, as well as
        # excluded dirs
        if includeprivate:
            exclude_prefixes: tuple[str, ...] = ('.',)
        else:
            exclude_prefixes = ('.', '_')

        subs[:] = sorted(sub for sub in subs if not sub.startswith(exclude_prefixes) and
                         not is_excluded(path.join(root, sub), excludes))

        yield root, subs, files


def has_child_module(rootpath: str, excludes: Sequence[re.Pattern[str]], opts: Any) -> bool:
    """Check the given directory contains child module/s (at least one)."""
    return any(
        files
        for _root, _subs, files in walk(rootpath, excludes, opts)
    )


def recurse_tree(rootpath: str, excludes: Sequence[re.Pattern[str]], opts: Any,
                 user_template_dir: str | None = None) -> list[str]:
    """
    Look for every file in the directory tree and create the corresponding
    ReST files.
    """
    implicit_namespaces = getattr(opts, 'implicit_namespaces', False)

    # check if the base directory is a package and get its name
    if is_packagedir(rootpath) or implicit_namespaces:
        root_package = rootpath.split(path.sep)[-1]
    else:
        # otherwise, the base is a directory with packages
        root_package = None

    toplevels = []
    for root, subs, files in walk(rootpath, excludes, opts):
        is_pkg = is_packagedir(None, files)
        is_namespace = not is_pkg and implicit_namespaces
        if is_pkg:
            for f in files[:]:
                if is_initpy(f):
                    files.remove(f)
                    files.insert(0, f)
        elif root != rootpath:
            # only accept non-package at toplevel unless using implicit namespaces
            if not implicit_namespaces:
                del subs[:]
                continue

        if is_pkg or is_namespace:
            # we are in a package with something to document
            if subs or len(files) > 1 or not is_skipped_package(root, opts):
                subpackage = root[len(rootpath):].lstrip(path.sep).\
                    replace(path.sep, '.')
                # if this is not a namespace or
                # a namespace and there is something there to document
                if not is_namespace or has_child_module(root, excludes, opts):
                    create_package_file(root, root_package, subpackage,
                                        files, opts, subs, is_namespace, excludes,
                                        user_template_dir)
                    toplevels.append(module_join(root_package, subpackage))
        else:
            # if we are at the root level, we don't require it to be a package
            assert root == rootpath
            assert root_package is None
            for py_file in files:
                if not is_skipped_module(path.join(rootpath, py_file), opts, excludes):
                    module = py_file.split('.')[0]
                    create_module_file(root_package, module, opts, user_template_dir)
                    toplevels.append(module)

    return toplevels


def is_excluded(root: str, excludes: Sequence[re.Pattern[str]]) -> bool:
    """Check if the directory is in the exclude list.

    Note: by having trailing slashes, we avoid common prefix issues, like
          e.g. an exclude "foo" also accidentally excluding "foobar".
    """
    return any(exclude.match(root) for exclude in excludes)


def get_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        usage='%(prog)s [OPTIONS] -o <OUTPUT_PATH> <MODULE_PATH> '
              '[EXCLUDE_PATTERN, ...]',
        epilog=__('For more information, visit <https://www.sphinx-doc.org/>.'),
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
    parser.add_argument('-q', action='store_true', dest='quiet',
                        help=__('no output on stdout, just warnings on stderr'))
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
    group.add_argument('--extensions', metavar='EXTENSIONS', dest='extensions',
                       action='append', help=__('enable arbitrary extensions'))
    for ext in EXTENSIONS:
        group.add_argument('--ext-%s' % ext, action='append_const',
                           const='sphinx.ext.%s' % ext, dest='extensions',
                           help=__('enable %s extension') % ext)

    group = parser.add_argument_group(__('Project templating'))
    group.add_argument('-t', '--templatedir', metavar='TEMPLATEDIR',
                       dest='templatedir',
                       help=__('template directory for template files'))

    return parser


def main(argv: Sequence[str] = (), /) -> int:
    """Parse and check the command line arguments."""
    locale.setlocale(locale.LC_ALL, '')
    sphinx.locale.init_console()

    parser = get_parser()
    args = parser.parse_args(argv or sys.argv[1:])

    rootpath = path.abspath(args.module_path)

    # normalize opts

    if args.header is None:
        args.header = rootpath.split(path.sep)[-1]
    if args.suffix.startswith('.'):
        args.suffix = args.suffix[1:]
    if not path.isdir(rootpath):
        logger.error(__('%s is not a directory.'), rootpath)
        raise SystemExit(1)
    if not args.dryrun:
        ensuredir(args.destdir)
    excludes = tuple(
        re.compile(fnmatch.translate(path.abspath(exclude)))
        for exclude in dict.fromkeys(args.exclude_pattern)
    )
    modules = recurse_tree(rootpath, excludes, args, args.templatedir)

    if args.full:
        from sphinx.cmd import quickstart as qs
        modules.sort()
        prev_module = ''
        text = ''
        for module in modules:
            if module.startswith(prev_module + '.'):
                continue
            prev_module = module
            text += '   %s\n' % module
        d = {
            'path': args.destdir,
            'sep': False,
            'dot': '_',
            'project': args.header,
            'author': args.author or 'Author',
            'version': args.version or '',
            'release': args.release or args.version or '',
            'suffix': '.' + args.suffix,
            'master': 'index',
            'epub': True,
            'extensions': ['sphinx.ext.autodoc', 'sphinx.ext.viewcode',
                           'sphinx.ext.todo'],
            'makefile': True,
            'batchfile': True,
            'make_mode': True,
            'mastertocmaxdepth': args.maxdepth,
            'mastertoctree': text,
            'language': 'en',
            'module_path': rootpath,
            'append_syspath': args.append_syspath,
        }
        if args.extensions:
            d['extensions'].extend(args.extensions)
        if args.quiet:
            d['quiet'] = True

        for ext in d['extensions'][:]:
            if ',' in ext:
                d['extensions'].remove(ext)
                d['extensions'].extend(ext.split(','))

        if not args.dryrun:
            qs.generate(d, silent=True, overwrite=args.force,
                        templatedir=args.templatedir)
    elif args.tocfile:
        create_modules_toc_file(modules, args, args.tocfile, args.templatedir)

    return 0


# So program can be started with "python -m sphinx.apidoc ..."
if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
