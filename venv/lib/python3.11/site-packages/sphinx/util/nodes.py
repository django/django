"""Docutils node-related utility functions for Sphinx."""

from __future__ import annotations

import contextlib
import re
import unicodedata
from typing import TYPE_CHECKING, Any, Callable

from docutils import nodes

from sphinx import addnodes
from sphinx.locale import __
from sphinx.util import logging

if TYPE_CHECKING:
    from collections.abc import Iterable

    from docutils.nodes import Element, Node
    from docutils.parsers.rst import Directive
    from docutils.parsers.rst.states import Inliner
    from docutils.statemachine import StringList

    from sphinx.builders import Builder
    from sphinx.environment import BuildEnvironment
    from sphinx.util.tags import Tags

logger = logging.getLogger(__name__)


# \x00 means the "<" was backslash-escaped
explicit_title_re = re.compile(r'^(.+?)\s*(?<!\x00)<([^<]*?)>$', re.DOTALL)
caption_ref_re = explicit_title_re  # b/w compat alias


class NodeMatcher:
    """A helper class for Node.findall().

    It checks that the given node is an instance of the specified node-classes and
    has the specified node-attributes.

    For example, following example searches ``reference`` node having ``refdomain``
    and ``reftype`` attributes::

        matcher = NodeMatcher(nodes.reference, refdomain='std', reftype='citation')
        doctree.findall(matcher)
        # => [<reference ...>, <reference ...>, ...]

    A special value ``typing.Any`` matches any kind of node-attributes.  For example,
    following example searches ``reference`` node having ``refdomain`` attributes::

        from __future__ import annotations
from typing import TYPE_CHECKING, Any
        matcher = NodeMatcher(nodes.reference, refdomain=Any)
        doctree.findall(matcher)
        # => [<reference ...>, <reference ...>, ...]
    """

    def __init__(self, *node_classes: type[Node], **attrs: Any) -> None:
        self.classes = node_classes
        self.attrs = attrs

    def match(self, node: Node) -> bool:
        try:
            if self.classes and not isinstance(node, self.classes):
                return False

            if self.attrs:
                if not isinstance(node, nodes.Element):
                    return False

                for key, value in self.attrs.items():
                    if key not in node:
                        return False
                    elif value is Any:
                        continue
                    elif node.get(key) != value:
                        return False

            return True
        except Exception:
            # for non-Element nodes
            return False

    def __call__(self, node: Node) -> bool:
        return self.match(node)


def get_full_module_name(node: Node) -> str:
    """
    Return full module dotted path like: 'docutils.nodes.paragraph'

    :param nodes.Node node: target node
    :return: full module dotted path
    """
    return f'{node.__module__}.{node.__class__.__name__}'


def repr_domxml(node: Node, length: int = 80) -> str:
    """
    return DOM XML representation of the specified node like:
    '<paragraph translatable="False"><inline classes="versionmodified">New in version...'

    :param nodes.Node node: target node
    :param int length:
       length of return value to be striped. if false-value is specified, repr_domxml
       returns full of DOM XML representation.
    :return: DOM XML representation
    """
    try:
        text = node.asdom().toxml()
    except Exception:
        text = str(node)
    if length and len(text) > length:
        text = text[:length] + '...'
    return text


def apply_source_workaround(node: Element) -> None:
    # workaround: nodes.term have wrong rawsource if classifier is specified.
    # The behavior of docutils-0.11, 0.12 is:
    # * when ``term text : classifier1 : classifier2`` is specified,
    # * rawsource of term node will have: ``term text : classifier1 : classifier2``
    # * rawsource of classifier node will be None
    if isinstance(node, nodes.classifier) and not node.rawsource:
        logger.debug('[i18n] PATCH: %r to have source, line and rawsource: %s',
                     get_full_module_name(node), repr_domxml(node))
        definition_list_item = node.parent
        node.source = definition_list_item.source
        node.line = definition_list_item.line - 1
        node.rawsource = node.astext()  # set 'classifier1' (or 'classifier2')
    elif isinstance(node, nodes.classifier) and not node.source:
        # docutils-0.15 fills in rawsource attribute, but not in source.
        node.source = node.parent.source
    if isinstance(node, nodes.image) and node.source is None:
        logger.debug('[i18n] PATCH: %r to have source, line: %s',
                     get_full_module_name(node), repr_domxml(node))
        node.source, node.line = node.parent.source, node.parent.line
    if isinstance(node, nodes.title) and node.source is None:
        logger.debug('[i18n] PATCH: %r to have source: %s',
                     get_full_module_name(node), repr_domxml(node))
        node.source, node.line = node.parent.source, node.parent.line
    if isinstance(node, nodes.term):
        logger.debug('[i18n] PATCH: %r to have rawsource: %s',
                     get_full_module_name(node), repr_domxml(node))
        # strip classifier from rawsource of term
        for classifier in reversed(list(node.parent.findall(nodes.classifier))):
            node.rawsource = re.sub(r'\s*:\s*%s' % re.escape(classifier.astext()),
                                    '', node.rawsource)
    if isinstance(node, nodes.topic) and node.source is None:
        # docutils-0.18 does not fill the source attribute of topic
        logger.debug('[i18n] PATCH: %r to have source, line: %s',
                     get_full_module_name(node), repr_domxml(node))
        node.source, node.line = node.parent.source, node.parent.line

    # workaround: literal_block under bullet list (#4913)
    if isinstance(node, nodes.literal_block) and node.source is None:
        with contextlib.suppress(ValueError):
            node.source = get_node_source(node)

    # workaround: recommonmark-0.2.0 doesn't set rawsource attribute
    if not node.rawsource:
        node.rawsource = node.astext()

    if node.source and node.rawsource:
        return

    # workaround: some docutils nodes doesn't have source, line.
    if (isinstance(node, (
            nodes.rubric,  # #1305 rubric directive
            nodes.line,  # #1477 line node
            nodes.image,  # #3093 image directive in substitution
            nodes.field_name,  # #3335 field list syntax
    ))):
        logger.debug('[i18n] PATCH: %r to have source and line: %s',
                     get_full_module_name(node), repr_domxml(node))
        try:
            node.source = get_node_source(node)
        except ValueError:
            node.source = ''
        node.line = 0  # need fix docutils to get `node.line`
        return


IGNORED_NODES = (
    nodes.Invisible,
    nodes.literal_block,
    nodes.doctest_block,
    addnodes.versionmodified,
    # XXX there are probably more
)


def is_translatable(node: Node) -> bool:
    if isinstance(node, addnodes.translatable):
        return True

    # image node marked as translatable or having alt text
    if isinstance(node, nodes.image) and (node.get('translatable') or node.get('alt')):
        return True

    if isinstance(node, nodes.Inline) and 'translatable' not in node:  # type: ignore[operator]
        # inline node must not be translated if 'translatable' is not set
        return False

    if isinstance(node, nodes.TextElement):
        if not node.source:
            logger.debug('[i18n] SKIP %r because no node.source: %s',
                         get_full_module_name(node), repr_domxml(node))
            return False  # built-in message
        if isinstance(node, IGNORED_NODES) and 'translatable' not in node:
            logger.debug("[i18n] SKIP %r because node is in IGNORED_NODES "
                         "and no node['translatable']: %s",
                         get_full_module_name(node), repr_domxml(node))
            return False
        if not node.get('translatable', True):
            # not(node['translatable'] == True or node['translatable'] is None)
            logger.debug("[i18n] SKIP %r because not node['translatable']: %s",
                         get_full_module_name(node), repr_domxml(node))
            return False
        # <field_name>orphan</field_name>
        # XXX ignore all metadata (== docinfo)
        if isinstance(node, nodes.field_name) and node.children[0] == 'orphan':
            logger.debug('[i18n] SKIP %r because orphan node: %s',
                         get_full_module_name(node), repr_domxml(node))
            return False
        return True

    if isinstance(node, nodes.meta):  # type: ignore[attr-defined]
        return True

    return False


LITERAL_TYPE_NODES = (
    nodes.literal_block,
    nodes.doctest_block,
    nodes.math_block,
    nodes.raw,
)
IMAGE_TYPE_NODES = (
    nodes.image,
)


def extract_messages(doctree: Element) -> Iterable[tuple[Element, str]]:
    """Extract translatable messages from a document tree."""
    for node in doctree.findall(is_translatable):  # type: Element
        if isinstance(node, addnodes.translatable):
            for msg in node.extract_original_messages():
                yield node, msg
            continue
        if isinstance(node, LITERAL_TYPE_NODES):
            msg = node.rawsource
            if not msg:
                msg = node.astext()
        elif isinstance(node, nodes.image):
            if node.get('alt'):
                yield node, node['alt']
            if node.get('translatable'):
                image_uri = node.get('original_uri', node['uri'])
                msg = f'.. image:: {image_uri}'
            else:
                msg = ''
        elif isinstance(node, nodes.meta):  # type: ignore[attr-defined]
            msg = node["content"]
        else:
            msg = node.rawsource.replace('\n', ' ').strip()

        # XXX nodes rendering empty are likely a bug in sphinx.addnodes
        if msg:
            yield node, msg


def get_node_source(node: Element) -> str:
    for pnode in traverse_parent(node):
        if pnode.source:
            return pnode.source
    msg = 'node source not found'
    raise ValueError(msg)


def get_node_line(node: Element) -> int:
    for pnode in traverse_parent(node):
        if pnode.line:
            return pnode.line
    msg = 'node line not found'
    raise ValueError(msg)


def traverse_parent(node: Element, cls: Any = None) -> Iterable[Element]:
    while node:
        if cls is None or isinstance(node, cls):
            yield node
        node = node.parent


def get_prev_node(node: Node) -> Node | None:
    pos = node.parent.index(node)
    if pos > 0:
        return node.parent[pos - 1]
    else:
        return None


def traverse_translatable_index(
    doctree: Element,
) -> Iterable[tuple[Element, list[tuple[str, str, str, str, str | None]]]]:
    """Traverse translatable index node from a document tree."""
    matcher = NodeMatcher(addnodes.index, inline=False)
    for node in doctree.findall(matcher):  # type: addnodes.index
        if 'raw_entries' in node:
            entries = node['raw_entries']
        else:
            entries = node['entries']
        yield node, entries


def nested_parse_with_titles(state: Any, content: StringList, node: Node,
                             content_offset: int = 0) -> str:
    """Version of state.nested_parse() that allows titles and does not require
    titles to have the same decoration as the calling document.

    This is useful when the parsed content comes from a completely different
    context, such as docstrings.
    """
    # hack around title style bookkeeping
    surrounding_title_styles = state.memo.title_styles
    surrounding_section_level = state.memo.section_level
    state.memo.title_styles = []
    state.memo.section_level = 0
    try:
        return state.nested_parse(content, content_offset, node, match_titles=1)
    finally:
        state.memo.title_styles = surrounding_title_styles
        state.memo.section_level = surrounding_section_level


def clean_astext(node: Element) -> str:
    """Like node.astext(), but ignore images."""
    node = node.deepcopy()
    for img in node.findall(nodes.image):
        img['alt'] = ''
    for raw in list(node.findall(nodes.raw)):
        raw.parent.remove(raw)
    return node.astext()


def split_explicit_title(text: str) -> tuple[bool, str, str]:
    """Split role content into title and target, if given."""
    match = explicit_title_re.match(text)
    if match:
        return True, match.group(1), match.group(2)
    return False, text, text


indextypes = [
    'single', 'pair', 'double', 'triple', 'see', 'seealso',
]


def process_index_entry(entry: str, targetid: str,
                        ) -> list[tuple[str, str, str, str, str | None]]:
    from sphinx.domains.python import pairindextypes

    indexentries: list[tuple[str, str, str, str, str | None]] = []
    entry = entry.strip()
    oentry = entry
    main = ''
    if entry.startswith('!'):
        main = 'main'
        entry = entry[1:].lstrip()
    for index_type in pairindextypes:
        if entry.startswith(f'{index_type}:'):
            value = entry[len(index_type) + 1:].strip()
            value = f'{pairindextypes[index_type]}; {value}'
            # xref RemovedInSphinx90Warning
            logger.warning(__('%r is deprecated for index entries (from entry %r). '
                              "Use 'pair: %s' instead."),
                           index_type, entry, value, type='index')
            indexentries.append(('pair', value, targetid, main, None))
            break
    else:
        for index_type in indextypes:
            if entry.startswith(f'{index_type}:'):
                value = entry[len(index_type) + 1:].strip()
                if index_type == 'double':
                    index_type = 'pair'
                indexentries.append((index_type, value, targetid, main, None))
                break
        # shorthand notation for single entries
        else:
            for value in oentry.split(','):
                value = value.strip()
                main = ''
                if value.startswith('!'):
                    main = 'main'
                    value = value[1:].lstrip()
                if not value:
                    continue
                indexentries.append(('single', value, targetid, main, None))
    return indexentries


def inline_all_toctrees(builder: Builder, docnameset: set[str], docname: str,
                        tree: nodes.document, colorfunc: Callable, traversed: list[str],
                        ) -> nodes.document:
    """Inline all toctrees in the *tree*.

    Record all docnames in *docnameset*, and output docnames with *colorfunc*.
    """
    tree = tree.deepcopy()
    for toctreenode in list(tree.findall(addnodes.toctree)):
        newnodes = []
        includefiles = map(str, toctreenode['includefiles'])
        for includefile in includefiles:
            if includefile not in traversed:
                try:
                    traversed.append(includefile)
                    logger.info(colorfunc(includefile) + " ", nonl=True)
                    subtree = inline_all_toctrees(builder, docnameset, includefile,
                                                  builder.env.get_doctree(includefile),
                                                  colorfunc, traversed)
                    docnameset.add(includefile)
                except Exception:
                    logger.warning(__('toctree contains ref to nonexisting file %r'),
                                   includefile, location=docname)
                else:
                    sof = addnodes.start_of_file(docname=includefile)
                    sof.children = subtree.children
                    for sectionnode in sof.findall(nodes.section):
                        if 'docname' not in sectionnode:
                            sectionnode['docname'] = includefile
                    newnodes.append(sof)
        toctreenode.parent.replace(toctreenode, newnodes)
    return tree


def _make_id(string: str) -> str:
    """Convert `string` into an identifier and return it.

    This function is a modified version of ``docutils.nodes.make_id()`` of
    docutils-0.16.

    Changes:

    * Allow to use capital alphabet characters
    * Allow to use dots (".") and underscores ("_") for an identifier
      without a leading character.

    # Author: David Goodger <goodger@python.org>
    # Maintainer: docutils-develop@lists.sourceforge.net
    # Copyright: This module has been placed in the public domain.
    """
    id = string.translate(_non_id_translate_digraphs)
    id = id.translate(_non_id_translate)
    # get rid of non-ascii characters.
    # 'ascii' lowercase to prevent problems with turkish locale.
    id = unicodedata.normalize('NFKD', id).encode('ascii', 'ignore').decode('ascii')
    # shrink runs of whitespace and replace by hyphen
    id = _non_id_chars.sub('-', ' '.join(id.split()))
    id = _non_id_at_ends.sub('', id)
    return str(id)


_non_id_chars = re.compile('[^a-zA-Z0-9._]+')
_non_id_at_ends = re.compile('^[-0-9._]+|-+$')
_non_id_translate = {
    0x00f8: 'o',       # o with stroke
    0x0111: 'd',       # d with stroke
    0x0127: 'h',       # h with stroke
    0x0131: 'i',       # dotless i
    0x0142: 'l',       # l with stroke
    0x0167: 't',       # t with stroke
    0x0180: 'b',       # b with stroke
    0x0183: 'b',       # b with topbar
    0x0188: 'c',       # c with hook
    0x018c: 'd',       # d with topbar
    0x0192: 'f',       # f with hook
    0x0199: 'k',       # k with hook
    0x019a: 'l',       # l with bar
    0x019e: 'n',       # n with long right leg
    0x01a5: 'p',       # p with hook
    0x01ab: 't',       # t with palatal hook
    0x01ad: 't',       # t with hook
    0x01b4: 'y',       # y with hook
    0x01b6: 'z',       # z with stroke
    0x01e5: 'g',       # g with stroke
    0x0225: 'z',       # z with hook
    0x0234: 'l',       # l with curl
    0x0235: 'n',       # n with curl
    0x0236: 't',       # t with curl
    0x0237: 'j',       # dotless j
    0x023c: 'c',       # c with stroke
    0x023f: 's',       # s with swash tail
    0x0240: 'z',       # z with swash tail
    0x0247: 'e',       # e with stroke
    0x0249: 'j',       # j with stroke
    0x024b: 'q',       # q with hook tail
    0x024d: 'r',       # r with stroke
    0x024f: 'y',       # y with stroke
}
_non_id_translate_digraphs = {
    0x00df: 'sz',      # ligature sz
    0x00e6: 'ae',      # ae
    0x0153: 'oe',      # ligature oe
    0x0238: 'db',      # db digraph
    0x0239: 'qp',      # qp digraph
}


def make_id(env: BuildEnvironment, document: nodes.document,
            prefix: str = '', term: str | None = None) -> str:
    """Generate an appropriate node_id for given *prefix* and *term*."""
    node_id = None
    if prefix:
        idformat = prefix + "-%s"
    else:
        idformat = (document.settings.id_prefix or "id") + "%s"

    # try to generate node_id by *term*
    if prefix and term:
        node_id = _make_id(idformat % term)
        if node_id == prefix:
            # *term* is not good to generate a node_id.
            node_id = None
    elif term:
        node_id = _make_id(term)
        if node_id == '':
            node_id = None  # fallback to None

    while node_id is None or node_id in document.ids:
        node_id = idformat % env.new_serialno(prefix)

    return node_id


def find_pending_xref_condition(node: addnodes.pending_xref, condition: str,
                                ) -> Element | None:
    """Pick matched pending_xref_condition node up from the pending_xref."""
    for subnode in node:
        if (isinstance(subnode, addnodes.pending_xref_condition) and
                subnode.get('condition') == condition):
            return subnode
    return None


def make_refnode(builder: Builder, fromdocname: str, todocname: str, targetid: str | None,
                 child: Node | list[Node], title: str | None = None,
                 ) -> nodes.reference:
    """Shortcut to create a reference node."""
    node = nodes.reference('', '', internal=True)
    if fromdocname == todocname and targetid:
        node['refid'] = targetid
    else:
        if targetid:
            node['refuri'] = (builder.get_relative_uri(fromdocname, todocname) +
                              '#' + targetid)
        else:
            node['refuri'] = builder.get_relative_uri(fromdocname, todocname)
    if title:
        node['reftitle'] = title
    node += child
    return node


def set_source_info(directive: Directive, node: Node) -> None:
    node.source, node.line = \
        directive.state_machine.get_source_and_line(directive.lineno)


def set_role_source_info(inliner: Inliner, lineno: int, node: Node) -> None:
    gsal = inliner.reporter.get_source_and_line  # type: ignore[attr-defined]
    node.source, node.line = gsal(lineno)


def copy_source_info(src: Element, dst: Element) -> None:
    with contextlib.suppress(ValueError):
        dst.source = get_node_source(src)
        dst.line = get_node_line(src)


NON_SMARTQUOTABLE_PARENT_NODES = (
    nodes.FixedTextElement,
    nodes.literal,
    nodes.math,
    nodes.image,
    nodes.raw,
    nodes.problematic,
    addnodes.not_smartquotable,
)


def is_smartquotable(node: Node) -> bool:
    """Check whether the node is smart-quotable or not."""
    for pnode in traverse_parent(node.parent):
        if isinstance(pnode, NON_SMARTQUOTABLE_PARENT_NODES):
            return False
        if pnode.get('support_smartquotes', None) is False:
            return False

    if getattr(node, 'support_smartquotes', None) is False:
        return False

    return True


def process_only_nodes(document: Node, tags: Tags) -> None:
    """Filter ``only`` nodes which do not match *tags*."""
    for node in document.findall(addnodes.only):
        if _only_node_keep_children(node, tags):
            node.replace_self(node.children or nodes.comment())
        else:
            # A comment on the comment() nodes being inserted: replacing by [] would
            # result in a "Losing ids" exception if there is a target node before
            # the only node, so we make sure docutils can transfer the id to
            # something, even if it's just a comment and will lose the id anyway...
            node.replace_self(nodes.comment())


def _only_node_keep_children(node: addnodes.only, tags: Tags) -> bool:
    """Keep children if tags match or error."""
    try:
        return tags.eval_condition(node['expr'])
    except Exception as err:
        logger.warning(
            __('exception while evaluating only directive expression: %s'),
            err,
            location=node)
        return True


def _copy_except__document(el: Element) -> Element:
    """Monkey-patch ```nodes.Element.copy``` to not copy the ``_document``
    attribute.

    xref: https://github.com/sphinx-doc/sphinx/issues/11116#issuecomment-1376767086
    """
    newnode = object.__new__(el.__class__)
    # set in Element.__init__()
    newnode.children = []
    newnode.rawsource = el.rawsource
    newnode.tagname = el.tagname
    # copied in Element.copy()
    newnode.attributes = {k: (v
                              if k not in {'ids', 'classes', 'names', 'dupnames', 'backrefs'}
                              else v[:])
                          for k, v in el.attributes.items()}
    newnode.line = el.line
    newnode.source = el.source
    return newnode


nodes.Element.copy = _copy_except__document  # type: ignore[assignment]


def _deepcopy(el: Element) -> Element:
    """Monkey-patch ```nodes.Element.deepcopy``` for speed."""
    newnode = el.copy()
    newnode.children = [child.deepcopy() for child in el.children]
    for child in newnode.children:
        child.parent = newnode
        if el.document:
            child.document = el.document
            if child.source is None:
                child.source = el.document.current_source
            if child.line is None:
                child.line = el.document.current_line
    return newnode


nodes.Element.deepcopy = _deepcopy  # type: ignore[assignment]
