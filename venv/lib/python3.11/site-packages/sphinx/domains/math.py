"""The math domain."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from docutils import nodes
from docutils.nodes import Element, Node, make_id, system_message

from sphinx.domains import Domain
from sphinx.locale import __
from sphinx.roles import XRefRole
from sphinx.util import logging
from sphinx.util.nodes import make_refnode

if TYPE_CHECKING:
    from collections.abc import Iterable

    from sphinx.addnodes import pending_xref
    from sphinx.application import Sphinx
    from sphinx.builders import Builder
    from sphinx.environment import BuildEnvironment


logger = logging.getLogger(__name__)


class MathReferenceRole(XRefRole):
    def result_nodes(self, document: nodes.document, env: BuildEnvironment, node: Element,
                     is_ref: bool) -> tuple[list[Node], list[system_message]]:
        node['refdomain'] = 'math'
        return [node], []


class MathDomain(Domain):
    """Mathematics domain."""
    name = 'math'
    label = 'mathematics'

    initial_data: dict[str, Any] = {
        'objects': {},  # labelid -> (docname, eqno)
        'has_equations': {},  # docname -> bool
    }
    dangling_warnings = {
        'eq': 'equation not found: %(target)s',
    }
    enumerable_nodes = {  # node_class -> (figtype, title_getter)
        nodes.math_block: ('displaymath', None),
    }
    roles = {
        'numref': MathReferenceRole(),
    }

    @property
    def equations(self) -> dict[str, tuple[str, int]]:
        return self.data.setdefault('objects', {})  # labelid -> (docname, eqno)

    def note_equation(self, docname: str, labelid: str, location: Any = None) -> None:
        if labelid in self.equations:
            other = self.equations[labelid][0]
            logger.warning(__('duplicate label of equation %s, other instance in %s') %
                           (labelid, other), location=location)

        self.equations[labelid] = (docname, self.env.new_serialno('eqno') + 1)

    def get_equation_number_for(self, labelid: str) -> int | None:
        if labelid in self.equations:
            return self.equations[labelid][1]
        else:
            return None

    def process_doc(self, env: BuildEnvironment, docname: str,
                    document: nodes.document) -> None:
        def math_node(node: Node) -> bool:
            return isinstance(node, (nodes.math, nodes.math_block))

        self.data['has_equations'][docname] = any(document.findall(math_node))

    def clear_doc(self, docname: str) -> None:
        for equation_id, (doc, _eqno) in list(self.equations.items()):
            if doc == docname:
                del self.equations[equation_id]

        self.data['has_equations'].pop(docname, None)

    def merge_domaindata(self, docnames: Iterable[str], otherdata: dict[str, Any]) -> None:
        for labelid, (doc, eqno) in otherdata['objects'].items():
            if doc in docnames:
                self.equations[labelid] = (doc, eqno)

        for docname in docnames:
            self.data['has_equations'][docname] = otherdata['has_equations'][docname]

    def resolve_xref(self, env: BuildEnvironment, fromdocname: str, builder: Builder,
                     typ: str, target: str, node: pending_xref, contnode: Element,
                     ) -> Element | None:
        assert typ in ('eq', 'numref')
        result = self.equations.get(target)
        if result:
            docname, number = result
            # TODO: perhaps use rather a sphinx-core provided prefix here?
            node_id = make_id('equation-%s' % target)
            if env.config.math_numfig and env.config.numfig:
                if docname in env.toc_fignumbers:
                    numbers = env.toc_fignumbers[docname]['displaymath'].get(node_id, ())
                    eqno = '.'.join(map(str, numbers))
                else:
                    eqno = ''
            else:
                eqno = str(number)

            try:
                eqref_format = env.config.math_eqref_format or "({number})"
                title = nodes.Text(eqref_format.format(number=eqno))
            except KeyError as exc:
                logger.warning(__('Invalid math_eqref_format: %r'), exc,
                               location=node)
                title = nodes.Text("(%d)" % number)
                title = nodes.Text("(%d)" % number)
            return make_refnode(builder, fromdocname, docname, node_id, title)
        else:
            return None

    def resolve_any_xref(self, env: BuildEnvironment, fromdocname: str, builder: Builder,
                         target: str, node: pending_xref, contnode: Element,
                         ) -> list[tuple[str, Element]]:
        refnode = self.resolve_xref(env, fromdocname, builder, 'eq', target, node, contnode)
        if refnode is None:
            return []
        else:
            return [('eq', refnode)]

    def get_objects(self) -> Iterable[tuple[str, str, str, str, str, int]]:
        return []

    def has_equations(self, docname: str | None = None) -> bool:
        if docname:
            return self.data['has_equations'].get(docname, False)
        else:
            return any(self.data['has_equations'].values())


def setup(app: Sphinx) -> dict[str, Any]:
    app.add_domain(MathDomain)
    app.add_role('eq', MathReferenceRole(warn_dangling=True))

    return {
        'version': 'builtin',
        'env_version': 2,
        'parallel_read_safe': True,
        'parallel_write_safe': True,
    }
