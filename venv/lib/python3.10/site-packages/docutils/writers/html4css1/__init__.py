# $Id: __init__.py 9282 2022-11-28 23:55:46Z milde $
# Author: David Goodger
# Maintainer: docutils-develop@lists.sourceforge.net
# Copyright: This module has been placed in the public domain.

"""
Simple HyperText Markup Language document tree Writer.

The output conforms to the XHTML version 1.0 Transitional DTD
(*almost* strict).  The output contains a minimum of formatting
information.  The cascading style sheet "html4css1.css" is required
for proper viewing with a modern graphical browser.
"""

__docformat__ = 'reStructuredText'

import os.path
import re

from docutils import frontend, nodes, writers
from docutils.writers import _html_base
from docutils.writers._html_base import PIL, url2pathname


class Writer(writers._html_base.Writer):

    supported = ('html', 'html4', 'html4css1', 'xhtml', 'xhtml10')
    """Formats this writer supports."""

    default_stylesheets = ['html4css1.css']
    default_stylesheet_dirs = ['.',
                               os.path.abspath(os.path.dirname(__file__)),
                               os.path.abspath(os.path.join(
                                   os.path.dirname(os.path.dirname(__file__)),
                                   'html5_polyglot'))  # for math.css
                               ]
    default_template = os.path.join(
        os.path.dirname(os.path.abspath(__file__)), 'template.txt')

    # use a copy of the parent spec with some modifications
    settings_spec = frontend.filter_settings_spec(
        writers._html_base.Writer.settings_spec,
        template=(
            'Template file. (UTF-8 encoded, default: "%s")' % default_template,
            ['--template'],
            {'default': default_template, 'metavar': '<file>'}),
        stylesheet_path=(
            'Comma separated list of stylesheet paths. '
            'Relative paths are expanded if a matching file is found in '
            'the --stylesheet-dirs. With --link-stylesheet, '
            'the path is rewritten relative to the output HTML file. '
            '(default: "%s")' % ','.join(default_stylesheets),
            ['--stylesheet-path'],
            {'metavar': '<file[,file,...]>', 'overrides': 'stylesheet',
             'validator': frontend.validate_comma_separated_list,
             'default': default_stylesheets}),
        stylesheet_dirs=(
            'Comma-separated list of directories where stylesheets are found. '
            'Used by --stylesheet-path when expanding relative path '
            'arguments. (default: "%s")' % ','.join(default_stylesheet_dirs),
            ['--stylesheet-dirs'],
            {'metavar': '<dir[,dir,...]>',
             'validator': frontend.validate_comma_separated_list,
             'default': default_stylesheet_dirs}),
        initial_header_level=(
            'Specify the initial header level. Does not affect document '
            'title & subtitle (see --no-doc-title). (default: 1 for "<h1>")',
            ['--initial-header-level'],
            {'choices': '1 2 3 4 5 6'.split(), 'default': '1',
             'metavar': '<level>'}),
        xml_declaration=(
            'Prepend an XML declaration (default). ',
            ['--xml-declaration'],
            {'default': True, 'action': 'store_true',
             'validator': frontend.validate_boolean}),
        )
    settings_spec = settings_spec + (
        'HTML4 Writer Options',
        '',
        (('Specify the maximum width (in characters) for one-column field '
          'names.  Longer field names will span an entire row of the table '
          'used to render the field list.  Default is 14 characters.  '
          'Use 0 for "no limit".',
          ['--field-name-limit'],
          {'default': 14, 'metavar': '<level>',
           'validator': frontend.validate_nonnegative_int}),
         ('Specify the maximum width (in characters) for options in option '
          'lists.  Longer options will span an entire row of the table used '
          'to render the option list.  Default is 14 characters.  '
          'Use 0 for "no limit".',
          ['--option-limit'],
          {'default': 14, 'metavar': '<level>',
           'validator': frontend.validate_nonnegative_int}),
         )
        )

    config_section = 'html4css1 writer'

    def __init__(self):
        self.parts = {}
        self.translator_class = HTMLTranslator


class HTMLTranslator(writers._html_base.HTMLTranslator):
    """
    The html4css1 writer has been optimized to produce visually compact
    lists (less vertical whitespace).  HTML's mixed content models
    allow list items to contain "<li><p>body elements</p></li>" or
    "<li>just text</li>" or even "<li>text<p>and body
    elements</p>combined</li>", each with different effects.  It would
    be best to stick with strict body elements in list items, but they
    affect vertical spacing in older browsers (although they really
    shouldn't).
    The html5_polyglot writer solves this using CSS2.

    Here is an outline of the optimization:

    - Check for and omit <p> tags in "simple" lists: list items
      contain either a single paragraph, a nested simple list, or a
      paragraph followed by a nested simple list.  This means that
      this list can be compact:

          - Item 1.
          - Item 2.

      But this list cannot be compact:

          - Item 1.

            This second paragraph forces space between list items.

          - Item 2.

    - In non-list contexts, omit <p> tags on a paragraph if that
      paragraph is the only child of its parent (footnotes & citations
      are allowed a label first).

    - Regardless of the above, in definitions, table cells, field bodies,
      option descriptions, and list items, mark the first child with
      'class="first"' and the last child with 'class="last"'.  The stylesheet
      sets the margins (top & bottom respectively) to 0 for these elements.

    The ``no_compact_lists`` setting (``--no-compact-lists`` command-line
    option) disables list whitespace optimization.
    """

    # The following definitions are required for display in browsers limited
    # to CSS1 or backwards compatible behaviour of the writer:

    doctype = (
        '<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN"'
        ' "http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd">\n')

    content_type = ('<meta http-equiv="Content-Type"'
                    ' content="text/html; charset=%s" />\n')
    content_type_mathml = ('<meta http-equiv="Content-Type"'
                           ' content="application/xhtml+xml; charset=%s" />\n')

    # encode also non-breaking space
    special_characters = _html_base.HTMLTranslator.special_characters.copy()
    special_characters[0xa0] = '&nbsp;'

    # use character reference for dash (not valid in HTML5)
    attribution_formats = {'dash': ('&mdash;', ''),
                           'parentheses': ('(', ')'),
                           'parens': ('(', ')'),
                           'none': ('', '')}

    # ersatz for first/last pseudo-classes missing in CSS1
    def set_first_last(self, node):
        self.set_class_on_child(node, 'first', 0)
        self.set_class_on_child(node, 'last', -1)

    # add newline after opening tag
    def visit_address(self, node):
        self.visit_docinfo_item(node, 'address', meta=False)
        self.body.append(self.starttag(node, 'pre', CLASS='address'))

    def depart_address(self, node):
        self.body.append('\n</pre>\n')
        self.depart_docinfo_item()

    # ersatz for first/last pseudo-classes
    def visit_admonition(self, node):
        node['classes'].insert(0, 'admonition')
        self.body.append(self.starttag(node, 'div'))
        self.set_first_last(node)

    def depart_admonition(self, node=None):
        self.body.append('</div>\n')

    # author, authors: use <br> instead of paragraphs
    def visit_author(self, node):
        if isinstance(node.parent, nodes.authors):
            if self.author_in_authors:
                self.body.append('\n<br />')
        else:
            self.visit_docinfo_item(node, 'author')

    def depart_author(self, node):
        if isinstance(node.parent, nodes.authors):
            self.author_in_authors = True
        else:
            self.depart_docinfo_item()

    def visit_authors(self, node):
        self.visit_docinfo_item(node, 'authors')
        self.author_in_authors = False  # initialize

    def depart_authors(self, node):
        self.depart_docinfo_item()

    # use "width" argument instead of "style: 'width'":
    def visit_colspec(self, node):
        self.colspecs.append(node)
        # "stubs" list is an attribute of the tgroup element:
        node.parent.stubs.append(node.attributes.get('stub'))

    def depart_colspec(self, node):
        # write out <colgroup> when all colspecs are processed
        if isinstance(node.next_node(descend=False, siblings=True),
                      nodes.colspec):
            return
        if ('colwidths-auto' in node.parent.parent['classes']
            or ('colwidths-auto' in self.settings.table_style
                and 'colwidths-given' not in node.parent.parent['classes'])):
            return
        total_width = sum(node['colwidth'] for node in self.colspecs)
        self.body.append(self.starttag(node, 'colgroup'))
        for node in self.colspecs:
            colwidth = int(node['colwidth'] * 100.0 / total_width + 0.5)
            self.body.append(self.emptytag(node, 'col',
                                           width='%i%%' % colwidth))
        self.body.append('</colgroup>\n')

    # Compact lists:
    # exclude definition lists and field lists (non-compact by default)

    def is_compactable(self, node):
        return ('compact' in node['classes']
                or (self.settings.compact_lists
                    and 'open' not in node['classes']
                    and (self.compact_simple
                         or 'contents' in node.parent['classes']
                         # TODO: self.in_contents
                         or self.check_simple_list(node))))

    # citations: Use table for bibliographic references.
    def visit_citation(self, node):
        self.body.append(self.starttag(node, 'table',
                                       CLASS='docutils citation',
                                       frame="void", rules="none"))
        self.body.append('<colgroup><col class="label" /><col /></colgroup>\n'
                         '<tbody valign="top">\n'
                         '<tr>')
        self.footnote_backrefs(node)

    def depart_citation(self, node):
        self.body.append('</td></tr>\n'
                         '</tbody>\n</table>\n')

    def visit_citation_reference(self, node):
        href = '#'
        if 'refid' in node:
            href += node['refid']
        elif 'refname' in node:
            href += self.document.nameids[node['refname']]
        self.body.append(self.starttag(node, 'a', suffix='[', href=href,
                                       classes=['citation-reference']))

    def depart_citation_reference(self, node):
        self.body.append(']</a>')

    # insert classifier-delimiter (not required with CSS2)
    def visit_classifier(self, node):
        self.body.append(' <span class="classifier-delimiter">:</span> ')
        self.body.append(self.starttag(node, 'span', '', CLASS='classifier'))

    def depart_classifier(self, node):
        self.body.append('</span>')

    # ersatz for first/last pseudo-classes
    def visit_compound(self, node):
        self.body.append(self.starttag(node, 'div', CLASS='compound'))
        if len(node) > 1:
            node[0]['classes'].append('compound-first')
            node[-1]['classes'].append('compound-last')
            for child in node[1:-1]:
                child['classes'].append('compound-middle')

    def depart_compound(self, node):
        self.body.append('</div>\n')

    # ersatz for first/last pseudo-classes, no special handling of "details"
    def visit_definition(self, node):
        self.body.append('</dt>\n')
        self.body.append(self.starttag(node, 'dd', ''))
        self.set_first_last(node)

    def depart_definition(self, node):
        self.body.append('</dd>\n')

    # don't add "simple" class value, no special handling of "details"
    def visit_definition_list(self, node):
        self.body.append(self.starttag(node, 'dl', CLASS='docutils'))

    def depart_definition_list(self, node):
        self.body.append('</dl>\n')

    # no special handling of "details"
    def visit_definition_list_item(self, node):
        pass

    def depart_definition_list_item(self, node):
        pass

    # use a table for description lists
    def visit_description(self, node):
        self.body.append(self.starttag(node, 'td', ''))
        self.set_first_last(node)

    def depart_description(self, node):
        self.body.append('</td>')

    # use table for docinfo
    def visit_docinfo(self, node):
        self.context.append(len(self.body))
        self.body.append(self.starttag(node, 'table',
                                       CLASS='docinfo',
                                       frame="void", rules="none"))
        self.body.append('<col class="docinfo-name" />\n'
                         '<col class="docinfo-content" />\n'
                         '<tbody valign="top">\n')
        self.in_docinfo = True

    def depart_docinfo(self, node):
        self.body.append('</tbody>\n</table>\n')
        self.in_docinfo = False
        start = self.context.pop()
        self.docinfo = self.body[start:]
        self.body = []

    def visit_docinfo_item(self, node, name, meta=True):
        if meta:
            meta_tag = '<meta name="%s" content="%s" />\n' \
                       % (name, self.attval(node.astext()))
            self.meta.append(meta_tag)
        self.body.append(self.starttag(node, 'tr', ''))
        self.body.append('<th class="docinfo-name">%s:</th>\n<td>'
                         % self.language.labels[name])
        if len(node):
            if isinstance(node[0], nodes.Element):
                node[0]['classes'].append('first')
            if isinstance(node[-1], nodes.Element):
                node[-1]['classes'].append('last')

    def depart_docinfo_item(self):
        self.body.append('</td></tr>\n')

    # add newline after opening tag
    def visit_doctest_block(self, node):
        self.body.append(self.starttag(node, 'pre', CLASS='doctest-block'))

    def depart_doctest_block(self, node):
        self.body.append('\n</pre>\n')

    # insert an NBSP into empty cells, ersatz for first/last
    def visit_entry(self, node):
        writers._html_base.HTMLTranslator.visit_entry(self, node)
        if len(node) == 0:              # empty cell
            self.body.append('&nbsp;')
        self.set_first_last(node)

    def depart_entry(self, node):
        self.body.append(self.context.pop())

    # ersatz for first/last pseudo-classes
    def visit_enumerated_list(self, node):
        """
        The 'start' attribute does not conform to HTML 4.01's strict.dtd, but
        cannot be emulated in CSS1 (HTML 5 reincludes it).
        """
        atts = {}
        if 'start' in node:
            atts['start'] = node['start']
        if 'enumtype' in node:
            atts['class'] = node['enumtype']
        # @@@ To do: prefix, suffix. How? Change prefix/suffix to a
        # single "format" attribute? Use CSS2?
        old_compact_simple = self.compact_simple
        self.context.append((self.compact_simple, self.compact_p))
        self.compact_p = None
        self.compact_simple = self.is_compactable(node)
        if self.compact_simple and not old_compact_simple:
            atts['class'] = (atts.get('class', '') + ' simple').strip()
        self.body.append(self.starttag(node, 'ol', **atts))

    def depart_enumerated_list(self, node):
        self.compact_simple, self.compact_p = self.context.pop()
        self.body.append('</ol>\n')

    # use table for field-list:
    def visit_field(self, node):
        self.body.append(self.starttag(node, 'tr', '', CLASS='field'))

    def depart_field(self, node):
        self.body.append('</tr>\n')

    def visit_field_body(self, node):
        self.body.append(self.starttag(node, 'td', '', CLASS='field-body'))
        self.set_class_on_child(node, 'first', 0)
        field = node.parent
        if (self.compact_field_list
            or isinstance(field.parent, nodes.docinfo)
            or field.parent.index(field) == len(field.parent) - 1):
            # If we are in a compact list, the docinfo, or if this is
            # the last field of the field list, do not add vertical
            # space after last element.
            self.set_class_on_child(node, 'last', -1)

    def depart_field_body(self, node):
        self.body.append('</td>\n')

    def visit_field_list(self, node):
        self.context.append((self.compact_field_list, self.compact_p))
        self.compact_p = None
        if 'compact' in node['classes']:
            self.compact_field_list = True
        elif (self.settings.compact_field_lists
              and 'open' not in node['classes']):
            self.compact_field_list = True
        if self.compact_field_list:
            for field in node:
                field_body = field[-1]
                assert isinstance(field_body, nodes.field_body)
                children = [n for n in field_body
                            if not isinstance(n, nodes.Invisible)]
                if not (len(children) == 0
                        or len(children) == 1
                        and isinstance(children[0],
                                       (nodes.paragraph, nodes.line_block))):
                    self.compact_field_list = False
                    break
        self.body.append(self.starttag(node, 'table', frame='void',
                                       rules='none',
                                       CLASS='docutils field-list'))
        self.body.append('<col class="field-name" />\n'
                         '<col class="field-body" />\n'
                         '<tbody valign="top">\n')

    def depart_field_list(self, node):
        self.body.append('</tbody>\n</table>\n')
        self.compact_field_list, self.compact_p = self.context.pop()

    def visit_field_name(self, node):
        atts = {}
        if self.in_docinfo:
            atts['class'] = 'docinfo-name'
        else:
            atts['class'] = 'field-name'
        if (self.settings.field_name_limit
            and len(node.astext()) > self.settings.field_name_limit):
            atts['colspan'] = 2
            self.context.append('</tr>\n'
                                + self.starttag(node.parent, 'tr', '',
                                                CLASS='field')
                                + '<td>&nbsp;</td>')
        else:
            self.context.append('')
        self.body.append(self.starttag(node, 'th', '', **atts))

    def depart_field_name(self, node):
        self.body.append(':</th>')
        self.body.append(self.context.pop())

    # use table for footnote text
    def visit_footnote(self, node):
        self.body.append(self.starttag(node, 'table',
                                       CLASS='docutils footnote',
                                       frame="void", rules="none"))
        self.body.append('<colgroup><col class="label" /><col /></colgroup>\n'
                         '<tbody valign="top">\n'
                         '<tr>')
        self.footnote_backrefs(node)

    def footnote_backrefs(self, node):
        backlinks = []
        backrefs = node['backrefs']
        if self.settings.footnote_backlinks and backrefs:
            if len(backrefs) == 1:
                self.context.append('')
                self.context.append('</a>')
                self.context.append('<a class="fn-backref" href="#%s">'
                                    % backrefs[0])
            else:
                for (i, backref) in enumerate(backrefs, 1):
                    backlinks.append('<a class="fn-backref" href="#%s">%s</a>'
                                     % (backref, i))
                self.context.append('<em>(%s)</em> ' % ', '.join(backlinks))
                self.context += ['', '']
        else:
            self.context.append('')
            self.context += ['', '']
        # If the node does not only consist of a label.
        if len(node) > 1:
            # If there are preceding backlinks, we do not set class
            # 'first', because we need to retain the top-margin.
            if not backlinks:
                node[1]['classes'].append('first')
            node[-1]['classes'].append('last')

    def depart_footnote(self, node):
        self.body.append('</td></tr>\n'
                         '</tbody>\n</table>\n')

    # insert markers in text (pseudo-classes are not supported in CSS1):
    def visit_footnote_reference(self, node):
        href = '#' + node['refid']
        format = self.settings.footnote_references
        if format == 'brackets':
            suffix = '['
            self.context.append(']')
        else:
            assert format == 'superscript'
            suffix = '<sup>'
            self.context.append('</sup>')
        self.body.append(self.starttag(node, 'a', suffix,
                                       CLASS='footnote-reference', href=href))

    def depart_footnote_reference(self, node):
        self.body.append(self.context.pop() + '</a>')

    # just pass on generated text
    def visit_generated(self, node):
        pass

    # Backwards-compatibility implementation:
    # * Do not use <video>,
    # * don't embed images,
    # * use <object> instead of <img> for SVG.
    #   (SVG not supported by IE up to version 8,
    #   html4css1 strives for IE6 compatibility.)
    object_image_types = {'.svg': 'image/svg+xml',
                          '.swf': 'application/x-shockwave-flash'}

    def visit_image(self, node):
        atts = {}
        uri = node['uri']
        ext = os.path.splitext(uri)[1].lower()
        if ext in self.object_image_types:
            atts['data'] = uri
            atts['type'] = self.object_image_types[ext]
        else:
            atts['src'] = uri
            atts['alt'] = node.get('alt', uri)
        # image size
        if 'width' in node:
            atts['width'] = node['width']
        if 'height' in node:
            atts['height'] = node['height']
        if 'scale' in node:
            if (PIL and ('width' not in node or 'height' not in node)
                and self.settings.file_insertion_enabled):
                imagepath = url2pathname(uri)
                try:
                    with PIL.Image.open(imagepath) as img:
                        img_size = img.size
                except (OSError, UnicodeEncodeError):
                    pass  # TODO: warn/info?
                else:
                    self.settings.record_dependencies.add(
                        imagepath.replace('\\', '/'))
                    if 'width' not in atts:
                        atts['width'] = '%dpx' % img_size[0]
                    if 'height' not in atts:
                        atts['height'] = '%dpx' % img_size[1]
            for att_name in 'width', 'height':
                if att_name in atts:
                    match = re.match(r'([0-9.]+)(\S*)$', atts[att_name])
                    assert match
                    atts[att_name] = '%s%s' % (
                        float(match.group(1)) * (float(node['scale']) / 100),
                        match.group(2))
        style = []
        for att_name in 'width', 'height':
            if att_name in atts:
                if re.match(r'^[0-9.]+$', atts[att_name]):
                    # Interpret unitless values as pixels.
                    atts[att_name] += 'px'
                style.append('%s: %s;' % (att_name, atts[att_name]))
                del atts[att_name]
        if style:
            atts['style'] = ' '.join(style)
        if (isinstance(node.parent, nodes.TextElement)
            or (isinstance(node.parent, nodes.reference)
                and not isinstance(node.parent.parent, nodes.TextElement))):
            # Inline context or surrounded by <a>...</a>.
            suffix = ''
        else:
            suffix = '\n'
        if 'align' in node:
            atts['class'] = 'align-%s' % node['align']
        if ext in self.object_image_types:
            # do NOT use an empty tag: incorrect rendering in browsers
            self.body.append(self.starttag(node, 'object', '', **atts)
                             + node.get('alt', uri) + '</object>' + suffix)
        else:
            self.body.append(self.emptytag(node, 'img', suffix, **atts))

    def depart_image(self, node):
        pass

    # use table for footnote text,
    # context added in footnote_backrefs.
    def visit_label(self, node):
        self.body.append(self.starttag(node, 'td', '%s[' % self.context.pop(),
                                       CLASS='label'))

    def depart_label(self, node):
        self.body.append(f']{self.context.pop()}</td><td>{self.context.pop()}')

    # ersatz for first/last pseudo-classes
    def visit_list_item(self, node):
        self.body.append(self.starttag(node, 'li', ''))
        if len(node):
            node[0]['classes'].append('first')

    def depart_list_item(self, node):
        self.body.append('</li>\n')

    # use <tt> (not supported by HTML5),
    # cater for limited styling options in CSS1 using hard-coded NBSPs
    def visit_literal(self, node):
        # special case: "code" role
        classes = node['classes']
        if 'code' in classes:
            # filter 'code' from class arguments
            node['classes'] = [cls for cls in classes if cls != 'code']
            self.body.append(self.starttag(node, 'code', ''))
            return
        self.body.append(
            self.starttag(node, 'tt', '', CLASS='docutils literal'))
        text = node.astext()
        for token in self.words_and_spaces.findall(text):
            if token.strip():
                # Protect text like "--an-option" and the regular expression
                # ``[+]?(\d+(\.\d*)?|\.\d+)`` from bad line wrapping
                if self.in_word_wrap_point.search(token):
                    self.body.append('<span class="pre">%s</span>'
                                     % self.encode(token))
                else:
                    self.body.append(self.encode(token))
            elif token in ('\n', ' '):
                # Allow breaks at whitespace:
                self.body.append(token)
            else:
                # Protect runs of multiple spaces; the last space can wrap:
                self.body.append('&nbsp;' * (len(token) - 1) + ' ')
        self.body.append('</tt>')
        # Content already processed:
        raise nodes.SkipNode

    def depart_literal(self, node):
        # skipped unless literal element is from "code" role:
        self.body.append('</code>')

    # add newline after wrapper tags, don't use <code> for code
    def visit_literal_block(self, node):
        self.body.append(self.starttag(node, 'pre', CLASS='literal-block'))

    def depart_literal_block(self, node):
        self.body.append('\n</pre>\n')

    # use table for option list
    def visit_option_group(self, node):
        atts = {}
        if (self.settings.option_limit
            and len(node.astext()) > self.settings.option_limit):
            atts['colspan'] = 2
            self.context.append('</tr>\n<tr><td>&nbsp;</td>')
        else:
            self.context.append('')
        self.body.append(
            self.starttag(node, 'td', CLASS='option-group', **atts))
        self.body.append('<kbd>')
        self.context.append(0)          # count number of options

    def depart_option_group(self, node):
        self.context.pop()
        self.body.append('</kbd></td>\n')
        self.body.append(self.context.pop())

    def visit_option_list(self, node):
        self.body.append(
              self.starttag(node, 'table', CLASS='docutils option-list',
                            frame="void", rules="none"))
        self.body.append('<col class="option" />\n'
                         '<col class="description" />\n'
                         '<tbody valign="top">\n')

    def depart_option_list(self, node):
        self.body.append('</tbody>\n</table>\n')

    def visit_option_list_item(self, node):
        self.body.append(self.starttag(node, 'tr', ''))

    def depart_option_list_item(self, node):
        self.body.append('</tr>\n')

    # Omit <p> tags to produce visually compact lists (less vertical
    # whitespace) as CSS styling requires CSS2.
    def should_be_compact_paragraph(self, node):
        """
        Determine if the <p> tags around paragraph ``node`` can be omitted.
        """
        if (isinstance(node.parent, nodes.document)
            or isinstance(node.parent, nodes.compound)):
            # Never compact paragraphs in document or compound.
            return False
        for key, value in node.attlist():
            if (node.is_not_default(key)
                and not (key == 'classes'
                         and value in ([], ['first'],
                                       ['last'], ['first', 'last']))):
                # Attribute which needs to survive.
                return False
        first = isinstance(node.parent[0], nodes.label)  # skip label
        for child in node.parent.children[first:]:
            # only first paragraph can be compact
            if isinstance(child, nodes.Invisible):
                continue
            if child is node:
                break
            return False
        parent_length = len([n for n in node.parent if not isinstance(
            n, (nodes.Invisible, nodes.label))])
        if (self.compact_simple
            or self.compact_field_list
            or self.compact_p and parent_length == 1):
            return True
        return False

    def visit_paragraph(self, node):
        if self.should_be_compact_paragraph(node):
            self.context.append('')
        else:
            self.body.append(self.starttag(node, 'p', ''))
            self.context.append('</p>\n')

    def depart_paragraph(self, node):
        self.body.append(self.context.pop())

    # ersatz for first/last pseudo-classes
    def visit_sidebar(self, node):
        self.body.append(
            self.starttag(node, 'div', CLASS='sidebar'))
        self.set_first_last(node)
        self.in_sidebar = True

    def depart_sidebar(self, node):
        self.body.append('</div>\n')
        self.in_sidebar = False

    # <sub> not allowed in <pre>
    def visit_subscript(self, node):
        if isinstance(node.parent, nodes.literal_block):
            self.body.append(self.starttag(node, 'span', '',
                                           CLASS='subscript'))
        else:
            self.body.append(self.starttag(node, 'sub', ''))

    def depart_subscript(self, node):
        if isinstance(node.parent, nodes.literal_block):
            self.body.append('</span>')
        else:
            self.body.append('</sub>')

    # Use <h*> for subtitles (deprecated in HTML 5)
    def visit_subtitle(self, node):
        if isinstance(node.parent, nodes.sidebar):
            self.body.append(self.starttag(node, 'p', '',
                                           CLASS='sidebar-subtitle'))
            self.context.append('</p>\n')
        elif isinstance(node.parent, nodes.document):
            self.body.append(self.starttag(node, 'h2', '', CLASS='subtitle'))
            self.context.append('</h2>\n')
            self.in_document_title = len(self.body)
        elif isinstance(node.parent, nodes.section):
            tag = 'h%s' % (self.section_level + self.initial_header_level - 1)
            self.body.append(
                self.starttag(node, tag, '', CLASS='section-subtitle')
                + self.starttag({}, 'span', '', CLASS='section-subtitle'))
            self.context.append('</span></%s>\n' % tag)

    def depart_subtitle(self, node):
        self.body.append(self.context.pop())
        if self.in_document_title:
            self.subtitle = self.body[self.in_document_title:-1]
            self.in_document_title = 0
            self.body_pre_docinfo.extend(self.body)
            self.html_subtitle.extend(self.body)
            del self.body[:]

    # <sup> not allowed in <pre> in HTML 4
    def visit_superscript(self, node):
        if isinstance(node.parent, nodes.literal_block):
            self.body.append(self.starttag(node, 'span', '',
                                           CLASS='superscript'))
        else:
            self.body.append(self.starttag(node, 'sup', ''))

    def depart_superscript(self, node):
        if isinstance(node.parent, nodes.literal_block):
            self.body.append('</span>')
        else:
            self.body.append('</sup>')

    # <tt> element deprecated in HTML 5
    def visit_system_message(self, node):
        self.body.append(self.starttag(node, 'div', CLASS='system-message'))
        self.body.append('<p class="system-message-title">')
        backref_text = ''
        if len(node['backrefs']):
            backrefs = node['backrefs']
            if len(backrefs) == 1:
                backref_text = ('; <em><a href="#%s">backlink</a></em>'
                                % backrefs[0])
            else:
                i = 1
                backlinks = []
                for backref in backrefs:
                    backlinks.append('<a href="#%s">%s</a>' % (backref, i))
                    i += 1
                backref_text = ('; <em>backlinks: %s</em>'
                                % ', '.join(backlinks))
        if node.hasattr('line'):
            line = ', line %s' % node['line']
        else:
            line = ''
        self.body.append('System Message: %s/%s '
                         '(<tt class="docutils">%s</tt>%s)%s</p>\n'
                         % (node['type'], node['level'],
                            self.encode(node['source']), line, backref_text))

    def depart_system_message(self, node):
        self.body.append('</div>\n')

    # "hard coded" border setting
    def visit_table(self, node):
        self.context.append(self.compact_p)
        self.compact_p = True
        atts = {'border': 1}
        classes = ['docutils', self.settings.table_style]
        if 'align' in node:
            classes.append('align-%s' % node['align'])
        if 'width' in node:
            atts['style'] = 'width: %s' % node['width']
        self.body.append(
            self.starttag(node, 'table', CLASS=' '.join(classes), **atts))

    def depart_table(self, node):
        self.compact_p = self.context.pop()
        self.body.append('</table>\n')

    # hard-coded vertical alignment
    def visit_tbody(self, node):
        self.body.append(self.starttag(node, 'tbody', valign='top'))

    def depart_tbody(self, node):
        self.body.append('</tbody>\n')

    # no special handling of "details" in definition list
    def visit_term(self, node):
        self.body.append(self.starttag(node, 'dt', '',
                                       classes=node.parent['classes'],
                                       ids=node.parent['ids']))

    def depart_term(self, node):
        pass

    # hard-coded vertical alignment
    def visit_thead(self, node):
        self.body.append(self.starttag(node, 'thead', valign='bottom'))

    def depart_thead(self, node):
        self.body.append('</thead>\n')

    # auxiliary method, called by visit_title()
    # "with-subtitle" class, no ARIA roles
    def section_title_tags(self, node):
        classes = []
        h_level = self.section_level + self.initial_header_level - 1
        if (len(node.parent) >= 2
            and isinstance(node.parent[1], nodes.subtitle)):
            classes.append('with-subtitle')
        if h_level > 6:
            classes.append('h%i' % h_level)
        tagname = 'h%i' % min(h_level, 6)
        start_tag = self.starttag(node, tagname, '', classes=classes)
        if node.hasattr('refid'):
            atts = {}
            atts['class'] = 'toc-backref'
            atts['href'] = '#' + node['refid']
            start_tag += self.starttag({}, 'a', '', **atts)
            close_tag = '</a></%s>\n' % tagname
        else:
            close_tag = '</%s>\n' % tagname
        return start_tag, close_tag


class SimpleListChecker(writers._html_base.SimpleListChecker):

    """
    Raise `nodes.NodeFound` if non-simple list item is encountered.

    Here "simple" means a list item containing nothing other than a single
    paragraph, a simple list, or a paragraph followed by a simple list.
    """

    def visit_list_item(self, node):
        children = []
        for child in node.children:
            if not isinstance(child, nodes.Invisible):
                children.append(child)
        if (children and isinstance(children[0], nodes.paragraph)
            and (isinstance(children[-1], nodes.bullet_list)
                 or isinstance(children[-1], nodes.enumerated_list))):
            children.pop()
        if len(children) <= 1:
            return
        else:
            raise nodes.NodeFound

    # def visit_bullet_list(self, node):
    #     pass

    # def visit_enumerated_list(self, node):
    #     pass

    def visit_paragraph(self, node):
        raise nodes.SkipNode

    def visit_definition_list(self, node):
        raise nodes.NodeFound

    def visit_docinfo(self, node):
        raise nodes.NodeFound
