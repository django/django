# -*- coding: utf-8 -*-
"""
    sphinx.builders.latex.transforms
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    Transforms for LaTeX builder.

    :copyright: Copyright 2007-2019 by the Sphinx team, see AUTHORS.
    :license: BSD, see LICENSE for details.
"""

from docutils import nodes

from sphinx import addnodes
from sphinx.builders.latex.nodes import (
    captioned_literal_block, footnotemark, footnotetext, math_reference, thebibliography
)
from sphinx.transforms import SphinxTransform

if False:
    # For type annotation
    from typing import Dict, List, Set, Tuple, Union  # NOQA

URI_SCHEMES = ('mailto:', 'http:', 'https:', 'ftp:')


class FootnoteDocnameUpdater(SphinxTransform):
    """Add docname to footnote and footnote_reference nodes."""
    default_priority = 700
    TARGET_NODES = (nodes.footnote, nodes.footnote_reference)

    def apply(self):
        for node in self.document.traverse(lambda n: isinstance(n, self.TARGET_NODES)):
            node['docname'] = self.env.docname


class ShowUrlsTransform(SphinxTransform):
    """Expand references to inline text or footnotes.

    For more information, see :confval:`latex_show_urls`.

    .. note:: This transform is used for integrated doctree
    """
    default_priority = 400

    # references are expanded to footnotes (or not)
    expanded = False

    def apply(self):
        # type: () -> None
        try:
            # replace id_prefix temporarily
            id_prefix = self.document.settings.id_prefix
            self.document.settings.id_prefix = 'show_urls'

            self.expand_show_urls()
            if self.expanded:
                self.renumber_footnotes()
        finally:
            # restore id_prefix
            self.document.settings.id_prefix = id_prefix

    def expand_show_urls(self):
        # type: () -> None
        show_urls = self.document.settings.env.config.latex_show_urls
        if show_urls is False or show_urls == 'no':
            return

        for node in self.document.traverse(nodes.reference):
            uri = node.get('refuri', '')
            if uri.startswith(URI_SCHEMES):
                if uri.startswith('mailto:'):
                    uri = uri[7:]
                if node.astext() != uri:
                    index = node.parent.index(node)
                    docname = self.get_docname_for_node(node)
                    if show_urls == 'footnote':
                        fn, fnref = self.create_footnote(uri, docname)
                        node.parent.insert(index + 1, fn)
                        node.parent.insert(index + 2, fnref)

                        self.expanded = True
                    else:  # all other true values (b/w compat)
                        textnode = nodes.Text(" (%s)" % uri)
                        node.parent.insert(index + 1, textnode)

    def get_docname_for_node(self, node):
        # type: (nodes.Node) -> unicode
        while node:
            if isinstance(node, nodes.document):
                return self.env.path2doc(node['source'])
            elif isinstance(node, addnodes.start_of_file):
                return node['docname']
            else:
                node = node.parent

        return None  # never reached here. only for type hinting

    def create_footnote(self, uri, docname):
        # type: (unicode, unicode) -> Tuple[nodes.footnote, nodes.footnote_ref]
        label = nodes.label('', '#')
        para = nodes.paragraph()
        para.append(nodes.reference('', nodes.Text(uri), refuri=uri, nolinkurl=True))
        footnote = nodes.footnote(uri, label, para, auto=1, docname=docname)
        footnote['names'].append('#')
        self.document.note_autofootnote(footnote)

        label = nodes.Text('#')
        footnote_ref = nodes.footnote_reference('[#]_', label, auto=1,
                                                refid=footnote['ids'][0], docname=docname)
        self.document.note_autofootnote_ref(footnote_ref)
        footnote.add_backref(footnote_ref['ids'][0])

        return footnote, footnote_ref

    def renumber_footnotes(self):
        # type: () -> None
        collector = FootnoteCollector(self.document)
        self.document.walkabout(collector)

        num = 0
        for footnote in collector.auto_footnotes:
            # search unused footnote number
            while True:
                num += 1
                if str(num) not in collector.used_footnote_numbers:
                    break

            # assign new footnote number
            old_label = footnote[0].astext()
            footnote[0].replace_self(nodes.label('', str(num)))
            if old_label in footnote['names']:
                footnote['names'].remove(old_label)
            footnote['names'].append(str(num))

            # update footnote_references by new footnote number
            docname = footnote['docname']
            for ref in collector.footnote_refs:
                if docname == ref['docname'] and footnote['ids'][0] == ref['refid']:
                    ref.remove(ref[0])
                    ref += nodes.Text(str(num))


class FootnoteCollector(nodes.NodeVisitor):
    """Collect footnotes and footnote references on the document"""

    def __init__(self, document):
        # type: (nodes.document) -> None
        self.auto_footnotes = []            # type: List[nodes.footnote]
        self.used_footnote_numbers = set()  # type: Set[unicode]
        self.footnote_refs = []             # type: List[nodes.footnote_reference]
        nodes.NodeVisitor.__init__(self, document)

    def unknown_visit(self, node):
        # type: (nodes.Node) -> None
        pass

    def unknown_departure(self, node):
        # type: (nodes.Node) -> None
        pass

    def visit_footnote(self, node):
        # type: (nodes.footnote) -> None
        if node.get('auto'):
            self.auto_footnotes.append(node)
        else:
            for name in node['names']:
                self.used_footnote_numbers.add(name)

    def visit_footnote_reference(self, node):
        # type: (nodes.footnote_reference) -> None
        self.footnote_refs.append(node)


class LaTeXFootnoteTransform(SphinxTransform):
    """Convert footnote definitions and references to appropriate form to LaTeX.

    * Replace footnotes on restricted zone (e.g. headings) by footnotemark node.
      In addition, append a footnotetext node after the zone.

      Before::

          <section>
              <title>
                  headings having footnotes
                  <footnote_reference>
                      1
              <footnote ids="1">
                  <label>
                      1
                  <paragraph>
                      footnote body

      After::

          <section>
              <title>
                  headings having footnotes
                  <footnotemark>
                      1
              <footnotetext>
                  footnote body
              <footnotetext>
                  <label>
                      1
                  <paragraph>
                      footnote body

    * Integrate footnote definitions and footnote references to single footnote node

      Before::

          blah blah blah
          <footnote_reference refid="id1">
              1
          blah blah blah ...

          <footnote ids="1">
              <label>
                  1
              <paragraph>
                  footnote body

      After::

          blah blah blah
          <footnote ids="1">
              <label>
                  1
              <paragraph>
                  footnote body
          blah blah blah ...

    * Replace second and subsequent footnote references which refers same footnote definition
      by footnotemark node.

      Before::

          blah blah blah
          <footnote_reference refid="id1">
              1
          blah blah blah
          <footnote_reference refid="id1">
              1
          blah blah blah ...

          <footnote ids="1">
              <label>
                  1
              <paragraph>
                  footnote body

      After::

          blah blah blah
          <footnote ids="1">
              <label>
                  1
              <paragraph>
                  footnote body
          blah blah blah
          <footnotemark>
              1
          blah blah blah ...

    * Remove unreferenced footnotes

      Before::

          <footnote ids="1">
              <label>
                  1
              <paragraph>
                  Unreferenced footnote!

      After::

          <!-- nothing! -->

    * Move footnotes in a title of table or thead to head of tbody

      Before::

          <table>
              <title>
                  title having footnote_reference
                  <footnote_reference refid="1">
                      1
              <tgroup>
                  <thead>
                      <row>
                          <entry>
                              header having footnote_reference
                              <footnote_reference refid="2">
                                  2
                  <tbody>
                      <row>
                      ...

          <footnote ids="1">
              <label>
                  1
              <paragraph>
                  footnote body

          <footnote ids="2">
              <label>
                  2
              <paragraph>
                  footnote body

      After::

          <table>
              <title>
                  title having footnote_reference
                  <footnotemark>
                      1
              <tgroup>
                  <thead>
                      <row>
                          <entry>
                              header having footnote_reference
                              <footnotemark>
                                  2
                  <tbody>
                      <footnotetext>
                          <label>
                              1
                          <paragraph>
                              footnote body

                      <footnotetext>
                          <label>
                              2
                          <paragraph>
                              footnote body
                      <row>
                      ...
    """

    default_priority = 600

    def apply(self):
        footnotes = list(self.document.traverse(nodes.footnote))
        for node in footnotes:
            node.parent.remove(node)

        visitor = LaTeXFootnoteVisitor(self.document, footnotes)
        self.document.walkabout(visitor)


class LaTeXFootnoteVisitor(nodes.NodeVisitor):
    def __init__(self, document, footnotes):
        # type: (nodes.document, List[nodes.footnote]) -> None
        self.appeared = set()       # type: Set[Tuple[unicode, nodes.footnote]]
        self.footnotes = footnotes  # type: List[nodes.footnote]
        self.pendings = []          # type: List[nodes.Node]
        self.table_footnotes = []   # type: List[nodes.Node]
        self.restricted = None      # type: nodes.Node
        nodes.NodeVisitor.__init__(self, document)

    def unknown_visit(self, node):
        # type: (nodes.Node) -> None
        pass

    def unknown_departure(self, node):
        # type: (nodes.Node) -> None
        pass

    def restrict(self, node):
        # type: (nodes.Node) -> None
        if self.restricted is None:
            self.restricted = node

    def unrestrict(self, node):
        # type: (nodes.Node) -> None
        if self.restricted == node:
            self.restricted = None
            pos = node.parent.index(node)
            for i, footnote, in enumerate(self.pendings):
                fntext = footnotetext('', *footnote.children)
                node.parent.insert(pos + i + 1, fntext)
            self.pendings = []

    def visit_figure(self, node):
        # type: (nodes.Node) -> None
        self.restrict(node)

    def depart_figure(self, node):
        # type: (nodes.Node) -> None
        self.unrestrict(node)

    def visit_term(self, node):
        # type: (nodes.Node) -> None
        self.restrict(node)

    def depart_term(self, node):
        # type: (nodes.Node) -> None
        self.unrestrict(node)

    def visit_caption(self, node):
        # type: (nodes.Node) -> None
        self.restrict(node)

    def depart_caption(self, node):
        # type: (nodes.Node) -> None
        self.unrestrict(node)

    def visit_title(self, node):
        # type: (nodes.Node) -> None
        if isinstance(node.parent, (nodes.section, nodes.table)):
            self.restrict(node)

    def depart_title(self, node):
        # type: (nodes.Node) -> None
        if isinstance(node.parent, nodes.section):
            self.unrestrict(node)
        elif isinstance(node.parent, nodes.table):
            self.table_footnotes += self.pendings
            self.pendings = []
            self.unrestrict(node)

    def visit_thead(self, node):
        # type: (nodes.Node) -> None
        self.restrict(node)

    def depart_thead(self, node):
        # type: (nodes.Node) -> None
        self.table_footnotes += self.pendings
        self.pendings = []
        self.unrestrict(node)

    def depart_table(self, node):
        # type: (nodes.Node) -> None
        tbody = list(node.traverse(nodes.tbody))[0]
        for footnote in reversed(self.table_footnotes):
            fntext = footnotetext('', *footnote.children)
            tbody.insert(0, fntext)

        self.table_footnotes = []

    def visit_footnote(self, node):
        # type: (nodes.Node) -> None
        self.restrict(node)

    def depart_footnote(self, node):
        # type: (nodes.Node) -> None
        self.unrestrict(node)

    def visit_footnote_reference(self, node):
        # type: (nodes.Node) -> None
        number = node.astext().strip()
        docname = node['docname']
        if self.restricted:
            mark = footnotemark('', number)
            node.replace_self(mark)
            if (docname, number) not in self.appeared:
                footnote = self.get_footnote_by_reference(node)
                self.pendings.append(footnote)
        elif (docname, number) in self.appeared:
            mark = footnotemark('', number)
            node.replace_self(mark)
        else:
            footnote = self.get_footnote_by_reference(node)
            self.footnotes.remove(footnote)
            node.replace_self(footnote)
            footnote.walkabout(self)

        self.appeared.add((docname, number))
        raise nodes.SkipNode

    def get_footnote_by_reference(self, node):
        # type: (nodes.Node) -> nodes.Node
        docname = node['docname']
        for footnote in self.footnotes:
            if docname == footnote['docname'] and footnote['ids'][0] == node['refid']:
                return footnote

        return None


class BibliographyTransform(SphinxTransform):
    """Gather bibliography entries to tail of document.

    Before::

        <document>
            <paragraph>
                blah blah blah
            <citation>
                ...
            <paragraph>
                blah blah blah
            <citation>
                ...
            ...

    After::

        <document>
            <paragraph>
                blah blah blah
            <paragraph>
                blah blah blah
            ...
            <thebibliography>
                <citation>
                    ...
                <citation>
                    ...
    """
    default_priority = 750

    def apply(self):
        # type: () -> None
        citations = thebibliography()
        for node in self.document.traverse(nodes.citation):
            node.parent.remove(node)
            citations += node

        if len(citations) > 0:
            self.document += citations


class CitationReferenceTransform(SphinxTransform):
    """Replace pending_xref nodes for citation by citation_reference.

    To handle citation reference easily on LaTeX writer, this converts
    pending_xref nodes to citation_reference.
    """
    default_priority = 5  # before ReferencesResolver

    def apply(self):
        # type: () -> None
        if self.app.builder.name != 'latex':
            return

        citations = self.env.get_domain('std').data['citations']
        for node in self.document.traverse(addnodes.pending_xref):
            if node['refdomain'] == 'std' and node['reftype'] == 'citation':
                docname, labelid, _ = citations.get(node['reftarget'], ('', '', 0))
                if docname:
                    citation_ref = nodes.citation_reference('', *node.children,
                                                            docname=docname, refname=labelid)
                    node.replace_self(citation_ref)


class MathReferenceTransform(SphinxTransform):
    """Replace pending_xref nodes for math by math_reference.

    To handle math reference easily on LaTeX writer, this converts pending_xref
    nodes to math_reference.
    """
    default_priority = 5  # before ReferencesResolver

    def apply(self):
        # type: () -> None
        if self.app.builder.name != 'latex':
            return

        equations = self.env.get_domain('math').data['objects']
        for node in self.document.traverse(addnodes.pending_xref):
            if node['refdomain'] == 'math' and node['reftype'] in ('eq', 'numref'):
                docname, _ = equations.get(node['reftarget'], (None, None))
                if docname:
                    refnode = math_reference('', docname=docname, target=node['reftarget'])
                    node.replace_self(refnode)


class LiteralBlockTransform(SphinxTransform):
    """Replace container nodes for literal_block by captioned_literal_block."""
    default_priority = 400

    def apply(self):
        # type: () -> None
        if self.app.builder.name != 'latex':
            return

        for node in self.document.traverse(nodes.container):
            if node.get('literal_block') is True:
                newnode = captioned_literal_block('', *node.children, **node.attributes)
                node.replace_self(newnode)


class DocumentTargetTransform(SphinxTransform):
    """Add :doc label to the first section of each document."""
    default_priority = 400

    def apply(self):
        # type: () -> None
        if self.app.builder.name != 'latex':
            return

        for node in self.document.traverse(addnodes.start_of_file):
            section = node.next_node(nodes.section)
            if section:
                section['ids'].append(':doc')  # special label for :doc:


class IndexInSectionTitleTransform(SphinxTransform):
    """Move index nodes in section title to outside of the title.

    LaTeX index macro is not compatible with some handling of section titles
    such as uppercasing done on LaTeX side (cf. fncychap handling of ``\\chapter``).
    Moving the index node to after the title node fixes that.

    Before::

        <section>
            <title>
                blah blah <index entries=[...]/>blah
            <paragraph>
                blah blah blah
            ...

    After::

        <section>
            <title>
                blah blah blah
            <index entries=[...]/>
            <paragraph>
                blah blah blah
            ...
    """
    default_priority = 400

    def apply(self):
        for node in self.document.traverse(nodes.title):
            if isinstance(node.parent, nodes.section):
                for i, index in enumerate(node.traverse(addnodes.index)):
                    # move the index node next to the section title
                    node.remove(index)
                    node.parent.insert(i + 1, index)
