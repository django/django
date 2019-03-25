# -*- coding: utf-8 -*-
"""
    sphinx.builders.xml
    ~~~~~~~~~~~~~~~~~~~

    Docutils-native XML and pseudo-XML builders.

    :copyright: Copyright 2007-2019 by the Sphinx team, see AUTHORS.
    :license: BSD, see LICENSE for details.
"""

import codecs
from os import path

from docutils import nodes
from docutils.io import StringOutput
from docutils.writers.docutils_xml import XMLTranslator

from sphinx.builders import Builder
from sphinx.locale import __
from sphinx.util import logging
from sphinx.util.osutil import ensuredir, os_path
from sphinx.writers.xml import XMLWriter, PseudoXMLWriter

if False:
    # For type annotation
    from typing import Any, Dict, Iterator, Set  # NOQA
    from sphinx.application import Sphinx  # NOQA

logger = logging.getLogger(__name__)


class XMLBuilder(Builder):
    """
    Builds Docutils-native XML.
    """
    name = 'xml'
    format = 'xml'
    epilog = __('The XML files are in %(outdir)s.')

    out_suffix = '.xml'
    allow_parallel = True

    _writer_class = XMLWriter
    default_translator_class = XMLTranslator

    def init(self):
        # type: () -> None
        pass

    def get_outdated_docs(self):
        # type: () -> Iterator[unicode]
        for docname in self.env.found_docs:
            if docname not in self.env.all_docs:
                yield docname
                continue
            targetname = self.env.doc2path(docname, self.outdir,
                                           self.out_suffix)
            try:
                targetmtime = path.getmtime(targetname)
            except Exception:
                targetmtime = 0
            try:
                srcmtime = path.getmtime(self.env.doc2path(docname))
                if srcmtime > targetmtime:
                    yield docname
            except EnvironmentError:
                # source doesn't exist anymore
                pass

    def get_target_uri(self, docname, typ=None):
        # type: (unicode, unicode) -> unicode
        return docname

    def prepare_writing(self, docnames):
        # type: (Set[unicode]) -> None
        self.writer = self._writer_class(self)

    def write_doc(self, docname, doctree):
        # type: (unicode, nodes.Node) -> None
        # work around multiple string % tuple issues in docutils;
        # replace tuples in attribute values with lists
        doctree = doctree.deepcopy()
        for node in doctree.traverse(nodes.Element):
            for att, value in node.attributes.items():
                if isinstance(value, tuple):
                    node.attributes[att] = list(value)
                value = node.attributes[att]
                if isinstance(value, list):
                    for i, val in enumerate(value):
                        if isinstance(val, tuple):
                            value[i] = list(val)
        destination = StringOutput(encoding='utf-8')
        self.writer.write(doctree, destination)
        outfilename = path.join(self.outdir, os_path(docname) + self.out_suffix)
        ensuredir(path.dirname(outfilename))
        try:
            with codecs.open(outfilename, 'w', 'utf-8') as f:  # type: ignore
                f.write(self.writer.output)
        except (IOError, OSError) as err:
            logger.warning(__("error writing file %s: %s"), outfilename, err)

    def finish(self):
        # type: () -> None
        pass


class PseudoXMLBuilder(XMLBuilder):
    """
    Builds pseudo-XML for display purposes.
    """
    name = 'pseudoxml'
    format = 'pseudoxml'
    epilog = __('The pseudo-XML files are in %(outdir)s.')

    out_suffix = '.pseudoxml'

    _writer_class = PseudoXMLWriter


def setup(app):
    # type: (Sphinx) -> Dict[unicode, Any]
    app.add_builder(XMLBuilder)
    app.add_builder(PseudoXMLBuilder)

    app.add_config_value('xml_pretty', True, 'env')

    return {
        'version': 'builtin',
        'parallel_read_safe': True,
        'parallel_write_safe': True,
    }
