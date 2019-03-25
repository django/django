# -*- coding: utf-8 -*-
"""
    sphinx.domains.math
    ~~~~~~~~~~~~~~~~~~~

    The math domain.

    :copyright: Copyright 2007-2019 by the Sphinx team, see AUTHORS.
    :license: BSD, see LICENSE for details.
"""

from docutils import nodes
from docutils.nodes import make_id

from sphinx.addnodes import math_block as displaymath
from sphinx.domains import Domain
from sphinx.locale import __
from sphinx.roles import XRefRole
from sphinx.util import logging
from sphinx.util.nodes import make_refnode

if False:
    # For type annotation
    from typing import Any, Callable, Dict, Iterable, List, Tuple, Union  # NOQA
    from sphinx.application import Sphinx  # NOQA
    from sphinx.builders import Builder  # NOQA
    from sphinx.environment import BuildEnvironment  # NOQA
    from sphinx.util.typing import RoleFunction  # NOQA

logger = logging.getLogger(__name__)


class MathReferenceRole(XRefRole):
    def result_nodes(self, document, env, node, is_ref):
        # type: (nodes.Node, BuildEnvironment, nodes.Node, bool) -> Tuple[List[nodes.Node], List[nodes.Node]]  # NOQA
        node['refdomain'] = 'math'
        return [node], []


class MathDomain(Domain):
    """Mathematics domain."""
    name = 'math'
    label = 'mathematics'

    initial_data = {
        'objects': {},  # labelid -> (docname, eqno)
        'has_equations': {},  # docname -> bool
    }  # type: Dict[unicode, Dict[unicode, Tuple[unicode, int]]]
    dangling_warnings = {
        'eq': 'equation not found: %(target)s',
    }
    enumerable_nodes = {  # node_class -> (figtype, title_getter)
        displaymath: ('displaymath', None),
        nodes.math_block: ('displaymath', None),
    }  # type: Dict[nodes.Node, Tuple[unicode, Callable]]
    roles = {
        'numref': MathReferenceRole(),
    }

    def process_doc(self, env, docname, document):
        # type: (BuildEnvironment, unicode, nodes.Node) -> None
        def math_node(node):
            return isinstance(node, (nodes.math, nodes.math_block))

        self.data['has_equations'][docname] = any(document.traverse(math_node))

    def clear_doc(self, docname):
        # type: (unicode) -> None
        for equation_id, (doc, eqno) in list(self.data['objects'].items()):
            if doc == docname:
                del self.data['objects'][equation_id]

        self.data['has_equations'].pop(docname, None)

    def merge_domaindata(self, docnames, otherdata):
        # type: (Iterable[unicode], Dict) -> None
        for labelid, (doc, eqno) in otherdata['objects'].items():
            if doc in docnames:
                self.data['objects'][labelid] = (doc, eqno)

        for docname in docnames:
            self.data['has_equations'][docname] = otherdata['has_equations'][docname]

    def resolve_xref(self, env, fromdocname, builder, typ, target, node, contnode):
        # type: (BuildEnvironment, unicode, Builder, unicode, unicode, nodes.Node, nodes.Node) -> nodes.Node  # NOQA
        assert typ in ('eq', 'numref')
        docname, number = self.data['objects'].get(target, (None, None))
        if docname:
            # TODO: perhaps use rather a sphinx-core provided prefix here?
            node_id = make_id('equation-%s' % target)
            if env.config.math_numfig and env.config.numfig:
                if docname in env.toc_fignumbers:
                    number = env.toc_fignumbers[docname]['displaymath'].get(node_id, ())
                    number = '.'.join(map(str, number))
                else:
                    number = ''
            try:
                eqref_format = env.config.math_eqref_format or "({number})"
                title = nodes.Text(eqref_format.format(number=number))
            except KeyError as exc:
                logger.warning(__('Invalid math_eqref_format: %r'), exc,
                               location=node)
                title = nodes.Text("(%d)" % number)
                title = nodes.Text("(%d)" % number)
            return make_refnode(builder, fromdocname, docname, node_id, title)
        else:
            return None

    def resolve_any_xref(self, env, fromdocname, builder, target, node, contnode):
        # type: (BuildEnvironment, unicode, Builder, unicode, nodes.Node, nodes.Node) -> List[nodes.Node]  # NOQA
        refnode = self.resolve_xref(env, fromdocname, builder, 'eq', target, node, contnode)
        if refnode is None:
            return []
        else:
            return [refnode]

    def get_objects(self):
        # type: () -> List
        return []

    def add_equation(self, env, docname, labelid):
        # type: (BuildEnvironment, unicode, unicode) -> int
        equations = self.data['objects']
        if labelid in equations:
            path = env.doc2path(equations[labelid][0])
            msg = __('duplicate label of equation %s, other instance in %s') % (labelid, path)
            raise UserWarning(msg)
        else:
            eqno = self.get_next_equation_number(docname)
            equations[labelid] = (docname, eqno)
            return eqno

    def get_next_equation_number(self, docname):
        # type: (unicode) -> int
        targets = [eq for eq in self.data['objects'].values() if eq[0] == docname]
        return len(targets) + 1

    def has_equations(self):
        # type: () -> bool
        return any(self.data['has_equations'].values())


def setup(app):
    # type: (Sphinx) -> Dict[unicode, Any]
    app.add_domain(MathDomain)
    app.add_role('eq', MathReferenceRole(warn_dangling=True))

    return {
        'version': 'builtin',
        'env_version': 2,
        'parallel_read_safe': True,
        'parallel_write_safe': True,
    }
