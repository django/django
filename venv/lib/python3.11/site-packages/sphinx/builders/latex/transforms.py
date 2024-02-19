"""Transforms for LaTeX builder."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, cast

from docutils import nodes
from docutils.transforms.references import Substitutions

from sphinx import addnodes
from sphinx.builders.latex.nodes import (
    captioned_literal_block,
    footnotemark,
    footnotetext,
    math_reference,
    thebibliography,
)
from sphinx.domains.citation import CitationDomain
from sphinx.locale import __
from sphinx.transforms import SphinxTransform
from sphinx.transforms.post_transforms import SphinxPostTransform
from sphinx.util.nodes import NodeMatcher

if TYPE_CHECKING:
    from docutils.nodes import Element, Node

    from sphinx.application import Sphinx

URI_SCHEMES = ('mailto:', 'http:', 'https:', 'ftp:')


class FootnoteDocnameUpdater(SphinxTransform):
    """Add docname to footnote and footnote_reference nodes."""
    default_priority = 700
    TARGET_NODES = (nodes.footnote, nodes.footnote_reference)

    def apply(self, **kwargs: Any) -> None:
        matcher = NodeMatcher(*self.TARGET_NODES)
        for node in self.document.findall(matcher):  # type: Element
            node['docname'] = self.env.docname


class SubstitutionDefinitionsRemover(SphinxPostTransform):
    """Remove ``substitution_definition`` nodes from doctrees."""

    # should be invoked after Substitutions process
    default_priority = Substitutions.default_priority + 1
    formats = ('latex',)

    def run(self, **kwargs: Any) -> None:
        for node in list(self.document.findall(nodes.substitution_definition)):
            node.parent.remove(node)


class ShowUrlsTransform(SphinxPostTransform):
    """Expand references to inline text or footnotes.

    For more information, see :confval:`latex_show_urls`.

    .. note:: This transform is used for integrated doctree
    """
    default_priority = 400
    formats = ('latex',)

    # references are expanded to footnotes (or not)
    expanded = False

    def run(self, **kwargs: Any) -> None:
        try:
            # replace id_prefix temporarily
            settings: Any = self.document.settings
            id_prefix = settings.id_prefix
            settings.id_prefix = 'show_urls'

            self.expand_show_urls()
            if self.expanded:
                self.renumber_footnotes()
        finally:
            # restore id_prefix
            settings.id_prefix = id_prefix

    def expand_show_urls(self) -> None:
        show_urls = self.config.latex_show_urls
        if show_urls is False or show_urls == 'no':
            return

        for node in list(self.document.findall(nodes.reference)):
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

    def get_docname_for_node(self, node: Node) -> str:
        while node:
            if isinstance(node, nodes.document):
                return self.env.path2doc(node['source']) or ''
            elif isinstance(node, addnodes.start_of_file):
                return node['docname']
            else:
                node = node.parent

        try:
            source = node['source']  # type: ignore[index]
        except TypeError:
            raise ValueError(__('Failed to get a docname!')) from None
        raise ValueError(__('Failed to get a docname '
                            'for source {source!r}!').format(source=source))

    def create_footnote(
        self, uri: str, docname: str,
    ) -> tuple[nodes.footnote, nodes.footnote_reference]:
        reference = nodes.reference('', nodes.Text(uri), refuri=uri, nolinkurl=True)
        footnote = nodes.footnote(uri, auto=1, docname=docname)
        footnote['names'].append('#')
        footnote += nodes.label('', '#')
        footnote += nodes.paragraph('', '', reference)
        self.document.note_autofootnote(footnote)

        footnote_ref = nodes.footnote_reference('[#]_', auto=1,
                                                refid=footnote['ids'][0], docname=docname)
        footnote_ref += nodes.Text('#')
        self.document.note_autofootnote_ref(footnote_ref)
        footnote.add_backref(footnote_ref['ids'][0])

        return footnote, footnote_ref

    def renumber_footnotes(self) -> None:
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
            old_label = cast(nodes.label, footnote[0])
            old_label.replace_self(nodes.label('', str(num)))
            if old_label in footnote['names']:
                footnote['names'].remove(old_label.astext())
            footnote['names'].append(str(num))

            # update footnote_references by new footnote number
            docname = footnote['docname']
            for ref in collector.footnote_refs:
                if docname == ref['docname'] and footnote['ids'][0] == ref['refid']:
                    ref.remove(ref[0])
                    ref += nodes.Text(str(num))


class FootnoteCollector(nodes.NodeVisitor):
    """Collect footnotes and footnote references on the document"""

    def __init__(self, document: nodes.document) -> None:
        self.auto_footnotes: list[nodes.footnote] = []
        self.used_footnote_numbers: set[str] = set()
        self.footnote_refs: list[nodes.footnote_reference] = []
        super().__init__(document)

    def unknown_visit(self, node: Node) -> None:
        pass

    def unknown_departure(self, node: Node) -> None:
        pass

    def visit_footnote(self, node: nodes.footnote) -> None:
        if node.get('auto'):
            self.auto_footnotes.append(node)
        else:
            for name in node['names']:
                self.used_footnote_numbers.add(name)

    def visit_footnote_reference(self, node: nodes.footnote_reference) -> None:
        self.footnote_refs.append(node)


class LaTeXFootnoteTransform(SphinxPostTransform):
    """Convert footnote definitions and references to appropriate form to LaTeX.

    * Replace footnotes on restricted zone (e.g. headings) by footnotemark node.
      In addition, append a footnotetext node after the zone.

      Before::

          <section>
              <title>
                  headings having footnotes
                  <footnote_reference>
                      1
              <footnote ids="id1">
                  <label>
                      1
                  <paragraph>
                      footnote body

      After::

          <section>
              <title>
                  headings having footnotes
                  <footnotemark refid="id1">
                      1
              <footnotetext ids="id1">
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

          <footnote ids="id1">
              <label>
                  1
              <paragraph>
                  footnote body

      After::

          blah blah blah
          <footnote ids="id1">
              <label>
                  1
              <paragraph>
                  footnote body
          blah blah blah ...

    * Replace second and subsequent footnote references which refers same footnote definition
      by footnotemark node.  Additionally, the footnote definition node is marked as
      "referred".

      Before::

          blah blah blah
          <footnote_reference refid="id1">
              1
          blah blah blah
          <footnote_reference refid="id1">
              1
          blah blah blah ...

          <footnote ids="id1">
              <label>
                  1
              <paragraph>
                  footnote body

      After::

          blah blah blah
          <footnote ids="id1" referred=True>
              <label>
                  1
              <paragraph>
                  footnote body
          blah blah blah
          <footnotemark refid="id1">
              1
          blah blah blah ...

    * Remove unreferenced footnotes

      Before::

          <footnote ids="id1">
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
                  <footnote_reference refid="id1">
                      1
              <tgroup>
                  <thead>
                      <row>
                          <entry>
                              header having footnote_reference
                              <footnote_reference refid="id2">
                                  2
                  <tbody>
                      <row>
                      ...

          <footnote ids="id1">
              <label>
                  1
              <paragraph>
                  footnote body

          <footnote ids="id2">
              <label>
                  2
              <paragraph>
                  footnote body

      After::

          <table>
              <title>
                  title having footnote_reference
                  <footnotemark refid="id1">
                      1
              <tgroup>
                  <thead>
                      <row>
                          <entry>
                              header having footnote_reference
                              <footnotemark refid="id2">
                                  2
                  <tbody>
                      <footnotetext ids="id1">
                          <label>
                              1
                          <paragraph>
                              footnote body

                      <footnotetext ids="id2">
                          <label>
                              2
                          <paragraph>
                              footnote body
                      <row>
                      ...
    """

    default_priority = 600
    formats = ('latex',)

    def run(self, **kwargs: Any) -> None:
        footnotes = list(self.document.findall(nodes.footnote))
        for node in footnotes:
            node.parent.remove(node)

        visitor = LaTeXFootnoteVisitor(self.document, footnotes)
        self.document.walkabout(visitor)


class LaTeXFootnoteVisitor(nodes.NodeVisitor):
    def __init__(self, document: nodes.document, footnotes: list[nodes.footnote]) -> None:
        self.appeared: dict[tuple[str, str], nodes.footnote] = {}
        self.footnotes: list[nodes.footnote] = footnotes
        self.pendings: list[nodes.footnote] = []
        self.table_footnotes: list[nodes.footnote] = []
        self.restricted: Element | None = None
        super().__init__(document)

    def unknown_visit(self, node: Node) -> None:
        pass

    def unknown_departure(self, node: Node) -> None:
        pass

    def restrict(self, node: Element) -> None:
        if self.restricted is None:
            self.restricted = node

    def unrestrict(self, node: Element) -> None:
        if self.restricted == node:
            self.restricted = None
            pos = node.parent.index(node)
            for i, footnote, in enumerate(self.pendings):
                fntext = footnotetext('', *footnote.children, ids=footnote['ids'])
                node.parent.insert(pos + i + 1, fntext)
            self.pendings = []

    def visit_figure(self, node: nodes.figure) -> None:
        self.restrict(node)

    def depart_figure(self, node: nodes.figure) -> None:
        self.unrestrict(node)

    def visit_term(self, node: nodes.term) -> None:
        self.restrict(node)

    def depart_term(self, node: nodes.term) -> None:
        self.unrestrict(node)

    def visit_caption(self, node: nodes.caption) -> None:
        self.restrict(node)

    def depart_caption(self, node: nodes.caption) -> None:
        self.unrestrict(node)

    def visit_title(self, node: nodes.title) -> None:
        if isinstance(node.parent, (nodes.section, nodes.table)):
            self.restrict(node)

    def depart_title(self, node: nodes.title) -> None:
        if isinstance(node.parent, nodes.section):
            self.unrestrict(node)
        elif isinstance(node.parent, nodes.table):
            self.table_footnotes += self.pendings
            self.pendings = []
            self.unrestrict(node)

    def visit_thead(self, node: nodes.thead) -> None:
        self.restrict(node)

    def depart_thead(self, node: nodes.thead) -> None:
        self.table_footnotes += self.pendings
        self.pendings = []
        self.unrestrict(node)

    def depart_table(self, node: nodes.table) -> None:
        tbody = next(node.findall(nodes.tbody))
        for footnote in reversed(self.table_footnotes):
            fntext = footnotetext('', *footnote.children, ids=footnote['ids'])
            tbody.insert(0, fntext)

        self.table_footnotes = []

    def visit_footnote(self, node: nodes.footnote) -> None:
        self.restrict(node)

    def depart_footnote(self, node: nodes.footnote) -> None:
        self.unrestrict(node)

    def visit_footnote_reference(self, node: nodes.footnote_reference) -> None:
        number = node.astext().strip()
        docname = node['docname']
        if (docname, number) in self.appeared:
            footnote = self.appeared[(docname, number)]
            footnote["referred"] = True

            mark = footnotemark('', number, refid=node['refid'])
            node.replace_self(mark)
        else:
            footnote = self.get_footnote_by_reference(node)
            if self.restricted:
                mark = footnotemark('', number, refid=node['refid'])
                node.replace_self(mark)
                self.pendings.append(footnote)
            else:
                self.footnotes.remove(footnote)
                node.replace_self(footnote)
                footnote.walkabout(self)

            self.appeared[(docname, number)] = footnote
        raise nodes.SkipNode

    def get_footnote_by_reference(self, node: nodes.footnote_reference) -> nodes.footnote:
        docname = node['docname']
        for footnote in self.footnotes:
            if docname == footnote['docname'] and footnote['ids'][0] == node['refid']:
                return footnote

        raise ValueError(__('No footnote was found for given reference node %r') % node)


class BibliographyTransform(SphinxPostTransform):
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
    formats = ('latex',)

    def run(self, **kwargs: Any) -> None:
        citations = thebibliography()
        for node in list(self.document.findall(nodes.citation)):
            node.parent.remove(node)
            citations += node

        if len(citations) > 0:
            self.document += citations


class CitationReferenceTransform(SphinxPostTransform):
    """Replace pending_xref nodes for citation by citation_reference.

    To handle citation reference easily on LaTeX writer, this converts
    pending_xref nodes to citation_reference.
    """
    default_priority = 5  # before ReferencesResolver
    formats = ('latex',)

    def run(self, **kwargs: Any) -> None:
        domain = cast(CitationDomain, self.env.get_domain('citation'))
        matcher = NodeMatcher(addnodes.pending_xref, refdomain='citation', reftype='ref')
        for node in self.document.findall(matcher):  # type: addnodes.pending_xref
            docname, labelid, _ = domain.citations.get(node['reftarget'], ('', '', 0))
            if docname:
                citation_ref = nodes.citation_reference('', '', *node.children,
                                                        docname=docname, refname=labelid)
                node.replace_self(citation_ref)


class MathReferenceTransform(SphinxPostTransform):
    """Replace pending_xref nodes for math by math_reference.

    To handle math reference easily on LaTeX writer, this converts pending_xref
    nodes to math_reference.
    """
    default_priority = 5  # before ReferencesResolver
    formats = ('latex',)

    def run(self, **kwargs: Any) -> None:
        equations = self.env.get_domain('math').data['objects']
        for node in self.document.findall(addnodes.pending_xref):
            if node['refdomain'] == 'math' and node['reftype'] in ('eq', 'numref'):
                docname, _ = equations.get(node['reftarget'], (None, None))
                if docname:
                    refnode = math_reference('', docname=docname, target=node['reftarget'])
                    node.replace_self(refnode)


class LiteralBlockTransform(SphinxPostTransform):
    """Replace container nodes for literal_block by captioned_literal_block."""
    default_priority = 400
    formats = ('latex',)

    def run(self, **kwargs: Any) -> None:
        matcher = NodeMatcher(nodes.container, literal_block=True)
        for node in self.document.findall(matcher):  # type: nodes.container
            newnode = captioned_literal_block('', *node.children, **node.attributes)
            node.replace_self(newnode)


class DocumentTargetTransform(SphinxPostTransform):
    """Add :doc label to the first section of each document."""
    default_priority = 400
    formats = ('latex',)

    def run(self, **kwargs: Any) -> None:
        for node in self.document.findall(addnodes.start_of_file):
            section = node.next_node(nodes.section)
            if section:
                section['ids'].append(':doc')  # special label for :doc:


class IndexInSectionTitleTransform(SphinxPostTransform):
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
    formats = ('latex',)

    def run(self, **kwargs: Any) -> None:
        for node in list(self.document.findall(nodes.title)):
            if isinstance(node.parent, nodes.section):
                for i, index in enumerate(node.findall(addnodes.index)):
                    # move the index node next to the section title
                    node.remove(index)
                    node.parent.insert(i + 1, index)


def setup(app: Sphinx) -> dict[str, Any]:
    app.add_transform(FootnoteDocnameUpdater)
    app.add_post_transform(SubstitutionDefinitionsRemover)
    app.add_post_transform(BibliographyTransform)
    app.add_post_transform(CitationReferenceTransform)
    app.add_post_transform(DocumentTargetTransform)
    app.add_post_transform(IndexInSectionTitleTransform)
    app.add_post_transform(LaTeXFootnoteTransform)
    app.add_post_transform(LiteralBlockTransform)
    app.add_post_transform(MathReferenceTransform)
    app.add_post_transform(ShowUrlsTransform)

    return {
        'version': 'builtin',
        'parallel_read_safe': True,
        'parallel_write_safe': True,
    }
