"""Extension that adds an autosummary:: directive.

The directive can be used to generate function/method/attribute/etc. summary
lists, similar to those output eg. by Epydoc and other API doc generation tools.

An :autolink: role is also provided.

autosummary directive
---------------------

The autosummary directive has the form::

    .. autosummary::
       :nosignatures:
       :toctree: generated/

       module.function_1
       module.function_2
       ...

and it generates an output table (containing signatures, optionally)

    ========================  =============================================
    module.function_1(args)   Summary line from the docstring of function_1
    module.function_2(args)   Summary line from the docstring
    ...
    ========================  =============================================

If the :toctree: option is specified, files matching the function names
are inserted to the toctree with the given prefix:

    generated/module.function_1
    generated/module.function_2
    ...

Note: The file names contain the module:: or currentmodule:: prefixes.

.. seealso:: autosummary_generate.py


autolink role
-------------

The autolink role functions as ``:obj:`` when the name referred can be
resolved to a Python object, and otherwise it becomes simple emphasis.
This can be used as the default role to make links 'smart'.
"""

from __future__ import annotations

import inspect
import os
import posixpath
import re
import sys
from inspect import Parameter
from os import path
from types import ModuleType
from typing import TYPE_CHECKING, Any, cast

from docutils import nodes
from docutils.parsers.rst import directives
from docutils.parsers.rst.states import RSTStateMachine, Struct, state_classes
from docutils.statemachine import StringList

import sphinx
from sphinx import addnodes
from sphinx.config import Config
from sphinx.environment import BuildEnvironment
from sphinx.ext.autodoc import INSTANCEATTR, Documenter
from sphinx.ext.autodoc.directive import DocumenterBridge, Options
from sphinx.ext.autodoc.importer import import_module
from sphinx.ext.autodoc.mock import mock
from sphinx.locale import __
from sphinx.project import Project
from sphinx.pycode import ModuleAnalyzer, PycodeError
from sphinx.registry import SphinxComponentRegistry
from sphinx.util import logging, rst
from sphinx.util.docutils import (
    NullReporter,
    SphinxDirective,
    SphinxRole,
    new_document,
    switch_source_input,
)
from sphinx.util.inspect import getmro, signature_from_str
from sphinx.util.matching import Matcher

if TYPE_CHECKING:
    from collections.abc import Sequence

    from docutils.nodes import Node, system_message

    from sphinx.application import Sphinx
    from sphinx.extension import Extension
    from sphinx.util.typing import OptionSpec
    from sphinx.writers.html import HTML5Translator

logger = logging.getLogger(__name__)


periods_re = re.compile(r'\.(?:\s+)')
literal_re = re.compile(r'::\s*$')

WELL_KNOWN_ABBREVIATIONS = ('et al.', 'e.g.', 'i.e.')


# -- autosummary_toc node ------------------------------------------------------

class autosummary_toc(nodes.comment):
    pass


def autosummary_toc_visit_html(self: nodes.NodeVisitor, node: autosummary_toc) -> None:
    """Hide autosummary toctree list in HTML output."""
    raise nodes.SkipNode


def autosummary_noop(self: nodes.NodeVisitor, node: Node) -> None:
    pass


# -- autosummary_table node ----------------------------------------------------

class autosummary_table(nodes.comment):
    pass


def autosummary_table_visit_html(self: HTML5Translator, node: autosummary_table) -> None:
    """Make the first column of the table non-breaking."""
    try:
        table = cast(nodes.table, node[0])
        tgroup = cast(nodes.tgroup, table[0])
        tbody = cast(nodes.tbody, tgroup[-1])
        rows = cast(list[nodes.row], tbody)
        for row in rows:
            col1_entry = cast(nodes.entry, row[0])
            par = cast(nodes.paragraph, col1_entry[0])
            for j, subnode in enumerate(list(par)):
                if isinstance(subnode, nodes.Text):
                    new_text = subnode.astext().replace(" ", "\u00a0")
                    par[j] = nodes.Text(new_text)
    except IndexError:
        pass


# -- autodoc integration -------------------------------------------------------

class FakeApplication:
    def __init__(self) -> None:
        self.doctreedir = None
        self.events = None
        self.extensions: dict[str, Extension] = {}
        self.srcdir = None
        self.config = Config()
        self.project = Project('', {})
        self.registry = SphinxComponentRegistry()


class FakeDirective(DocumenterBridge):
    def __init__(self) -> None:
        settings = Struct(tab_width=8)
        document = Struct(settings=settings)
        app = FakeApplication()
        app.config.add('autodoc_class_signature', 'mixed', True, None)
        env = BuildEnvironment(app)  # type: ignore[arg-type]
        state = Struct(document=document)
        super().__init__(env, None, Options(), 0, state)


def get_documenter(app: Sphinx, obj: Any, parent: Any) -> type[Documenter]:
    """Get an autodoc.Documenter class suitable for documenting the given
    object.

    *obj* is the Python object to be documented, and *parent* is an
    another Python object (e.g. a module or a class) to which *obj*
    belongs to.
    """
    from sphinx.ext.autodoc import DataDocumenter, ModuleDocumenter

    if inspect.ismodule(obj):
        # ModuleDocumenter.can_document_member always returns False
        return ModuleDocumenter

    # Construct a fake documenter for *parent*
    if parent is not None:
        parent_doc_cls = get_documenter(app, parent, None)
    else:
        parent_doc_cls = ModuleDocumenter

    if hasattr(parent, '__name__'):
        parent_doc = parent_doc_cls(FakeDirective(), parent.__name__)
    else:
        parent_doc = parent_doc_cls(FakeDirective(), "")

    # Get the correct documenter class for *obj*
    classes = [cls for cls in app.registry.documenters.values()
               if cls.can_document_member(obj, '', False, parent_doc)]
    if classes:
        classes.sort(key=lambda cls: cls.priority)
        return classes[-1]
    else:
        return DataDocumenter


# -- .. autosummary:: ----------------------------------------------------------

class Autosummary(SphinxDirective):
    """
    Pretty table containing short signatures and summaries of functions etc.

    autosummary can also optionally generate a hidden toctree:: node.
    """

    required_arguments = 0
    optional_arguments = 0
    final_argument_whitespace = False
    has_content = True
    option_spec: OptionSpec = {
        'caption': directives.unchanged_required,
        'toctree': directives.unchanged,
        'nosignatures': directives.flag,
        'recursive': directives.flag,
        'template': directives.unchanged,
    }

    def run(self) -> list[Node]:
        self.bridge = DocumenterBridge(self.env, self.state.document.reporter,
                                       Options(), self.lineno, self.state)

        names = [x.strip().split()[0] for x in self.content
                 if x.strip() and re.search(r'^[~a-zA-Z_]', x.strip()[0])]
        items = self.get_items(names)
        nodes = self.get_table(items)

        if 'toctree' in self.options:
            dirname = posixpath.dirname(self.env.docname)

            tree_prefix = self.options['toctree'].strip()
            docnames = []
            excluded = Matcher(self.config.exclude_patterns)
            filename_map = self.config.autosummary_filename_map
            for _name, _sig, _summary, real_name in items:
                real_name = filename_map.get(real_name, real_name)
                docname = posixpath.join(tree_prefix, real_name)
                docname = posixpath.normpath(posixpath.join(dirname, docname))
                if docname not in self.env.found_docs:
                    if excluded(self.env.doc2path(docname, False)):
                        msg = __('autosummary references excluded document %r. Ignored.')
                    else:
                        msg = __('autosummary: stub file not found %r. '
                                 'Check your autosummary_generate setting.')

                    logger.warning(msg, real_name, location=self.get_location())
                    continue

                docnames.append(docname)

            if docnames:
                tocnode = addnodes.toctree()
                tocnode['includefiles'] = docnames
                tocnode['entries'] = [(None, docn) for docn in docnames]
                tocnode['maxdepth'] = -1
                tocnode['glob'] = None
                tocnode['caption'] = self.options.get('caption')

                nodes.append(autosummary_toc('', '', tocnode))

        if 'toctree' not in self.options and 'caption' in self.options:
            logger.warning(__('A captioned autosummary requires :toctree: option. ignored.'),
                           location=nodes[-1])

        return nodes

    def import_by_name(
        self, name: str, prefixes: list[str | None],
    ) -> tuple[str, Any, Any, str]:
        with mock(self.config.autosummary_mock_imports):
            try:
                return import_by_name(name, prefixes)
            except ImportExceptionGroup as exc:
                # check existence of instance attribute
                try:
                    return import_ivar_by_name(name, prefixes)
                except ImportError as exc2:
                    if exc2.__cause__:
                        errors: list[BaseException] = exc.exceptions + [exc2.__cause__]
                    else:
                        errors = exc.exceptions + [exc2]

                    raise ImportExceptionGroup(exc.args[0], errors) from None

    def create_documenter(self, app: Sphinx, obj: Any,
                          parent: Any, full_name: str) -> Documenter:
        """Get an autodoc.Documenter class suitable for documenting the given
        object.

        Wraps get_documenter and is meant as a hook for extensions.
        """
        doccls = get_documenter(app, obj, parent)
        return doccls(self.bridge, full_name)

    def get_items(self, names: list[str]) -> list[tuple[str, str, str, str]]:
        """Try to import the given names, and return a list of
        ``[(name, signature, summary_string, real_name), ...]``.
        """
        prefixes = get_import_prefixes_from_env(self.env)

        items: list[tuple[str, str, str, str]] = []

        max_item_chars = 50

        for name in names:
            display_name = name
            if name.startswith('~'):
                name = name[1:]
                display_name = name.split('.')[-1]

            try:
                real_name, obj, parent, modname = self.import_by_name(name, prefixes=prefixes)
            except ImportExceptionGroup as exc:
                errors = list({f"* {type(e).__name__}: {e}" for e in exc.exceptions})
                logger.warning(__('autosummary: failed to import %s.\nPossible hints:\n%s'),
                               name, '\n'.join(errors), location=self.get_location())
                continue

            self.bridge.result = StringList()  # initialize for each documenter
            full_name = real_name
            if not isinstance(obj, ModuleType):
                # give explicitly separated module name, so that members
                # of inner classes can be documented
                full_name = modname + '::' + full_name[len(modname) + 1:]
            # NB. using full_name here is important, since Documenters
            #     handle module prefixes slightly differently
            documenter = self.create_documenter(self.env.app, obj, parent, full_name)
            if not documenter.parse_name():
                logger.warning(__('failed to parse name %s'), real_name,
                               location=self.get_location())
                items.append((display_name, '', '', real_name))
                continue
            if not documenter.import_object():
                logger.warning(__('failed to import object %s'), real_name,
                               location=self.get_location())
                items.append((display_name, '', '', real_name))
                continue

            # try to also get a source code analyzer for attribute docs
            try:
                documenter.analyzer = ModuleAnalyzer.for_module(
                    documenter.get_real_modname())
                # parse right now, to get PycodeErrors on parsing (results will
                # be cached anyway)
                documenter.analyzer.find_attr_docs()
            except PycodeError as err:
                logger.debug('[autodoc] module analyzer failed: %s', err)
                # no source file -- e.g. for builtin and C modules
                documenter.analyzer = None

            # -- Grab the signature

            try:
                sig = documenter.format_signature(show_annotation=False)
            except TypeError:
                # the documenter does not support ``show_annotation`` option
                sig = documenter.format_signature()

            if not sig:
                sig = ''
            else:
                max_chars = max(10, max_item_chars - len(display_name))
                sig = mangle_signature(sig, max_chars=max_chars)

            # -- Grab the summary

            # bodge for ModuleDocumenter
            documenter._extra_indent = ''  # type: ignore[attr-defined]

            documenter.add_content(None)
            summary = extract_summary(self.bridge.result.data[:], self.state.document)

            items.append((display_name, sig, summary, real_name))

        return items

    def get_table(self, items: list[tuple[str, str, str, str]]) -> list[Node]:
        """Generate a proper list of table nodes for autosummary:: directive.

        *items* is a list produced by :meth:`get_items`.
        """
        table_spec = addnodes.tabular_col_spec()
        table_spec['spec'] = r'\X{1}{2}\X{1}{2}'

        table = autosummary_table('')
        real_table = nodes.table('', classes=['autosummary longtable'])
        table.append(real_table)
        group = nodes.tgroup('', cols=2)
        real_table.append(group)
        group.append(nodes.colspec('', colwidth=10))
        group.append(nodes.colspec('', colwidth=90))
        body = nodes.tbody('')
        group.append(body)

        def append_row(*column_texts: str) -> None:
            row = nodes.row('')
            source, line = self.state_machine.get_source_and_line()
            for text in column_texts:
                node = nodes.paragraph('')
                vl = StringList()
                vl.append(text, '%s:%d:<autosummary>' % (source, line))
                with switch_source_input(self.state, vl):
                    self.state.nested_parse(vl, 0, node)
                    try:
                        if isinstance(node[0], nodes.paragraph):
                            node = node[0]
                    except IndexError:
                        pass
                    row.append(nodes.entry('', node))
            body.append(row)

        for name, sig, summary, real_name in items:
            qualifier = 'obj'
            if 'nosignatures' not in self.options:
                col1 = f':py:{qualifier}:`{name} <{real_name}>`\\ {rst.escape(sig)}'
            else:
                col1 = f':py:{qualifier}:`{name} <{real_name}>`'
            col2 = summary
            append_row(col1, col2)

        return [table_spec, table]


def strip_arg_typehint(s: str) -> str:
    """Strip a type hint from argument definition."""
    return s.split(':')[0].strip()


def _cleanup_signature(s: str) -> str:
    """Clean up signature using inspect.signautre() for mangle_signature()"""
    try:
        sig = signature_from_str(s)
        parameters = list(sig.parameters.values())
        for i, param in enumerate(parameters):
            if param.annotation is not Parameter.empty:
                # Remove typehints
                param = param.replace(annotation=Parameter.empty)
            if param.default is not Parameter.empty:
                # Replace default value by "None"
                param = param.replace(default=None)
            parameters[i] = param
        sig = sig.replace(parameters=parameters, return_annotation=Parameter.empty)
        return str(sig)
    except Exception:
        # Return the original signature string if failed to clean (ex. parsing error)
        return s


def mangle_signature(sig: str, max_chars: int = 30) -> str:
    """Reformat a function signature to a more compact form."""
    s = _cleanup_signature(sig)

    # Strip return type annotation
    s = re.sub(r"\)\s*->\s.*$", ")", s)

    # Remove parenthesis
    s = re.sub(r"^\((.*)\)$", r"\1", s).strip()

    # Strip literals (which can contain things that confuse the code below)
    s = re.sub(r"\\\\", "", s)      # escaped backslash (maybe inside string)
    s = re.sub(r"\\'", "", s)       # escaped single quote
    s = re.sub(r'\\"', "", s)       # escaped double quote
    s = re.sub(r"'[^']*'", "", s)   # string literal (w/ single quote)
    s = re.sub(r'"[^"]*"', "", s)   # string literal (w/ double quote)

    # Strip complex objects (maybe default value of arguments)
    while re.search(r'\([^)]*\)', s):   # contents of parenthesis (ex. NamedTuple(attr=...))
        s = re.sub(r'\([^)]*\)', '', s)
    while re.search(r'<[^>]*>', s):     # contents of angle brackets (ex. <object>)
        s = re.sub(r'<[^>]*>', '', s)
    while re.search(r'{[^}]*}', s):     # contents of curly brackets (ex. dict)
        s = re.sub(r'{[^}]*}', '', s)

    # Parse the signature to arguments + options
    args: list[str] = []
    opts: list[str] = []

    opt_re = re.compile(r"^(.*, |)([a-zA-Z0-9_*]+)\s*=\s*")
    while s:
        m = opt_re.search(s)
        if not m:
            # The rest are arguments
            args = s.split(', ')
            break

        opts.insert(0, m.group(2))
        s = m.group(1)[:-2]

    # Strip typehints
    for i, arg in enumerate(args):
        args[i] = strip_arg_typehint(arg)

    for i, opt in enumerate(opts):
        opts[i] = strip_arg_typehint(opt)

    # Produce a more compact signature
    sig = limited_join(", ", args, max_chars=max_chars - 2)
    if opts:
        if not sig:
            sig = "[%s]" % limited_join(", ", opts, max_chars=max_chars - 4)
        elif len(sig) < max_chars - 4 - 2 - 3:
            sig += "[, %s]" % limited_join(", ", opts,
                                           max_chars=max_chars - len(sig) - 4 - 2)

    return "(%s)" % sig


def extract_summary(doc: list[str], document: Any) -> str:
    """Extract summary from docstring."""
    def parse(doc: list[str], settings: Any) -> nodes.document:
        state_machine = RSTStateMachine(state_classes, 'Body')
        node = new_document('', settings)
        node.reporter = NullReporter()
        state_machine.run(doc, node)

        return node

    # Skip a blank lines at the top
    while doc and not doc[0].strip():
        doc.pop(0)

    # If there's a blank line, then we can assume the first sentence /
    # paragraph has ended, so anything after shouldn't be part of the
    # summary
    for i, piece in enumerate(doc):
        if not piece.strip():
            doc = doc[:i]
            break

    if doc == []:
        return ''

    # parse the docstring
    node = parse(doc, document.settings)
    if isinstance(node[0], nodes.section):
        # document starts with a section heading, so use that.
        summary = node[0].astext().strip()
    elif not isinstance(node[0], nodes.paragraph):
        # document starts with non-paragraph: pick up the first line
        summary = doc[0].strip()
    else:
        # Try to find the "first sentence", which may span multiple lines
        sentences = periods_re.split(" ".join(doc))
        if len(sentences) == 1:
            summary = sentences[0].strip()
        else:
            summary = ''
            for i in range(len(sentences)):
                summary = ". ".join(sentences[:i + 1]).rstrip(".") + "."
                node[:] = []
                node = parse(doc, document.settings)
                if summary.endswith(WELL_KNOWN_ABBREVIATIONS):
                    pass
                elif not any(node.findall(nodes.system_message)):
                    # considered as that splitting by period does not break inline markups
                    break

    # strip literal notation mark ``::`` from tail of summary
    summary = literal_re.sub('.', summary)

    return summary


def limited_join(sep: str, items: list[str], max_chars: int = 30,
                 overflow_marker: str = "...") -> str:
    """Join a number of strings into one, limiting the length to *max_chars*.

    If the string overflows this limit, replace the last fitting item by
    *overflow_marker*.

    Returns: joined_string
    """
    full_str = sep.join(items)
    if len(full_str) < max_chars:
        return full_str

    n_chars = 0
    n_items = 0
    for item in items:
        n_chars += len(item) + len(sep)
        if n_chars < max_chars - len(overflow_marker):
            n_items += 1
        else:
            break

    return sep.join(list(items[:n_items]) + [overflow_marker])


# -- Importing items -----------------------------------------------------------


class ImportExceptionGroup(Exception):
    """Exceptions raised during importing the target objects.

    It contains an error messages and a list of exceptions as its arguments.
    """

    def __init__(self, message: str | None, exceptions: Sequence[BaseException]):
        super().__init__(message)
        self.exceptions = list(exceptions)


def get_import_prefixes_from_env(env: BuildEnvironment) -> list[str | None]:
    """
    Obtain current Python import prefixes (for `import_by_name`)
    from ``document.env``
    """
    prefixes: list[str | None] = [None]

    currmodule = env.ref_context.get('py:module')
    if currmodule:
        prefixes.insert(0, currmodule)

    currclass = env.ref_context.get('py:class')
    if currclass:
        if currmodule:
            prefixes.insert(0, currmodule + "." + currclass)
        else:
            prefixes.insert(0, currclass)

    return prefixes


def import_by_name(
    name: str, prefixes: Sequence[str | None] = (None,),
) -> tuple[str, Any, Any, str]:
    """Import a Python object that has the given *name*, under one of the
    *prefixes*.  The first name that succeeds is used.
    """
    tried = []
    errors: list[ImportExceptionGroup] = []
    for prefix in prefixes:
        try:
            if prefix:
                prefixed_name = '.'.join([prefix, name])
            else:
                prefixed_name = name
            obj, parent, modname = _import_by_name(prefixed_name, grouped_exception=True)
            return prefixed_name, obj, parent, modname
        except ImportError:
            tried.append(prefixed_name)
        except ImportExceptionGroup as exc:
            tried.append(prefixed_name)
            errors.append(exc)

    exceptions: list[BaseException] = sum((e.exceptions for e in errors), [])
    raise ImportExceptionGroup('no module named %s' % ' or '.join(tried), exceptions)


def _import_by_name(name: str, grouped_exception: bool = True) -> tuple[Any, Any, str]:
    """Import a Python object given its full name."""
    errors: list[BaseException] = []

    try:
        name_parts = name.split('.')

        # try first interpret `name` as MODNAME.OBJ
        modname = '.'.join(name_parts[:-1])
        if modname:
            try:
                mod = import_module(modname)
                return getattr(mod, name_parts[-1]), mod, modname
            except (ImportError, IndexError, AttributeError) as exc:
                errors.append(exc.__cause__ or exc)

        # ... then as MODNAME, MODNAME.OBJ1, MODNAME.OBJ1.OBJ2, ...
        last_j = 0
        modname = ''
        for j in reversed(range(1, len(name_parts) + 1)):
            last_j = j
            modname = '.'.join(name_parts[:j])
            try:
                import_module(modname)
            except ImportError as exc:
                errors.append(exc.__cause__ or exc)

            if modname in sys.modules:
                break

        if last_j < len(name_parts):
            parent = None
            obj = sys.modules[modname]
            for obj_name in name_parts[last_j:]:
                parent = obj
                obj = getattr(obj, obj_name)
            return obj, parent, modname
        else:
            return sys.modules[modname], None, modname
    except (ValueError, ImportError, AttributeError, KeyError) as exc:
        errors.append(exc)
        if grouped_exception:
            raise ImportExceptionGroup('', errors) from None  # NoQA: EM101
        else:
            raise ImportError(*exc.args) from exc


def import_ivar_by_name(name: str, prefixes: Sequence[str | None] = (None,),
                        grouped_exception: bool = True) -> tuple[str, Any, Any, str]:
    """Import an instance variable that has the given *name*, under one of the
    *prefixes*.  The first name that succeeds is used.
    """
    try:
        name, attr = name.rsplit(".", 1)
        real_name, obj, parent, modname = import_by_name(name, prefixes)

        # Get ancestors of the object (class.__mro__ includes the class itself as
        # the first entry)
        candidate_objects = getmro(obj)
        if len(candidate_objects) == 0:
            candidate_objects = (obj,)

        for candidate_obj in candidate_objects:
            analyzer = ModuleAnalyzer.for_module(getattr(candidate_obj, '__module__', modname))
            analyzer.analyze()
            # check for presence in `annotations` to include dataclass attributes
            found_attrs = set()
            found_attrs |= {attr for (qualname, attr) in analyzer.attr_docs}
            found_attrs |= {attr for (qualname, attr) in analyzer.annotations}
            if attr in found_attrs:
                return real_name + "." + attr, INSTANCEATTR, obj, modname
    except (ImportError, ValueError, PycodeError) as exc:
        raise ImportError from exc
    except ImportExceptionGroup:
        raise  # pass through it as is

    raise ImportError


# -- :autolink: (smart default role) -------------------------------------------

class AutoLink(SphinxRole):
    """Smart linking role.

    Expands to ':obj:`text`' if `text` is an object that can be imported;
    otherwise expands to '*text*'.
    """
    def run(self) -> tuple[list[Node], list[system_message]]:
        pyobj_role = self.env.get_domain('py').role('obj')
        assert pyobj_role is not None
        objects, errors = pyobj_role('obj', self.rawtext, self.text, self.lineno,
                                     self.inliner, self.options, self.content)
        if errors:
            return objects, errors

        assert len(objects) == 1
        pending_xref = cast(addnodes.pending_xref, objects[0])
        try:
            # try to import object by name
            prefixes = get_import_prefixes_from_env(self.env)
            import_by_name(pending_xref['reftarget'], prefixes)
        except ImportExceptionGroup:
            literal = cast(nodes.literal, pending_xref[0])
            objects[0] = nodes.emphasis(self.rawtext, literal.astext(),
                                        classes=literal['classes'])

        return objects, errors


def get_rst_suffix(app: Sphinx) -> str | None:
    def get_supported_format(suffix: str) -> tuple[str, ...]:
        parser_class = app.registry.get_source_parsers().get(suffix)
        if parser_class is None:
            return ('restructuredtext',)
        return parser_class.supported

    suffix = None
    for suffix in app.config.source_suffix:
        if 'restructuredtext' in get_supported_format(suffix):
            return suffix

    return None


def process_generate_options(app: Sphinx) -> None:
    genfiles = app.config.autosummary_generate

    if genfiles is True:
        env = app.builder.env
        genfiles = [env.doc2path(x, base=False) for x in env.found_docs
                    if os.path.isfile(env.doc2path(x))]
    elif genfiles is False:
        pass
    else:
        ext = list(app.config.source_suffix)
        genfiles = [genfile + (ext[0] if not genfile.endswith(tuple(ext)) else '')
                    for genfile in genfiles]

        for entry in genfiles[:]:
            if not path.isfile(path.join(app.srcdir, entry)):
                logger.warning(__('autosummary_generate: file not found: %s'), entry)
                genfiles.remove(entry)

    if not genfiles:
        return

    suffix = get_rst_suffix(app)
    if suffix is None:
        logger.warning(__('autosummary generats .rst files internally. '
                          'But your source_suffix does not contain .rst. Skipped.'))
        return

    from sphinx.ext.autosummary.generate import generate_autosummary_docs

    imported_members = app.config.autosummary_imported_members
    with mock(app.config.autosummary_mock_imports):
        generate_autosummary_docs(genfiles, suffix=suffix, base_path=app.srcdir,
                                  app=app, imported_members=imported_members,
                                  overwrite=app.config.autosummary_generate_overwrite,
                                  encoding=app.config.source_encoding)


def setup(app: Sphinx) -> dict[str, Any]:
    # I need autodoc
    app.setup_extension('sphinx.ext.autodoc')
    app.add_node(autosummary_toc,
                 html=(autosummary_toc_visit_html, autosummary_noop),
                 latex=(autosummary_noop, autosummary_noop),
                 text=(autosummary_noop, autosummary_noop),
                 man=(autosummary_noop, autosummary_noop),
                 texinfo=(autosummary_noop, autosummary_noop))
    app.add_node(autosummary_table,
                 html=(autosummary_table_visit_html, autosummary_noop),
                 latex=(autosummary_noop, autosummary_noop),
                 text=(autosummary_noop, autosummary_noop),
                 man=(autosummary_noop, autosummary_noop),
                 texinfo=(autosummary_noop, autosummary_noop))
    app.add_directive('autosummary', Autosummary)
    app.add_role('autolink', AutoLink())
    app.connect('builder-inited', process_generate_options)
    app.add_config_value('autosummary_context', {}, True)
    app.add_config_value('autosummary_filename_map', {}, 'html')
    app.add_config_value('autosummary_generate', True, True, [bool, list])
    app.add_config_value('autosummary_generate_overwrite', True, False)
    app.add_config_value('autosummary_mock_imports',
                         lambda config: config.autodoc_mock_imports, 'env')
    app.add_config_value('autosummary_imported_members', [], False, [bool])
    app.add_config_value('autosummary_ignore_module_all', True, 'env', bool)

    return {'version': sphinx.__display_version__, 'parallel_read_safe': True}
