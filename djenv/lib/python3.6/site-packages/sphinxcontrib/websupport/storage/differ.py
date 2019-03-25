# -*- coding: utf-8 -*-
"""
    sphinxcontrib.websupport.storage.differ
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    A differ for creating an HTML representations of proposal diffs

    :copyright: Copyright 2007-2016 by the Sphinx team, see AUTHORS.
    :license: BSD, see LICENSE for details.
"""

import re
from difflib import Differ

from sphinx.util.pycompat import htmlescape


class CombinedHtmlDiff(object):
    """Create an HTML representation of the differences between two pieces
    of text.
    """
    highlight_regex = re.compile(r'([\+\-\^]+)')

    def __init__(self, source, proposal):
        proposal = htmlescape(proposal)

        differ = Differ()
        self.diff = list(differ.compare(source.splitlines(1),
                                        proposal.splitlines(1)))

    def make_text(self):
        return '\n'.join(self.diff)

    def make_html(self):
        """Return the HTML representation of the differences between
        `source` and `proposal`.

        :param source: the original text
        :param proposal: the proposed text
        """
        html = []
        diff = self.diff[:]
        line = diff.pop(0)
        next = diff.pop(0)
        while True:
            html.append(self._handle_line(line, next))
            line = next
            try:
                next = diff.pop(0)
            except IndexError:
                html.append(self._handle_line(line))
                break
        return ''.join(html).rstrip()

    def _handle_line(self, line, next=None):
        """Handle an individual line in a diff."""
        prefix = line[0]
        text = line[2:]

        if prefix == ' ':
            return text
        elif prefix == '?':
            return ''

        if next is not None and next[0] == '?':
            tag = prefix == '+' and 'ins' or 'del'
            text = self._highlight_text(text, next, tag)
        css_class = prefix == '+' and 'prop-added' or 'prop-removed'

        return '<span class="%s">%s</span>\n' % (css_class, text.rstrip())

    def _highlight_text(self, text, next, tag):
        """Highlight the specific changes made to a line by adding
        <ins> and <del> tags.
        """
        next = next[2:]
        new_text = []
        start = 0
        for match in self.highlight_regex.finditer(next):
            new_text.append(text[start:match.start()])
            new_text.append('<%s>' % tag)
            new_text.append(text[match.start():match.end()])
            new_text.append('</%s>' % tag)
            start = match.end()
        new_text.append(text[start:])
        return ''.join(new_text)
