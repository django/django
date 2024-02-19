"""Generates reST source files for autosummary.

Usable as a library or script to generate automatic RST source files for
items referred to in autosummary:: directives.

Each generated RST file contains a single auto*:: directive which
extracts the docstring of the referred item.

Example Makefile rule::

   generate:
           sphinx-autogen -o source/generated source/*.rst
"""

from __future__ import annotations

import argparse
import importlib
import inspect
import locale
import os
import pkgutil
import pydoc
import re
import sys
from os import path
from typing import TYPE_CHECKING, Any, NamedTuple

from jinja2 import TemplateNotFound
from jinja2.sandbox import SandboxedEnvironment

import sphinx.locale
from sphinx import __display_version__, package_dir
from sphinx.builders import Builder
from sphinx.config import Config
from sphinx.ext.autodoc.importer import import_module
from sphinx.ext.autosummary import (
    ImportExceptionGroup,
    get_documenter,
    import_by_name,
    import_ivar_by_name,
)
from sphinx.locale import __
from sphinx.pycode import ModuleAnalyzer, PycodeError
from sphinx.registry import SphinxComponentRegistry
from sphinx.util import logging, rst
from sphinx.util.inspect import getall, safe_getattr
from sphinx.util.osutil import ensuredir
from sphinx.util.template import SphinxTemplateLoader

if TYPE_CHECKING:
    from collections.abc import Sequence, Set
    from gettext import NullTranslations

    from sphinx.application import Sphinx
    from sphinx.ext.autodoc import Documenter

logger = logging.getLogger(__name__)


class DummyApplication:
    """Dummy Application class for sphinx-autogen command."""

    def __init__(self, translator: NullTranslations) -> None:
        self.config = Config()
        self.registry = SphinxComponentRegistry()
        self.messagelog: list[str] = []
        self.srcdir = "/"
        self.translator = translator
        self.verbosity = 0
        self._warncount = 0
        self.warningiserror = False

        self.config.add('autosummary_context', {}, True, None)
        self.config.add('autosummary_filename_map', {}, True, None)
        self.config.add('autosummary_ignore_module_all', True, 'env', bool)
        self.config.init_values()

    def emit_firstresult(self, *args: Any) -> None:
        pass


class AutosummaryEntry(NamedTuple):
    name: str
    path: str | None
    template: str
    recursive: bool


def setup_documenters(app: Any) -> None:
    from sphinx.ext.autodoc import (
        AttributeDocumenter,
        ClassDocumenter,
        DataDocumenter,
        DecoratorDocumenter,
        ExceptionDocumenter,
        FunctionDocumenter,
        MethodDocumenter,
        ModuleDocumenter,
        PropertyDocumenter,
    )
    documenters: list[type[Documenter]] = [
        ModuleDocumenter, ClassDocumenter, ExceptionDocumenter, DataDocumenter,
        FunctionDocumenter, MethodDocumenter,
        AttributeDocumenter, DecoratorDocumenter, PropertyDocumenter,
    ]
    for documenter in documenters:
        app.registry.add_documenter(documenter.objtype, documenter)


def _underline(title: str, line: str = '=') -> str:
    if '\n' in title:
        msg = 'Can only underline single lines'
        raise ValueError(msg)
    return title + '\n' + line * len(title)


class AutosummaryRenderer:
    """A helper class for rendering."""

    def __init__(self, app: Sphinx) -> None:
        if isinstance(app, Builder):
            msg = 'Expected a Sphinx application object!'
            raise ValueError(msg)

        system_templates_path = [os.path.join(package_dir, 'ext', 'autosummary', 'templates')]
        loader = SphinxTemplateLoader(app.srcdir, app.config.templates_path,
                                      system_templates_path)

        self.env = SandboxedEnvironment(loader=loader)
        self.env.filters['escape'] = rst.escape
        self.env.filters['e'] = rst.escape
        self.env.filters['underline'] = _underline

        if app.translator:
            self.env.add_extension("jinja2.ext.i18n")
            self.env.install_gettext_translations(app.translator)

    def render(self, template_name: str, context: dict) -> str:
        """Render a template file."""
        try:
            template = self.env.get_template(template_name)
        except TemplateNotFound:
            try:
                # objtype is given as template_name
                template = self.env.get_template('autosummary/%s.rst' % template_name)
            except TemplateNotFound:
                # fallback to base.rst
                template = self.env.get_template('autosummary/base.rst')

        return template.render(context)


def _split_full_qualified_name(name: str) -> tuple[str | None, str]:
    """Split full qualified name to a pair of modname and qualname.

    A qualname is an abbreviation for "Qualified name" introduced at PEP-3155
    (https://peps.python.org/pep-3155/).  It is a dotted path name
    from the module top-level.

    A "full" qualified name means a string containing both module name and
    qualified name.

    .. note:: This function actually imports the module to check its existence.
              Therefore you need to mock 3rd party modules if needed before
              calling this function.
    """
    parts = name.split('.')
    for i, _part in enumerate(parts, 1):
        try:
            modname = ".".join(parts[:i])
            importlib.import_module(modname)
        except ImportError:
            if parts[:i - 1]:
                return ".".join(parts[:i - 1]), ".".join(parts[i - 1:])
            else:
                return None, ".".join(parts)
        except IndexError:
            pass

    return name, ""


# -- Generating output ---------------------------------------------------------


class ModuleScanner:
    def __init__(self, app: Any, obj: Any) -> None:
        self.app = app
        self.object = obj

    def get_object_type(self, name: str, value: Any) -> str:
        return get_documenter(self.app, value, self.object).objtype

    def is_skipped(self, name: str, value: Any, objtype: str) -> bool:
        try:
            return self.app.emit_firstresult('autodoc-skip-member', objtype,
                                             name, value, False, {})
        except Exception as exc:
            logger.warning(__('autosummary: failed to determine %r to be documented, '
                              'the following exception was raised:\n%s'),
                           name, exc, type='autosummary')
            return False

    def scan(self, imported_members: bool) -> list[str]:
        members = []
        try:
            analyzer = ModuleAnalyzer.for_module(self.object.__name__)
            attr_docs = analyzer.find_attr_docs()
        except PycodeError:
            attr_docs = {}

        for name in members_of(self.object, self.app.config):
            try:
                value = safe_getattr(self.object, name)
            except AttributeError:
                value = None

            objtype = self.get_object_type(name, value)
            if self.is_skipped(name, value, objtype):
                continue

            try:
                if ('', name) in attr_docs:
                    imported = False
                elif inspect.ismodule(value):  # NoQA: SIM114
                    imported = True
                elif safe_getattr(value, '__module__') != self.object.__name__:
                    imported = True
                else:
                    imported = False
            except AttributeError:
                imported = False

            respect_module_all = not self.app.config.autosummary_ignore_module_all
            if (
                # list all members up
                imported_members
                # list not-imported members
                or imported is False
                # list members that have __all__ set
                or (respect_module_all and '__all__' in dir(self.object))
            ):
                members.append(name)

        return members


def members_of(obj: Any, conf: Config) -> Sequence[str]:
    """Get the members of ``obj``, possibly ignoring the ``__all__`` module attribute

    Follows the ``conf.autosummary_ignore_module_all`` setting."""

    if conf.autosummary_ignore_module_all:
        return dir(obj)
    else:
        return getall(obj) or dir(obj)


def generate_autosummary_content(name: str, obj: Any, parent: Any,
                                 template: AutosummaryRenderer, template_name: str,
                                 imported_members: bool, app: Any,
                                 recursive: bool, context: dict,
                                 modname: str | None = None,
                                 qualname: str | None = None) -> str:
    doc = get_documenter(app, obj, parent)

    ns: dict[str, Any] = {}
    ns.update(context)

    if doc.objtype == 'module':
        scanner = ModuleScanner(app, obj)
        ns['members'] = scanner.scan(imported_members)

        respect_module_all = not app.config.autosummary_ignore_module_all
        imported_members = imported_members or ('__all__' in dir(obj) and respect_module_all)

        ns['functions'], ns['all_functions'] = \
            _get_members(doc, app, obj, {'function'}, imported=imported_members)
        ns['classes'], ns['all_classes'] = \
            _get_members(doc, app, obj, {'class'}, imported=imported_members)
        ns['exceptions'], ns['all_exceptions'] = \
            _get_members(doc, app, obj, {'exception'}, imported=imported_members)
        ns['attributes'], ns['all_attributes'] = \
            _get_module_attrs(name, ns['members'])
        ispackage = hasattr(obj, '__path__')
        if ispackage and recursive:
            # Use members that are not modules as skip list, because it would then mean
            # that module was overwritten in the package namespace
            skip = (
                ns["all_functions"]
                + ns["all_classes"]
                + ns["all_exceptions"]
                + ns["all_attributes"]
            )

            # If respect_module_all and module has a __all__ attribute, first get
            # modules that were explicitly imported. Next, find the rest with the
            # get_modules method, but only put in "public" modules that are in the
            # __all__ list
            #
            # Otherwise, use get_modules method normally
            if respect_module_all and '__all__' in dir(obj):
                imported_modules, all_imported_modules = \
                    _get_members(doc, app, obj, {'module'}, imported=True)
                skip += all_imported_modules
                imported_modules = [name + '.' + modname for modname in imported_modules]
                all_imported_modules = \
                    [name + '.' + modname for modname in all_imported_modules]
                public_members = getall(obj)
            else:
                imported_modules, all_imported_modules = [], []
                public_members = None

            modules, all_modules = _get_modules(obj, skip=skip, name=name,
                                                public_members=public_members)
            ns['modules'] = imported_modules + modules
            ns["all_modules"] = all_imported_modules + all_modules
    elif doc.objtype == 'class':
        ns['members'] = dir(obj)
        ns['inherited_members'] = \
            set(dir(obj)) - set(obj.__dict__.keys())
        ns['methods'], ns['all_methods'] = \
            _get_members(doc, app, obj, {'method'}, include_public={'__init__'})
        ns['attributes'], ns['all_attributes'] = \
            _get_members(doc, app, obj, {'attribute', 'property'})

    if modname is None or qualname is None:
        modname, qualname = _split_full_qualified_name(name)

    if doc.objtype in ('method', 'attribute', 'property'):
        ns['class'] = qualname.rsplit(".", 1)[0]

    if doc.objtype in ('class',):
        shortname = qualname
    else:
        shortname = qualname.rsplit(".", 1)[-1]

    ns['fullname'] = name
    ns['module'] = modname
    ns['objname'] = qualname
    ns['name'] = shortname

    ns['objtype'] = doc.objtype
    ns['underline'] = len(name) * '='

    if template_name:
        return template.render(template_name, ns)
    else:
        return template.render(doc.objtype, ns)


def _skip_member(app: Sphinx, obj: Any, name: str, objtype: str) -> bool:
    try:
        return app.emit_firstresult('autodoc-skip-member', objtype, name,
                                    obj, False, {})
    except Exception as exc:
        logger.warning(__('autosummary: failed to determine %r to be documented, '
                          'the following exception was raised:\n%s'),
                       name, exc, type='autosummary')
        return False


def _get_class_members(obj: Any) -> dict[str, Any]:
    members = sphinx.ext.autodoc.get_class_members(obj, None, safe_getattr)
    return {name: member.object for name, member in members.items()}


def _get_module_members(app: Sphinx, obj: Any) -> dict[str, Any]:
    members = {}
    for name in members_of(obj, app.config):
        try:
            members[name] = safe_getattr(obj, name)
        except AttributeError:
            continue
    return members


def _get_all_members(doc: type[Documenter], app: Sphinx, obj: Any) -> dict[str, Any]:
    if doc.objtype == 'module':
        return _get_module_members(app, obj)
    elif doc.objtype == 'class':
        return _get_class_members(obj)
    return {}


def _get_members(doc: type[Documenter], app: Sphinx, obj: Any, types: set[str], *,
                 include_public: Set[str] = frozenset(),
                 imported: bool = True) -> tuple[list[str], list[str]]:
    items: list[str] = []
    public: list[str] = []

    all_members = _get_all_members(doc, app, obj)
    for name, value in all_members.items():
        documenter = get_documenter(app, value, obj)
        if documenter.objtype in types:
            # skip imported members if expected
            if imported or getattr(value, '__module__', None) == obj.__name__:
                skipped = _skip_member(app, value, name, documenter.objtype)
                if skipped is True:
                    pass
                elif skipped is False:
                    # show the member forcedly
                    items.append(name)
                    public.append(name)
                else:
                    items.append(name)
                    if name in include_public or not name.startswith('_'):
                        # considers member as public
                        public.append(name)
    return public, items


def _get_module_attrs(name: str, members: Any) -> tuple[list[str], list[str]]:
    """Find module attributes with docstrings."""
    attrs, public = [], []
    try:
        analyzer = ModuleAnalyzer.for_module(name)
        attr_docs = analyzer.find_attr_docs()
        for namespace, attr_name in attr_docs:
            if namespace == '' and attr_name in members:
                attrs.append(attr_name)
                if not attr_name.startswith('_'):
                    public.append(attr_name)
    except PycodeError:
        pass    # give up if ModuleAnalyzer fails to parse code
    return public, attrs


def _get_modules(
        obj: Any,
        *,
        skip: Sequence[str],
        name: str,
        public_members: Sequence[str] | None = None) -> tuple[list[str], list[str]]:
    items: list[str] = []
    public: list[str] = []
    for _, modname, _ispkg in pkgutil.iter_modules(obj.__path__):

        if modname in skip:
            # module was overwritten in __init__.py, so not accessible
            continue
        fullname = name + '.' + modname
        try:
            module = import_module(fullname)
            if module and hasattr(module, '__sphinx_mock__'):
                continue
        except ImportError:
            pass

        items.append(fullname)
        if public_members is not None:
            if modname in public_members:
                public.append(fullname)
        else:
            if not modname.startswith('_'):
                public.append(fullname)
    return public, items


def generate_autosummary_docs(sources: list[str],
                              output_dir: str | os.PathLike[str] | None = None,
                              suffix: str = '.rst',
                              base_path: str | os.PathLike[str] | None = None,
                              imported_members: bool = False, app: Any = None,
                              overwrite: bool = True, encoding: str = 'utf-8') -> None:
    showed_sources = sorted(sources)
    if len(showed_sources) > 20:
        showed_sources = showed_sources[:10] + ['...'] + showed_sources[-10:]
    logger.info(__('[autosummary] generating autosummary for: %s') %
                ', '.join(showed_sources))

    if output_dir:
        logger.info(__('[autosummary] writing to %s') % output_dir)

    if base_path is not None:
        sources = [os.path.join(base_path, filename) for filename in sources]

    template = AutosummaryRenderer(app)

    # read
    items = find_autosummary_in_files(sources)

    # keep track of new files
    new_files = []

    if app:
        filename_map = app.config.autosummary_filename_map
    else:
        filename_map = {}

    # write
    for entry in sorted(set(items), key=str):
        if entry.path is None:
            # The corresponding autosummary:: directive did not have
            # a :toctree: option
            continue

        path = output_dir or os.path.abspath(entry.path)
        ensuredir(path)

        try:
            name, obj, parent, modname = import_by_name(entry.name)
            qualname = name.replace(modname + ".", "")
        except ImportExceptionGroup as exc:
            try:
                # try to import as an instance attribute
                name, obj, parent, modname = import_ivar_by_name(entry.name)
                qualname = name.replace(modname + ".", "")
            except ImportError as exc2:
                if exc2.__cause__:
                    exceptions: list[BaseException] = exc.exceptions + [exc2.__cause__]
                else:
                    exceptions = exc.exceptions + [exc2]

                errors = list({f"* {type(e).__name__}: {e}" for e in exceptions})
                logger.warning(__('[autosummary] failed to import %s.\nPossible hints:\n%s'),
                               entry.name, '\n'.join(errors))
                continue

        context: dict[str, Any] = {}
        if app:
            context.update(app.config.autosummary_context)

        content = generate_autosummary_content(name, obj, parent, template, entry.template,
                                               imported_members, app, entry.recursive, context,
                                               modname, qualname)

        filename = os.path.join(path, filename_map.get(name, name) + suffix)
        if os.path.isfile(filename):
            with open(filename, encoding=encoding) as f:
                old_content = f.read()

            if content == old_content:
                continue
            if overwrite:  # content has changed
                with open(filename, 'w', encoding=encoding) as f:
                    f.write(content)
                new_files.append(filename)
        else:
            with open(filename, 'w', encoding=encoding) as f:
                f.write(content)
            new_files.append(filename)

    # descend recursively to new files
    if new_files:
        generate_autosummary_docs(new_files, output_dir=output_dir,
                                  suffix=suffix, base_path=base_path,
                                  imported_members=imported_members, app=app,
                                  overwrite=overwrite)


# -- Finding documented entries in files ---------------------------------------

def find_autosummary_in_files(filenames: list[str]) -> list[AutosummaryEntry]:
    """Find out what items are documented in source/*.rst.

    See `find_autosummary_in_lines`.
    """
    documented: list[AutosummaryEntry] = []
    for filename in filenames:
        with open(filename, encoding='utf-8', errors='ignore') as f:
            lines = f.read().splitlines()
            documented.extend(find_autosummary_in_lines(lines, filename=filename))
    return documented


def find_autosummary_in_docstring(
    name: str, filename: str | None = None,
) -> list[AutosummaryEntry]:
    """Find out what items are documented in the given object's docstring.

    See `find_autosummary_in_lines`.
    """
    try:
        real_name, obj, parent, modname = import_by_name(name)
        lines = pydoc.getdoc(obj).splitlines()
        return find_autosummary_in_lines(lines, module=name, filename=filename)
    except AttributeError:
        pass
    except ImportExceptionGroup as exc:
        errors = '\n'.join({f"* {type(e).__name__}: {e}" for e in exc.exceptions})
        logger.warning(f'Failed to import {name}.\nPossible hints:\n{errors}')  # NoQA: G004
    except SystemExit:
        logger.warning("Failed to import '%s'; the module executes module level "
                       'statement and it might call sys.exit().', name)
    return []


def find_autosummary_in_lines(
    lines: list[str], module: str | None = None, filename: str | None = None,
) -> list[AutosummaryEntry]:
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
    recursive_arg_re = re.compile(r'^\s+:recursive:\s*$')
    toctree_arg_re = re.compile(r'^\s+:toctree:\s*(.*?)\s*$')
    template_arg_re = re.compile(r'^\s+:template:\s*(.*?)\s*$')

    documented: list[AutosummaryEntry] = []

    recursive = False
    toctree: str | None = None
    template = ''
    current_module = module
    in_autosummary = False
    base_indent = ""

    for line in lines:
        if in_autosummary:
            m = recursive_arg_re.match(line)
            if m:
                recursive = True
                continue

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
                    name = f"{current_module}.{name}"
                documented.append(AutosummaryEntry(name, toctree, template, recursive))
                continue

            if not line.strip() or line.startswith(base_indent + " "):
                continue

            in_autosummary = False

        m = autosummary_re.match(line)
        if m:
            in_autosummary = True
            base_indent = m.group(1)
            recursive = False
            toctree = None
            template = ''
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


def get_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        usage='%(prog)s [OPTIONS] <SOURCE_FILE>...',
        epilog=__('For more information, visit <https://www.sphinx-doc.org/>.'),
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
    parser.add_argument('-a', '--respect-module-all', action='store_true',
                        dest='respect_module_all', default=False,
                        help=__('document exactly the members in module __all__ attribute. '
                                '(default: %(default)s)'))

    return parser


def main(argv: Sequence[str] = (), /) -> None:
    locale.setlocale(locale.LC_ALL, '')
    sphinx.locale.init_console()

    app = DummyApplication(sphinx.locale.get_translator())
    logging.setup(app, sys.stdout, sys.stderr)  # type: ignore[arg-type]
    setup_documenters(app)
    args = get_parser().parse_args(argv or sys.argv[1:])

    if args.templates:
        app.config.templates_path.append(path.abspath(args.templates))
    app.config.autosummary_ignore_module_all = (  # type: ignore[attr-defined]
        not args.respect_module_all
    )

    generate_autosummary_docs(args.source_file, args.output_dir,
                              '.' + args.suffix,
                              imported_members=args.imported_members,
                              app=app)


if __name__ == '__main__':
    main(sys.argv[1:])
