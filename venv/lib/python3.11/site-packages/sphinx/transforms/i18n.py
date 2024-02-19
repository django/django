"""Docutils transforms used by Sphinx when reading documents."""

from __future__ import annotations

import contextlib
from os import path
from re import DOTALL, match
from textwrap import indent
from typing import TYPE_CHECKING, Any, TypeVar

from docutils import nodes
from docutils.io import StringInput

from sphinx import addnodes
from sphinx.domains.std import make_glossary_term, split_term_classifiers
from sphinx.errors import ConfigError
from sphinx.locale import __
from sphinx.locale import init as init_locale
from sphinx.transforms import SphinxTransform
from sphinx.util import get_filetype, logging
from sphinx.util.i18n import docname_to_domain
from sphinx.util.index_entries import split_index_msg
from sphinx.util.nodes import (
    IMAGE_TYPE_NODES,
    LITERAL_TYPE_NODES,
    NodeMatcher,
    extract_messages,
    traverse_translatable_index,
)

if TYPE_CHECKING:
    from collections.abc import Sequence

    from sphinx.application import Sphinx
    from sphinx.config import Config


logger = logging.getLogger(__name__)

# The attributes not copied to the translated node
#
# * refexplict: For allow to give (or not to give) an explicit title
#               to the pending_xref on translation
EXCLUDED_PENDING_XREF_ATTRIBUTES = ('refexplicit',)


N = TypeVar('N', bound=nodes.Node)


def publish_msgstr(app: Sphinx, source: str, source_path: str, source_line: int,
                   config: Config, settings: Any) -> nodes.Element:
    """Publish msgstr (single line) into docutils document

    :param sphinx.application.Sphinx app: sphinx application
    :param str source: source text
    :param str source_path: source path for warning indication
    :param source_line: source line for warning indication
    :param sphinx.config.Config config: sphinx config
    :param docutils.frontend.Values settings: docutils settings
    :return: document
    :rtype: docutils.nodes.document
    """
    try:
        # clear rst_prolog temporarily
        rst_prolog = config.rst_prolog
        config.rst_prolog = None  # type: ignore[attr-defined]

        from sphinx.io import SphinxI18nReader
        reader = SphinxI18nReader()
        reader.setup(app)
        filetype = get_filetype(config.source_suffix, source_path)
        parser = app.registry.create_source_parser(app, filetype)
        doc = reader.read(
            source=StringInput(source=source,
                               source_path=f"{source_path}:{source_line}:<translated>"),
            parser=parser,
            settings=settings,
        )
        with contextlib.suppress(IndexError):  # empty node
            return doc[0]  # type: ignore[return-value]
        return doc
    finally:
        config.rst_prolog = rst_prolog  # type: ignore[attr-defined]


def parse_noqa(source: str) -> tuple[str, bool]:
    m = match(r"(.*)(?<!\\)#\s*noqa\s*$", source, DOTALL)
    if m:
        return m.group(1), True
    else:
        return source, False


class PreserveTranslatableMessages(SphinxTransform):
    """
    Preserve original translatable messages before translation
    """
    default_priority = 10  # this MUST be invoked before Locale transform

    def apply(self, **kwargs: Any) -> None:
        for node in self.document.findall(addnodes.translatable):
            node.preserve_original_messages()


class _NodeUpdater:
    """Contains logic for updating one node with the translated content."""

    def __init__(
        self, node: nodes.Element, patch: nodes.Element, document: nodes.document, noqa: bool,
    ) -> None:
        self.node: nodes.Element = node
        self.patch: nodes.Element = patch
        self.document: nodes.document = document
        self.noqa: bool = noqa

    def compare_references(self, old_refs: Sequence[nodes.Element],
                           new_refs: Sequence[nodes.Element],
                           warning_msg: str) -> None:
        """Warn about mismatches between references in original and translated content."""
        # FIXME: could use a smarter strategy than len(old_refs) == len(new_refs)
        if not self.noqa and len(old_refs) != len(new_refs):
            old_ref_rawsources = [ref.rawsource for ref in old_refs]
            new_ref_rawsources = [ref.rawsource for ref in new_refs]
            logger.warning(warning_msg.format(old_ref_rawsources, new_ref_rawsources),
                           location=self.node, type='i18n', subtype='inconsistent_references')

    def update_title_mapping(self) -> bool:
        processed = False  # skip flag

        # update title(section) target name-id mapping
        if isinstance(self.node, nodes.title) and isinstance(self.node.parent, nodes.section):
            section_node = self.node.parent
            new_name = nodes.fully_normalize_name(self.patch.astext())
            old_name = nodes.fully_normalize_name(self.node.astext())

            if old_name != new_name:
                # if name would be changed, replace node names and
                # document nameids mapping with new name.
                names = section_node.setdefault('names', [])
                names.append(new_name)
                # Original section name (reference target name) should be kept to refer
                # from other nodes which is still not translated or uses explicit target
                # name like "`text to display <explicit target name_>`_"..
                # So, `old_name` is still exist in `names`.

                _id = self.document.nameids.get(old_name, None)
                explicit = self.document.nametypes.get(old_name, None)

                # * if explicit: _id is label. title node need another id.
                # * if not explicit:
                #
                #   * if _id is None:
                #
                #     _id is None means:
                #
                #     1. _id was not provided yet.
                #
                #     2. _id was duplicated.
                #
                #        old_name entry still exists in nameids and
                #        nametypes for another duplicated entry.
                #
                #   * if _id is provided: below process
                if _id:
                    if not explicit:
                        # _id was not duplicated.
                        # remove old_name entry from document ids database
                        # to reuse original _id.
                        self.document.nameids.pop(old_name, None)
                        self.document.nametypes.pop(old_name, None)
                        self.document.ids.pop(_id, None)

                    # re-entry with new named section node.
                    #
                    # Note: msgnode that is a second parameter of the
                    # `note_implicit_target` is not necessary here because
                    # section_node has been noted previously on rst parsing by
                    # `docutils.parsers.rst.states.RSTState.new_subsection()`
                    # and already has `system_message` if needed.
                    self.document.note_implicit_target(section_node)

                # replace target's refname to new target name
                matcher = NodeMatcher(nodes.target, refname=old_name)
                for old_target in self.document.findall(matcher):  # type: nodes.target
                    old_target['refname'] = new_name

                processed = True

        return processed

    def update_autofootnote_references(self) -> None:
        # auto-numbered foot note reference should use original 'ids'.
        def list_replace_or_append(lst: list[N], old: N, new: N) -> None:
            if old in lst:
                lst[lst.index(old)] = new
            else:
                lst.append(new)

        is_autofootnote_ref = NodeMatcher(nodes.footnote_reference, auto=Any)
        old_foot_refs: list[nodes.footnote_reference] = [
            *self.node.findall(is_autofootnote_ref)]
        new_foot_refs: list[nodes.footnote_reference] = [
            *self.patch.findall(is_autofootnote_ref)]
        self.compare_references(old_foot_refs, new_foot_refs,
                                __('inconsistent footnote references in translated message.' +
                                   ' original: {0}, translated: {1}'))
        old_foot_namerefs: dict[str, list[nodes.footnote_reference]] = {}
        for r in old_foot_refs:
            old_foot_namerefs.setdefault(r.get('refname'), []).append(r)
        for newf in new_foot_refs:
            refname = newf.get('refname')
            refs = old_foot_namerefs.get(refname, [])
            if not refs:
                newf.parent.remove(newf)
                continue

            oldf = refs.pop(0)
            newf['ids'] = oldf['ids']
            for id in newf['ids']:
                self.document.ids[id] = newf

            if newf['auto'] == 1:
                # autofootnote_refs
                list_replace_or_append(self.document.autofootnote_refs, oldf, newf)
            else:
                # symbol_footnote_refs
                list_replace_or_append(self.document.symbol_footnote_refs, oldf, newf)

            if refname:
                footnote_refs = self.document.footnote_refs.setdefault(refname, [])
                list_replace_or_append(footnote_refs, oldf, newf)

                refnames = self.document.refnames.setdefault(refname, [])
                list_replace_or_append(refnames, oldf, newf)

    def update_refnamed_references(self) -> None:
        # reference should use new (translated) 'refname'.
        # * reference target ".. _Python: ..." is not translatable.
        # * use translated refname for section refname.
        # * inline reference "`Python <...>`_" has no 'refname'.
        is_refnamed_ref = NodeMatcher(nodes.reference, refname=Any)
        old_refs: list[nodes.reference] = [*self.node.findall(is_refnamed_ref)]
        new_refs: list[nodes.reference] = [*self.patch.findall(is_refnamed_ref)]
        self.compare_references(old_refs, new_refs,
                                __('inconsistent references in translated message.' +
                                   ' original: {0}, translated: {1}'))
        old_ref_names = [r['refname'] for r in old_refs]
        new_ref_names = [r['refname'] for r in new_refs]
        orphans = [*({*old_ref_names} - {*new_ref_names})]
        for newr in new_refs:
            if not self.document.has_name(newr['refname']):
                # Maybe refname is translated but target is not translated.
                # Note: multiple translated refnames break link ordering.
                if orphans:
                    newr['refname'] = orphans.pop(0)
                else:
                    # orphan refnames is already empty!
                    # reference number is same in new_refs and old_refs.
                    pass

            self.document.note_refname(newr)

    def update_refnamed_footnote_references(self) -> None:
        # refnamed footnote should use original 'ids'.
        is_refnamed_footnote_ref = NodeMatcher(nodes.footnote_reference, refname=Any)
        old_foot_refs: list[nodes.footnote_reference] = [*self.node.findall(
            is_refnamed_footnote_ref)]
        new_foot_refs: list[nodes.footnote_reference] = [*self.patch.findall(
            is_refnamed_footnote_ref)]
        refname_ids_map: dict[str, list[str]] = {}
        self.compare_references(old_foot_refs, new_foot_refs,
                                __('inconsistent footnote references in translated message.' +
                                   ' original: {0}, translated: {1}'))
        for oldf in old_foot_refs:
            refname_ids_map.setdefault(oldf["refname"], []).append(oldf["ids"])
        for newf in new_foot_refs:
            refname = newf["refname"]
            if refname_ids_map.get(refname):
                newf["ids"] = refname_ids_map[refname].pop(0)

    def update_citation_references(self) -> None:
        # citation should use original 'ids'.
        is_citation_ref = NodeMatcher(nodes.citation_reference, refname=Any)
        old_cite_refs: list[nodes.citation_reference] = [*self.node.findall(is_citation_ref)]
        new_cite_refs: list[nodes.citation_reference] = [*self.patch.findall(is_citation_ref)]
        self.compare_references(old_cite_refs, new_cite_refs,
                                __('inconsistent citation references in translated message.' +
                                   ' original: {0}, translated: {1}'))
        refname_ids_map: dict[str, list[str]] = {}
        for oldc in old_cite_refs:
            refname_ids_map.setdefault(oldc["refname"], []).append(oldc["ids"])
        for newc in new_cite_refs:
            refname = newc["refname"]
            if refname_ids_map.get(refname):
                newc["ids"] = refname_ids_map[refname].pop()

    def update_pending_xrefs(self) -> None:
        # Original pending_xref['reftarget'] contain not-translated
        # target name, new pending_xref must use original one.
        # This code restricts to change ref-targets in the translation.
        old_xrefs = [*self.node.findall(addnodes.pending_xref)]
        new_xrefs = [*self.patch.findall(addnodes.pending_xref)]
        self.compare_references(old_xrefs, new_xrefs,
                                __('inconsistent term references in translated message.' +
                                   ' original: {0}, translated: {1}'))

        xref_reftarget_map: dict[tuple[str, str, str] | None, dict[str, Any]] = {}

        def get_ref_key(node: addnodes.pending_xref) -> tuple[str, str, str] | None:
            case = node["refdomain"], node["reftype"]
            if case == ('std', 'term'):
                return None
            else:
                return (
                    node["refdomain"],
                    node["reftype"],
                    node['reftarget'],
                )

        for old in old_xrefs:
            key = get_ref_key(old)
            if key:
                xref_reftarget_map[key] = old.attributes
        for new in new_xrefs:
            key = get_ref_key(new)
            # Copy attributes to keep original node behavior. Especially
            # copying 'reftarget', 'py:module', 'py:class' are needed.
            for k, v in xref_reftarget_map.get(key, {}).items():
                if k not in EXCLUDED_PENDING_XREF_ATTRIBUTES:
                    new[k] = v

    def update_leaves(self) -> None:
        for child in self.patch.children:
            child.parent = self.node
        self.node.children = self.patch.children


class Locale(SphinxTransform):
    """
    Replace translatable nodes with their translated doctree.
    """
    default_priority = 20

    def apply(self, **kwargs: Any) -> None:
        settings, source = self.document.settings, self.document['source']
        msgstr = ''

        textdomain = docname_to_domain(self.env.docname, self.config.gettext_compact)

        # fetch translations
        dirs = [path.join(self.env.srcdir, directory)
                for directory in self.config.locale_dirs]
        catalog, has_catalog = init_locale(dirs, self.config.language, textdomain)
        if not has_catalog:
            return

        catalogues = [getattr(catalog, '_catalog', None)]
        while (catalog := catalog._fallback) is not None:  # type: ignore[attr-defined]
            catalogues.append(getattr(catalog, '_catalog', None))
        merged: dict[str, str] = {}
        for catalogue in filter(None, reversed(catalogues)):  # type: dict[str, str]
            merged |= catalogue

        # phase1: replace reference ids with translated names
        for node, msg in extract_messages(self.document):
            msgstr = merged.get(msg, '')

            # There is no point in having #noqa on literal blocks because
            # they cannot contain references.  Recognizing it would just
            # completely prevent escaping the #noqa.  Outside of literal
            # blocks, one can always write \#noqa.
            if not isinstance(node, LITERAL_TYPE_NODES):
                msgstr, _ = parse_noqa(msgstr)

            if msgstr.strip() == '':
                # as-of-yet untranslated
                node['translated'] = False
                continue
            if msgstr == msg:
                # identical source and translated messages
                node['translated'] = True
                continue

            # Avoid "Literal block expected; none found." warnings.
            # If msgstr ends with '::' then it cause warning message at
            # parser.parse() processing.
            # literal-block-warning is only appear in avobe case.
            if msgstr.strip().endswith('::'):
                msgstr += '\n\n   dummy literal'
                # dummy literal node will discard by 'patch = patch[0]'

            # literalblock need literal block notation to avoid it become
            # paragraph.
            if isinstance(node, LITERAL_TYPE_NODES):
                msgstr = '::\n\n' + indent(msgstr, ' ' * 3)

            patch = publish_msgstr(self.app, msgstr, source,
                                   node.line, self.config, settings)
            # FIXME: no warnings about inconsistent references in this part
            # XXX doctest and other block markup
            if not isinstance(patch, nodes.paragraph):
                continue  # skip for now

            updater = _NodeUpdater(node, patch, self.document, noqa=False)
            processed = updater.update_title_mapping()

            # glossary terms update refid
            if isinstance(node, nodes.term):
                for _id in node['ids']:
                    parts = split_term_classifiers(msgstr)
                    patch = publish_msgstr(
                        self.app, parts[0] or '', source, node.line, self.config, settings,
                    )
                    updater.patch = make_glossary_term(
                        self.env, patch, parts[1] or '', source, node.line, _id, self.document,
                    )
                    processed = True

            # update leaves with processed nodes
            if processed:
                updater.update_leaves()
                node['translated'] = True  # to avoid double translation
            else:
                node['translated'] = False

        # phase2: translation
        for node, msg in extract_messages(self.document):
            if node.setdefault('translated', False):  # to avoid double translation
                continue  # skip if the node is already translated by phase1

            msgstr = merged.get(msg, '')
            noqa = False

            # See above.
            if not isinstance(node, LITERAL_TYPE_NODES):
                msgstr, noqa = parse_noqa(msgstr)

            if not msgstr or msgstr == msg:  # as-of-yet untranslated
                node['translated'] = False
                continue

            # update translatable nodes
            if isinstance(node, addnodes.translatable):
                node.apply_translated_message(msg, msgstr)  # type: ignore[attr-defined]
                continue

            # update meta nodes
            if isinstance(node, nodes.meta):  # type: ignore[attr-defined]
                node['content'] = msgstr
                node['translated'] = True
                continue

            if isinstance(node, nodes.image) and node.get('alt') == msg:
                node['alt'] = msgstr
                continue

            # Avoid "Literal block expected; none found." warnings.
            # If msgstr ends with '::' then it cause warning message at
            # parser.parse() processing.
            # literal-block-warning is only appear in avobe case.
            if msgstr.strip().endswith('::'):
                msgstr += '\n\n   dummy literal'
                # dummy literal node will discard by 'patch = patch[0]'

            # literalblock need literal block notation to avoid it become
            # paragraph.
            if isinstance(node, LITERAL_TYPE_NODES):
                msgstr = '::\n\n' + indent(msgstr, ' ' * 3)

            # Structural Subelements phase1
            # There is a possibility that only the title node is created.
            # see: https://docutils.sourceforge.io/docs/ref/doctree.html#structural-subelements
            if isinstance(node, nodes.title):
                # This generates: <section ...><title>msgstr</title></section>
                msgstr = msgstr + '\n' + '=' * len(msgstr) * 2

            patch = publish_msgstr(self.app, msgstr, source,
                                   node.line, self.config, settings)
            # Structural Subelements phase2
            if isinstance(node, nodes.title):
                # get <title> node that placed as a first child
                patch = patch.next_node()

            # ignore unexpected markups in translation message
            unexpected: tuple[type[nodes.Element], ...] = (
                nodes.paragraph,    # expected form of translation
                nodes.title,        # generated by above "Subelements phase2"
            )

            # following types are expected if
            # config.gettext_additional_targets is configured
            unexpected += LITERAL_TYPE_NODES
            unexpected += IMAGE_TYPE_NODES

            if not isinstance(patch, unexpected):
                continue  # skip

            updater = _NodeUpdater(node, patch, self.document, noqa)
            updater.update_autofootnote_references()
            updater.update_refnamed_references()
            updater.update_refnamed_footnote_references()
            updater.update_citation_references()
            updater.update_pending_xrefs()
            updater.update_leaves()

            # for highlighting that expects .rawsource and .astext() are same.
            if isinstance(node, LITERAL_TYPE_NODES):
                node.rawsource = node.astext()

            if isinstance(node, nodes.image) and node.get('alt') != msg:
                node['uri'] = patch['uri']
                node['translated'] = False
                continue  # do not mark translated

            node['translated'] = True  # to avoid double translation

        if 'index' in self.config.gettext_additional_targets:
            # Extract and translate messages for index entries.
            for node, entries in traverse_translatable_index(self.document):
                new_entries: list[tuple[str, str, str, str, str | None]] = []
                for entry_type, value, target_id, main, _category_key in entries:
                    msg_parts = split_index_msg(entry_type, value)
                    msgstr_parts = []
                    for part in msg_parts:
                        msgstr = merged.get(part, '')
                        if not msgstr:
                            msgstr = part
                        msgstr_parts.append(msgstr)

                    new_entry = entry_type, ';'.join(msgstr_parts), target_id, main, None
                    new_entries.append(new_entry)

                node['raw_entries'] = entries
                node['entries'] = new_entries


class TranslationProgressTotaliser(SphinxTransform):
    """
    Calculate the number of translated and untranslated nodes.
    """
    default_priority = 25  # MUST happen after Locale

    def apply(self, **kwargs: Any) -> None:
        from sphinx.builders.gettext import MessageCatalogBuilder
        if isinstance(self.app.builder, MessageCatalogBuilder):
            return

        total = translated = 0
        for node in self.document.findall(NodeMatcher(translated=Any)):  # type: nodes.Element
            total += 1
            if node['translated']:
                translated += 1

        self.document['translation_progress'] = {
            'total': total,
            'translated': translated,
        }


class AddTranslationClasses(SphinxTransform):
    """
    Add ``translated`` or ``untranslated`` classes to indicate translation status.
    """
    default_priority = 950

    def apply(self, **kwargs: Any) -> None:
        from sphinx.builders.gettext import MessageCatalogBuilder
        if isinstance(self.app.builder, MessageCatalogBuilder):
            return

        if not self.config.translation_progress_classes:
            return

        if self.config.translation_progress_classes is True:
            add_translated = add_untranslated = True
        elif self.config.translation_progress_classes == 'translated':
            add_translated = True
            add_untranslated = False
        elif self.config.translation_progress_classes == 'untranslated':
            add_translated = False
            add_untranslated = True
        else:
            msg = ('translation_progress_classes must be '
                   'True, False, "translated" or "untranslated"')
            raise ConfigError(msg)

        for node in self.document.findall(NodeMatcher(translated=Any)):  # type: nodes.Element
            if node['translated']:
                if add_translated:
                    node.setdefault('classes', []).append('translated')
            else:
                if add_untranslated:
                    node.setdefault('classes', []).append('untranslated')


class RemoveTranslatableInline(SphinxTransform):
    """
    Remove inline nodes used for translation as placeholders.
    """
    default_priority = 999

    def apply(self, **kwargs: Any) -> None:
        from sphinx.builders.gettext import MessageCatalogBuilder
        if isinstance(self.app.builder, MessageCatalogBuilder):
            return

        matcher = NodeMatcher(nodes.inline, translatable=Any)
        for inline in list(self.document.findall(matcher)):  # type: nodes.inline
            inline.parent.remove(inline)
            inline.parent += inline.children


def setup(app: Sphinx) -> dict[str, Any]:
    app.add_transform(PreserveTranslatableMessages)
    app.add_transform(Locale)
    app.add_transform(TranslationProgressTotaliser)
    app.add_transform(AddTranslationClasses)
    app.add_transform(RemoveTranslatableInline)

    return {
        'version': 'builtin',
        'parallel_read_safe': True,
        'parallel_write_safe': True,
    }
