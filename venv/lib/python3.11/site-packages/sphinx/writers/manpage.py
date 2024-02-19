"""Manual page writer, extended for Sphinx custom nodes."""

from __future__ import annotations

from collections.abc import Iterable
from typing import TYPE_CHECKING, Any, cast

from docutils import nodes
from docutils.writers.manpage import Translator as BaseTranslator
from docutils.writers.manpage import Writer

from sphinx import addnodes
from sphinx.locale import _, admonitionlabels
from sphinx.util import logging
from sphinx.util.docutils import SphinxTranslator
from sphinx.util.i18n import format_date
from sphinx.util.nodes import NodeMatcher

if TYPE_CHECKING:
    from docutils.nodes import Element

    from sphinx.builders import Builder

logger = logging.getLogger(__name__)


class ManualPageWriter(Writer):
    def __init__(self, builder: Builder) -> None:
        super().__init__()
        self.builder = builder

    def translate(self) -> None:
        transform = NestedInlineTransform(self.document)
        transform.apply()
        visitor = self.builder.create_translator(self.document, self.builder)
        self.visitor = cast(ManualPageTranslator, visitor)
        self.document.walkabout(visitor)
        self.output = self.visitor.astext()


class NestedInlineTransform:
    """
    Flatten nested inline nodes:

    Before:
        <strong>foo=<emphasis>1</emphasis>
        &bar=<emphasis>2</emphasis></strong>
    After:
        <strong>foo=</strong><emphasis>var</emphasis>
        <strong>&bar=</strong><emphasis>2</emphasis>
    """
    def __init__(self, document: nodes.document) -> None:
        self.document = document

    def apply(self, **kwargs: Any) -> None:
        matcher = NodeMatcher(nodes.literal, nodes.emphasis, nodes.strong)
        for node in list(self.document.findall(matcher)):  # type: nodes.TextElement
            if any(matcher(subnode) for subnode in node):
                pos = node.parent.index(node)
                for subnode in reversed(list(node)):
                    node.remove(subnode)
                    if matcher(subnode):
                        node.parent.insert(pos + 1, subnode)
                    else:
                        newnode = node.__class__('', '', subnode, **node.attributes)
                        node.parent.insert(pos + 1, newnode)
                # move node if all children became siblings of the node
                if not len(node):
                    node.parent.remove(node)


class ManualPageTranslator(SphinxTranslator, BaseTranslator):
    """
    Custom man page translator.
    """

    _docinfo: dict[str, Any] = {}

    def __init__(self, document: nodes.document, builder: Builder) -> None:
        super().__init__(document, builder)

        self.in_productionlist = 0

        # first title is the manpage title
        self.section_level = -1

        # docinfo set by man_pages config value
        self._docinfo['title'] = self.settings.title
        self._docinfo['subtitle'] = self.settings.subtitle
        if self.settings.authors:
            # don't set it if no author given
            self._docinfo['author'] = self.settings.authors
        self._docinfo['manual_section'] = self.settings.section

        # docinfo set by other config values
        self._docinfo['title_upper'] = self._docinfo['title'].upper()
        if self.config.today:
            self._docinfo['date'] = self.config.today
        else:
            self._docinfo['date'] = format_date(self.config.today_fmt or _('%b %d, %Y'),
                                                language=self.config.language)
        self._docinfo['copyright'] = self.config.copyright
        self._docinfo['version'] = self.config.version
        self._docinfo['manual_group'] = self.config.project

        # Overwrite admonition label translations with our own
        for label, translation in admonitionlabels.items():
            self.language.labels[label] = self.deunicode(translation)

    # overwritten -- added quotes around all .TH arguments
    def header(self) -> str:
        tmpl = (".TH \"%(title_upper)s\" \"%(manual_section)s\""
                " \"%(date)s\" \"%(version)s\" \"%(manual_group)s\"\n")
        if self._docinfo['subtitle']:
            tmpl += (".SH NAME\n"
                     "%(title)s \\- %(subtitle)s\n")
        return tmpl % self._docinfo

    def visit_start_of_file(self, node: Element) -> None:
        pass

    def depart_start_of_file(self, node: Element) -> None:
        pass

    #############################################################
    # Domain-specific object descriptions
    #############################################################

    # Top-level nodes for descriptions
    ##################################

    def visit_desc(self, node: Element) -> None:
        self.visit_definition_list(node)

    def depart_desc(self, node: Element) -> None:
        self.depart_definition_list(node)

    def visit_desc_signature(self, node: Element) -> None:
        self.visit_definition_list_item(node)
        self.visit_term(node)

    def depart_desc_signature(self, node: Element) -> None:
        self.depart_term(node)

    def visit_desc_signature_line(self, node: Element) -> None:
        pass

    def depart_desc_signature_line(self, node: Element) -> None:
        self.body.append(' ')

    def visit_desc_content(self, node: Element) -> None:
        self.visit_definition(node)

    def depart_desc_content(self, node: Element) -> None:
        self.depart_definition(node)

    def visit_desc_inline(self, node: Element) -> None:
        pass

    def depart_desc_inline(self, node: Element) -> None:
        pass

    # Nodes for high-level structure in signatures
    ##############################################

    def visit_desc_name(self, node: Element) -> None:
        pass

    def depart_desc_name(self, node: Element) -> None:
        pass

    def visit_desc_addname(self, node: Element) -> None:
        pass

    def depart_desc_addname(self, node: Element) -> None:
        pass

    def visit_desc_type(self, node: Element) -> None:
        pass

    def depart_desc_type(self, node: Element) -> None:
        pass

    def visit_desc_returns(self, node: Element) -> None:
        self.body.append(' -> ')

    def depart_desc_returns(self, node: Element) -> None:
        pass

    def visit_desc_parameterlist(self, node: Element) -> None:
        self.body.append('(')
        self.first_param = 1

    def depart_desc_parameterlist(self, node: Element) -> None:
        self.body.append(')')

    def visit_desc_type_parameter_list(self, node: Element) -> None:
        self.body.append('[')
        self.first_param = 1

    def depart_desc_type_parameter_list(self, node: Element) -> None:
        self.body.append(']')

    def visit_desc_parameter(self, node: Element) -> None:
        if not self.first_param:
            self.body.append(', ')
        else:
            self.first_param = 0

    def depart_desc_parameter(self, node: Element) -> None:
        pass

    def visit_desc_type_parameter(self, node: Element) -> None:
        self.visit_desc_parameter(node)

    def depart_desc_type_parameter(self, node: Element) -> None:
        self.depart_desc_parameter(node)

    def visit_desc_optional(self, node: Element) -> None:
        self.body.append('[')

    def depart_desc_optional(self, node: Element) -> None:
        self.body.append(']')

    def visit_desc_annotation(self, node: Element) -> None:
        pass

    def depart_desc_annotation(self, node: Element) -> None:
        pass

    ##############################################

    def visit_versionmodified(self, node: Element) -> None:
        self.visit_paragraph(node)

    def depart_versionmodified(self, node: Element) -> None:
        self.depart_paragraph(node)

    # overwritten -- don't make whole of term bold if it includes strong node
    def visit_term(self, node: Element) -> None:
        if any(node.findall(nodes.strong)):
            self.body.append('\n')
        else:
            super().visit_term(node)

    # overwritten -- we don't want source comments to show up
    def visit_comment(self, node: Element) -> None:  # type: ignore[override]
        raise nodes.SkipNode

    # overwritten -- added ensure_eol()
    def visit_footnote(self, node: Element) -> None:
        self.ensure_eol()
        super().visit_footnote(node)

    # overwritten -- handle footnotes rubric
    def visit_rubric(self, node: Element) -> None:
        self.ensure_eol()
        if len(node) == 1 and node.astext() in ('Footnotes', _('Footnotes')):
            self.body.append('.SH ' + self.deunicode(node.astext()).upper() + '\n')
            raise nodes.SkipNode
        self.body.append('.sp\n')

    def depart_rubric(self, node: Element) -> None:
        self.body.append('\n')

    def visit_seealso(self, node: Element) -> None:
        self.visit_admonition(node, 'seealso')

    def depart_seealso(self, node: Element) -> None:
        self.depart_admonition(node)

    def visit_productionlist(self, node: Element) -> None:
        self.ensure_eol()
        names = []
        self.in_productionlist += 1
        self.body.append('.sp\n.nf\n')
        productionlist = cast(Iterable[addnodes.production], node)
        for production in productionlist:
            names.append(production['tokenname'])
        maxlen = max(len(name) for name in names)
        lastname = None
        for production in productionlist:
            if production['tokenname']:
                lastname = production['tokenname'].ljust(maxlen)
                self.body.append(self.defs['strong'][0])
                self.body.append(self.deunicode(lastname))
                self.body.append(self.defs['strong'][1])
                self.body.append(' ::= ')
            elif lastname is not None:
                self.body.append('%s     ' % (' ' * len(lastname)))
            production.walkabout(self)
            self.body.append('\n')
        self.body.append('\n.fi\n')
        self.in_productionlist -= 1
        raise nodes.SkipNode

    def visit_production(self, node: Element) -> None:
        pass

    def depart_production(self, node: Element) -> None:
        pass

    # overwritten -- don't emit a warning for images
    def visit_image(self, node: Element) -> None:
        if 'alt' in node.attributes:
            self.body.append(_('[image: %s]') % node['alt'] + '\n')
        self.body.append(_('[image]') + '\n')
        raise nodes.SkipNode

    # overwritten -- don't visit inner marked up nodes
    def visit_reference(self, node: Element) -> None:
        self.body.append(self.defs['reference'][0])
        # avoid repeating escaping code... fine since
        # visit_Text calls astext() and only works on that afterwards
        self.visit_Text(node)  # type: ignore[arg-type]
        self.body.append(self.defs['reference'][1])

        uri = node.get('refuri', '')
        if uri.startswith(('mailto:', 'http:', 'https:', 'ftp:')):
            # if configured, put the URL after the link
            if self.config.man_show_urls and node.astext() != uri:
                if uri.startswith('mailto:'):
                    uri = uri[7:]
                self.body.extend([
                    ' <',
                    self.defs['strong'][0], uri, self.defs['strong'][1],
                    '>'])
        raise nodes.SkipNode

    def visit_number_reference(self, node: Element) -> None:
        text = nodes.Text(node.get('title', '#'))
        self.visit_Text(text)
        raise nodes.SkipNode

    def visit_centered(self, node: Element) -> None:
        self.ensure_eol()
        self.body.append('.sp\n.ce\n')

    def depart_centered(self, node: Element) -> None:
        self.body.append('\n.ce 0\n')

    def visit_compact_paragraph(self, node: Element) -> None:
        pass

    def depart_compact_paragraph(self, node: Element) -> None:
        pass

    def visit_download_reference(self, node: Element) -> None:
        pass

    def depart_download_reference(self, node: Element) -> None:
        pass

    def visit_toctree(self, node: Element) -> None:
        raise nodes.SkipNode

    def visit_index(self, node: Element) -> None:
        raise nodes.SkipNode

    def visit_tabular_col_spec(self, node: Element) -> None:
        raise nodes.SkipNode

    def visit_glossary(self, node: Element) -> None:
        pass

    def depart_glossary(self, node: Element) -> None:
        pass

    def visit_acks(self, node: Element) -> None:
        bullet_list = cast(nodes.bullet_list, node[0])
        list_items = cast(Iterable[nodes.list_item], bullet_list)
        self.ensure_eol()
        bullet_list = cast(nodes.bullet_list, node[0])
        list_items = cast(Iterable[nodes.list_item], bullet_list)
        self.body.append(', '.join(n.astext() for n in list_items) + '.')
        self.body.append('\n')
        raise nodes.SkipNode

    def visit_hlist(self, node: Element) -> None:
        self.visit_bullet_list(node)

    def depart_hlist(self, node: Element) -> None:
        self.depart_bullet_list(node)

    def visit_hlistcol(self, node: Element) -> None:
        pass

    def depart_hlistcol(self, node: Element) -> None:
        pass

    def visit_literal_emphasis(self, node: Element) -> None:
        return self.visit_emphasis(node)

    def depart_literal_emphasis(self, node: Element) -> None:
        return self.depart_emphasis(node)

    def visit_literal_strong(self, node: Element) -> None:
        return self.visit_strong(node)

    def depart_literal_strong(self, node: Element) -> None:
        return self.depart_strong(node)

    def visit_abbreviation(self, node: Element) -> None:
        pass

    def depart_abbreviation(self, node: Element) -> None:
        pass

    def visit_manpage(self, node: Element) -> None:
        return self.visit_strong(node)

    def depart_manpage(self, node: Element) -> None:
        return self.depart_strong(node)

    # overwritten: handle section titles better than in 0.6 release
    def visit_caption(self, node: Element) -> None:
        if isinstance(node.parent, nodes.container) and node.parent.get('literal_block'):
            self.body.append('.sp\n')
        else:
            super().visit_caption(node)

    def depart_caption(self, node: Element) -> None:
        if isinstance(node.parent, nodes.container) and node.parent.get('literal_block'):
            self.body.append('\n')
        else:
            super().depart_caption(node)

    # overwritten: handle section titles better than in 0.6 release
    def visit_title(self, node: Element) -> None:
        if isinstance(node.parent, addnodes.seealso):
            self.body.append('.IP "')
            return None
        elif isinstance(node.parent, nodes.section):
            if self.section_level == 0:
                # skip the document title
                raise nodes.SkipNode
            elif self.section_level == 1:
                self.body.append('.SH %s\n' %
                                 self.deunicode(node.astext().upper()))
                raise nodes.SkipNode
        return super().visit_title(node)

    def depart_title(self, node: Element) -> None:
        if isinstance(node.parent, addnodes.seealso):
            self.body.append('"\n')
            return None
        return super().depart_title(node)

    def visit_raw(self, node: Element) -> None:
        if 'manpage' in node.get('format', '').split():
            self.body.append(node.astext())
        raise nodes.SkipNode

    def visit_meta(self, node: Element) -> None:
        raise nodes.SkipNode

    def visit_inline(self, node: Element) -> None:
        pass

    def depart_inline(self, node: Element) -> None:
        pass

    def visit_math(self, node: Element) -> None:
        pass

    def depart_math(self, node: Element) -> None:
        pass

    def visit_math_block(self, node: Element) -> None:
        self.visit_centered(node)

    def depart_math_block(self, node: Element) -> None:
        self.depart_centered(node)
