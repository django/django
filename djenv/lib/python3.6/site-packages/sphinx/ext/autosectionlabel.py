# -*- coding: utf-8 -*-
"""
    sphinx.ext.autosectionlabel
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~

    Allow reference sections by :ref: role using its title.

    :copyright: Copyright 2007-2019 by the Sphinx team, see AUTHORS.
    :license: BSD, see LICENSE for details.
"""

from docutils import nodes

from sphinx.locale import __
from sphinx.util import logging
from sphinx.util.nodes import clean_astext

if False:
    # For type annotation
    from typing import Any, Dict  # NOQA
    from sphinx.application import Sphinx  # NOQA


logger = logging.getLogger(__name__)

if False:
    # For type annotation
    from typing import Any, Dict  # NOQA
    from sphinx.application import Sphinx  # NOQA


def register_sections_as_label(app, document):
    # type: (Sphinx, nodes.Node) -> None
    labels = app.env.domaindata['std']['labels']
    anonlabels = app.env.domaindata['std']['anonlabels']
    for node in document.traverse(nodes.section):
        labelid = node['ids'][0]
        docname = app.env.docname
        ref_name = getattr(node[0], 'rawsource', node[0].astext())
        if app.config.autosectionlabel_prefix_document:
            name = nodes.fully_normalize_name(docname + ':' + ref_name)
        else:
            name = nodes.fully_normalize_name(ref_name)
        sectname = clean_astext(node[0])

        if name in labels:
            logger.warning(__('duplicate label %s, other instance in %s'),
                           name, app.env.doc2path(labels[name][0]),
                           location=node)

        anonlabels[name] = docname, labelid
        labels[name] = docname, labelid, sectname


def setup(app):
    # type: (Sphinx) -> Dict[unicode, Any]
    app.add_config_value('autosectionlabel_prefix_document', False, 'env')
    app.connect('doctree-read', register_sections_as_label)

    return {
        'version': 'builtin',
        'parallel_read_safe': True,
        'parallel_write_safe': True,
    }
