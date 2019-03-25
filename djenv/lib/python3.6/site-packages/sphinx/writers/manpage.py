# -*- coding: utf-8 -*-
"""
    sphinx.writers.manpage
    ~~~~~~~~~~~~~~~~~~~~~~

    Manual page writer, extended for Sphinx custom nodes.

    :copyright: Copyright 2007-2019 by the Sphinx team, see AUTHORS.
    :license: BSD, see LICENSE for details.
"""

from docutils import nodes
from docutils.writers.manpage import (
    MACRO_DEF,
    Writer,
    Translator as BaseTranslator
)

import sphinx.util.docutils
from sphinx import addnodes
from sphinx.locale import admonitionlabels, _
from sphinx.util import logging
from sphinx.util.i18n import format_date

if False:
    # For type annotation
    from typing import Any  # NOQA
    from sphinx.builders import Builder  # NOQA

logger = logging.getLogger(__name__)


class ManualPageWriter(Writer):
    def __init__(self, builder):
        # type: (Builder) -> None
        Writer.__init__(self)
        self.builder = builder

    def translate(self):
        # type: () -> None
        transform = NestedInlineTransform(self.document)
        transform.apply()
        visitor = self.builder.create_translator(self.builder, self.document)
        self.visitor = visitor
        self.document.walkabout(visitor)
        self.output = visitor.astext()


class NestedInlineTransform(object):
    """
    Flatten nested inline nodes:

    Before:
        <strong>foo=<emphasis>1</emphasis>
        &bar=<emphasis>2</emphasis></strong>
    After:
        <strong>foo=</strong><emphasis>var</emphasis>
        <strong>&bar=</strong><emphasis>2</emphasis>
    """
    def __init__(self, document):
        # type: (nodes.document) -> None
        self.document = document

    def apply(self):
        # type: () -> None
        def is_inline(node):
            # type: (nodes.Node) -> bool
            return isinstance(node, (nodes.literal, nodes.emphasis, nodes.strong))

        for node in self.document.traverse(is_inline):
            if any(is_inline(subnode) for subnode in node):
                pos = node.parent.index(node)
                for subnode in reversed(node[1:]):
                    node.remove(subnode)
                    if is_inline(subnode):
                        node.parent.insert(pos + 1, subnode)
                    else:
                        newnode = node.__class__('', subnode, **node.attributes)
                        node.parent.insert(pos + 1, newnode)


class ManualPageTranslator(BaseTranslator):
    """
    Custom translator.
    """

    def __init__(self, builder, *args, **kwds):
        # type: (Builder, Any, Any) -> None
        BaseTranslator.__init__(self, *args, **kwds)
        self.builder = builder

        self.in_productionlist = 0

        # first title is the manpage title
        self.section_level = -1

        # docinfo set by man_pages config value
        self._docinfo['title'] = self.document.settings.title
        self._docinfo['subtitle'] = self.document.settings.subtitle
        if self.document.settings.authors:
            # don't set it if no author given
            self._docinfo['author'] = self.document.settings.authors
        self._docinfo['manual_section'] = self.document.settings.section

        # docinfo set by other config values
        self._docinfo['title_upper'] = self._docinfo['title'].upper()
        if builder.config.today:
            self._docinfo['date'] = builder.config.today
        else:
            self._docinfo['date'] = format_date(builder.config.today_fmt or _('%b %d, %Y'),
                                                language=builder.config.language)
        self._docinfo['copyright'] = builder.config.copyright
        self._docinfo['version'] = builder.config.version
        self._docinfo['manual_group'] = builder.config.project

        # In docutils < 0.11 self.append_header() was never called
        if sphinx.util.docutils.__version_info__ < (0, 11):
            self.body.append(MACRO_DEF)

        # Overwrite admonition label translations with our own
        for label, translation in admonitionlabels.items():
            self.language.labels[label] = self.deunicode(translation)

    # overwritten -- added quotes around all .TH arguments
    def header(self):
        # type: () -> unicode
        tmpl = (".TH \"%(title_upper)s\" \"%(manual_section)s\""
                " \"%(date)s\" \"%(version)s\" \"%(manual_group)s\"\n"
                ".SH NAME\n"
                "%(title)s \\- %(subtitle)s\n")
        return tmpl % self._docinfo

    def visit_start_of_file(self, node):
        # type: (nodes.Node) -> None
        pass

    def depart_start_of_file(self, node):
        # type: (nodes.Node) -> None
        pass

    def visit_desc(self, node):
        # type: (nodes.Node) -> None
        self.visit_definition_list(node)

    def depart_desc(self, node):
        # type: (nodes.Node) -> None
        self.depart_definition_list(node)

    def visit_desc_signature(self, node):
        # type: (nodes.Node) -> None
        self.visit_definition_list_item(node)
        self.visit_term(node)

    def depart_desc_signature(self, node):
        # type: (nodes.Node) -> None
        self.depart_term(node)

    def visit_desc_signature_line(self, node):
        # type: (nodes.Node) -> None
        pass

    def depart_desc_signature_line(self, node):
        # type: (nodes.Node) -> None
        self.body.append(' ')

    def visit_desc_addname(self, node):
        # type: (nodes.Node) -> None
        pass

    def depart_desc_addname(self, node):
        # type: (nodes.Node) -> None
        pass

    def visit_desc_type(self, node):
        # type: (nodes.Node) -> None
        pass

    def depart_desc_type(self, node):
        # type: (nodes.Node) -> None
        pass

    def visit_desc_returns(self, node):
        # type: (nodes.Node) -> None
        self.body.append(' -> ')

    def depart_desc_returns(self, node):
        # type: (nodes.Node) -> None
        pass

    def visit_desc_name(self, node):
        # type: (nodes.Node) -> None
        pass

    def depart_desc_name(self, node):
        # type: (nodes.Node) -> None
        pass

    def visit_desc_parameterlist(self, node):
        # type: (nodes.Node) -> None
        self.body.append('(')
        self.first_param = 1

    def depart_desc_parameterlist(self, node):
        # type: (nodes.Node) -> None
        self.body.append(')')

    def visit_desc_parameter(self, node):
        # type: (nodes.Node) -> None
        if not self.first_param:
            self.body.append(', ')
        else:
            self.first_param = 0

    def depart_desc_parameter(self, node):
        # type: (nodes.Node) -> None
        pass

    def visit_desc_optional(self, node):
        # type: (nodes.Node) -> None
        self.body.append('[')

    def depart_desc_optional(self, node):
        # type: (nodes.Node) -> None
        self.body.append(']')

    def visit_desc_annotation(self, node):
        # type: (nodes.Node) -> None
        pass

    def depart_desc_annotation(self, node):
        # type: (nodes.Node) -> None
        pass

    def visit_desc_content(self, node):
        # type: (nodes.Node) -> None
        self.visit_definition(node)

    def depart_desc_content(self, node):
        # type: (nodes.Node) -> None
        self.depart_definition(node)

    def visit_versionmodified(self, node):
        # type: (nodes.Node) -> None
        self.visit_paragraph(node)

    def depart_versionmodified(self, node):
        # type: (nodes.Node) -> None
        self.depart_paragraph(node)

    # overwritten -- don't make whole of term bold if it includes strong node
    def visit_term(self, node):
        # type: (nodes.Node) -> None
        if node.traverse(nodes.strong):
            self.body.append('\n')
        else:
            BaseTranslator.visit_term(self, node)

    # overwritten -- we don't want source comments to show up
    def visit_comment(self, node):
        # type: (nodes.Node) -> None
        raise nodes.SkipNode

    # overwritten -- added ensure_eol()
    def visit_footnote(self, node):
        # type: (nodes.Node) -> None
        self.ensure_eol()
        BaseTranslator.visit_footnote(self, node)

    # overwritten -- handle footnotes rubric
    def visit_rubric(self, node):
        # type: (nodes.Node) -> None
        self.ensure_eol()
        if len(node.children) == 1:
            rubtitle = node.children[0].astext()
            if rubtitle in ('Footnotes', _('Footnotes')):
                self.body.append('.SH ' + self.deunicode(rubtitle).upper() +
                                 '\n')
                raise nodes.SkipNode
        else:
            self.body.append('.sp\n')

    def depart_rubric(self, node):
        # type: (nodes.Node) -> None
        pass

    def visit_seealso(self, node):
        # type: (nodes.Node) -> None
        self.visit_admonition(node, 'seealso')

    def depart_seealso(self, node):
        # type: (nodes.Node) -> None
        self.depart_admonition(node)

    def visit_productionlist(self, node):
        # type: (nodes.Node) -> None
        self.ensure_eol()
        names = []
        self.in_productionlist += 1
        self.body.append('.sp\n.nf\n')
        for production in node:
            names.append(production['tokenname'])
        maxlen = max(len(name) for name in names)
        lastname = None
        for production in node:
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

    def visit_production(self, node):
        # type: (nodes.Node) -> None
        pass

    def depart_production(self, node):
        # type: (nodes.Node) -> None
        pass

    # overwritten -- don't emit a warning for images
    def visit_image(self, node):
        # type: (nodes.Node) -> None
        if 'alt' in node.attributes:
            self.body.append(_('[image: %s]') % node['alt'] + '\n')
        self.body.append(_('[image]') + '\n')
        raise nodes.SkipNode

    # overwritten -- don't visit inner marked up nodes
    def visit_reference(self, node):
        # type: (nodes.Node) -> None
        self.body.append(self.defs['reference'][0])
        # avoid repeating escaping code... fine since
        # visit_Text calls astext() and only works on that afterwards
        self.visit_Text(node)
        self.body.append(self.defs['reference'][1])

        uri = node.get('refuri', '')
        if uri.startswith('mailto:') or uri.startswith('http:') or \
           uri.startswith('https:') or uri.startswith('ftp:'):
            # if configured, put the URL after the link
            if self.builder.config.man_show_urls and \
               node.astext() != uri:
                if uri.startswith('mailto:'):
                    uri = uri[7:]
                self.body.extend([
                    ' <',
                    self.defs['strong'][0], uri, self.defs['strong'][1],
                    '>'])
        raise nodes.SkipNode

    def visit_number_reference(self, node):
        # type: (nodes.Node) -> None
        text = nodes.Text(node.get('title', '#'))
        self.visit_Text(text)
        raise nodes.SkipNode

    def visit_centered(self, node):
        # type: (nodes.Node) -> None
        self.ensure_eol()
        self.body.append('.sp\n.ce\n')

    def depart_centered(self, node):
        # type: (nodes.Node) -> None
        self.body.append('\n.ce 0\n')

    def visit_compact_paragraph(self, node):
        # type: (nodes.Node) -> None
        pass

    def depart_compact_paragraph(self, node):
        # type: (nodes.Node) -> None
        pass

    def visit_download_reference(self, node):
        # type: (nodes.Node) -> None
        pass

    def depart_download_reference(self, node):
        # type: (nodes.Node) -> None
        pass

    def visit_toctree(self, node):
        # type: (nodes.Node) -> None
        raise nodes.SkipNode

    def visit_index(self, node):
        # type: (nodes.Node) -> None
        raise nodes.SkipNode

    def visit_tabular_col_spec(self, node):
        # type: (nodes.Node) -> None
        raise nodes.SkipNode

    def visit_glossary(self, node):
        # type: (nodes.Node) -> None
        pass

    def depart_glossary(self, node):
        # type: (nodes.Node) -> None
        pass

    def visit_acks(self, node):
        # type: (nodes.Node) -> None
        self.ensure_eol()
        self.body.append(', '.join(n.astext()
                                   for n in node.children[0].children) + '.')
        self.body.append('\n')
        raise nodes.SkipNode

    def visit_hlist(self, node):
        # type: (nodes.Node) -> None
        self.visit_bullet_list(node)

    def depart_hlist(self, node):
        # type: (nodes.Node) -> None
        self.depart_bullet_list(node)

    def visit_hlistcol(self, node):
        # type: (nodes.Node) -> None
        pass

    def depart_hlistcol(self, node):
        # type: (nodes.Node) -> None
        pass

    def visit_literal_emphasis(self, node):
        # type: (nodes.Node) -> None
        return self.visit_emphasis(node)

    def depart_literal_emphasis(self, node):
        # type: (nodes.Node) -> None
        return self.depart_emphasis(node)

    def visit_literal_strong(self, node):
        # type: (nodes.Node) -> None
        return self.visit_strong(node)

    def depart_literal_strong(self, node):
        # type: (nodes.Node) -> None
        return self.depart_strong(node)

    def visit_abbreviation(self, node):
        # type: (nodes.Node) -> None
        pass

    def depart_abbreviation(self, node):
        # type: (nodes.Node) -> None
        pass

    def visit_manpage(self, node):
        # type: (nodes.Node) -> None
        return self.visit_strong(node)

    def depart_manpage(self, node):
        # type: (nodes.Node) -> None
        return self.depart_strong(node)

    # overwritten: handle section titles better than in 0.6 release
    def visit_caption(self, node):
        # type: (nodes.Element) -> None
        if isinstance(node.parent, nodes.container) and node.parent.get('literal_block'):
            self.body.append('.sp\n')
        else:
            BaseTranslator.visit_caption(self, node)

    def depart_caption(self, node):
        # type: (nodes.Element) -> None
        if isinstance(node.parent, nodes.container) and node.parent.get('literal_block'):
            self.body.append('\n')
        else:
            BaseTranslator.depart_caption(self, node)

    # overwritten: handle section titles better than in 0.6 release
    def visit_title(self, node):
        # type: (nodes.Node) -> None
        if isinstance(node.parent, addnodes.seealso):
            self.body.append('.IP "')
            return
        elif isinstance(node.parent, nodes.section):
            if self.section_level == 0:
                # skip the document title
                raise nodes.SkipNode
            elif self.section_level == 1:
                self.body.append('.SH %s\n' %
                                 self.deunicode(node.astext().upper()))
                raise nodes.SkipNode
        return BaseTranslator.visit_title(self, node)

    def depart_title(self, node):
        # type: (nodes.Node) -> None
        if isinstance(node.parent, addnodes.seealso):
            self.body.append('"\n')
            return
        return BaseTranslator.depart_title(self, node)

    def visit_raw(self, node):
        # type: (nodes.Node) -> None
        if 'manpage' in node.get('format', '').split():
            self.body.append(node.astext())
        raise nodes.SkipNode

    def visit_meta(self, node):
        # type: (nodes.Node) -> None
        raise nodes.SkipNode

    def visit_inline(self, node):
        # type: (nodes.Node) -> None
        pass

    def depart_inline(self, node):
        # type: (nodes.Node) -> None
        pass

    def visit_math(self, node):
        # type: (nodes.Node) -> None
        pass

    def depart_math(self, node):
        # type: (nodes.Node) -> None
        pass

    def visit_math_block(self, node):
        # type: (nodes.Node) -> None
        self.visit_centered(node)

    def depart_math_block(self, node):
        # type: (nodes.Node) -> None
        self.depart_centered(node)

    def unknown_visit(self, node):
        # type: (nodes.Node) -> None
        raise NotImplementedError('Unknown node: ' + node.__class__.__name__)
