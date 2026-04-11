#! /usr/bin/env python3
# :Copyright: © 2024 Günter Milde.
# :License: Released under the terms of the `2-Clause BSD license`_, in short:
#
#    Copying and distribution of this file, with or without modification,
#    are permitted in any medium without royalty provided the copyright
#    notice and this notice are preserved.
#    This file is offered as-is, without any warranty.
#
# .. _2-Clause BSD license: https://opensource.org/licenses/BSD-2-Clause
#
# Revision: $Revision: 10136 $
# Date: $Date: 2025-05-20 17:48:27 +0200 (Di, 20. Mai 2025) $

"""A Docutils-XML parser.

   Provisional:
     The API is not fixed yet.
     Defined objects may be renamed or changed
     in any Docutils release without prior notice.
"""

from __future__ import annotations

__docformat__ = 'reStructuredText'

import re
import xml.etree.ElementTree as ET

from docutils import frontend, nodes, parsers, utils


class Parser(parsers.Parser):

    """A Docutils-XML parser."""

    supported = ('xml', 'docutils-xml')
    """Aliases this parser supports."""

    config_section = 'xml parser'
    config_section_dependencies = ('parsers',)
    settings_default_overrides = {'doctitle_xform': False,
                                  'validate': True,
                                  }

    def parse(self, inputstring, document) -> None:
        """
        Parse `inputstring` and populate `document`, a "document tree".

        Provisional.
        """
        self.setup_parse(inputstring, document)

        node = parse_element(inputstring, document)
        if not isinstance(node, nodes.document):
            document.append(node)

        self.finish_parse()


class Unknown(nodes.Special, nodes.Inline, nodes.Element):
    """An unknown element found by the XML parser."""
    content_model = (((nodes.Element, nodes.Text), '*'),)  # no restrictions


def parse_element(inputstring, document=None):
    """
    Parse `inputstring` as "Docutils XML", return `nodes.Element` instance.

    :inputstring: XML source.
    :document: `nodes.document` instance (default: a new dummy instance).
               Provides settings and reporter.
               Populated and returned, if the inputstring's root element
               is <document>.

    Caution:
      The function does not detect invalid XML.

      To check the validity of the returned node,
      you may use its `validate()` method::

        node = parse_element('<tip><hint>text</hint></tip>')
        node.validate()

    Provisional.
    """
    root = None
    parser = ET.XMLPullParser(events=('start',))
    for i, line in enumerate(inputstring.splitlines(keepends=True)):
        try:
            parser.feed(line)
            for event, element in parser.read_events():
                if root is None:
                    root = element
                element.attrib['source line'] = str(i+1)
        except ET.ParseError as e:
            if document is None:
                raise
            document.reporter.error(f'XML parse error: {e}.',
                                    source=document.settings._source,
                                    line=e.position[0])
            break
    return element2node(root, document)


def element2node(element, document=None, unindent=True):
    """
    Convert an `etree` element and its children to Docutils doctree nodes.

    :element:  `xml.etree` element
    :document: see `parse_element()`
    :unindent: Remove formatting indentation of follow-up text lines?
               Cf. `append_text()`.
               TODO: do we need an "unindent" configuration setting?

    Return a `docutils.nodes.Element` instance.

    Internal.
    """
    if document is None:
        document = utils.new_document('xml input',
                                      frontend.get_default_settings(Parser))
        document.source == 'xml input'
    if element is None:
        problem = nodes.problematic('', 'No XML element found.')
        return nodes.paragraph('', '', problem)
    # Get the corresponding `nodes.Element` instance:
    try:
        nodeclass = getattr(nodes, element.tag)
        if not issubclass(nodeclass, nodes.Element):
            nodeclass = Unknown
    except AttributeError:
        nodeclass = Unknown
    if nodeclass == nodes.document:
        node = document
        document.source = document.source or document.settings._source
    else:
        node = nodeclass()

    node.line = int(element.get('source line'))
    if isinstance(node, Unknown):
        node.tagname = element.tag
        document.reporter.warning(
            f'Unknown element type <{element.tag}>.',
            base_node=node)

    # Attributes: convert and add to `node.attributes`.
    for key, value in element.items():
        if key.startswith('{') or key == 'source line':
            continue  # skip duplicate attributes with namespace URL
        try:
            node.attributes[key] = nodes.ATTRIBUTE_VALIDATORS[key](value)
        except (ValueError, KeyError):
            if key in node.list_attributes:
                value = value.split()
            node.attributes[key] = value  # node becomes invalid!

    # Bookkeeping (register some elements/attributes in document-wide lists)
    if isinstance(node, nodes.decoration):
        document.decoration = node
    elif isinstance(node, nodes.substitution_definition):
        document.note_substitution_def(node, ' '.join(node['names']), document)
    if node['ids']:  # register, check for duplicates
        document.set_id(node)
    # TODO: anything missing?

    # Append content:
    # update "unindent" flag: change line indentation?
    unindent = unindent and not isinstance(
                   node, (nodes.FixedTextElement, nodes.literal, Unknown))
    # (leading) text
    append_text(node, element.text, unindent)
    # children and their tailing text
    for child in element:
        node.append(element2node(child, document, unindent))
        # Text after a child node
        append_text(node, child.tail, unindent)

    return node


def append_text(node, text, unindent) -> None:
    # Format `text`, wrap in a TextElement and append to `node`.
    # Skip if `text` is empty or just formatting whitespace.
    if not text:
        return
    if unindent:
        text = re.sub('\n +', '\n', text)
    if isinstance(node, nodes.TextElement):
        node.append(nodes.Text(text))
    elif text.strip():
        # no TextElement: ignore formatting whitespace
        # but append other text (node becomes invalid!)
        node.append(nodes.Text(text.strip()))
