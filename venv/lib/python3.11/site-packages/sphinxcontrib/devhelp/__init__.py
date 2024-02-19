"""Build HTML documentation and Devhelp_ support files.

.. _Devhelp: https://wiki.gnome.org/Apps/Devhelp
"""

from __future__ import annotations

import gzip
import os
import re
from os import path
from typing import Any

from docutils import nodes
from sphinx import addnodes
from sphinx.application import Sphinx
from sphinx.builders.html import StandaloneHTMLBuilder
from sphinx.environment.adapters.indexentries import IndexEntries
from sphinx.locale import get_translation
from sphinx.util import logging
from sphinx.util.nodes import NodeMatcher
from sphinx.util.osutil import make_filename

try:
    import xml.etree.ElementTree as etree
except ImportError:
    import lxml.etree as etree  # type: ignore

__version__ = '1.0.6'
__version_info__ = (1, 0, 6)

logger = logging.getLogger(__name__)
__ = get_translation(__name__, 'console')

package_dir = path.abspath(path.dirname(__file__))


class DevhelpBuilder(StandaloneHTMLBuilder):
    """
    Builder that also outputs GNOME Devhelp file.
    """
    name = 'devhelp'
    epilog = __('To view the help file:\n'
                '$ mkdir -p $HOME/.local/share/devhelp/books\n'
                '$ ln -s $PWD/%(outdir)s $HOME/.local/share/devhelp/books/%(project)s\n'
                '$ devhelp')

    # don't copy the reST source
    copysource = False
    supported_image_types = ['image/png', 'image/gif', 'image/jpeg']

    # don't add links
    add_permalinks = False
    # don't add sidebar etc.
    embedded = True

    def init(self) -> None:
        super().init()
        self.out_suffix = '.html'
        self.link_suffix = '.html'

    def handle_finish(self) -> None:
        self.build_devhelp(self.outdir, self.config.devhelp_basename)

    def build_devhelp(self, outdir: str | os.PathLike[str], outname: str) -> None:
        logger.info(__('dumping devhelp index...'))

        # Basic info
        root = etree.Element('book',
                             title=self.config.html_title,
                             name=self.config.project,
                             link="index.html",
                             version=self.config.version)
        tree = etree.ElementTree(root)

        # TOC
        chapters = etree.SubElement(root, 'chapters')

        tocdoc = self.env.get_and_resolve_doctree(
            self.config.master_doc, self, prune_toctrees=False)

        def write_toc(node: nodes.Node, parent: etree.Element) -> None:
            if isinstance(node, addnodes.compact_paragraph) or \
               isinstance(node, nodes.bullet_list):
                for subnode in node:
                    write_toc(subnode, parent)
            elif isinstance(node, nodes.list_item):
                item = etree.SubElement(parent, 'sub')
                for subnode in node:
                    write_toc(subnode, item)
            elif isinstance(node, nodes.reference):
                parent.attrib['link'] = node['refuri']
                parent.attrib['name'] = node.astext()

        matcher = NodeMatcher(addnodes.compact_paragraph, toctree=Any)
        for node in tocdoc.findall(matcher):  # type: addnodes.compact_paragraph
            write_toc(node, chapters)

        # Index
        functions = etree.SubElement(root, 'functions')
        index = IndexEntries(self.env).create_index(self)

        def write_index(title: str, refs: list[Any], subitems: Any) -> None:
            if len(refs) == 0:
                pass
            elif len(refs) == 1:
                etree.SubElement(functions, 'function',
                                 name=title, link=refs[0][1])
            else:
                for i, ref in enumerate(refs):
                    etree.SubElement(functions, 'function',
                                     name="[%d] %s" % (i, title),
                                     link=ref[1])

            if subitems:
                parent_title = re.sub(r'\s*\(.*\)\s*$', '', title)
                for subitem in subitems:
                    write_index("%s %s" % (parent_title, subitem[0]),
                                subitem[1], [])

        for (key, group) in index:
            for title, (refs, subitems, key) in group:
                write_index(title, refs, subitems)

        # Dump the XML file
        xmlfile = path.join(outdir, outname + '.devhelp.gz')
        with gzip.open(xmlfile, 'w') as f:
            tree.write(f, 'utf-8')  # type: ignore


def setup(app: Sphinx) -> dict[str, Any]:
    app.require_sphinx('5.0')
    app.setup_extension('sphinx.builders.html')
    app.add_builder(DevhelpBuilder)
    app.add_message_catalog(__name__, path.join(package_dir, 'locales'))

    app.add_config_value('devhelp_basename',
                         lambda self: make_filename(self.project),
                         'devhelp')

    return {
        'version': __version__,
        'parallel_read_safe': True,
        'parallel_write_safe': True,
    }
