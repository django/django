"""Experimental docutils writers for HTML5 handling Sphinx's custom nodes."""

from __future__ import annotations

import os
import posixpath
import re
import urllib.parse
from collections.abc import Iterable
from typing import TYPE_CHECKING, cast

from docutils import nodes
from docutils.writers.html5_polyglot import HTMLTranslator as BaseTranslator

from sphinx import addnodes
from sphinx.locale import _, __, admonitionlabels
from sphinx.util import logging
from sphinx.util.docutils import SphinxTranslator
from sphinx.util.images import get_image_size

if TYPE_CHECKING:
    from docutils.nodes import Element, Node, Text

    from sphinx.builders import Builder
    from sphinx.builders.html import StandaloneHTMLBuilder


logger = logging.getLogger(__name__)

# A good overview of the purpose behind these classes can be found here:
# http://www.arnebrodowski.de/blog/write-your-own-restructuredtext-writer.html


def multiply_length(length: str, scale: int) -> str:
    """Multiply *length* (width or height) by *scale*."""
    matched = re.match(r'^(\d*\.?\d*)\s*(\S*)$', length)
    if not matched:
        return length
    if scale == 100:
        return length
    amount, unit = matched.groups()
    result = float(amount) * scale / 100
    return f"{int(result)}{unit}"


class HTML5Translator(SphinxTranslator, BaseTranslator):
    """
    Our custom HTML translator.
    """

    builder: StandaloneHTMLBuilder
    # Override docutils.writers.html5_polyglot:HTMLTranslator
    # otherwise, nodes like <inline classes="s">...</inline> will be
    # converted to <s>...</s> by `visit_inline`.
    supported_inline_tags: set[str] = set()

    def __init__(self, document: nodes.document, builder: Builder) -> None:
        super().__init__(document, builder)

        self.highlighter = self.builder.highlighter
        self.docnames = [self.builder.current_docname]  # for singlehtml builder
        self.manpages_url = self.config.manpages_url
        self.protect_literal_text = 0
        self.secnumber_suffix = self.config.html_secnumber_suffix
        self.param_separator = ''
        self.optional_param_level = 0
        self._table_row_indices = [0]
        self._fieldlist_row_indices = [0]
        self.required_params_left = 0

    def visit_start_of_file(self, node: Element) -> None:
        # only occurs in the single-file builder
        self.docnames.append(node['docname'])
        self.body.append('<span id="document-%s"></span>' % node['docname'])

    def depart_start_of_file(self, node: Element) -> None:
        self.docnames.pop()

    #############################################################
    # Domain-specific object descriptions
    #############################################################

    # Top-level nodes for descriptions
    ##################################

    def visit_desc(self, node: Element) -> None:
        self.body.append(self.starttag(node, 'dl'))

    def depart_desc(self, node: Element) -> None:
        self.body.append('</dl>\n\n')

    def visit_desc_signature(self, node: Element) -> None:
        # the id is set automatically
        self.body.append(self.starttag(node, 'dt'))
        self.protect_literal_text += 1

    def depart_desc_signature(self, node: Element) -> None:
        self.protect_literal_text -= 1
        if not node.get('is_multiline'):
            self.add_permalink_ref(node, _('Link to this definition'))
        self.body.append('</dt>\n')

    def visit_desc_signature_line(self, node: Element) -> None:
        pass

    def depart_desc_signature_line(self, node: Element) -> None:
        if node.get('add_permalink'):
            # the permalink info is on the parent desc_signature node
            self.add_permalink_ref(node.parent, _('Link to this definition'))
        self.body.append('<br />')

    def visit_desc_content(self, node: Element) -> None:
        self.body.append(self.starttag(node, 'dd', ''))

    def depart_desc_content(self, node: Element) -> None:
        self.body.append('</dd>')

    def visit_desc_inline(self, node: Element) -> None:
        self.body.append(self.starttag(node, 'span', ''))

    def depart_desc_inline(self, node: Element) -> None:
        self.body.append('</span>')

    # Nodes for high-level structure in signatures
    ##############################################

    def visit_desc_name(self, node: Element) -> None:
        self.body.append(self.starttag(node, 'span', ''))

    def depart_desc_name(self, node: Element) -> None:
        self.body.append('</span>')

    def visit_desc_addname(self, node: Element) -> None:
        self.body.append(self.starttag(node, 'span', ''))

    def depart_desc_addname(self, node: Element) -> None:
        self.body.append('</span>')

    def visit_desc_type(self, node: Element) -> None:
        pass

    def depart_desc_type(self, node: Element) -> None:
        pass

    def visit_desc_returns(self, node: Element) -> None:
        self.body.append(' <span class="sig-return">')
        self.body.append('<span class="sig-return-icon">&#x2192;</span>')
        self.body.append(' <span class="sig-return-typehint">')

    def depart_desc_returns(self, node: Element) -> None:
        self.body.append('</span></span>')

    def _visit_sig_parameter_list(
        self,
        node: Element,
        parameter_group: type[Element],
        sig_open_paren: str,
        sig_close_paren: str,
    ) -> None:
        """Visit a signature parameters or type parameters list.

        The *parameter_group* value is the type of child nodes acting as required parameters
        or as a set of contiguous optional parameters.
        """
        self.body.append(f'<span class="sig-paren">{sig_open_paren}</span>')
        self.is_first_param = True
        self.optional_param_level = 0
        self.params_left_at_level = 0
        self.param_group_index = 0
        # Counts as what we call a parameter group either a required parameter, or a
        # set of contiguous optional ones.
        self.list_is_required_param = [isinstance(c, parameter_group) for c in node.children]
        # How many required parameters are left.
        self.required_params_left = sum(self.list_is_required_param)
        self.param_separator = node.child_text_separator
        self.multi_line_parameter_list = node.get('multi_line_parameter_list', False)
        if self.multi_line_parameter_list:
            self.body.append('\n\n')
            self.body.append(self.starttag(node, 'dl'))
            self.param_separator = self.param_separator.rstrip()
        self.context.append(sig_close_paren)

    def _depart_sig_parameter_list(self, node: Element) -> None:
        if node.get('multi_line_parameter_list'):
            self.body.append('</dl>\n\n')
        sig_close_paren = self.context.pop()
        self.body.append(f'<span class="sig-paren">{sig_close_paren}</span>')

    def visit_desc_parameterlist(self, node: Element) -> None:
        self._visit_sig_parameter_list(node, addnodes.desc_parameter, '(', ')')

    def depart_desc_parameterlist(self, node: Element) -> None:
        self._depart_sig_parameter_list(node)

    def visit_desc_type_parameter_list(self, node: Element) -> None:
        self._visit_sig_parameter_list(node, addnodes.desc_type_parameter, '[', ']')

    def depart_desc_type_parameter_list(self, node: Element) -> None:
        self._depart_sig_parameter_list(node)

    # If required parameters are still to come, then put the comma after
    # the parameter.  Otherwise, put the comma before.  This ensures that
    # signatures like the following render correctly (see issue #1001):
    #
    #     foo([a, ]b, c[, d])
    #
    def visit_desc_parameter(self, node: Element) -> None:
        on_separate_line = self.multi_line_parameter_list
        if on_separate_line and not (self.is_first_param and self.optional_param_level > 0):
            self.body.append(self.starttag(node, 'dd', ''))
        if self.is_first_param:
            self.is_first_param = False
        elif not on_separate_line and not self.required_params_left:
            self.body.append(self.param_separator)
        if self.optional_param_level == 0:
            self.required_params_left -= 1
        else:
            self.params_left_at_level -= 1
        if not node.hasattr('noemph'):
            self.body.append('<em class="sig-param">')

    def depart_desc_parameter(self, node: Element) -> None:
        if not node.hasattr('noemph'):
            self.body.append('</em>')
        is_required = self.list_is_required_param[self.param_group_index]
        if self.multi_line_parameter_list:
            is_last_group = self.param_group_index + 1 == len(self.list_is_required_param)
            next_is_required = (
                not is_last_group
                and self.list_is_required_param[self.param_group_index + 1]
            )
            opt_param_left_at_level = self.params_left_at_level > 0
            if opt_param_left_at_level or is_required and (is_last_group or next_is_required):
                self.body.append(self.param_separator)
                self.body.append('</dd>\n')

        elif self.required_params_left:
            self.body.append(self.param_separator)

        if is_required:
            self.param_group_index += 1

    def visit_desc_type_parameter(self, node: Element) -> None:
        self.visit_desc_parameter(node)

    def depart_desc_type_parameter(self, node: Element) -> None:
        self.depart_desc_parameter(node)

    def visit_desc_optional(self, node: Element) -> None:
        self.params_left_at_level = sum([isinstance(c, addnodes.desc_parameter)
                                         for c in node.children])
        self.optional_param_level += 1
        self.max_optional_param_level = self.optional_param_level
        if self.multi_line_parameter_list:
            # If the first parameter is optional, start a new line and open the bracket.
            if self.is_first_param:
                self.body.append(self.starttag(node, 'dd', ''))
                self.body.append('<span class="optional">[</span>')
            # Else, if there remains at least one required parameter, append the
            # parameter separator, open a new bracket, and end the line.
            elif self.required_params_left:
                self.body.append(self.param_separator)
                self.body.append('<span class="optional">[</span>')
                self.body.append('</dd>\n')
            # Else, open a new bracket, append the parameter separator,
            # and end the line.
            else:
                self.body.append('<span class="optional">[</span>')
                self.body.append(self.param_separator)
                self.body.append('</dd>\n')
        else:
            self.body.append('<span class="optional">[</span>')

    def depart_desc_optional(self, node: Element) -> None:
        self.optional_param_level -= 1
        if self.multi_line_parameter_list:
            # If it's the first time we go down one level, add the separator
            # before the bracket.
            if self.optional_param_level == self.max_optional_param_level - 1:
                self.body.append(self.param_separator)
            self.body.append('<span class="optional">]</span>')
            # End the line if we have just closed the last bracket of this
            # optional parameter group.
            if self.optional_param_level == 0:
                self.body.append('</dd>\n')
        else:
            self.body.append('<span class="optional">]</span>')
        if self.optional_param_level == 0:
            self.param_group_index += 1

    def visit_desc_annotation(self, node: Element) -> None:
        self.body.append(self.starttag(node, 'em', '', CLASS='property'))

    def depart_desc_annotation(self, node: Element) -> None:
        self.body.append('</em>')

    ##############################################

    def visit_versionmodified(self, node: Element) -> None:
        self.body.append(self.starttag(node, 'div', CLASS=node['type']))

    def depart_versionmodified(self, node: Element) -> None:
        self.body.append('</div>\n')

    # overwritten
    def visit_reference(self, node: Element) -> None:
        atts = {'class': 'reference'}
        if node.get('internal') or 'refuri' not in node:
            atts['class'] += ' internal'
        else:
            atts['class'] += ' external'
        if 'refuri' in node:
            atts['href'] = node['refuri'] or '#'
            if self.settings.cloak_email_addresses and atts['href'].startswith('mailto:'):
                atts['href'] = self.cloak_mailto(atts['href'])
                self.in_mailto = True
        else:
            assert 'refid' in node, \
                   'References must have "refuri" or "refid" attribute.'
            atts['href'] = '#' + node['refid']
        if not isinstance(node.parent, nodes.TextElement):
            assert len(node) == 1 and isinstance(node[0], nodes.image)  # NoQA: PT018
            atts['class'] += ' image-reference'
        if 'reftitle' in node:
            atts['title'] = node['reftitle']
        if 'target' in node:
            atts['target'] = node['target']
        self.body.append(self.starttag(node, 'a', '', **atts))

        if node.get('secnumber'):
            self.body.append(('%s' + self.secnumber_suffix) %
                             '.'.join(map(str, node['secnumber'])))

    def visit_number_reference(self, node: Element) -> None:
        self.visit_reference(node)

    def depart_number_reference(self, node: Element) -> None:
        self.depart_reference(node)

    # overwritten -- we don't want source comments to show up in the HTML
    def visit_comment(self, node: Element) -> None:  # type: ignore[override]
        raise nodes.SkipNode

    # overwritten
    def visit_admonition(self, node: Element, name: str = '') -> None:
        self.body.append(self.starttag(
            node, 'div', CLASS=('admonition ' + name)))
        if name:
            node.insert(0, nodes.title(name, admonitionlabels[name]))

    def depart_admonition(self, node: Element | None = None) -> None:
        self.body.append('</div>\n')

    def visit_seealso(self, node: Element) -> None:
        self.visit_admonition(node, 'seealso')

    def depart_seealso(self, node: Element) -> None:
        self.depart_admonition(node)

    def get_secnumber(self, node: Element) -> tuple[int, ...] | None:
        if node.get('secnumber'):
            return node['secnumber']

        if isinstance(node.parent, nodes.section):
            if self.builder.name == 'singlehtml':
                docname = self.docnames[-1]
                anchorname = "{}/#{}".format(docname, node.parent['ids'][0])
                if anchorname not in self.builder.secnumbers:
                    anchorname = "%s/" % docname  # try first heading which has no anchor
            else:
                anchorname = '#' + node.parent['ids'][0]
                if anchorname not in self.builder.secnumbers:
                    anchorname = ''  # try first heading which has no anchor

            if self.builder.secnumbers.get(anchorname):
                return self.builder.secnumbers[anchorname]

        return None

    def add_secnumber(self, node: Element) -> None:
        secnumber = self.get_secnumber(node)
        if secnumber:
            self.body.append('<span class="section-number">%s</span>' %
                             ('.'.join(map(str, secnumber)) + self.secnumber_suffix))

    def add_fignumber(self, node: Element) -> None:
        def append_fignumber(figtype: str, figure_id: str) -> None:
            if self.builder.name == 'singlehtml':
                key = f"{self.docnames[-1]}/{figtype}"
            else:
                key = figtype

            if figure_id in self.builder.fignumbers.get(key, {}):
                self.body.append('<span class="caption-number">')
                prefix = self.config.numfig_format.get(figtype)
                if prefix is None:
                    msg = __('numfig_format is not defined for %s') % figtype
                    logger.warning(msg)
                else:
                    numbers = self.builder.fignumbers[key][figure_id]
                    self.body.append(prefix % '.'.join(map(str, numbers)) + ' ')
                    self.body.append('</span>')

        figtype = self.builder.env.domains['std'].get_enumerable_node_type(node)
        if figtype:
            if len(node['ids']) == 0:
                msg = __('Any IDs not assigned for %s node') % node.tagname
                logger.warning(msg, location=node)
            else:
                append_fignumber(figtype, node['ids'][0])

    def add_permalink_ref(self, node: Element, title: str) -> None:
        icon = self.config.html_permalinks_icon
        if node['ids'] and self.config.html_permalinks and self.builder.add_permalinks:
            self.body.append(
                f'<a class="headerlink" href="#{node["ids"][0]}" title="{title}">{icon}</a>',
            )

    # overwritten
    def visit_bullet_list(self, node: Element) -> None:
        if len(node) == 1 and isinstance(node[0], addnodes.toctree):
            # avoid emitting empty <ul></ul>
            raise nodes.SkipNode
        super().visit_bullet_list(node)

    # overwritten
    def visit_definition(self, node: Element) -> None:
        # don't insert </dt> here.
        self.body.append(self.starttag(node, 'dd', ''))

    # overwritten
    def depart_definition(self, node: Element) -> None:
        self.body.append('</dd>\n')

    # overwritten
    def visit_classifier(self, node: Element) -> None:
        self.body.append(self.starttag(node, 'span', '', CLASS='classifier'))

    # overwritten
    def depart_classifier(self, node: Element) -> None:
        self.body.append('</span>')

        next_node: Node = node.next_node(descend=False, siblings=True)
        if not isinstance(next_node, nodes.classifier):
            # close `<dt>` tag at the tail of classifiers
            self.body.append('</dt>')

    # overwritten
    def visit_term(self, node: Element) -> None:
        self.body.append(self.starttag(node, 'dt', ''))

    # overwritten
    def depart_term(self, node: Element) -> None:
        next_node: Node = node.next_node(descend=False, siblings=True)
        if isinstance(next_node, nodes.classifier):
            # Leave the end tag to `self.depart_classifier()`, in case
            # there's a classifier.
            pass
        else:
            if isinstance(node.parent.parent.parent, addnodes.glossary):
                # add permalink if glossary terms
                self.add_permalink_ref(node, _('Link to this term'))

            self.body.append('</dt>')

    # overwritten
    def visit_title(self, node: Element) -> None:
        if isinstance(node.parent, addnodes.compact_paragraph) and node.parent.get('toctree'):
            self.body.append(self.starttag(node, 'p', '', CLASS='caption', ROLE='heading'))
            self.body.append('<span class="caption-text">')
            self.context.append('</span></p>\n')
        else:
            super().visit_title(node)
        self.add_secnumber(node)
        self.add_fignumber(node.parent)
        if isinstance(node.parent, nodes.table):
            self.body.append('<span class="caption-text">')

    def depart_title(self, node: Element) -> None:
        close_tag = self.context[-1]
        if (self.config.html_permalinks and self.builder.add_permalinks and
                node.parent.hasattr('ids') and node.parent['ids']):
            # add permalink anchor
            if close_tag.startswith('</h'):
                self.add_permalink_ref(node.parent, _('Link to this heading'))
            elif close_tag.startswith('</a></h'):
                self.body.append('</a><a class="headerlink" href="#%s" ' %
                                 node.parent['ids'][0] +
                                 'title="{}">{}'.format(
                                     _('Link to this heading'),
                                     self.config.html_permalinks_icon))
            elif isinstance(node.parent, nodes.table):
                self.body.append('</span>')
                self.add_permalink_ref(node.parent, _('Link to this table'))
        elif isinstance(node.parent, nodes.table):
            self.body.append('</span>')

        super().depart_title(node)

    # overwritten
    def visit_literal_block(self, node: Element) -> None:
        if node.rawsource != node.astext():
            # most probably a parsed-literal block -- don't highlight
            return super().visit_literal_block(node)

        lang = node.get('language', 'default')
        linenos = node.get('linenos', False)
        highlight_args = node.get('highlight_args', {})
        highlight_args['force'] = node.get('force', False)
        opts = self.config.highlight_options.get(lang, {})

        if linenos and self.config.html_codeblock_linenos_style:
            linenos = self.config.html_codeblock_linenos_style

        highlighted = self.highlighter.highlight_block(
            node.rawsource, lang, opts=opts, linenos=linenos,
            location=node, **highlight_args,
        )
        starttag = self.starttag(node, 'div', suffix='',
                                 CLASS='highlight-%s notranslate' % lang)
        self.body.append(starttag + highlighted + '</div>\n')
        raise nodes.SkipNode

    def visit_caption(self, node: Element) -> None:
        if isinstance(node.parent, nodes.container) and node.parent.get('literal_block'):
            self.body.append('<div class="code-block-caption">')
        else:
            super().visit_caption(node)
        self.add_fignumber(node.parent)
        self.body.append(self.starttag(node, 'span', '', CLASS='caption-text'))

    def depart_caption(self, node: Element) -> None:
        self.body.append('</span>')

        # append permalink if available
        if isinstance(node.parent, nodes.container) and node.parent.get('literal_block'):
            self.add_permalink_ref(node.parent, _('Link to this code'))
        elif isinstance(node.parent, nodes.figure):
            self.add_permalink_ref(node.parent, _('Link to this image'))
        elif node.parent.get('toctree'):
            self.add_permalink_ref(node.parent.parent, _('Link to this toctree'))

        if isinstance(node.parent, nodes.container) and node.parent.get('literal_block'):
            self.body.append('</div>\n')
        else:
            super().depart_caption(node)

    def visit_doctest_block(self, node: Element) -> None:
        self.visit_literal_block(node)

    # overwritten to add the <div> (for XHTML compliance)
    def visit_block_quote(self, node: Element) -> None:
        self.body.append(self.starttag(node, 'blockquote') + '<div>')

    def depart_block_quote(self, node: Element) -> None:
        self.body.append('</div></blockquote>\n')

    # overwritten
    def visit_literal(self, node: Element) -> None:
        if 'kbd' in node['classes']:
            self.body.append(self.starttag(node, 'kbd', '',
                                           CLASS='docutils literal notranslate'))
            return
        lang = node.get("language", None)
        if 'code' not in node['classes'] or not lang:
            self.body.append(self.starttag(node, 'code', '',
                                           CLASS='docutils literal notranslate'))
            self.protect_literal_text += 1
            return

        opts = self.config.highlight_options.get(lang, {})
        highlighted = self.highlighter.highlight_block(
            node.astext(), lang, opts=opts, location=node, nowrap=True)
        starttag = self.starttag(
            node,
            "code",
            suffix="",
            CLASS="docutils literal highlight highlight-%s" % lang,
        )
        self.body.append(starttag + highlighted.strip() + "</code>")
        raise nodes.SkipNode

    def depart_literal(self, node: Element) -> None:
        if 'kbd' in node['classes']:
            self.body.append('</kbd>')
        else:
            self.protect_literal_text -= 1
            self.body.append('</code>')

    def visit_productionlist(self, node: Element) -> None:
        self.body.append(self.starttag(node, 'pre'))
        names = []
        productionlist = cast(Iterable[addnodes.production], node)
        for production in productionlist:
            names.append(production['tokenname'])
        maxlen = max(len(name) for name in names)
        lastname = None
        for production in productionlist:
            if production['tokenname']:
                lastname = production['tokenname'].ljust(maxlen)
                self.body.append(self.starttag(production, 'strong', ''))
                self.body.append(lastname + '</strong> ::= ')
            elif lastname is not None:
                self.body.append('%s     ' % (' ' * len(lastname)))
            production.walkabout(self)
            self.body.append('\n')
        self.body.append('</pre>\n')
        raise nodes.SkipNode

    def depart_productionlist(self, node: Element) -> None:
        pass

    def visit_production(self, node: Element) -> None:
        pass

    def depart_production(self, node: Element) -> None:
        pass

    def visit_centered(self, node: Element) -> None:
        self.body.append(self.starttag(node, 'p', CLASS="centered") +
                         '<strong>')

    def depart_centered(self, node: Element) -> None:
        self.body.append('</strong></p>')

    def visit_compact_paragraph(self, node: Element) -> None:
        pass

    def depart_compact_paragraph(self, node: Element) -> None:
        pass

    def visit_download_reference(self, node: Element) -> None:
        atts = {'class': 'reference download',
                'download': ''}

        if not self.builder.download_support:
            self.context.append('')
        elif 'refuri' in node:
            atts['class'] += ' external'
            atts['href'] = node['refuri']
            self.body.append(self.starttag(node, 'a', '', **atts))
            self.context.append('</a>')
        elif 'filename' in node:
            atts['class'] += ' internal'
            atts['href'] = posixpath.join(self.builder.dlpath,
                                          urllib.parse.quote(node['filename']))
            self.body.append(self.starttag(node, 'a', '', **atts))
            self.context.append('</a>')
        else:
            self.context.append('')

    def depart_download_reference(self, node: Element) -> None:
        self.body.append(self.context.pop())

    # overwritten
    def visit_figure(self, node: Element) -> None:
        # set align=default if align not specified to give a default style
        node.setdefault('align', 'default')

        return super().visit_figure(node)

    # overwritten
    def visit_image(self, node: Element) -> None:
        olduri = node['uri']
        # rewrite the URI if the environment knows about it
        if olduri in self.builder.images:
            node['uri'] = posixpath.join(self.builder.imgpath,
                                         urllib.parse.quote(self.builder.images[olduri]))

        if 'scale' in node:
            # Try to figure out image height and width.  Docutils does that too,
            # but it tries the final file name, which does not necessarily exist
            # yet at the time the HTML file is written.
            if not ('width' in node and 'height' in node):
                path = os.path.join(self.builder.srcdir, olduri)  # type: ignore[has-type]
                size = get_image_size(path)
                if size is None:
                    logger.warning(
                        __('Could not obtain image size. :scale: option is ignored.'),
                        location=node,
                    )
                else:
                    if 'width' not in node:
                        node['width'] = str(size[0])
                    if 'height' not in node:
                        node['height'] = str(size[1])

        uri = node['uri']
        if uri.lower().endswith(('svg', 'svgz')):
            atts = {'src': uri}
            if 'width' in node:
                atts['width'] = node['width']
            if 'height' in node:
                atts['height'] = node['height']
            if 'scale' in node:
                if 'width' in atts:
                    atts['width'] = multiply_length(atts['width'], node['scale'])
                if 'height' in atts:
                    atts['height'] = multiply_length(atts['height'], node['scale'])
            atts['alt'] = node.get('alt', uri)
            if 'align' in node:
                atts['class'] = 'align-%s' % node['align']
            self.body.append(self.emptytag(node, 'img', '', **atts))
            return

        super().visit_image(node)

    # overwritten
    def depart_image(self, node: Element) -> None:
        if node['uri'].lower().endswith(('svg', 'svgz')):
            pass
        else:
            super().depart_image(node)

    def visit_toctree(self, node: Element) -> None:
        # this only happens when formatting a toc from env.tocs -- in this
        # case we don't want to include the subtree
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
        pass

    def depart_acks(self, node: Element) -> None:
        pass

    def visit_hlist(self, node: Element) -> None:
        self.body.append('<table class="hlist"><tr>')

    def depart_hlist(self, node: Element) -> None:
        self.body.append('</tr></table>\n')

    def visit_hlistcol(self, node: Element) -> None:
        self.body.append('<td>')

    def depart_hlistcol(self, node: Element) -> None:
        self.body.append('</td>')

    # overwritten
    def visit_Text(self, node: Text) -> None:
        text = node.astext()
        encoded = self.encode(text)
        if self.protect_literal_text:
            # moved here from base class's visit_literal to support
            # more formatting in literal nodes
            for token in self.words_and_spaces.findall(encoded):
                if token.strip():
                    # protect literal text from line wrapping
                    self.body.append('<span class="pre">%s</span>' % token)
                elif token in ' \n':
                    # allow breaks at whitespace
                    self.body.append(token)
                else:
                    # protect runs of multiple spaces; the last one can wrap
                    self.body.append('&#160;' * (len(token) - 1) + ' ')
        else:
            if self.in_mailto and self.settings.cloak_email_addresses:
                encoded = self.cloak_email(encoded)
            self.body.append(encoded)

    def visit_note(self, node: Element) -> None:
        self.visit_admonition(node, 'note')

    def depart_note(self, node: Element) -> None:
        self.depart_admonition(node)

    def visit_warning(self, node: Element) -> None:
        self.visit_admonition(node, 'warning')

    def depart_warning(self, node: Element) -> None:
        self.depart_admonition(node)

    def visit_attention(self, node: Element) -> None:
        self.visit_admonition(node, 'attention')

    def depart_attention(self, node: Element) -> None:
        self.depart_admonition(node)

    def visit_caution(self, node: Element) -> None:
        self.visit_admonition(node, 'caution')

    def depart_caution(self, node: Element) -> None:
        self.depart_admonition(node)

    def visit_danger(self, node: Element) -> None:
        self.visit_admonition(node, 'danger')

    def depart_danger(self, node: Element) -> None:
        self.depart_admonition(node)

    def visit_error(self, node: Element) -> None:
        self.visit_admonition(node, 'error')

    def depart_error(self, node: Element) -> None:
        self.depart_admonition(node)

    def visit_hint(self, node: Element) -> None:
        self.visit_admonition(node, 'hint')

    def depart_hint(self, node: Element) -> None:
        self.depart_admonition(node)

    def visit_important(self, node: Element) -> None:
        self.visit_admonition(node, 'important')

    def depart_important(self, node: Element) -> None:
        self.depart_admonition(node)

    def visit_tip(self, node: Element) -> None:
        self.visit_admonition(node, 'tip')

    def depart_tip(self, node: Element) -> None:
        self.depart_admonition(node)

    def visit_literal_emphasis(self, node: Element) -> None:
        return self.visit_emphasis(node)

    def depart_literal_emphasis(self, node: Element) -> None:
        return self.depart_emphasis(node)

    def visit_literal_strong(self, node: Element) -> None:
        return self.visit_strong(node)

    def depart_literal_strong(self, node: Element) -> None:
        return self.depart_strong(node)

    def visit_abbreviation(self, node: Element) -> None:
        attrs = {}
        if node.hasattr('explanation'):
            attrs['title'] = node['explanation']
        self.body.append(self.starttag(node, 'abbr', '', **attrs))

    def depart_abbreviation(self, node: Element) -> None:
        self.body.append('</abbr>')

    def visit_manpage(self, node: Element) -> None:
        self.visit_literal_emphasis(node)
        if self.manpages_url:
            node['refuri'] = self.manpages_url.format(**node.attributes)
            self.visit_reference(node)

    def depart_manpage(self, node: Element) -> None:
        if self.manpages_url:
            self.depart_reference(node)
        self.depart_literal_emphasis(node)

    # overwritten to add even/odd classes

    def visit_table(self, node: Element) -> None:
        self._table_row_indices.append(0)

        atts = {}
        classes = [cls.strip(' \t\n') for cls in self.settings.table_style.split(',')]
        classes.insert(0, "docutils")  # compat

        # set align-default if align not specified to give a default style
        classes.append('align-%s' % node.get('align', 'default'))

        if 'width' in node:
            atts['style'] = 'width: %s' % node['width']
        tag = self.starttag(node, 'table', CLASS=' '.join(classes), **atts)
        self.body.append(tag)

    def depart_table(self, node: Element) -> None:
        self._table_row_indices.pop()
        super().depart_table(node)

    def visit_row(self, node: Element) -> None:
        self._table_row_indices[-1] += 1
        if self._table_row_indices[-1] % 2 == 0:
            node['classes'].append('row-even')
        else:
            node['classes'].append('row-odd')
        self.body.append(self.starttag(node, 'tr', ''))
        node.column = 0  # type: ignore[attr-defined]

    def visit_field_list(self, node: Element) -> None:
        self._fieldlist_row_indices.append(0)
        return super().visit_field_list(node)

    def depart_field_list(self, node: Element) -> None:
        self._fieldlist_row_indices.pop()
        return super().depart_field_list(node)

    def visit_field(self, node: Element) -> None:
        self._fieldlist_row_indices[-1] += 1
        if self._fieldlist_row_indices[-1] % 2 == 0:
            node['classes'].append('field-even')
        else:
            node['classes'].append('field-odd')

    def visit_math(self, node: Element, math_env: str = '') -> None:
        # see validate_math_renderer
        name: str = self.builder.math_renderer_name  # type: ignore[assignment]
        visit, _ = self.builder.app.registry.html_inline_math_renderers[name]
        visit(self, node)

    def depart_math(self, node: Element, math_env: str = '') -> None:
        # see validate_math_renderer
        name: str = self.builder.math_renderer_name  # type: ignore[assignment]
        _, depart = self.builder.app.registry.html_inline_math_renderers[name]
        if depart:
            depart(self, node)

    def visit_math_block(self, node: Element, math_env: str = '') -> None:
        # see validate_math_renderer
        name: str = self.builder.math_renderer_name  # type: ignore[assignment]
        visit, _ = self.builder.app.registry.html_block_math_renderers[name]
        visit(self, node)

    def depart_math_block(self, node: Element, math_env: str = '') -> None:
        # see validate_math_renderer
        name: str = self.builder.math_renderer_name  # type: ignore[assignment]
        _, depart = self.builder.app.registry.html_block_math_renderers[name]
        if depart:
            depart(self, node)

    # See Docutils r9413
    # Re-instate the footnote-reference class
    def visit_footnote_reference(self, node):
        href = '#' + node['refid']
        classes = ['footnote-reference', self.settings.footnote_references]
        self.body.append(self.starttag(node, 'a', suffix='', classes=classes,
                                       role='doc-noteref', href=href))
        self.body.append('<span class="fn-bracket">[</span>')
