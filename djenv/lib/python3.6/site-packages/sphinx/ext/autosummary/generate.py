# -*- coding: utf-8 -*-
"""
    sphinx.ext.autosummary.generate
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    Usable as a library or script to generate automatic RST source files for
    items referred to in autosummary:: directives.

    Each generated RST file contains a single auto*:: directive which
    extracts the docstring of the referred item.

    Example Makefile rule::

       generate:
               sphinx-autogen -o source/generated source/*.rst

    :copyright: Copyright 2007-2019 by the Sphinx team, see AUTHORS.
    :license: BSD, see LICENSE for details.
"""
from __future__ import print_function

import argparse
import codecs
import locale
import os
import pydoc
import re
import sys

from jinja2 import FileSystemLoader, TemplateNotFound
from jinja2.sandbox import SandboxedEnvironment

import sphinx.locale
from sphinx import __display_version__
from sphinx import package_dir
from sphinx.ext.autosummary import import_by_name, get_documenter
from sphinx.jinja2glue import BuiltinTemplateLoader
from sphinx.locale import __
from sphinx.registry import SphinxComponentRegistry
from sphinx.util.inspect import safe_getattr
from sphinx.util.osutil import ensuredir
from sphinx.util.rst import escape as rst_escape

if False:
    # For type annotation
    from typing import Any, Callable, Dict, List, Tuple, Type  # NOQA
    from jinja2 import BaseLoader  # NOQA
    from sphinx import addnodes  # NOQA
    from sphinx.builders import Builder  # NOQA
    from sphinx.environment import BuildEnvironment  # NOQA
    from sphinx.ext.autodoc import Documenter  # NOQA


class DummyApplication(object):
    """Dummy Application class for sphinx-autogen command."""

    def __init__(self):
        # type: () -> None
        self.registry = SphinxComponentRegistry()


def setup_documenters(app):
    # type: (Any) -> None
    from sphinx.ext.autodoc import (
        ModuleDocumenter, ClassDocumenter, ExceptionDocumenter, DataDocumenter,
        FunctionDocumenter, MethodDocumenter, AttributeDocumenter,
        InstanceAttributeDocumenter
    )
    documenters = [
        ModuleDocumenter, ClassDocumenter, ExceptionDocumenter, DataDocumenter,
        FunctionDocumenter, MethodDocumenter, AttributeDocumenter,
        InstanceAttributeDocumenter
    ]  # type: List[Type[Documenter]]
    for documenter in documenters:
        app.registry.add_documenter(documenter.objtype, documenter)


def _simple_info(msg):
    # type: (unicode) -> None
    print(msg)


def _simple_warn(msg):
    # type: (unicode) -> None
    print('WARNING: ' + msg, file=sys.stderr)


def _underline(title, line='='):
    # type: (unicode, unicode) -> unicode
    if '\n' in title:
        raise ValueError('Can only underline single lines')
    return title + '\n' + line * len(title)


# -- Generating output ---------------------------------------------------------

def generate_autosummary_docs(sources, output_dir=None, suffix='.rst',
                              warn=_simple_warn, info=_simple_info,
                              base_path=None, builder=None, template_dir=None,
                              imported_members=False, app=None):
    # type: (List[unicode], unicode, unicode, Callable, Callable, unicode, Builder, unicode, bool, Any) -> None  # NOQA

    showed_sources = list(sorted(sources))
    if len(showed_sources) > 20:
        showed_sources = showed_sources[:10] + ['...'] + showed_sources[-10:]
    info(__('[autosummary] generating autosummary for: %s') %
         ', '.join(showed_sources))

    if output_dir:
        info(__('[autosummary] writing to %s') % output_dir)

    if base_path is not None:
        sources = [os.path.join(base_path, filename) for filename in sources]

    # create our own templating environment
    template_dirs = None  # type: List[unicode]
    template_dirs = [os.path.join(package_dir, 'ext',
                                  'autosummary', 'templates')]

    template_loader = None  # type: BaseLoader
    if builder is not None:
        # allow the user to override the templates
        template_loader = BuiltinTemplateLoader()
        template_loader.init(builder, dirs=template_dirs)
    else:
        if template_dir:
            template_dirs.insert(0, template_dir)
        template_loader = FileSystemLoader(template_dirs)
    template_env = SandboxedEnvironment(loader=template_loader)
    template_env.filters['underline'] = _underline

    # replace the builtin html filters
    template_env.filters['escape'] = rst_escape
    template_env.filters['e'] = rst_escape

    # read
    items = find_autosummary_in_files(sources)

    # keep track of new files
    new_files = []

    # write
    for name, path, template_name in sorted(set(items), key=str):
        if path is None:
            # The corresponding autosummary:: directive did not have
            # a :toctree: option
            continue

        path = output_dir or os.path.abspath(path)
        ensuredir(path)

        try:
            name, obj, parent, mod_name = import_by_name(name)
        except ImportError as e:
            warn('[autosummary] failed to import %r: %s' % (name, e))
            continue

        fn = os.path.join(path, name + suffix)

        # skip it if it exists
        if os.path.isfile(fn):
            continue

        new_files.append(fn)

        with open(fn, 'w') as f:
            doc = get_documenter(app, obj, parent)

            if template_name is not None:
                template = template_env.get_template(template_name)
            else:
                try:
                    template = template_env.get_template('autosummary/%s.rst'
                                                         % doc.objtype)
                except TemplateNotFound:
                    template = template_env.get_template('autosummary/base.rst')

            def get_members(obj, typ, include_public=[], imported=True):
                # type: (Any, unicode, List[unicode], bool) -> Tuple[List[unicode], List[unicode]]  # NOQA
                items = []  # type: List[unicode]
                for name in dir(obj):
                    try:
                        value = safe_getattr(obj, name)
                    except AttributeError:
                        continue
                    documenter = get_documenter(app, value, obj)
                    if documenter.objtype == typ:
                        if imported or getattr(value, '__module__', None) == obj.__name__:
                            # skip imported members if expected
                            items.append(name)
                public = [x for x in items
                          if x in include_public or not x.startswith('_')]
                return public, items

            ns = {}  # type: Dict[unicode, Any]

            if doc.objtype == 'module':
                ns['members'] = dir(obj)
                ns['functions'], ns['all_functions'] = \
                    get_members(obj, 'function', imported=imported_members)
                ns['classes'], ns['all_classes'] = \
                    get_members(obj, 'class', imported=imported_members)
                ns['exceptions'], ns['all_exceptions'] = \
                    get_members(obj, 'exception', imported=imported_members)
            elif doc.objtype == 'class':
                ns['members'] = dir(obj)
                ns['inherited_members'] = \
                    set(dir(obj)) - set(obj.__dict__.keys())
                ns['methods'], ns['all_methods'] = \
                    get_members(obj, 'method', ['__init__'])
                ns['attributes'], ns['all_attributes'] = \
                    get_members(obj, 'attribute')

            parts = name.split('.')
            if doc.objtype in ('method', 'attribute'):
                mod_name = '.'.join(parts[:-2])
                cls_name = parts[-2]
                obj_name = '.'.join(parts[-2:])
                ns['class'] = cls_name
            else:
                mod_name, obj_name = '.'.join(parts[:-1]), parts[-1]

            ns['fullname'] = name
            ns['module'] = mod_name
            ns['objname'] = obj_name
            ns['name'] = parts[-1]

            ns['objtype'] = doc.objtype
            ns['underline'] = len(name) * '='

            rendered = template.render(**ns)
            f.write(rendered)  # type: ignore

    # descend recursively to new files
    if new_files:
        generate_autosummary_docs(new_files, output_dir=output_dir,
                                  suffix=suffix, warn=warn, info=info,
                                  base_path=base_path, builder=builder,
                                  template_dir=template_dir, app=app)


# -- Finding documented entries in files ---------------------------------------

def find_autosummary_in_files(filenames):
    # type: (List[unicode]) -> List[Tuple[unicode, unicode, unicode]]
    """Find out what items are documented in source/*.rst.

    See `find_autosummary_in_lines`.
    """
    documented = []  # type: List[Tuple[unicode, unicode, unicode]]
    for filename in filenames:
        with codecs.open(filename, 'r', encoding='utf-8',  # type: ignore
                         errors='ignore') as f:
            lines = f.read().splitlines()
            documented.extend(find_autosummary_in_lines(lines, filename=filename))
    return documented


def find_autosummary_in_docstring(name, module=None, filename=None):
    # type: (unicode, Any, unicode) -> List[Tuple[unicode, unicode, unicode]]
    """Find out what items are documented in the given object's docstring.

    See `find_autosummary_in_lines`.
    """
    try:
        real_name, obj, parent, modname = import_by_name(name)
        lines = pydoc.getdoc(obj).splitlines()
        return find_autosummary_in_lines(lines, module=name, filename=filename)  # type: ignore
    except AttributeError:
        pass
    except ImportError as e:
        print("Failed to import '%s': %s" % (name, e))
    except SystemExit:
        print("Failed to import '%s'; the module executes module level "
              "statement and it might call sys.exit()." % name)
    return []


def find_autosummary_in_lines(lines, module=None, filename=None):
    # type: (List[unicode], Any, unicode) -> List[Tuple[unicode, unicode, unicode]]
    """Find out what items appear in autosummary:: directives in the
    given lines.

    Returns a list of (name, toctree, template) where *name* is a name
    of an object and *toctree* the :toctree: path of the corresponding
    autosummary directive (relative to the root of the file name), and
    *template* the value of the :template: option. *toctree* and
    *template* ``None`` if the directive does not have the
    corresponding options set.
    """
    autosummary_re = re.compile(r'^(\s*)\.\.\s+autosummary::\s*')
    automodule_re = re.compile(
        r'^\s*\.\.\s+automodule::\s*([A-Za-z0-9_.]+)\s*$')
    module_re = re.compile(
        r'^\s*\.\.\s+(current)?module::\s*([a-zA-Z0-9_.]+)\s*$')
    autosummary_item_re = re.compile(r'^\s+(~?[_a-zA-Z][a-zA-Z0-9_.]*)\s*.*?')
    toctree_arg_re = re.compile(r'^\s+:toctree:\s*(.*?)\s*$')
    template_arg_re = re.compile(r'^\s+:template:\s*(.*?)\s*$')

    documented = []  # type: List[Tuple[unicode, unicode, unicode]]

    toctree = None  # type: unicode
    template = None
    current_module = module
    in_autosummary = False
    base_indent = ""  # type: unicode

    for line in lines:
        if in_autosummary:
            m = toctree_arg_re.match(line)
            if m:
                toctree = m.group(1)
                if filename:
                    toctree = os.path.join(os.path.dirname(filename),
                                           toctree)
                continue

            m = template_arg_re.match(line)
            if m:
                template = m.group(1).strip()
                continue

            if line.strip().startswith(':'):
                continue  # skip options

            m = autosummary_item_re.match(line)
            if m:
                name = m.group(1).strip()
                if name.startswith('~'):
                    name = name[1:]
                if current_module and \
                   not name.startswith(current_module + '.'):
                    name = "%s.%s" % (current_module, name)
                documented.append((name, toctree, template))
                continue

            if not line.strip() or line.startswith(base_indent + " "):
                continue

            in_autosummary = False

        m = autosummary_re.match(line)
        if m:
            in_autosummary = True
            base_indent = m.group(1)
            toctree = None
            template = None
            continue

        m = automodule_re.search(line)
        if m:
            current_module = m.group(1).strip()
            # recurse into the automodule docstring
            documented.extend(find_autosummary_in_docstring(
                current_module, filename=filename))
            continue

        m = module_re.match(line)
        if m:
            current_module = m.group(2)
            continue

    return documented


def get_parser():
    # type: () -> argparse.ArgumentParser
    parser = argparse.ArgumentParser(
        usage='%(prog)s [OPTIONS] <SOURCE_FILE>...',
        epilog=__('For more information, visit <http://sphinx-doc.org/>.'),
        description=__("""
Generate ReStructuredText using autosummary directives.

sphinx-autogen is a frontend to sphinx.ext.autosummary.generate. It generates
the reStructuredText files from the autosummary directives contained in the
given input files.

The format of the autosummary directive is documented in the
``sphinx.ext.autosummary`` Python module and can be read using::

  pydoc sphinx.ext.autosummary
"""))

    parser.add_argument('--version', action='version', dest='show_version',
                        version='%%(prog)s %s' % __display_version__)

    parser.add_argument('source_file', nargs='+',
                        help=__('source files to generate rST files for'))

    parser.add_argument('-o', '--output-dir', action='store',
                        dest='output_dir',
                        help=__('directory to place all output in'))
    parser.add_argument('-s', '--suffix', action='store', dest='suffix',
                        default='rst',
                        help=__('default suffix for files (default: '
                                '%(default)s)'))
    parser.add_argument('-t', '--templates', action='store', dest='templates',
                        default=None,
                        help=__('custom template directory (default: '
                                '%(default)s)'))
    parser.add_argument('-i', '--imported-members', action='store_true',
                        dest='imported_members', default=False,
                        help=__('document imported members (default: '
                                '%(default)s)'))

    return parser


def main(argv=sys.argv[1:]):
    # type: (List[str]) -> None
    sphinx.locale.setlocale(locale.LC_ALL, '')
    sphinx.locale.init_console(os.path.join(package_dir, 'locale'), 'sphinx')

    app = DummyApplication()
    setup_documenters(app)
    args = get_parser().parse_args(argv)
    generate_autosummary_docs(args.source_file, args.output_dir,
                              '.' + args.suffix,
                              template_dir=args.templates,
                              imported_members=args.imported_members,
                              app=app)


if __name__ == '__main__':
    main()
