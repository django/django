"""The citation domain."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, cast

from docutils import nodes

from sphinx.addnodes import pending_xref
from sphinx.domains import Domain
from sphinx.locale import __
from sphinx.transforms import SphinxTransform
from sphinx.util import logging
from sphinx.util.nodes import copy_source_info, make_refnode

if TYPE_CHECKING:
    from docutils.nodes import Element

    from sphinx.application import Sphinx
    from sphinx.builders import Builder
    from sphinx.environment import BuildEnvironment


logger = logging.getLogger(__name__)


class CitationDomain(Domain):
    """Domain for citations."""

    name = 'citation'
    label = 'citation'

    dangling_warnings = {
        'ref': 'citation not found: %(target)s',
    }

    @property
    def citations(self) -> dict[str, tuple[str, str, int]]:
        return self.data.setdefault('citations', {})

    @property
    def citation_refs(self) -> dict[str, set[str]]:
        return self.data.setdefault('citation_refs', {})

    def clear_doc(self, docname: str) -> None:
        for key, (fn, _l, _lineno) in list(self.citations.items()):
            if fn == docname:
                del self.citations[key]
        for key, docnames in list(self.citation_refs.items()):
            if docnames == {docname}:
                del self.citation_refs[key]
            elif docname in docnames:
                docnames.remove(docname)

    def merge_domaindata(self, docnames: list[str], otherdata: dict[str, Any]) -> None:
        # XXX duplicates?
        for key, data in otherdata['citations'].items():
            if data[0] in docnames:
                self.citations[key] = data
        for key, data in otherdata['citation_refs'].items():
            citation_refs = self.citation_refs.setdefault(key, set())
            for docname in data:
                if docname in docnames:
                    citation_refs.add(docname)

    def note_citation(self, node: nodes.citation) -> None:
        label = node[0].astext()
        if label in self.citations:
            path = self.env.doc2path(self.citations[label][0])
            logger.warning(__('duplicate citation %s, other instance in %s'), label, path,
                           location=node, type='ref', subtype='citation')
        self.citations[label] = (node['docname'], node['ids'][0], node.line)

    def note_citation_reference(self, node: pending_xref) -> None:
        docnames = self.citation_refs.setdefault(node['reftarget'], set())
        docnames.add(self.env.docname)

    def check_consistency(self) -> None:
        for name, (docname, _labelid, lineno) in self.citations.items():
            if name not in self.citation_refs:
                logger.warning(__('Citation [%s] is not referenced.'), name,
                               type='ref', subtype='citation', location=(docname, lineno))

    def resolve_xref(self, env: BuildEnvironment, fromdocname: str, builder: Builder,
                     typ: str, target: str, node: pending_xref, contnode: Element,
                     ) -> Element | None:
        docname, labelid, lineno = self.citations.get(target, ('', '', 0))
        if not docname:
            return None

        return make_refnode(builder, fromdocname, docname,
                            labelid, contnode)

    def resolve_any_xref(self, env: BuildEnvironment, fromdocname: str, builder: Builder,
                         target: str, node: pending_xref, contnode: Element,
                         ) -> list[tuple[str, Element]]:
        refnode = self.resolve_xref(env, fromdocname, builder, 'ref', target, node, contnode)
        if refnode is None:
            return []
        else:
            return [('ref', refnode)]


class CitationDefinitionTransform(SphinxTransform):
    """Mark citation definition labels as not smartquoted."""
    default_priority = 619

    def apply(self, **kwargs: Any) -> None:
        domain = cast(CitationDomain, self.env.get_domain('citation'))
        for node in self.document.findall(nodes.citation):
            # register citation node to domain
            node['docname'] = self.env.docname
            domain.note_citation(node)

            # mark citation labels as not smartquoted
            label = cast(nodes.label, node[0])
            label['support_smartquotes'] = False


class CitationReferenceTransform(SphinxTransform):
    """
    Replace citation references by pending_xref nodes before the default
    docutils transform tries to resolve them.
    """
    default_priority = 619

    def apply(self, **kwargs: Any) -> None:
        domain = cast(CitationDomain, self.env.get_domain('citation'))
        for node in self.document.findall(nodes.citation_reference):
            target = node.astext()
            ref = pending_xref(target, refdomain='citation', reftype='ref',
                               reftarget=target, refwarn=True,
                               support_smartquotes=False,
                               ids=node["ids"],
                               classes=node.get('classes', []))
            ref += nodes.inline(target, '[%s]' % target)
            copy_source_info(node, ref)
            node.replace_self(ref)

            # register reference node to domain
            domain.note_citation_reference(ref)


def setup(app: Sphinx) -> dict[str, Any]:
    app.add_domain(CitationDomain)
    app.add_transform(CitationDefinitionTransform)
    app.add_transform(CitationReferenceTransform)

    return {
        'version': 'builtin',
        'env_version': 1,
        'parallel_read_safe': True,
        'parallel_write_safe': True,
    }
