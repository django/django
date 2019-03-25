# -*- coding: utf-8 -*-
"""
    sphinx.ext.autosummary
    ~~~~~~~~~~~~~~~~~~~~~~

    Sphinx extension that adds an autosummary:: directive, which can be
    used to generate function/method/attribute/etc. summary lists, similar
    to those output eg. by Epydoc and other API doc generation tools.

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

    :copyright: Copyright 2007-2019 by the Sphinx team, see AUTHORS.
    :license: BSD, see LICENSE for details.
"""

import inspect
import os
import posixpath
import re
import sys
import warnings
from types import ModuleType

from docutils import nodes
from docutils.parsers.rst import directives
from docutils.parsers.rst.states import RSTStateMachine, state_classes
from docutils.statemachine import ViewList
from six import string_types
from six import text_type

import sphinx
from sphinx import addnodes
from sphinx.deprecation import RemovedInSphinx20Warning
from sphinx.environment.adapters.toctree import TocTree
from sphinx.ext.autodoc import get_documenters
from sphinx.ext.autodoc.directive import DocumenterBridge, Options
from sphinx.ext.autodoc.importer import import_module
from sphinx.locale import __
from sphinx.pycode import ModuleAnalyzer, PycodeError
from sphinx.util import import_object, rst, logging
from sphinx.util.docutils import (
    NullReporter, SphinxDirective, new_document, switch_source_input
)
from sphinx.util.matching import Matcher

if False:
    # For type annotation
    from typing import Any, Dict, List, Tuple, Type, Union  # NOQA
    from docutils.utils import Inliner  # NOQA
    from sphinx.application import Sphinx  # NOQA
    from sphinx.environment import BuildEnvironment  # NOQA
    from sphinx.ext.autodoc import Documenter  # NOQA

logger = logging.getLogger(__name__)


periods_re = re.compile(r'\.(?:\s+)')
literal_re = re.compile(r'::\s*$')


# -- autosummary_toc node ------------------------------------------------------

class autosummary_toc(nodes.comment):
    pass


def process_autosummary_toc(app, doctree):
    # type: (Sphinx, nodes.Node) -> None
    """Insert items described in autosummary:: to the TOC tree, but do
    not generate the toctree:: list.
    """
    env = app.builder.env
    crawled = {}

    def crawl_toc(node, depth=1):
        # type: (nodes.Node, int) -> None
        crawled[node] = True
        for j, subnode in enumerate(node):
            try:
                if (isinstance(subnode, autosummary_toc) and
                        isinstance(subnode[0], addnodes.toctree)):
                    TocTree(env).note(env.docname, subnode[0])
                    continue
            except IndexError:
                continue
            if not isinstance(subnode, nodes.section):
                continue
            if subnode not in crawled:
                crawl_toc(subnode, depth + 1)
    crawl_toc(doctree)


def autosummary_toc_visit_html(self, node):
    # type: (nodes.NodeVisitor, autosummary_toc) -> None
    """Hide autosummary toctree list in HTML output."""
    raise nodes.SkipNode


def autosummary_noop(self, node):
    # type: (nodes.NodeVisitor, nodes.Node) -> None
    pass


# -- autosummary_table node ----------------------------------------------------

class autosummary_table(nodes.comment):
    pass


def autosummary_table_visit_html(self, node):
    # type: (nodes.NodeVisitor, autosummary_table) -> None
    """Make the first column of the table non-breaking."""
    try:
        tbody = node[0][0][-1]
        for row in tbody:
            col1_entry = row[0]
            par = col1_entry[0]
            for j, subnode in enumerate(list(par)):
                if isinstance(subnode, nodes.Text):
                    new_text = text_type(subnode.astext())
                    new_text = new_text.replace(u" ", u"\u00a0")
                    par[j] = nodes.Text(new_text)
    except IndexError:
        pass


# -- autodoc integration -------------------------------------------------------

# current application object (used in `get_documenter()`).
_app = None  # type: Sphinx


class FakeDirective(DocumenterBridge):
    def __init__(self):
        # type: () -> None
        super(FakeDirective, self).__init__({}, None, Options(), 0)  # type: ignore


def get_documenter(*args):
    # type: (Any) -> Type[Documenter]
    """Get an autodoc.Documenter class suitable for documenting the given
    object.

    *obj* is the Python object to be documented, and *parent* is an
    another Python object (e.g. a module or a class) to which *obj*
    belongs to.
    """
    from sphinx.ext.autodoc import DataDocumenter, ModuleDocumenter
    if len(args) == 3:
        # new style arguments: (app, obj, parent)
        app, obj, parent = args
    else:
        # old style arguments: (obj, parent)
        app = _app
        obj, parent = args
        warnings.warn('the interface of get_documenter() has been changed. '
                      'Please give application object as first argument.',
                      RemovedInSphinx20Warning, stacklevel=2)

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

    # Get the corrent documenter class for *obj*
    classes = [cls for cls in get_documenters(app).values()
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
    option_spec = {
        'toctree': directives.unchanged,
        'nosignatures': directives.flag,
        'template': directives.unchanged,
    }

    def warn(self, msg):
        # type: (unicode) -> None
        self.warnings.append(self.state.document.reporter.warning(
            msg, line=self.lineno))

    def run(self):
        # type: () -> List[nodes.Node]
        self.genopt = Options()
        self.warnings = []  # type: List[nodes.Node]
        self.result = ViewList()

        names = [x.strip().split()[0] for x in self.content
                 if x.strip() and re.search(r'^[~a-zA-Z_]', x.strip()[0])]
        items = self.get_items(names)
        nodes = self.get_table(items)

        if 'toctree' in self.options:
            dirname = posixpath.dirname(self.env.docname)

            tree_prefix = self.options['toctree'].strip()
            docnames = []
            excluded = Matcher(self.config.exclude_patterns)
            for name, sig, summary, real_name in items:
                docname = posixpath.join(tree_prefix, real_name)
                docname = posixpath.normpath(posixpath.join(dirname, docname))
                if docname not in self.env.found_docs:
                    if excluded(self.env.doc2path(docname, None)):
                        self.warn('toctree references excluded document %r'
                                  % docname)
                    else:
                        self.warn('toctree references unknown document %r'
                                  % docname)
                docnames.append(docname)

            tocnode = addnodes.toctree()
            tocnode['includefiles'] = docnames
            tocnode['entries'] = [(None, docn) for docn in docnames]
            tocnode['maxdepth'] = -1
            tocnode['glob'] = None

            tocnode = autosummary_toc('', '', tocnode)
            nodes.append(tocnode)

        return self.warnings + nodes

    def get_items(self, names):
        # type: (List[unicode]) -> List[Tuple[unicode, unicode, unicode, unicode]]
        """Try to import the given names, and return a list of
        ``[(name, signature, summary_string, real_name), ...]``.
        """
        prefixes = get_import_prefixes_from_env(self.env)

        items = []  # type: List[Tuple[unicode, unicode, unicode, unicode]]

        max_item_chars = 50

        for name in names:
            display_name = name
            if name.startswith('~'):
                name = name[1:]
                display_name = name.split('.')[-1]

            try:
                real_name, obj, parent, modname = import_by_name(name, prefixes=prefixes)
            except ImportError:
                self.warn('failed to import %s' % name)
                items.append((name, '', '', name))
                continue

            self.result = ViewList()  # initialize for each documenter
            full_name = real_name
            if not isinstance(obj, ModuleType):
                # give explicitly separated module name, so that members
                # of inner classes can be documented
                full_name = modname + '::' + full_name[len(modname) + 1:]
            # NB. using full_name here is important, since Documenters
            #     handle module prefixes slightly differently
            documenter = get_documenter(self.env.app, obj, parent)(self, full_name)
            if not documenter.parse_name():
                self.warn('failed to parse name %s' % real_name)
                items.append((display_name, '', '', real_name))
                continue
            if not documenter.import_object():
                self.warn('failed to import object %s' % real_name)
                items.append((display_name, '', '', real_name))
                continue
            if documenter.options.members and not documenter.check_module():
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

            sig = documenter.format_signature()
            if not sig:
                sig = ''
            else:
                max_chars = max(10, max_item_chars - len(display_name))
                sig = mangle_signature(sig, max_chars=max_chars)

            # -- Grab the summary

            documenter.add_content(None)
            summary = extract_summary(self.result.data[:], self.state.document)

            items.append((display_name, sig, summary, real_name))

        return items

    def get_table(self, items):
        # type: (List[Tuple[unicode, unicode, unicode, unicode]]) -> List[Union[addnodes.tabular_col_spec, autosummary_table]]  # NOQA
        """Generate a proper list of table nodes for autosummary:: directive.

        *items* is a list produced by :meth:`get_items`.
        """
        table_spec = addnodes.tabular_col_spec()
        table_spec['spec'] = r'\X{1}{2}\X{1}{2}'

        table = autosummary_table('')
        real_table = nodes.table('', classes=['longtable'])
        table.append(real_table)
        group = nodes.tgroup('', cols=2)
        real_table.append(group)
        group.append(nodes.colspec('', colwidth=10))
        group.append(nodes.colspec('', colwidth=90))
        body = nodes.tbody('')
        group.append(body)

        def append_row(*column_texts):
            # type: (unicode) -> None
            row = nodes.row('')
            source, line = self.state_machine.get_source_and_line()
            for text in column_texts:
                node = nodes.paragraph('')
                vl = ViewList()
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
                col1 = ':%s:`%s <%s>`\\ %s' % (qualifier, name, real_name, rst.escape(sig))  # type: unicode  # NOQA
            else:
                col1 = ':%s:`%s <%s>`' % (qualifier, name, real_name)
            col2 = summary
            append_row(col1, col2)

        return [table_spec, table]


def strip_arg_typehint(s):
    # type: (unicode) -> unicode
    """Strip a type hint from argument definition."""
    return s.split(':')[0].strip()


def mangle_signature(sig, max_chars=30):
    # type: (unicode, int) -> unicode
    """Reformat a function signature to a more compact form."""
    # Strip return type annotation
    s = re.sub(r"\)\s*->\s.*$", ")", sig)

    # Remove parenthesis
    s = re.sub(r"^\((.*)\)$", r"\1", s).strip()

    # Strip strings (which can contain things that confuse the code below)
    s = re.sub(r"\\\\", "", s)
    s = re.sub(r"\\'", "", s)
    s = re.sub(r"'[^']*'", "", s)

    # Parse the signature to arguments + options
    args = []  # type: List[unicode]
    opts = []  # type: List[unicode]

    opt_re = re.compile(r"^(.*, |)([a-zA-Z0-9_*]+)=")
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

    return u"(%s)" % sig


def extract_summary(doc, document):
    # type: (List[unicode], Any) -> unicode
    """Extract summary from docstring."""

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
    state_machine = RSTStateMachine(state_classes, 'Body')
    node = new_document('', document.settings)
    node.reporter = NullReporter()
    state_machine.run(doc, node)

    if not isinstance(node[0], nodes.paragraph):
        # document starts with non-paragraph: pick up the first line
        summary = doc[0].strip()
    else:
        # Try to find the "first sentence", which may span multiple lines
        sentences = periods_re.split(" ".join(doc))
        if len(sentences) == 1:
            summary = sentences[0].strip()
        else:
            summary = ''
            while sentences:
                summary += sentences.pop(0) + '.'
                node[:] = []
                state_machine.run([summary], node)
                if not node.traverse(nodes.system_message):
                    # considered as that splitting by period does not break inline markups
                    break

    # strip literal notation mark ``::`` from tail of summary
    summary = literal_re.sub('.', summary)

    return summary


def limited_join(sep, items, max_chars=30, overflow_marker="..."):
    # type: (unicode, List[unicode], int, unicode) -> unicode
    """Join a number of strings to one, limiting the length to *max_chars*.

    If the string overflows this limit, replace the last fitting item by
    *overflow_marker*.

    Returns: joined_string
    """
    full_str = sep.join(items)
    if len(full_str) < max_chars:
        return full_str

    n_chars = 0
    n_items = 0
    for j, item in enumerate(items):
        n_chars += len(item) + len(sep)
        if n_chars < max_chars - len(overflow_marker):
            n_items += 1
        else:
            break

    return sep.join(list(items[:n_items]) + [overflow_marker])


# -- Importing items -----------------------------------------------------------

def get_import_prefixes_from_env(env):
    # type: (BuildEnvironment) -> List
    """
    Obtain current Python import prefixes (for `import_by_name`)
    from ``document.env``
    """
    prefixes = [None]  # type: List

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


def import_by_name(name, prefixes=[None]):
    # type: (unicode, List) -> Tuple[unicode, Any, Any, unicode]
    """Import a Python object that has the given *name*, under one of the
    *prefixes*.  The first name that succeeds is used.
    """
    tried = []
    for prefix in prefixes:
        try:
            if prefix:
                prefixed_name = '.'.join([prefix, name])
            else:
                prefixed_name = name
            obj, parent, modname = _import_by_name(prefixed_name)
            return prefixed_name, obj, parent, modname
        except ImportError:
            tried.append(prefixed_name)
    raise ImportError('no module named %s' % ' or '.join(tried))


def _import_by_name(name):
    # type: (str) -> Tuple[Any, Any, unicode]
    """Import a Python object given its full name."""
    try:
        name_parts = name.split('.')

        # try first interpret `name` as MODNAME.OBJ
        modname = '.'.join(name_parts[:-1])
        if modname:
            try:
                mod = import_module(modname)
                return getattr(mod, name_parts[-1]), mod, modname
            except (ImportError, IndexError, AttributeError):
                pass

        # ... then as MODNAME, MODNAME.OBJ1, MODNAME.OBJ1.OBJ2, ...
        last_j = 0
        modname = None
        for j in reversed(range(1, len(name_parts) + 1)):
            last_j = j
            modname = '.'.join(name_parts[:j])
            try:
                import_module(modname)
            except ImportError:
                continue

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
    except (ValueError, ImportError, AttributeError, KeyError) as e:
        raise ImportError(*e.args)


# -- :autolink: (smart default role) -------------------------------------------

def autolink_role(typ, rawtext, etext, lineno, inliner, options={}, content=[]):
    # type: (unicode, unicode, unicode, int, Inliner, Dict, List[unicode]) -> Tuple[List[nodes.Node], List[nodes.Node]]  # NOQA
    """Smart linking role.

    Expands to ':obj:`text`' if `text` is an object that can be imported;
    otherwise expands to '*text*'.
    """
    env = inliner.document.settings.env
    r = None  # type: Tuple[List[nodes.Node], List[nodes.Node]]
    r = env.get_domain('py').role('obj')(
        'obj', rawtext, etext, lineno, inliner, options, content)
    pnode = r[0][0]

    prefixes = get_import_prefixes_from_env(env)
    try:
        name, obj, parent, modname = import_by_name(pnode['reftarget'], prefixes)
    except ImportError:
        content_node = pnode[0]
        r[0][0] = nodes.emphasis(rawtext, content_node[0].astext(),
                                 classes=content_node['classes'])
    return r


def get_rst_suffix(app):
    # type: (Sphinx) -> unicode
    def get_supported_format(suffix):
        # type: (unicode) -> Tuple[unicode]
        parser_class = app.registry.get_source_parsers().get(suffix)
        if parser_class is None:
            return ('restructuredtext',)
        if isinstance(parser_class, string_types):
            parser_class = import_object(parser_class, 'source parser')  # type: ignore
        return parser_class.supported

    suffix = None  # type: unicode
    for suffix in app.config.source_suffix:
        if 'restructuredtext' in get_supported_format(suffix):
            return suffix

    return None


def process_generate_options(app):
    # type: (Sphinx) -> None
    genfiles = app.config.autosummary_generate

    if genfiles and not hasattr(genfiles, '__len__'):
        env = app.builder.env
        genfiles = [env.doc2path(x, base=None) for x in env.found_docs
                    if os.path.isfile(env.doc2path(x))]

    if not genfiles:
        return

    from sphinx.ext.autosummary.generate import generate_autosummary_docs

    ext = list(app.config.source_suffix)
    genfiles = [genfile + (not genfile.endswith(tuple(ext)) and ext[0] or '')
                for genfile in genfiles]

    suffix = get_rst_suffix(app)
    if suffix is None:
        logger.warning(__('autosummary generats .rst files internally. '
                          'But your source_suffix does not contain .rst. Skipped.'))
        return

    generate_autosummary_docs(genfiles, builder=app.builder,
                              warn=logger.warning, info=logger.info,
                              suffix=suffix, base_path=app.srcdir,
                              app=app)


def setup(app):
    # type: (Sphinx) -> Dict[unicode, Any]
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
    app.add_role('autolink', autolink_role)
    app.connect('doctree-read', process_autosummary_toc)
    app.connect('builder-inited', process_generate_options)
    app.add_config_value('autosummary_generate', [], True, [bool])
    return {'version': sphinx.__display_version__, 'parallel_read_safe': True}
