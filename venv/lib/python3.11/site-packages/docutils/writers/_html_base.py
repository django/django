#!/usr/bin/env python3
# :Author: David Goodger, Günter Milde
#          Based on the html4css1 writer by David Goodger.
# :Maintainer: docutils-develop@lists.sourceforge.net
# :Revision: $Revision: 9292 $
# :Date: $Date: 2005-06-28$
# :Copyright: © 2016 David Goodger, Günter Milde
# :License: Released under the terms of the `2-Clause BSD license`_, in short:
#
#    Copying and distribution of this file, with or without modification,
#    are permitted in any medium without royalty provided the copyright
#    notice and this notice are preserved.
#    This file is offered as-is, without any warranty.
#
# .. _2-Clause BSD license: https://opensource.org/licenses/BSD-2-Clause

"""common definitions for Docutils HTML writers"""

import base64
import mimetypes
import os
import os.path
import re
from urllib.request import unquote as unquote_url
from urllib.request import url2pathname  # unquote and use local path sep
import warnings

import docutils
from docutils import frontend, languages, nodes, utils, writers
from docutils.parsers.rst.directives import length_or_percentage_or_unitless
from docutils.parsers.rst.directives.images import PIL
from docutils.transforms import writer_aux
from docutils.utils.math import (unichar2tex, pick_math_environment,
                                 math2html, latex2mathml, tex2mathml_extern)


class Writer(writers.Writer):

    supported = ('html', 'xhtml')  # update in subclass
    """Formats this writer supports."""

    settings_spec = (
        'HTML Writer Options',
        None,
        (('Specify the template file (UTF-8 encoded). '
          '(default: writer dependent)',
          ['--template'],
          {'metavar': '<file>'}),
         ('Comma separated list of stylesheet URLs. '
          'Overrides previous --stylesheet and --stylesheet-path settings.',
          ['--stylesheet'],
          {'metavar': '<URL[,URL,...]>', 'overrides': 'stylesheet_path',
           'validator': frontend.validate_comma_separated_list}),
         ('Comma separated list of stylesheet paths. '
          'Relative paths are expanded if a matching file is found in '
          'the --stylesheet-dirs. With --link-stylesheet, '
          'the path is rewritten relative to the output HTML file. '
          '(default: writer dependent)',
          ['--stylesheet-path'],
          {'metavar': '<file[,file,...]>', 'overrides': 'stylesheet',
           'validator': frontend.validate_comma_separated_list}),
         ('Comma-separated list of directories where stylesheets are found. '
          'Used by --stylesheet-path when expanding relative path arguments. '
          '(default: writer dependent)',
          ['--stylesheet-dirs'],
          {'metavar': '<dir[,dir,...]>',
           'validator': frontend.validate_comma_separated_list}),
         ('Embed the stylesheet(s) in the output HTML file.  The stylesheet '
          'files must be accessible during processing. (default)',
          ['--embed-stylesheet'],
          {'default': 1, 'action': 'store_true',
           'validator': frontend.validate_boolean}),
         ('Link to the stylesheet(s) in the output HTML file. ',
          ['--link-stylesheet'],
          {'dest': 'embed_stylesheet', 'action': 'store_false'}),
         ('Specify the initial header level. '
          'Does not affect document title & subtitle (see --no-doc-title).'
          '(default: writer dependent).',
          ['--initial-header-level'],
          {'choices': '1 2 3 4 5 6'.split(), 'default': '2',
           'metavar': '<level>'}),
         ('Format for footnote references: one of "superscript" or '
          '"brackets". (default: "brackets")',
          ['--footnote-references'],
          {'choices': ['superscript', 'brackets'], 'default': 'brackets',
           'metavar': '<format>',
           'overrides': 'trim_footnote_reference_space'}),
         ('Format for block quote attributions: '
          'one of "dash" (em-dash prefix), "parentheses"/"parens", or "none". '
          '(default: "dash")',
          ['--attribution'],
          {'choices': ['dash', 'parentheses', 'parens', 'none'],
           'default': 'dash', 'metavar': '<format>'}),
         ('Remove extra vertical whitespace between items of "simple" bullet '
          'lists and enumerated lists. (default)',
          ['--compact-lists'],
          {'default': True, 'action': 'store_true',
           'validator': frontend.validate_boolean}),
         ('Disable compact simple bullet and enumerated lists.',
          ['--no-compact-lists'],
          {'dest': 'compact_lists', 'action': 'store_false'}),
         ('Remove extra vertical whitespace between items of simple field '
          'lists. (default)',
          ['--compact-field-lists'],
          {'default': True, 'action': 'store_true',
           'validator': frontend.validate_boolean}),
         ('Disable compact simple field lists.',
          ['--no-compact-field-lists'],
          {'dest': 'compact_field_lists', 'action': 'store_false'}),
         ('Added to standard table classes. '
          'Defined styles: borderless, booktabs, '
          'align-left, align-center, align-right, '
          'colwidths-auto, colwidths-grid.',
          ['--table-style'],
          {'default': ''}),
         ('Math output format (one of "MathML", "HTML", "MathJax", '
          'or "LaTeX") and option(s). '
          '(default: "HTML math.css")',
          ['--math-output'],
          {'default': 'HTML math.css'}),
         ('Prepend an XML declaration. ',
          ['--xml-declaration'],
          {'default': False, 'action': 'store_true',
           'validator': frontend.validate_boolean}),
         ('Omit the XML declaration.',
          ['--no-xml-declaration'],
          {'dest': 'xml_declaration', 'action': 'store_false'}),
         ('Obfuscate email addresses to confuse harvesters while still '
          'keeping email links usable with standards-compliant browsers.',
          ['--cloak-email-addresses'],
          {'action': 'store_true', 'validator': frontend.validate_boolean}),
         )
        )

    settings_defaults = {'output_encoding_error_handler': 'xmlcharrefreplace'}

    config_section = 'html base writer'  # overwrite in subclass
    config_section_dependencies = ('writers', 'html writers')

    visitor_attributes = (
        'head_prefix', 'head', 'stylesheet', 'body_prefix',
        'body_pre_docinfo', 'docinfo', 'body', 'body_suffix',
        'title', 'subtitle', 'header', 'footer', 'meta', 'fragment',
        'html_prolog', 'html_head', 'html_title', 'html_subtitle',
        'html_body')

    def get_transforms(self):
        return super().get_transforms() + [writer_aux.Admonitions]

    def translate(self):
        self.visitor = visitor = self.translator_class(self.document)
        self.document.walkabout(visitor)
        for attr in self.visitor_attributes:
            setattr(self, attr, getattr(visitor, attr))
        self.output = self.apply_template()

    def apply_template(self):
        with open(self.document.settings.template, encoding='utf-8') as fp:
            template = fp.read()
        subs = self.interpolation_dict()
        return template % subs

    def interpolation_dict(self):
        subs = {}
        settings = self.document.settings
        for attr in self.visitor_attributes:
            subs[attr] = ''.join(getattr(self, attr)).rstrip('\n')
        subs['encoding'] = settings.output_encoding
        subs['version'] = docutils.__version__
        return subs

    def assemble_parts(self):
        writers.Writer.assemble_parts(self)
        for part in self.visitor_attributes:
            self.parts[part] = ''.join(getattr(self, part))


class HTMLTranslator(nodes.NodeVisitor):

    """
    Generic Docutils to HTML translator.

    See the `html4css1` and `html5_polyglot` writers for full featured
    HTML writers.

    .. IMPORTANT::
      The `visit_*` and `depart_*` methods use a
      heterogeneous stack, `self.context`.
      When subclassing, make sure to be consistent in its use!

      Examples for robust coding:

      a) Override both `visit_*` and `depart_*` methods, don't call the
         parent functions.

      b) Extend both and unconditionally call the parent functions::

           def visit_example(self, node):
               if foo:
                   self.body.append('<div class="foo">')
               html4css1.HTMLTranslator.visit_example(self, node)

           def depart_example(self, node):
               html4css1.HTMLTranslator.depart_example(self, node)
               if foo:
                   self.body.append('</div>')

      c) Extend both, calling the parent functions under the same
         conditions::

           def visit_example(self, node):
               if foo:
                   self.body.append('<div class="foo">\n')
               else: # call the parent method
                   _html_base.HTMLTranslator.visit_example(self, node)

           def depart_example(self, node):
               if foo:
                   self.body.append('</div>\n')
               else: # call the parent method
                   _html_base.HTMLTranslator.depart_example(self, node)

      d) Extend one method (call the parent), but don't otherwise use the
         `self.context` stack::

           def depart_example(self, node):
               _html_base.HTMLTranslator.depart_example(self, node)
               if foo:
                   # implementation-specific code
                   # that does not use `self.context`
                   self.body.append('</div>\n')

      This way, changes in stack use will not bite you.
    """

    doctype = '<!DOCTYPE html>\n'
    doctype_mathml = doctype

    head_prefix_template = ('<html xmlns="http://www.w3.org/1999/xhtml"'
                            ' xml:lang="%(lang)s" lang="%(lang)s">\n<head>\n')
    content_type = '<meta charset="%s" />\n'
    generator = (
        f'<meta name="generator" content="Docutils {docutils.__version__}: '
        'https://docutils.sourceforge.io/" />\n')
    # `starttag()` arguments for the main document (HTML5 uses <main>)
    documenttag_args = {'tagname': 'div', 'CLASS': 'document'}

    # Template for the MathJax script in the header:
    mathjax_script = '<script type="text/javascript" src="%s"></script>\n'

    mathjax_url = 'file:/usr/share/javascript/mathjax/MathJax.js'
    """
    URL of the MathJax javascript library.

    The MathJax library ought to be installed on the same
    server as the rest of the deployed site files and specified
    in the `math-output` setting appended to "mathjax".
    See `Docutils Configuration`__.

    __ https://docutils.sourceforge.io/docs/user/config.html#math-output

    The fallback tries a local MathJax installation at
    ``/usr/share/javascript/mathjax/MathJax.js``.
    """

    stylesheet_link = '<link rel="stylesheet" href="%s" type="text/css" />\n'
    embedded_stylesheet = '<style type="text/css">\n\n%s\n</style>\n'
    words_and_spaces = re.compile(r'[^ \n]+| +|\n')
    # wrap point inside word:
    in_word_wrap_point = re.compile(r'.+\W\W.+|[-?].+')
    lang_attribute = 'lang'  # name changes to 'xml:lang' in XHTML 1.1

    special_characters = {ord('&'): '&amp;',
                          ord('<'): '&lt;',
                          ord('"'): '&quot;',
                          ord('>'): '&gt;',
                          ord('@'): '&#64;',  # may thwart address harvesters
                          }
    """Character references for characters with a special meaning in HTML."""

    def __init__(self, document):
        nodes.NodeVisitor.__init__(self, document)
        # process settings
        self.settings = settings = document.settings
        self.language = languages.get_language(
                            settings.language_code, document.reporter)
        self.initial_header_level = int(settings.initial_header_level)
        # image_loading (only defined for HTML5 writer)
        self.image_loading = getattr(settings, 'image_loading', None)
        # legacy setting embed_images:
        if getattr(settings, 'embed_images', None) is True:
            warnings.warn('The configuration setting "embed_images" '
                          'will be removed in Docutils 2.0. '
                          'Use "image_loading: embed".',
                          FutureWarning, stacklevel=8)
            if self.image_loading is None:
                self.image_loading = 'embed'
        if getattr(settings, 'embed_images', None) is False:
            warnings.warn('The configuration setting "embed_images" '
                          'will be removed in Docutils 2.0. '
                          'Use "image_loading: link".',
                          FutureWarning, stacklevel=8)
        if self.image_loading is None:
            self.image_loading = 'link'  # default
        self.math_output = settings.math_output.split()
        self.math_output_options = self.math_output[1:]
        self.math_output = self.math_output[0].lower()

        # set up "parts" (cf. docs/api/publisher.html#publish-parts-details)
        #
        self.body = []  # equivalent to `fragment`, ≠ `html_body`
        self.body_prefix = ['</head>\n<body>\n']  # + optional header
        self.body_pre_docinfo = []  # document heading (title and subtitle)
        self.body_suffix = ['</body>\n</html>\n']  # + optional footer
        self.docinfo = []
        self.footer = []
        self.fragment = []  # main content of the document ("naked" body)
        self.head = []
        self.head_prefix = []  # everything up to and including <head>
        self.header = []
        self.html_body = []
        self.html_head = [self.content_type]  # charset not interpolated
        self.html_prolog = []
        self.html_subtitle = []
        self.html_title = []
        self.meta = [self.generator]
        self.stylesheet = [self.stylesheet_call(path)
                           for path in utils.get_stylesheet_list(settings)]
        self.title = []
        self.subtitle = []
        if settings.xml_declaration:
            self.head_prefix.append(
                utils.xml_declaration(settings.output_encoding))
            self.html_prolog.append(
                utils.xml_declaration('%s'))  # encoding not interpolated
        if (settings.output_encoding
            and settings.output_encoding.lower() != 'unicode'):
            self.meta.insert(0, self.content_type % settings.output_encoding)

        # bookkeeping attributes; reflect state of translator
        #
        self.context = []
        """Heterogeneous stack.

        Used by visit_* and depart_* functions in conjunction with the tree
        traversal. Make sure that the pops correspond to the pushes.
        """
        self.section_level = 0
        self.colspecs = []
        self.compact_p = True
        self.compact_simple = False
        self.compact_field_list = False
        self.in_docinfo = False
        self.in_sidebar = False
        self.in_document_title = 0  # len(self.body) or 0
        self.in_mailto = False
        self.author_in_authors = False  # for html4css1
        self.math_header = []

    def astext(self):
        return ''.join(self.head_prefix + self.head
                       + self.stylesheet + self.body_prefix
                       + self.body_pre_docinfo + self.docinfo
                       + self.body + self.body_suffix)

    def encode(self, text):
        """Encode special characters in `text` & return."""
        # Use only named entities known in both XML and HTML
        # other characters are automatically encoded "by number" if required.
        # @@@ A codec to do these and all other HTML entities would be nice.
        text = str(text)
        return text.translate(self.special_characters)

    def cloak_mailto(self, uri):
        """Try to hide a mailto: URL from harvesters."""
        # Encode "@" using a URL octet reference (see RFC 1738).
        # Further cloaking with HTML entities will be done in the
        # `attval` function.
        return uri.replace('@', '%40')

    def cloak_email(self, addr):
        """Try to hide the link text of a email link from harversters."""
        # Surround at-signs and periods with <span> tags.  ("@" has
        # already been encoded to "&#64;" by the `encode` method.)
        addr = addr.replace('&#64;', '<span>&#64;</span>')
        return addr.replace('.', '<span>&#46;</span>')

    def attval(self, text,
               whitespace=re.compile('[\n\r\t\v\f]')):
        """Cleanse, HTML encode, and return attribute value text."""
        encoded = self.encode(whitespace.sub(' ', text))
        if self.in_mailto and self.settings.cloak_email_addresses:
            # Cloak at-signs ("%40") and periods with HTML entities.
            encoded = encoded.replace('%40', '&#37;&#52;&#48;')
            encoded = encoded.replace('.', '&#46;')
        return encoded

    def stylesheet_call(self, path, adjust_path=None):
        """Return code to reference or embed stylesheet file `path`"""
        if adjust_path is None:
            adjust_path = bool(self.settings.stylesheet_path)
        if self.settings.embed_stylesheet:
            try:
                with open(path, encoding='utf-8') as f:
                    content = f.read()
            except OSError as err:
                msg = f'Cannot embed stylesheet: {err}'
                self.document.reporter.error(msg)
                return '<--- %s --->\n' % msg
            else:
                self.settings.record_dependencies.add(path)
            return self.embedded_stylesheet % content
        # else link to style file:
        if adjust_path:
            # rewrite path relative to output (cf. config.html#stylesheet-path)
            path = utils.relative_path(self.settings._destination, path)
        return self.stylesheet_link % self.encode(path)

    def starttag(self, node, tagname, suffix='\n', empty=False, **attributes):
        """
        Construct and return a start tag given a node (id & class attributes
        are extracted), tag name, and optional attributes.
        """
        tagname = tagname.lower()
        prefix = []
        atts = {}
        for (name, value) in attributes.items():
            atts[name.lower()] = value
        classes = atts.pop('classes', [])
        languages = []
        # unify class arguments and move language specification
        for cls in node.get('classes', []) + atts.pop('class', '').split():
            if cls.startswith('language-'):
                languages.append(cls[9:])
            elif cls.strip() and cls not in classes:
                classes.append(cls)
        if languages:
            # attribute name is 'lang' in XHTML 1.0 but 'xml:lang' in 1.1
            atts[self.lang_attribute] = languages[0]
        # filter classes that are processed by the writer:
        internal = ('colwidths-auto', 'colwidths-given', 'colwidths-grid')
        if isinstance(node, nodes.table):
            classes = [cls for cls in classes if cls not in internal]
        if classes:
            atts['class'] = ' '.join(classes)
        assert 'id' not in atts
        ids = node.get('ids', [])
        ids.extend(atts.pop('ids', []))
        if ids:
            atts['id'] = ids[0]
            for id in ids[1:]:
                # Add empty "span" elements for additional IDs.  Note
                # that we cannot use empty "a" elements because there
                # may be targets inside of references, but nested "a"
                # elements aren't allowed in XHTML (even if they do
                # not all have a "href" attribute).
                if empty or isinstance(node, (nodes.Sequential,
                                              nodes.docinfo,
                                              nodes.table)):
                    # Insert target right in front of element.
                    prefix.append('<span id="%s"></span>' % id)
                else:
                    # Non-empty tag.  Place the auxiliary <span> tag
                    # *inside* the element, as the first child.
                    suffix += '<span id="%s"></span>' % id
        attlist = sorted(atts.items())
        parts = [tagname]
        for name, value in attlist:
            # value=None was used for boolean attributes without
            # value, but this isn't supported by XHTML.
            assert value is not None
            if isinstance(value, list):
                values = [str(v) for v in value]
                parts.append('%s="%s"' % (name.lower(),
                                          self.attval(' '.join(values))))
            else:
                parts.append('%s="%s"' % (name.lower(),
                                          self.attval(str(value))))
        if empty:
            infix = ' /'
        else:
            infix = ''
        return ''.join(prefix) + '<%s%s>' % (' '.join(parts), infix) + suffix

    def emptytag(self, node, tagname, suffix='\n', **attributes):
        """Construct and return an XML-compatible empty tag."""
        return self.starttag(node, tagname, suffix, empty=True, **attributes)

    def set_class_on_child(self, node, class_, index=0):
        """
        Set class `class_` on the visible child no. index of `node`.
        Do nothing if node has fewer children than `index`.
        """
        children = [n for n in node if not isinstance(n, nodes.Invisible)]
        try:
            child = children[index]
        except IndexError:
            return
        child['classes'].append(class_)

    def visit_Text(self, node):
        text = node.astext()
        encoded = self.encode(text)
        if self.in_mailto and self.settings.cloak_email_addresses:
            encoded = self.cloak_email(encoded)
        self.body.append(encoded)

    def depart_Text(self, node):
        pass

    def visit_abbreviation(self, node):
        # @@@ implementation incomplete ("title" attribute)
        self.body.append(self.starttag(node, 'abbr', ''))

    def depart_abbreviation(self, node):
        self.body.append('</abbr>')

    def visit_acronym(self, node):
        # @@@ implementation incomplete ("title" attribute)
        self.body.append(self.starttag(node, 'acronym', ''))

    def depart_acronym(self, node):
        self.body.append('</acronym>')

    def visit_address(self, node):
        self.visit_docinfo_item(node, 'address', meta=False)
        self.body.append(self.starttag(node, 'pre',
                                       suffix='', CLASS='address'))

    def depart_address(self, node):
        self.body.append('\n</pre>\n')
        self.depart_docinfo_item()

    def visit_admonition(self, node):
        self.body.append(self.starttag(node, 'aside', classes=['admonition']))

    def depart_admonition(self, node=None):
        self.body.append('</aside>\n')

    attribution_formats = {'dash': ('\u2014', ''),
                           'parentheses': ('(', ')'),
                           'parens': ('(', ')'),
                           'none': ('', '')}

    def visit_attribution(self, node):
        prefix, suffix = self.attribution_formats[self.settings.attribution]
        self.context.append(suffix)
        self.body.append(
            self.starttag(node, 'p', prefix, CLASS='attribution'))

    def depart_attribution(self, node):
        self.body.append(self.context.pop() + '</p>\n')

    def visit_author(self, node):
        if not isinstance(node.parent, nodes.authors):
            self.visit_docinfo_item(node, 'author')
        self.body.append('<p>')

    def depart_author(self, node):
        self.body.append('</p>')
        if isinstance(node.parent, nodes.authors):
            self.body.append('\n')
        else:
            self.depart_docinfo_item()

    def visit_authors(self, node):
        self.visit_docinfo_item(node, 'authors')

    def depart_authors(self, node):
        self.depart_docinfo_item()

    def visit_block_quote(self, node):
        self.body.append(self.starttag(node, 'blockquote'))

    def depart_block_quote(self, node):
        self.body.append('</blockquote>\n')

    def check_simple_list(self, node):
        """Check for a simple list that can be rendered compactly."""
        visitor = SimpleListChecker(self.document)
        try:
            node.walk(visitor)
        except nodes.NodeFound:
            return False
        else:
            return True

    # Compact lists
    # ------------
    # Include definition lists and field lists (in addition to ordered
    # and unordered lists) in the test if a list is "simple"  (cf. the
    # html4css1.HTMLTranslator docstring and the SimpleListChecker class at
    # the end of this file).

    def is_compactable(self, node):
        # explicit class arguments have precedence
        if 'compact' in node['classes']:
            return True
        if 'open' in node['classes']:
            return False
        # check config setting:
        if (isinstance(node, (nodes.field_list, nodes.definition_list))
            and not self.settings.compact_field_lists):
            return False
        if (isinstance(node, (nodes.enumerated_list, nodes.bullet_list))
            and not self.settings.compact_lists):
            return False
        # Table of Contents:
        if 'contents' in node.parent['classes']:
            return True
        # check the list items:
        return self.check_simple_list(node)

    def visit_bullet_list(self, node):
        atts = {}
        old_compact_simple = self.compact_simple
        self.context.append((self.compact_simple, self.compact_p))
        self.compact_p = None
        self.compact_simple = self.is_compactable(node)
        if self.compact_simple and not old_compact_simple:
            atts['class'] = 'simple'
        self.body.append(self.starttag(node, 'ul', **atts))

    def depart_bullet_list(self, node):
        self.compact_simple, self.compact_p = self.context.pop()
        self.body.append('</ul>\n')

    def visit_caption(self, node):
        self.body.append(self.starttag(node, 'p', '', CLASS='caption'))

    def depart_caption(self, node):
        self.body.append('</p>\n')

    # Use semantic tag and DPub role (HTML4 uses a table)
    def visit_citation(self, node):
        # role 'doc-bibloentry' requires wrapping in an element with
        # role 'list' and an element with role 'doc-bibliography'
        # https://www.w3.org/TR/dpub-aria-1.0/#doc-biblioentry)
        if not isinstance(node.previous_sibling(), type(node)):
            self.body.append('<div role="list" class="citation-list">\n')
        self.body.append(self.starttag(node, 'div', classes=[node.tagname],
                                       role="doc-biblioentry"))

    def depart_citation(self, node):
        self.body.append('</div>\n')
        if not isinstance(node.next_node(descend=False, siblings=True),
                          type(node)):
            self.body.append('</div>\n')

    # Use DPub role (overwritten in HTML4)
    def visit_citation_reference(self, node):
        href = '#'
        if 'refid' in node:
            href += node['refid']
        elif 'refname' in node:
            href += self.document.nameids[node['refname']]
        # else: # TODO system message (or already in the transform)?
        # 'Citation reference missing.'
        self.body.append(self.starttag(node, 'a', suffix='[', href=href,
                                       classes=['citation-reference'],
                                       role='doc-biblioref'))

    def depart_citation_reference(self, node):
        self.body.append(']</a>')

    # classifier
    # ----------
    # don't insert classifier-delimiter here (done by CSS)

    def visit_classifier(self, node):
        self.body.append(self.starttag(node, 'span', '', CLASS='classifier'))

    def depart_classifier(self, node):
        self.body.append('</span>')

    def visit_colspec(self, node):
        self.colspecs.append(node)
        # "stubs" list is an attribute of the tgroup element:
        node.parent.stubs.append(node.attributes.get('stub'))

    def depart_colspec(self, node):
        # write out <colgroup> when all colspecs are processed
        if isinstance(node.next_node(descend=False, siblings=True),
                      nodes.colspec):
            return
        if 'colwidths-auto' in node.parent.parent['classes'] or (
            'colwidths-grid' not in self.settings.table_style
            and 'colwidths-given' not in node.parent.parent['classes']):
            return
        self.body.append(self.starttag(node, 'colgroup'))
        total_width = sum(node['colwidth'] for node in self.colspecs)
        for node in self.colspecs:
            colwidth = node['colwidth'] / total_width
            self.body.append(self.emptytag(node, 'col',
                                           style=f'width: {colwidth:.1%}'))
        self.body.append('</colgroup>\n')

    def visit_comment(self, node,
                      sub=re.compile('-(?=-)').sub):
        """Escape double-dashes in comment text."""
        self.body.append('<!-- %s -->\n' % sub('- ', node.astext()))
        # Content already processed:
        raise nodes.SkipNode

    def visit_compound(self, node):
        self.body.append(self.starttag(node, 'div', CLASS='compound'))

    def depart_compound(self, node):
        self.body.append('</div>\n')

    def visit_container(self, node):
        self.body.append(self.starttag(node, 'div',
                                       CLASS='docutils container'))

    def depart_container(self, node):
        self.body.append('</div>\n')

    def visit_contact(self, node):
        self.visit_docinfo_item(node, 'contact', meta=False)

    def depart_contact(self, node):
        self.depart_docinfo_item()

    def visit_copyright(self, node):
        self.visit_docinfo_item(node, 'copyright')

    def depart_copyright(self, node):
        self.depart_docinfo_item()

    def visit_date(self, node):
        self.visit_docinfo_item(node, 'date')

    def depart_date(self, node):
        self.depart_docinfo_item()

    def visit_decoration(self, node):
        pass

    def depart_decoration(self, node):
        pass

    def visit_definition(self, node):
        if 'details' in node.parent.parent['classes']:
            self.body.append('</summary>\n')
        else:
            self.body.append('</dt>\n')
            self.body.append(self.starttag(node, 'dd', ''))

    def depart_definition(self, node):
        if 'details' not in node.parent.parent['classes']:
            self.body.append('</dd>\n')

    def visit_definition_list(self, node):
        if 'details' in node['classes']:
            self.body.append(self.starttag(node, 'div'))
        else:
            classes = ['simple'] if self.is_compactable(node) else []
            self.body.append(self.starttag(node, 'dl', classes=classes))

    def depart_definition_list(self, node):
        if 'details' in node['classes']:
            self.body.append('</div>\n')
        else:
            self.body.append('</dl>\n')

    # Use a "details" disclosure element if parent has "class" arg "details".
    def visit_definition_list_item(self, node):
        if 'details' in node.parent['classes']:
            atts = {}
            if "open" in node.parent['classes']:
                atts['open'] = 'open'
            self.body.append(self.starttag(node, 'details', **atts))

    def depart_definition_list_item(self, node):
        if 'details' in node.parent['classes']:
            self.body.append('</details>\n')

    def visit_description(self, node):
        self.body.append(self.starttag(node, 'dd', ''))

    def depart_description(self, node):
        self.body.append('</dd>\n')

    def visit_docinfo(self, node):
        self.context.append(len(self.body))
        classes = ['docinfo']
        if self.is_compactable(node):
            classes.append('simple')
        self.body.append(self.starttag(node, 'dl', classes=classes))

    def depart_docinfo(self, node):
        self.body.append('</dl>\n')
        start = self.context.pop()
        self.docinfo = self.body[start:]
        self.body = []

    def visit_docinfo_item(self, node, name, meta=True):
        if meta:
            self.meta.append(f'<meta name="{name}" '
                             f'content="{self.attval(node.astext())}" />\n')
        self.body.append(f'<dt class="{name}">{self.language.labels[name]}'
                         '<span class="colon">:</span></dt>\n')
        self.body.append(self.starttag(node, 'dd', '', CLASS=name))

    def depart_docinfo_item(self):
        self.body.append('</dd>\n')

    def visit_doctest_block(self, node):
        self.body.append(self.starttag(node, 'pre', suffix='',
                                       classes=['code', 'python', 'doctest']))

    def depart_doctest_block(self, node):
        self.body.append('\n</pre>\n')

    def visit_document(self, node):
        title = (node.get('title') or os.path.basename(node['source'])
                 or 'untitled Docutils document')
        self.head.append(f'<title>{self.encode(title)}</title>\n')

    def depart_document(self, node):
        self.head_prefix.extend([self.doctype,
                                 self.head_prefix_template %
                                 {'lang': self.settings.language_code}])
        self.html_prolog.append(self.doctype)
        self.head = self.meta[:] + self.head
        if 'name="dcterms.' in ''.join(self.meta):
            self.head.append('<link rel="schema.dcterms"'
                             ' href="http://purl.org/dc/terms/"/>')
        if self.math_header:
            if self.math_output == 'mathjax':
                self.head.extend(self.math_header)
            else:
                self.stylesheet.extend(self.math_header)
        # skip content-type meta tag with interpolated charset value:
        self.html_head.extend(self.head[1:])
        self.body_prefix.append(self.starttag(node, **self.documenttag_args))
        self.body_suffix.insert(0, f'</{self.documenttag_args["tagname"]}>\n')
        self.fragment.extend(self.body)  # self.fragment is the "naked" body
        self.html_body.extend(self.body_prefix[1:] + self.body_pre_docinfo
                              + self.docinfo + self.body
                              + self.body_suffix[:-1])
        assert not self.context, f'len(context) = {len(self.context)}'

    def visit_emphasis(self, node):
        self.body.append(self.starttag(node, 'em', ''))

    def depart_emphasis(self, node):
        self.body.append('</em>')

    def visit_entry(self, node):
        atts = {'classes': []}
        if isinstance(node.parent.parent, nodes.thead):
            atts['classes'].append('head')
        if node.parent.parent.parent.stubs[node.parent.column]:
            # "stubs" list is an attribute of the tgroup element
            atts['classes'].append('stub')
        if atts['classes']:
            tagname = 'th'
        else:
            tagname = 'td'
        node.parent.column += 1
        if 'morerows' in node:
            atts['rowspan'] = node['morerows'] + 1
        if 'morecols' in node:
            atts['colspan'] = node['morecols'] + 1
            node.parent.column += node['morecols']
        self.body.append(self.starttag(node, tagname, '', **atts))
        self.context.append('</%s>\n' % tagname.lower())

    def depart_entry(self, node):
        self.body.append(self.context.pop())

    def visit_enumerated_list(self, node):
        atts = {'classes': []}
        if 'start' in node:
            atts['start'] = node['start']
        if 'enumtype' in node:
            atts['classes'].append(node['enumtype'])
        if self.is_compactable(node):
            atts['classes'].append('simple')
        self.body.append(self.starttag(node, 'ol', **atts))

    def depart_enumerated_list(self, node):
        self.body.append('</ol>\n')

    def visit_field_list(self, node):
        atts = {}
        classes = node.setdefault('classes', [])
        for i, cls in enumerate(classes):
            if cls.startswith('field-indent-'):
                try:
                    indent_length = length_or_percentage_or_unitless(
                                                        cls[13:], 'px')
                except ValueError:
                    break
                atts['style'] = '--field-indent: %s;' % indent_length
                classes.pop(i)
                break
        classes.append('field-list')
        if self.is_compactable(node):
            classes.append('simple')
        self.body.append(self.starttag(node, 'dl', **atts))

    def depart_field_list(self, node):
        self.body.append('</dl>\n')

    def visit_field(self, node):
        pass

    def depart_field(self, node):
        pass

    # as field is ignored, pass class arguments to field-name and field-body:
    def visit_field_name(self, node):
        self.body.append(self.starttag(node, 'dt', '',
                                       classes=node.parent['classes']))

    def depart_field_name(self, node):
        self.body.append('<span class="colon">:</span></dt>\n')

    def visit_field_body(self, node):
        self.body.append(self.starttag(node, 'dd', '',
                                       classes=node.parent['classes']))
        # prevent misalignment of following content if the field is empty:
        if not node.children:
            self.body.append('<p></p>')

    def depart_field_body(self, node):
        self.body.append('</dd>\n')

    def visit_figure(self, node):
        atts = {'class': 'figure'}
        if node.get('width'):
            atts['style'] = 'width: %s' % node['width']
        if node.get('align'):
            atts['class'] += " align-" + node['align']
        self.body.append(self.starttag(node, 'div', **atts))

    def depart_figure(self, node):
        self.body.append('</div>\n')

    def visit_footer(self, node):
        self.context.append(len(self.body))

    def depart_footer(self, node):
        start = self.context.pop()
        footer = [self.starttag(node, 'div', CLASS='footer'),
                  '<hr class="footer" />\n']
        footer.extend(self.body[start:])
        footer.append('\n</div>\n')
        self.footer.extend(footer)
        self.body_suffix[:0] = footer
        del self.body[start:]

    def visit_footnote(self, node):
        # No native HTML element: use <aside> with ARIA role
        # (html4css1 uses tables).
        # Wrap groups of footnotes for easier styling.
        label_style = self.settings.footnote_references  # brackets/superscript
        if not isinstance(node.previous_sibling(), type(node)):
            self.body.append(f'<aside class="footnote-list {label_style}">\n')
        self.body.append(self.starttag(node, 'aside',
                                       classes=[node.tagname, label_style],
                                       role="doc-footnote"))

    def depart_footnote(self, node):
        self.body.append('</aside>\n')
        if not isinstance(node.next_node(descend=False, siblings=True),
                          type(node)):
            self.body.append('</aside>\n')

    def visit_footnote_reference(self, node):
        href = '#' + node['refid']
        classes = ['footnote-reference', self.settings.footnote_references]
        self.body.append(self.starttag(node, 'a', suffix='', classes=classes,
                                       role='doc-noteref', href=href))
        self.body.append('<span class="fn-bracket">[</span>')

    def depart_footnote_reference(self, node):
        self.body.append('<span class="fn-bracket">]</span>')
        self.body.append('</a>')

    # Docutils-generated text: put section numbers in a span for CSS styling:
    def visit_generated(self, node):
        if 'sectnum' in node['classes']:
            # get section number (strip trailing no-break-spaces)
            sectnum = node.astext().rstrip(' ')
            self.body.append('<span class="sectnum">%s </span>'
                             % self.encode(sectnum))
            # Content already processed:
            raise nodes.SkipNode

    def depart_generated(self, node):
        pass

    def visit_header(self, node):
        self.context.append(len(self.body))

    def depart_header(self, node):
        start = self.context.pop()
        header = [self.starttag(node, 'div', CLASS='header')]
        header.extend(self.body[start:])
        header.append('\n<hr class="header"/>\n</div>\n')
        self.body_prefix.extend(header)
        self.header.extend(header)
        del self.body[start:]

    def visit_image(self, node):
        atts = {}
        uri = node['uri']
        mimetype = mimetypes.guess_type(uri)[0]
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
                        imgsize = img.size
                except (OSError, UnicodeEncodeError):
                    pass  # TODO: warn?
                else:
                    self.settings.record_dependencies.add(
                        imagepath.replace('\\', '/'))
                    if 'width' not in atts:
                        atts['width'] = '%dpx' % imgsize[0]
                    if 'height' not in atts:
                        atts['height'] = '%dpx' % imgsize[1]
                    del img
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
        # Embed image file (embedded SVG or data URI):
        if self.image_loading == 'embed':
            try:
                with open(url2pathname(uri), 'rb') as imagefile:
                    imagedata = imagefile.read()
            except OSError as err:
                self.document.reporter.error('Cannot embed image %r: %s'
                                             % (uri, err.strerror))
            else:
                self.settings.record_dependencies.add(unquote_url(uri))
                # TODO: insert SVG as-is?
                # if mimetype == 'image/svg+xml':
                # read/parse, apply arguments,
                # insert as <svg ....> ... </svg> # (about 1/3 less data)
                data64 = base64.b64encode(imagedata).decode()
                uri = 'data:%s;base64,%s' % (mimetype, data64)
        elif self.image_loading == 'lazy':
            atts['loading'] = 'lazy'
        if mimetype == 'application/x-shockwave-flash':
            atts['type'] = mimetype
            # do NOT use an empty tag: incorrect rendering in browsers
            tag = (self.starttag(node, 'object', '', data=uri, **atts)
                   + node.get('alt', uri) + '</object>' + suffix)
        else:
            atts['alt'] = node.get('alt', node['uri'])
            tag = self.emptytag(node, 'img', suffix, src=uri, **atts)
        self.body.append(tag)

    def depart_image(self, node):
        pass

    def visit_inline(self, node):
        self.body.append(self.starttag(node, 'span', ''))

    def depart_inline(self, node):
        self.body.append('</span>')

    # footnote and citation labels:
    def visit_label(self, node):
        self.body.append('<span class="label">')
        self.body.append('<span class="fn-bracket">[</span>')
        # footnote/citation backrefs:
        if self.settings.footnote_backlinks:
            backrefs = node.parent.get('backrefs', [])
            if len(backrefs) == 1:
                self.body.append('<a role="doc-backlink"'
                                 ' href="#%s">' % backrefs[0])

    def depart_label(self, node):
        backrefs = []
        if self.settings.footnote_backlinks:
            backrefs = node.parent.get('backrefs', backrefs)
        if len(backrefs) == 1:
            self.body.append('</a>')
        self.body.append('<span class="fn-bracket">]</span></span>\n')
        if len(backrefs) > 1:
            backlinks = ['<a role="doc-backlink" href="#%s">%s</a>' % (ref, i)
                         for (i, ref) in enumerate(backrefs, 1)]
            self.body.append('<span class="backrefs">(%s)</span>\n'
                             % ','.join(backlinks))

    def visit_legend(self, node):
        self.body.append(self.starttag(node, 'div', CLASS='legend'))

    def depart_legend(self, node):
        self.body.append('</div>\n')

    def visit_line(self, node):
        self.body.append(self.starttag(node, 'div', suffix='', CLASS='line'))
        if not len(node):
            self.body.append('<br />')

    def depart_line(self, node):
        self.body.append('</div>\n')

    def visit_line_block(self, node):
        self.body.append(self.starttag(node, 'div', CLASS='line-block'))

    def depart_line_block(self, node):
        self.body.append('</div>\n')

    def visit_list_item(self, node):
        self.body.append(self.starttag(node, 'li', ''))

    def depart_list_item(self, node):
        self.body.append('</li>\n')

    # inline literal
    def visit_literal(self, node):
        # special case: "code" role
        classes = node['classes']
        if 'code' in classes:
            # filter 'code' from class arguments
            classes.pop(classes.index('code'))
            self.body.append(self.starttag(node, 'code', ''))
            return
        self.body.append(
            self.starttag(node, 'span', '', CLASS='docutils literal'))
        text = node.astext()
        if not isinstance(node.parent, nodes.literal_block):
            text = text.replace('\n', ' ')
        # Protect text like ``--an-option`` and the regular expression
        # ``[+]?(\d+(\.\d*)?|\.\d+)`` from bad line wrapping
        for token in self.words_and_spaces.findall(text):
            if token.strip() and self.in_word_wrap_point.search(token):
                self.body.append('<span class="pre">%s</span>'
                                 % self.encode(token))
            else:
                self.body.append(self.encode(token))
        self.body.append('</span>')
        raise nodes.SkipNode  # content already processed

    def depart_literal(self, node):
        # skipped unless literal element is from "code" role:
        self.body.append('</code>')

    def visit_literal_block(self, node):
        self.body.append(self.starttag(node, 'pre', '', CLASS='literal-block'))
        if 'code' in node['classes']:
            self.body.append('<code>')

    def depart_literal_block(self, node):
        if 'code' in node['classes']:
            self.body.append('</code>')
        self.body.append('</pre>\n')

    # Mathematics:
    # As there is no native HTML math support, we provide alternatives
    # for the math-output: LaTeX and MathJax simply wrap the content,
    # HTML and MathML also convert the math_code.
    # HTML container
    math_tags = {
                 # math_output: (block, inline, class-arguments)
                 'html': ('div', 'span', 'formula'),
                 'latex': ('pre', 'tt', 'math'),
                 'mathml': ('div', '', ''),
                 'mathjax': ('div', 'span', 'math'),
                }

    def visit_math(self, node, math_env=''):
        # If the method is called from visit_math_block(), math_env != ''.

        if self.math_output not in self.math_tags:
            self.document.reporter.error(
                f'math-output format "{self.math_output}" not supported '
                'falling back to "latex"')
            self.math_output = 'latex'
        tag = self.math_tags[self.math_output][math_env == '']
        clsarg = self.math_tags[self.math_output][2]
        # LaTeX container
        wrappers = {
                    # math_mode: (inline, block)
                    'html': ('$%s$', '\\begin{%s}\n%s\n\\end{%s}'),
                    'latex': (None, None),
                    'mathml': ('$%s$', '\\begin{%s}\n%s\n\\end{%s}'),
                    'mathjax': (r'\(%s\)', '\\begin{%s}\n%s\n\\end{%s}'),
                   }
        wrapper = wrappers[self.math_output][math_env != '']
        if (self.math_output == 'mathml'
            and (not self.math_output_options
                 or self.math_output_options[0] == 'blahtexml')):
            wrapper = None
        # get and wrap content
        math_code = node.astext().translate(unichar2tex.uni2tex_table)
        if wrapper:
            try:  # wrapper with three "%s"
                math_code = wrapper % (math_env, math_code, math_env)
            except TypeError:  # wrapper with one "%s"
                math_code = wrapper % math_code
        # settings and conversion
        if self.math_output in ('latex', 'mathjax'):
            math_code = self.encode(math_code)
        if self.math_output == 'mathjax' and not self.math_header:
            try:
                self.mathjax_url = self.math_output_options[0]
            except IndexError:
                self.document.reporter.warning('No MathJax URL specified, '
                                               'using local fallback '
                                               '(see config.html)')
            # append configuration, if not already present in the URL:
            # input LaTeX with AMS, output common HTML
            if '?' not in self.mathjax_url:
                self.mathjax_url += '?config=TeX-AMS_CHTML'
            self.math_header = [self.mathjax_script % self.mathjax_url]
        elif self.math_output == 'html':
            if self.math_output_options and not self.math_header:
                self.math_header = [self.stylesheet_call(
                    utils.find_file_in_dirs(s, self.settings.stylesheet_dirs),
                    adjust_path=True)
                    for s in self.math_output_options[0].split(',')]
            # TODO: fix display mode in matrices and fractions
            math2html.DocumentParameters.displaymode = (math_env != '')
            math_code = math2html.math2html(math_code)
        elif self.math_output == 'mathml':
            if 'XHTML 1' in self.doctype:
                self.doctype = self.doctype_mathml
                self.content_type = self.content_type_mathml
            converter = ' '.join(self.math_output_options).lower()
            try:
                if converter == 'latexml':
                    math_code = tex2mathml_extern.latexml(
                                    math_code, self.document.reporter)
                elif converter == 'ttm':
                    math_code = tex2mathml_extern.ttm(
                                    math_code, self.document.reporter)
                elif converter == 'blahtexml':
                    math_code = tex2mathml_extern.blahtexml(
                                    math_code,
                                    inline=(not math_env),
                                    reporter=self.document.reporter)
                elif converter == 'pandoc':
                    math_code = tex2mathml_extern.pandoc(
                                    math_code,
                                    reporter=self.document.reporter)
                elif not converter:
                    math_code = latex2mathml.tex2mathml(
                                    math_code, inline=(not math_env))
                else:
                    self.document.reporter.error('option "%s" not supported '
                                                 'with math-output "MathML"')
            except OSError:
                raise OSError('is "latexmlmath" in your PATH?')
            except SyntaxError as err:
                err_node = self.document.reporter.error(err, base_node=node)
                self.visit_system_message(err_node)
                self.body.append(self.starttag(node, 'p'))
                self.body.append(','.join(err.args))
                self.body.append('</p>\n')
                self.body.append(self.starttag(node, 'pre',
                                               CLASS='literal-block'))
                self.body.append(self.encode(math_code))
                self.body.append('\n</pre>\n')
                self.depart_system_message(err_node)
                raise nodes.SkipNode
        # append to document body
        if tag:
            self.body.append(self.starttag(node, tag,
                                           suffix='\n'*bool(math_env),
                                           CLASS=clsarg))
        self.body.append(math_code)
        if math_env:  # block mode (equation, display)
            self.body.append('\n')
        if tag:
            self.body.append('</%s>' % tag)
        if math_env:
            self.body.append('\n')
        # Content already processed:
        raise nodes.SkipNode

    def depart_math(self, node):
        pass  # never reached

    def visit_math_block(self, node):
        math_env = pick_math_environment(node.astext())
        self.visit_math(node, math_env=math_env)

    def depart_math_block(self, node):
        pass  # never reached

    # Meta tags: 'lang' attribute replaced by 'xml:lang' in XHTML 1.1
    # HTML5/polyglot recommends using both
    def visit_meta(self, node):
        self.meta.append(self.emptytag(node, 'meta',
                                       **node.non_default_attributes()))

    def depart_meta(self, node):
        pass

    def visit_option(self, node):
        self.body.append(self.starttag(node, 'span', '', CLASS='option'))

    def depart_option(self, node):
        self.body.append('</span>')
        if isinstance(node.next_node(descend=False, siblings=True),
                      nodes.option):
            self.body.append(', ')

    def visit_option_argument(self, node):
        self.body.append(node.get('delimiter', ' '))
        self.body.append(self.starttag(node, 'var', ''))

    def depart_option_argument(self, node):
        self.body.append('</var>')

    def visit_option_group(self, node):
        self.body.append(self.starttag(node, 'dt', ''))
        self.body.append('<kbd>')

    def depart_option_group(self, node):
        self.body.append('</kbd></dt>\n')

    def visit_option_list(self, node):
        self.body.append(
            self.starttag(node, 'dl', CLASS='option-list'))

    def depart_option_list(self, node):
        self.body.append('</dl>\n')

    def visit_option_list_item(self, node):
        pass

    def depart_option_list_item(self, node):
        pass

    def visit_option_string(self, node):
        pass

    def depart_option_string(self, node):
        pass

    def visit_organization(self, node):
        self.visit_docinfo_item(node, 'organization')

    def depart_organization(self, node):
        self.depart_docinfo_item()

    # Do not omit <p> tags
    # --------------------
    #
    # The HTML4CSS1 writer does this to "produce
    # visually compact lists (less vertical whitespace)". This writer
    # relies on CSS rules for visual compactness.
    #
    # * In XHTML 1.1, e.g., a <blockquote> element may not contain
    #   character data, so you cannot drop the <p> tags.
    # * Keeping simple paragraphs in the field_body enables a CSS
    #   rule to start the field-body on a new line if the label is too long
    # * it makes the code simpler.
    #
    # TODO: omit paragraph tags in simple table cells?

    def visit_paragraph(self, node):
        self.body.append(self.starttag(node, 'p', ''))

    def depart_paragraph(self, node):
        self.body.append('</p>')
        if not (isinstance(node.parent, (nodes.list_item, nodes.entry))
                and (len(node.parent) == 1)):
            self.body.append('\n')

    def visit_problematic(self, node):
        if node.hasattr('refid'):
            self.body.append('<a href="#%s">' % node['refid'])
            self.context.append('</a>')
        else:
            self.context.append('')
        self.body.append(self.starttag(node, 'span', '', CLASS='problematic'))

    def depart_problematic(self, node):
        self.body.append('</span>')
        self.body.append(self.context.pop())

    def visit_raw(self, node):
        if 'html' in node.get('format', '').split():
            if isinstance(node.parent, nodes.TextElement):
                tagname = 'span'
            else:
                tagname = 'div'
            if node['classes']:
                self.body.append(self.starttag(node, tagname, suffix=''))
            self.body.append(node.astext())
            if node['classes']:
                self.body.append('</%s>' % tagname)
        # Keep non-HTML raw text out of output:
        raise nodes.SkipNode

    def visit_reference(self, node):
        atts = {'class': 'reference'}
        if 'refuri' in node:
            atts['href'] = node['refuri']
            if (self.settings.cloak_email_addresses
                and atts['href'].startswith('mailto:')):
                atts['href'] = self.cloak_mailto(atts['href'])
                self.in_mailto = True
            atts['class'] += ' external'
        else:
            assert 'refid' in node, \
                   'References must have "refuri" or "refid" attribute.'
            atts['href'] = '#' + node['refid']
            atts['class'] += ' internal'
        if len(node) == 1 and isinstance(node[0], nodes.image):
            atts['class'] += ' image-reference'
        if not isinstance(node.parent, nodes.TextElement):
            assert len(node) == 1 and isinstance(node[0], nodes.image)
            atts['class'] += ' image-reference'
        self.body.append(self.starttag(node, 'a', '', **atts))

    def depart_reference(self, node):
        self.body.append('</a>')
        if not isinstance(node.parent, nodes.TextElement):
            self.body.append('\n')
        self.in_mailto = False

    def visit_revision(self, node):
        self.visit_docinfo_item(node, 'revision', meta=False)

    def depart_revision(self, node):
        self.depart_docinfo_item()

    def visit_row(self, node):
        self.body.append(self.starttag(node, 'tr', ''))
        node.column = 0

    def depart_row(self, node):
        self.body.append('</tr>\n')

    def visit_rubric(self, node):
        self.body.append(self.starttag(node, 'p', '', CLASS='rubric'))

    def depart_rubric(self, node):
        self.body.append('</p>\n')

    def visit_section(self, node):
        self.section_level += 1
        self.body.append(
            self.starttag(node, 'div', CLASS='section'))

    def depart_section(self, node):
        self.section_level -= 1
        self.body.append('</div>\n')

    # TODO: use the new HTML5 element <aside>
    def visit_sidebar(self, node):
        self.body.append(
            self.starttag(node, 'div', CLASS='sidebar'))
        self.in_sidebar = True

    def depart_sidebar(self, node):
        self.body.append('</div>\n')
        self.in_sidebar = False

    def visit_status(self, node):
        self.visit_docinfo_item(node, 'status', meta=False)

    def depart_status(self, node):
        self.depart_docinfo_item()

    def visit_strong(self, node):
        self.body.append(self.starttag(node, 'strong', ''))

    def depart_strong(self, node):
        self.body.append('</strong>')

    def visit_subscript(self, node):
        self.body.append(self.starttag(node, 'sub', ''))

    def depart_subscript(self, node):
        self.body.append('</sub>')

    def visit_substitution_definition(self, node):
        """Internal only."""
        raise nodes.SkipNode

    def visit_substitution_reference(self, node):
        self.unimplemented_visit(node)

    # h1–h6 elements must not be used to markup subheadings, subtitles,
    # alternative titles and taglines unless intended to be the heading for a
    # new section or subsection.
    # -- http://www.w3.org/TR/html51/sections.html#headings-and-sections
    def visit_subtitle(self, node):
        if isinstance(node.parent, nodes.sidebar):
            classes = ['sidebar-subtitle']
        elif isinstance(node.parent, nodes.document):
            classes = ['subtitle']
            self.in_document_title = len(self.body) + 1
        elif isinstance(node.parent, nodes.section):
            classes = ['section-subtitle']
        self.body.append(self.starttag(node, 'p', '', classes=classes))

    def depart_subtitle(self, node):
        self.body.append('</p>\n')
        if isinstance(node.parent, nodes.document):
            self.subtitle = self.body[self.in_document_title:-1]
            self.in_document_title = 0
            self.body_pre_docinfo.extend(self.body)
            self.html_subtitle.extend(self.body)
            del self.body[:]

    def visit_superscript(self, node):
        self.body.append(self.starttag(node, 'sup', ''))

    def depart_superscript(self, node):
        self.body.append('</sup>')

    def visit_system_message(self, node):
        self.body.append(self.starttag(node, 'aside', CLASS='system-message'))
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
                         '(<span class="docutils literal">%s</span>%s)%s</p>\n'
                         % (node['type'], node['level'],
                            self.encode(node['source']), line, backref_text))

    def depart_system_message(self, node):
        self.body.append('</aside>\n')

    def visit_table(self, node):
        atts = {'classes': self.settings.table_style.replace(',', ' ').split()}
        if 'align' in node:
            atts['classes'].append('align-%s' % node['align'])
        if 'width' in node:
            atts['style'] = 'width: %s;' % node['width']
        tag = self.starttag(node, 'table', **atts)
        self.body.append(tag)

    def depart_table(self, node):
        self.body.append('</table>\n')

    def visit_target(self, node):
        if ('refuri' not in node
                and 'refid' not in node
                and 'refname' not in node):
            self.body.append(self.starttag(node, 'span', '', CLASS='target'))
            self.context.append('</span>')
        else:
            self.context.append('')

    def depart_target(self, node):
        self.body.append(self.context.pop())

    # no hard-coded vertical alignment in table body
    def visit_tbody(self, node):
        self.body.append(self.starttag(node, 'tbody'))

    def depart_tbody(self, node):
        self.body.append('</tbody>\n')

    def visit_term(self, node):
        if 'details' in node.parent.parent['classes']:
            self.body.append(self.starttag(node, 'summary', suffix=''))
        else:
            # The parent node (definition_list_item) is omitted in HTML.
            self.body.append(self.starttag(node, 'dt', suffix='',
                                           classes=node.parent['classes'],
                                           ids=node.parent['ids']))

    def depart_term(self, node):
        # Leave the end tag to `self.visit_definition()`,
        # in case there's a classifier.
        pass

    def visit_tgroup(self, node):
        self.colspecs = []
        node.stubs = []

    def depart_tgroup(self, node):
        pass

    def visit_thead(self, node):
        self.body.append(self.starttag(node, 'thead'))

    def depart_thead(self, node):
        self.body.append('</thead>\n')

    def section_title_tags(self, node):
        atts = {}
        h_level = self.section_level + self.initial_header_level - 1
        # Only 6 heading levels have dedicated HTML tags.
        tagname = 'h%i' % min(h_level, 6)
        if h_level > 6:
            atts['aria-level'] = h_level
        start_tag = self.starttag(node, tagname, '', **atts)
        if node.hasattr('refid'):
            atts = {}
            atts['class'] = 'toc-backref'
            atts['role'] = 'doc-backlink'  # HTML5 only
            atts['href'] = '#' + node['refid']
            start_tag += self.starttag(nodes.reference(), 'a', '', **atts)
            close_tag = '</a></%s>\n' % tagname
        else:
            close_tag = '</%s>\n' % tagname
        return start_tag, close_tag

    def visit_title(self, node):
        close_tag = '</p>\n'
        if isinstance(node.parent, nodes.topic):
            # TODO: use role="heading" or <h1>? (HTML5 only)
            self.body.append(
                self.starttag(node, 'p', '', CLASS='topic-title'))
        elif isinstance(node.parent, nodes.sidebar):
            # TODO: use role="heading" or <h1>? (HTML5 only)
            self.body.append(
                self.starttag(node, 'p', '', CLASS='sidebar-title'))
        elif isinstance(node.parent, nodes.Admonition):
            self.body.append(
                  self.starttag(node, 'p', '', CLASS='admonition-title'))
        elif isinstance(node.parent, nodes.table):
            self.body.append(
                  self.starttag(node, 'caption', ''))
            close_tag = '</caption>\n'
        elif isinstance(node.parent, nodes.document):
            self.body.append(self.starttag(node, 'h1', '', CLASS='title'))
            close_tag = '</h1>\n'
            self.in_document_title = len(self.body)
        else:
            assert isinstance(node.parent, nodes.section)
            # Get correct heading and evt. backlink tags
            start_tag, close_tag = self.section_title_tags(node)
            self.body.append(start_tag)
        self.context.append(close_tag)

    def depart_title(self, node):
        self.body.append(self.context.pop())
        if self.in_document_title:
            self.title = self.body[self.in_document_title:-1]
            self.in_document_title = 0
            self.body_pre_docinfo.extend(self.body)
            self.html_title.extend(self.body)
            del self.body[:]

    def visit_title_reference(self, node):
        self.body.append(self.starttag(node, 'cite', ''))

    def depart_title_reference(self, node):
        self.body.append('</cite>')

    def visit_topic(self, node):
        self.body.append(self.starttag(node, 'div', CLASS='topic'))

    def depart_topic(self, node):
        self.body.append('</div>\n')

    def visit_transition(self, node):
        self.body.append(self.emptytag(node, 'hr', CLASS='docutils'))

    def depart_transition(self, node):
        pass

    def visit_version(self, node):
        self.visit_docinfo_item(node, 'version', meta=False)

    def depart_version(self, node):
        self.depart_docinfo_item()

    def unimplemented_visit(self, node):
        raise NotImplementedError('visiting unimplemented node type: %s'
                                  % node.__class__.__name__)


class SimpleListChecker(nodes.GenericNodeVisitor):

    """
    Raise `nodes.NodeFound` if non-simple list item is encountered.

    Here "simple" means a list item containing nothing other than a single
    paragraph, a simple list, or a paragraph followed by a simple list.

    This version also checks for simple field lists and docinfo.
    """

    def default_visit(self, node):
        raise nodes.NodeFound

    def visit_list_item(self, node):
        children = [child for child in node.children
                    if not isinstance(child, nodes.Invisible)]
        if (children and isinstance(children[0], nodes.paragraph)
            and (isinstance(children[-1], nodes.bullet_list)
                 or isinstance(children[-1], nodes.enumerated_list)
                 or isinstance(children[-1], nodes.field_list))):
            children.pop()
        if len(children) <= 1:
            return
        else:
            raise nodes.NodeFound

    def pass_node(self, node):
        pass

    def ignore_node(self, node):
        # ignore nodes that are never complex (can contain only inline nodes)
        raise nodes.SkipNode

    # Paragraphs and text
    visit_Text = ignore_node
    visit_paragraph = ignore_node

    # Lists
    visit_bullet_list = pass_node
    visit_enumerated_list = pass_node
    visit_docinfo = pass_node

    # Docinfo nodes:
    visit_author = ignore_node
    visit_authors = visit_list_item
    visit_address = visit_list_item
    visit_contact = pass_node
    visit_copyright = ignore_node
    visit_date = ignore_node
    visit_organization = ignore_node
    visit_status = ignore_node
    visit_version = visit_list_item

    # Definition list:
    visit_definition_list = pass_node
    visit_definition_list_item = pass_node
    visit_term = ignore_node
    visit_classifier = pass_node
    visit_definition = visit_list_item

    # Field list:
    visit_field_list = pass_node
    visit_field = pass_node
    # the field body corresponds to a list item
    visit_field_body = visit_list_item
    visit_field_name = ignore_node

    # Invisible nodes should be ignored.
    visit_comment = ignore_node
    visit_substitution_definition = ignore_node
    visit_target = ignore_node
    visit_pending = ignore_node
