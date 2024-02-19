"""Docutils transforms used by Sphinx when reading documents."""

from __future__ import annotations

import re
import unicodedata
from typing import TYPE_CHECKING, Any, cast

from docutils import nodes
from docutils.transforms import Transform, Transformer
from docutils.transforms.parts import ContentsFilter
from docutils.transforms.universal import SmartQuotes
from docutils.utils import normalize_language_tag
from docutils.utils.smartquotes import smartchars

from sphinx import addnodes
from sphinx.locale import _, __
from sphinx.util import logging
from sphinx.util.docutils import new_document
from sphinx.util.i18n import format_date
from sphinx.util.nodes import apply_source_workaround, is_smartquotable

if TYPE_CHECKING:
    from collections.abc import Generator

    from docutils.nodes import Node, Text

    from sphinx.application import Sphinx
    from sphinx.config import Config
    from sphinx.domains.std import StandardDomain
    from sphinx.environment import BuildEnvironment


logger = logging.getLogger(__name__)

default_substitutions = {
    'version',
    'release',
    'today',
    'translation progress',
}


class SphinxTransform(Transform):
    """A base class of Transforms.

    Compared with ``docutils.transforms.Transform``, this class improves accessibility to
    Sphinx APIs.
    """

    @property
    def app(self) -> Sphinx:
        """Reference to the :class:`.Sphinx` object."""
        return self.env.app

    @property
    def env(self) -> BuildEnvironment:
        """Reference to the :class:`.BuildEnvironment` object."""
        return self.document.settings.env

    @property
    def config(self) -> Config:
        """Reference to the :class:`.Config` object."""
        return self.env.config


class SphinxTransformer(Transformer):
    """
    A transformer for Sphinx.
    """

    document: nodes.document
    env: BuildEnvironment | None = None

    def set_environment(self, env: BuildEnvironment) -> None:
        self.env = env

    def apply_transforms(self) -> None:
        if isinstance(self.document, nodes.document):
            if not hasattr(self.document.settings, 'env') and self.env:
                self.document.settings.env = self.env

            super().apply_transforms()
        else:
            # wrap the target node by document node during transforming
            try:
                document = new_document('')
                if self.env:
                    document.settings.env = self.env
                document += self.document
                self.document = document
                super().apply_transforms()
            finally:
                self.document = self.document[0]


class DefaultSubstitutions(SphinxTransform):
    """
    Replace some substitutions if they aren't defined in the document.
    """
    # run before the default Substitutions
    default_priority = 210

    def apply(self, **kwargs: Any) -> None:
        # only handle those not otherwise defined in the document
        to_handle = default_substitutions - set(self.document.substitution_defs)
        for ref in self.document.findall(nodes.substitution_reference):
            refname = ref['refname']
            if refname in to_handle:
                if refname == 'translation progress':
                    # special handling: calculate translation progress
                    text = _calculate_translation_progress(self.document)
                else:
                    text = self.config[refname]
                if refname == 'today' and not text:
                    # special handling: can also specify a strftime format
                    text = format_date(self.config.today_fmt or _('%b %d, %Y'),
                                       language=self.config.language)
                ref.replace_self(nodes.Text(text))


def _calculate_translation_progress(document: nodes.document) -> str:
    try:
        translation_progress = document['translation_progress']
    except KeyError:
        return _('could not calculate translation progress!')

    total = translation_progress['total']
    translated = translation_progress['translated']
    if total <= 0:
        return _('no translated elements!')
    return f'{translated / total:.2%}'


class MoveModuleTargets(SphinxTransform):
    """
    Move module targets that are the first thing in a section to the section
    title.

    XXX Python specific
    """
    default_priority = 210

    def apply(self, **kwargs: Any) -> None:
        for node in list(self.document.findall(nodes.target)):
            if not node['ids']:
                continue
            if (
                'ismod' in node
                and type(node.parent) is nodes.section
                # index 0: section title node
                # index 1: index node
                # index 2: target node
                and node.parent.index(node) == 2
            ):
                node.parent['ids'][0:0] = node['ids']
                node.parent.remove(node)


class HandleCodeBlocks(SphinxTransform):
    """
    Several code block related transformations.
    """
    default_priority = 210

    def apply(self, **kwargs: Any) -> None:
        # move doctest blocks out of blockquotes
        for node in self.document.findall(nodes.block_quote):
            if all(isinstance(child, nodes.doctest_block) for child
                   in node.children):
                node.replace_self(node.children)
        # combine successive doctest blocks
        # for node in self.document.findall(nodes.doctest_block):
        #    if node not in node.parent.children:
        #        continue
        #    parindex = node.parent.index(node)
        #    while len(node.parent) > parindex+1 and \
        #            isinstance(node.parent[parindex+1], nodes.doctest_block):
        #        node[0] = nodes.Text(node[0] + '\n\n' +
        #                             node.parent[parindex+1][0])
        #        del node.parent[parindex+1]


class AutoNumbering(SphinxTransform):
    """
    Register IDs of tables, figures and literal_blocks to assign numbers.
    """
    default_priority = 210

    def apply(self, **kwargs: Any) -> None:
        domain: StandardDomain = self.env.domains['std']

        for node in self.document.findall(nodes.Element):
            if (domain.is_enumerable_node(node) and
                    domain.get_numfig_title(node) is not None and
                    node['ids'] == []):
                self.document.note_implicit_target(node)


class SortIds(SphinxTransform):
    """
    Sort section IDs so that the "id[0-9]+" one comes last.
    """
    default_priority = 261

    def apply(self, **kwargs: Any) -> None:
        for node in self.document.findall(nodes.section):
            if len(node['ids']) > 1 and node['ids'][0].startswith('id'):
                node['ids'] = node['ids'][1:] + [node['ids'][0]]


TRANSLATABLE_NODES = {
    'literal-block': nodes.literal_block,
    'doctest-block': nodes.doctest_block,
    'raw': nodes.raw,
    'index': addnodes.index,
    'image': nodes.image,
}


class ApplySourceWorkaround(SphinxTransform):
    """
    Update source and rawsource attributes
    """
    default_priority = 10

    def apply(self, **kwargs: Any) -> None:
        for node in self.document.findall():  # type: Node
            if isinstance(node, (nodes.TextElement, nodes.image, nodes.topic)):
                apply_source_workaround(node)


class AutoIndexUpgrader(SphinxTransform):
    """
    Detect old style (4 column based indices) and automatically upgrade to new style.
    """
    default_priority = 210

    def apply(self, **kwargs: Any) -> None:
        for node in self.document.findall(addnodes.index):
            if 'entries' in node and any(len(entry) == 4 for entry in node['entries']):
                msg = __('4 column based index found. '
                         'It might be a bug of extensions you use: %r') % node['entries']
                logger.warning(msg, location=node)
                for i, entry in enumerate(node['entries']):
                    if len(entry) == 4:
                        node['entries'][i] = entry + (None,)


class ExtraTranslatableNodes(SphinxTransform):
    """
    Make nodes translatable
    """
    default_priority = 10

    def apply(self, **kwargs: Any) -> None:
        targets = self.config.gettext_additional_targets
        target_nodes = [v for k, v in TRANSLATABLE_NODES.items() if k in targets]
        if not target_nodes:
            return

        def is_translatable_node(node: Node) -> bool:
            return isinstance(node, tuple(target_nodes))

        for node in self.document.findall(is_translatable_node):  # type: nodes.Element
            node['translatable'] = True


class UnreferencedFootnotesDetector(SphinxTransform):
    """
    Detect unreferenced footnotes and emit warnings
    """
    default_priority = 200

    def apply(self, **kwargs: Any) -> None:
        for node in self.document.footnotes:
            if node['names'] == []:
                # footnote having duplicated number.  It is already warned at parser.
                pass
            elif node['names'][0] not in self.document.footnote_refs:
                logger.warning(__('Footnote [%s] is not referenced.'), node['names'][0],
                               type='ref', subtype='footnote',
                               location=node)

        for node in self.document.autofootnotes:
            if not any(ref['auto'] == node['auto'] for ref in self.document.autofootnote_refs):
                logger.warning(__('Footnote [#] is not referenced.'),
                               type='ref', subtype='footnote',
                               location=node)


class DoctestTransform(SphinxTransform):
    """Set "doctest" style to each doctest_block node"""
    default_priority = 500

    def apply(self, **kwargs: Any) -> None:
        for node in self.document.findall(nodes.doctest_block):
            node['classes'].append('doctest')


class FilterSystemMessages(SphinxTransform):
    """Filter system messages from a doctree."""
    default_priority = 999

    def apply(self, **kwargs: Any) -> None:
        filterlevel = 2 if self.config.keep_warnings else 5
        for node in list(self.document.findall(nodes.system_message)):
            if node['level'] < filterlevel:
                logger.debug('%s [filtered system message]', node.astext())
                node.parent.remove(node)


class SphinxContentsFilter(ContentsFilter):
    """
    Used with BuildEnvironment.add_toc_from() to discard cross-file links
    within table-of-contents link nodes.
    """
    visit_pending_xref = ContentsFilter.ignore_node_but_process_children

    def visit_image(self, node: nodes.image) -> None:
        raise nodes.SkipNode


class SphinxSmartQuotes(SmartQuotes, SphinxTransform):
    """
    Customized SmartQuotes to avoid transform for some extra node types.

    refs: sphinx.parsers.RSTParser
    """
    default_priority = 750

    def apply(self, **kwargs: Any) -> None:
        if not self.is_available():
            return

        # override default settings with :confval:`smartquotes_action`
        self.smartquotes_action = self.config.smartquotes_action

        super().apply()

    def is_available(self) -> bool:
        builders = self.config.smartquotes_excludes.get('builders', [])
        languages = self.config.smartquotes_excludes.get('languages', [])

        if self.document.settings.smart_quotes is False:
            # disabled by 3rd party extension (workaround)
            return False
        if self.config.smartquotes is False:
            # disabled by confval smartquotes
            return False
        if self.app.builder.name in builders:
            # disabled by confval smartquotes_excludes['builders']
            return False
        if self.config.language in languages:
            # disabled by confval smartquotes_excludes['languages']
            return False

        # confirm selected language supports smart_quotes or not
        language = self.env.settings['language_code']
        return any(
            tag in smartchars.quotes
            for tag in normalize_language_tag(language)
        )

    def get_tokens(self, txtnodes: list[Text]) -> Generator[tuple[str, str], None, None]:
        # A generator that yields ``(texttype, nodetext)`` tuples for a list
        # of "Text" nodes (interface to ``smartquotes.educate_tokens()``).
        for txtnode in txtnodes:
            if is_smartquotable(txtnode):
                # SmartQuotes uses backslash escapes instead of null-escapes
                text = re.sub(r'(?<=\x00)([-\\\'".`])', r'\\\1', str(txtnode))
                yield 'plain', text
            else:
                # skip smart quotes
                yield 'literal', txtnode.astext()


class DoctreeReadEvent(SphinxTransform):
    """Emit :event:`doctree-read` event."""
    default_priority = 880

    def apply(self, **kwargs: Any) -> None:
        self.app.emit('doctree-read', self.document)


class ManpageLink(SphinxTransform):
    """Find manpage section numbers and names"""
    default_priority = 999

    def apply(self, **kwargs: Any) -> None:
        for node in self.document.findall(addnodes.manpage):
            manpage = ' '.join([str(x) for x in node.children
                                if isinstance(x, nodes.Text)])
            pattern = r'^(?P<path>(?P<page>.+)[\(\.](?P<section>[1-9]\w*)?\)?)$'
            info = {'path': manpage,
                    'page': manpage,
                    'section': ''}
            r = re.match(pattern, manpage)
            if r:
                info = r.groupdict()
            node.attributes.update(info)


class GlossarySorter(SphinxTransform):
    """Sort glossaries that have the ``sorted`` flag."""
    # This must be done after i18n, therefore not right
    # away in the glossary directive.
    default_priority = 500

    def apply(self, **kwargs: Any) -> None:
        for glossary in self.document.findall(addnodes.glossary):
            if glossary["sorted"]:
                definition_list = cast(nodes.definition_list, glossary[0])
                definition_list[:] = sorted(
                    definition_list,
                    key=lambda item: unicodedata.normalize(
                        'NFD',
                        cast(nodes.term, item)[0].astext().lower()),
                )


class ReorderConsecutiveTargetAndIndexNodes(SphinxTransform):
    """Index nodes interspersed between target nodes prevent other
    Transformations from combining those target nodes,
    e.g. ``PropagateTargets``.  This transformation reorders them:

    Given the following ``document`` as input::

        <document>
            <target ids="id1" ...>
            <index entries="...1...">
            <target ids="id2" ...>
            <target ids="id3" ...>
            <index entries="...2...">
            <target ids="id4" ...>

    The transformed result will be::

        <document>
            <index entries="...1...">
            <index entries="...2...">
            <target ids="id1" ...>
            <target ids="id2" ...>
            <target ids="id3" ...>
            <target ids="id4" ...>
    """

    # This transform MUST run before ``PropagateTargets``.
    default_priority = 220

    def apply(self, **kwargs: Any) -> None:
        for target in self.document.findall(nodes.target):
            _reorder_index_target_nodes(target)


def _reorder_index_target_nodes(start_node: nodes.target) -> None:
    """Sort target and index nodes.

    Find all consecutive target and index nodes starting from ``start_node``,
    and move all index nodes to before the first target node.
    """
    nodes_to_reorder: list[nodes.target | addnodes.index] = []

    # Note that we cannot use 'condition' to filter,
    # as we want *consecutive* target & index nodes.
    node: nodes.Node
    for node in start_node.findall(descend=False, siblings=True):
        if isinstance(node, (nodes.target, addnodes.index)):
            nodes_to_reorder.append(node)
            continue
        break  # must be a consecutive run of target or index nodes

    if len(nodes_to_reorder) < 2:
        return  # Nothing to reorder

    parent = nodes_to_reorder[0].parent
    if parent == nodes_to_reorder[-1].parent:
        first_idx = parent.index(nodes_to_reorder[0])
        last_idx = parent.index(nodes_to_reorder[-1])
        if first_idx + len(nodes_to_reorder) - 1 == last_idx:
            parent[first_idx:last_idx + 1] = sorted(nodes_to_reorder, key=_sort_key)


def _sort_key(node: nodes.Node) -> int:
    # Must be a stable sort.
    if isinstance(node, addnodes.index):
        return 0
    if isinstance(node, nodes.target):
        return 1
    msg = f'_sort_key called with unexpected node type {type(node)!r}'
    raise ValueError(msg)


def setup(app: Sphinx) -> dict[str, Any]:
    app.add_transform(ApplySourceWorkaround)
    app.add_transform(ExtraTranslatableNodes)
    app.add_transform(DefaultSubstitutions)
    app.add_transform(MoveModuleTargets)
    app.add_transform(HandleCodeBlocks)
    app.add_transform(SortIds)
    app.add_transform(DoctestTransform)
    app.add_transform(AutoNumbering)
    app.add_transform(AutoIndexUpgrader)
    app.add_transform(FilterSystemMessages)
    app.add_transform(UnreferencedFootnotesDetector)
    app.add_transform(SphinxSmartQuotes)
    app.add_transform(DoctreeReadEvent)
    app.add_transform(ManpageLink)
    app.add_transform(GlossarySorter)
    app.add_transform(ReorderConsecutiveTargetAndIndexNodes)

    return {
        'version': 'builtin',
        'parallel_read_safe': True,
        'parallel_write_safe': True,
    }
