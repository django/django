#!/usr/bin/env python3
# :Copyright: © 2020 Günter Milde.
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
"""
A parser for CommonMark Markdown text using `recommonmark`__.

__ https://pypi.org/project/recommonmark/

.. important:: This module is deprecated.

   * The "recommonmark" package is unmaintained and deprecated.
     This wrapper module will be removed in Docutils 1.0.

   * The API is not settled and may change with any minor Docutils version.
"""

from __future__ import annotations

__docformat__ = 'reStructuredText'

from docutils import Component
from docutils import nodes

try:
    # If possible, import Sphinx's 'addnodes'
    from sphinx import addnodes
except ImportError:
    # stub to prevent errors if Sphinx isn't installed
    import sys
    import types

    class pending_xref(nodes.Inline, nodes.Element):
        ...

    sys.modules['sphinx'] = sphinx = types.ModuleType('sphinx')
    sphinx.addnodes = addnodes = types.SimpleNamespace()
    addnodes.pending_xref = pending_xref
try:
    import recommonmark
    from recommonmark.parser import CommonMarkParser
except ImportError as err:
    raise ImportError(
        'Parsing "recommonmark" Markdown flavour requires the\n'
        '  package https://pypi.org/project/recommonmark.'
    ) from err
else:
    if recommonmark.__version__ < '0.6.0':
        raise ImportError('The installed version of "recommonmark" is too old.'
                          ' Update with "pip install -U recommonmark".')


# auxiliary function for `document.findall()`
def is_literal(node):
    return isinstance(node, (nodes.literal, nodes.literal_block))


class Parser(CommonMarkParser):
    """MarkDown parser based on recommonmark.

    This parser is provisional:
    the API is not settled and may change with any minor Docutils version.
    """
    supported = ('recommonmark', 'commonmark', 'markdown', 'md')
    """Formats this parser supports."""

    config_section = 'recommonmark parser'
    config_section_dependencies = ('parsers',)

    def get_transforms(self):
        return Component.get_transforms(self)  # + [AutoStructify]

    def parse(self, inputstring, document):
        """Wrapper of upstream method.

        Ensure "line-length-limt". Report errors with `document.reporter`.
        """
        # check for exorbitantly long lines
        for i, line in enumerate(inputstring.split('\n')):
            if len(line) > document.settings.line_length_limit:
                error = document.reporter.error(
                    'Line %d exceeds the line-length-limit.'%(i+1))
                document.append(error)
                return

        # pass to upstream parser
        try:
            CommonMarkParser.parse(self, inputstring, document)
        except Exception as err:
            if document.settings.traceback:
                raise err
            error = document.reporter.error('Parsing with "recommonmark" '
                                            'returned the error:\n%s'%err)
            document.append(error)

    # Post-Processing
    # ---------------

    def finish_parse(self) -> None:
        """Finalize parse details.  Call at end of `self.parse()`."""

        document = self.document

        # merge adjoining Text nodes:
        for node in document.findall(nodes.TextElement):
            children = node.children
            i = 0
            while i+1 < len(children):
                if (isinstance(children[i], nodes.Text)
                    and isinstance(children[i+1], nodes.Text)):
                    children[i] = nodes.Text(children[i]+children.pop(i+1))
                    children[i].parent = node
                else:
                    i += 1

        # remove empty Text nodes:
        for node in document.findall(nodes.Text):
            if not len(node):
                node.parent.remove(node)

        # add "code" class argument to literal elements (inline and block)
        for node in document.findall(is_literal):
            if 'code' not in node['classes']:
                node['classes'].append('code')
        # move "language" argument to classes
        for node in document.findall(nodes.literal_block):
            if 'language' in node.attributes:
                node['classes'].append(node['language'])
                del node['language']

        # replace raw nodes if raw is not allowed
        if not document.settings.raw_enabled:
            for node in document.findall(nodes.raw):
                message = document.reporter.warning('Raw content disabled.')
                if isinstance(node.parent, nodes.TextElement):
                    msgid = document.set_id(message)
                    problematic = nodes.problematic('', node.astext(),
                                                    refid=msgid)
                    node.parent.replace(node, problematic)
                    prbid = document.set_id(problematic)
                    message.add_backref(prbid)
                    document.append(message)
                else:
                    node.parent.replace(node, message)

        # drop pending_xref (Sphinx cross reference extension)
        for node in document.findall(addnodes.pending_xref):
            reference = node.children[0]
            if 'name' not in reference:
                reference['name'] = nodes.fully_normalize_name(
                                                    reference.astext())
            node.parent.replace(node, reference)
        # now we are ready to call the upstream function:
        super().finish_parse()

    def visit_document(self, node) -> None:
        """Dummy function to prevent spurious warnings.

        cf. https://github.com/readthedocs/recommonmark/issues/177
        """

    # Overwrite parent method with version that
    # doesn't pass deprecated `rawsource` argument to nodes.Text:
    def visit_text(self, mdnode) -> None:
        self.current_node.append(nodes.Text(mdnode.literal))
