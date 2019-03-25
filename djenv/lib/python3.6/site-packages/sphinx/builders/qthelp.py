# -*- coding: utf-8 -*-
"""
    sphinx.builders.qthelp
    ~~~~~~~~~~~~~~~~~~~~~~

    Build input files for the Qt collection generator.

    :copyright: Copyright 2007-2019 by the Sphinx team, see AUTHORS.
    :license: BSD, see LICENSE for details.
"""

import codecs
import os
import posixpath
import re
from os import path

from docutils import nodes
from six import text_type

from sphinx import addnodes
from sphinx import package_dir
from sphinx.builders.html import StandaloneHTMLBuilder
from sphinx.config import string_classes
from sphinx.environment.adapters.indexentries import IndexEntries
from sphinx.locale import __
from sphinx.util import force_decode, logging
from sphinx.util.osutil import make_filename
from sphinx.util.pycompat import htmlescape
from sphinx.util.template import SphinxRenderer

if False:
    # For type annotation
    from typing import Any, Dict, List, Tuple  # NOQA
    from sphinx.application import Sphinx  # NOQA


logger = logging.getLogger(__name__)


_idpattern = re.compile(
    r'(?P<title>.+) (\((class in )?(?P<id>[\w\.]+)( (?P<descr>\w+))?\))$')


section_template = '<section title="%(title)s" ref="%(ref)s"/>'


def render_file(filename, **kwargs):
    # type: (unicode, Any) -> unicode
    pathname = os.path.join(package_dir, 'templates', 'qthelp', filename)
    return SphinxRenderer.render_from_file(pathname, kwargs)


class QtHelpBuilder(StandaloneHTMLBuilder):
    """
    Builder that also outputs Qt help project, contents and index files.
    """
    name = 'qthelp'
    epilog = __('You can now run "qcollectiongenerator" with the .qhcp '
                'project file in %(outdir)s, like this:\n'
                '$ qcollectiongenerator %(outdir)s/%(project)s.qhcp\n'
                'To view the help file:\n'
                '$ assistant -collectionFile %(outdir)s/%(project)s.qhc')

    # don't copy the reST source
    copysource = False
    supported_image_types = ['image/svg+xml', 'image/png', 'image/gif',
                             'image/jpeg']

    # don't add links
    add_permalinks = False

    # don't add sidebar etc.
    embedded = True
    # disable download role
    download_support = False

    # don't generate the search index or include the search page
    search = False

    def init(self):
        # type: () -> None
        StandaloneHTMLBuilder.init(self)
        # the output files for HTML help must be .html only
        self.out_suffix = '.html'
        self.link_suffix = '.html'
        # self.config.html_style = 'traditional.css'

    def get_theme_config(self):
        # type: () -> Tuple[unicode, Dict]
        return self.config.qthelp_theme, self.config.qthelp_theme_options

    def handle_finish(self):
        # type: () -> None
        self.build_qhp(self.outdir, self.config.qthelp_basename)

    def build_qhp(self, outdir, outname):
        # type: (unicode, unicode) -> None
        logger.info(__('writing project file...'))

        # sections
        tocdoc = self.env.get_and_resolve_doctree(self.config.master_doc, self,
                                                  prune_toctrees=False)

        def istoctree(node):
            # type: (nodes.Node) -> bool
            return isinstance(node, addnodes.compact_paragraph) and \
                'toctree' in node
        sections = []
        for node in tocdoc.traverse(istoctree):
            sections.extend(self.write_toc(node))

        for indexname, indexcls, content, collapse in self.domain_indices:
            item = section_template % {'title': indexcls.localname,
                                       'ref': '%s.html' % indexname}
            sections.append(' ' * 4 * 4 + item)
        # sections may be unicode strings or byte strings, we have to make sure
        # they are all unicode strings before joining them
        new_sections = []
        for section in sections:
            if not isinstance(section, text_type):
                new_sections.append(force_decode(section, None))
            else:
                new_sections.append(section)
        sections = u'\n'.join(new_sections)  # type: ignore

        # keywords
        keywords = []
        index = IndexEntries(self.env).create_index(self, group_entries=False)
        for (key, group) in index:
            for title, (refs, subitems, key_) in group:
                keywords.extend(self.build_keywords(title, refs, subitems))
        keywords = u'\n'.join(keywords)  # type: ignore

        # it seems that the "namespace" may not contain non-alphanumeric
        # characters, and more than one successive dot, or leading/trailing
        # dots, are also forbidden
        if self.config.qthelp_namespace:
            nspace = self.config.qthelp_namespace
        else:
            nspace = 'org.sphinx.%s.%s' % (outname, self.config.version)

        nspace = re.sub(r'[^a-zA-Z0-9.\-]', '', nspace)
        nspace = re.sub(r'\.+', '.', nspace).strip('.')
        nspace = nspace.lower()

        # write the project file
        with codecs.open(path.join(outdir, outname + '.qhp'), 'w', 'utf-8') as f:  # type: ignore  # NOQA
            body = render_file('project.qhp', outname=outname,
                               title=self.config.html_title, version=self.config.version,
                               project=self.config.project, namespace=nspace,
                               master_doc=self.config.master_doc,
                               sections=sections, keywords=keywords,
                               files=self.get_project_files(outdir))
            f.write(body)

        homepage = 'qthelp://' + posixpath.join(
            nspace, 'doc', self.get_target_uri(self.config.master_doc))
        startpage = 'qthelp://' + posixpath.join(nspace, 'doc', 'index.html')

        logger.info(__('writing collection project file...'))
        with codecs.open(path.join(outdir, outname + '.qhcp'), 'w', 'utf-8') as f:  # type: ignore  # NOQA
            body = render_file('project.qhcp', outname=outname,
                               title=self.config.html_short_title,
                               homepage=homepage, startpage=startpage)
            f.write(body)

    def isdocnode(self, node):
        # type: (nodes.Node) -> bool
        if not isinstance(node, nodes.list_item):
            return False
        if len(node.children) != 2:
            return False
        if not isinstance(node.children[0], addnodes.compact_paragraph):
            return False
        if not isinstance(node.children[0][0], nodes.reference):
            return False
        if not isinstance(node.children[1], nodes.bullet_list):
            return False
        return True

    def write_toc(self, node, indentlevel=4):
        # type: (nodes.Node, int) -> List[unicode]
        # XXX this should return a Unicode string, not a bytestring
        parts = []  # type: List[unicode]
        if self.isdocnode(node):
            refnode = node.children[0][0]
            link = refnode['refuri']
            title = htmlescape(refnode.astext()).replace('"', '&quot;')
            item = '<section title="%(title)s" ref="%(ref)s">' % \
                {'title': title, 'ref': link}
            parts.append(' ' * 4 * indentlevel + item)
            for subnode in node.children[1]:
                parts.extend(self.write_toc(subnode, indentlevel + 1))
            parts.append(' ' * 4 * indentlevel + '</section>')
        elif isinstance(node, nodes.list_item):
            for subnode in node:
                parts.extend(self.write_toc(subnode, indentlevel))
        elif isinstance(node, nodes.reference):
            link = node['refuri']
            title = htmlescape(node.astext()).replace('"', '&quot;')
            item = section_template % {'title': title, 'ref': link}
            item = u' ' * 4 * indentlevel + item
            parts.append(item.encode('ascii', 'xmlcharrefreplace'))
        elif isinstance(node, nodes.bullet_list):
            for subnode in node:
                parts.extend(self.write_toc(subnode, indentlevel))
        elif isinstance(node, addnodes.compact_paragraph):
            for subnode in node:
                parts.extend(self.write_toc(subnode, indentlevel))

        return parts

    def keyword_item(self, name, ref):
        # type: (unicode, Any) -> unicode
        matchobj = _idpattern.match(name)
        if matchobj:
            groupdict = matchobj.groupdict()
            shortname = groupdict['title']
            id = groupdict.get('id')
            # descr = groupdict.get('descr')
            if shortname.endswith('()'):
                shortname = shortname[:-2]
            id = '%s.%s' % (id, shortname)
        else:
            id = None

        nameattr = htmlescape(name, quote=True)
        refattr = htmlescape(ref[1], quote=True)
        if id:
            item = ' ' * 12 + '<keyword name="%s" id="%s" ref="%s"/>' % (nameattr, id, refattr)
        else:
            item = ' ' * 12 + '<keyword name="%s" ref="%s"/>' % (nameattr, refattr)
        item.encode('ascii', 'xmlcharrefreplace')
        return item

    def build_keywords(self, title, refs, subitems):
        # type: (unicode, List[Any], Any) -> List[unicode]
        keywords = []  # type: List[unicode]

        # if len(refs) == 0: # XXX
        #     write_param('See Also', title)
        if len(refs) == 1:
            keywords.append(self.keyword_item(title, refs[0]))
        elif len(refs) > 1:
            for i, ref in enumerate(refs):  # XXX
                # item = (' '*12 +
                #         '<keyword name="%s [%d]" ref="%s"/>' % (
                #          title, i, ref))
                # item.encode('ascii', 'xmlcharrefreplace')
                # keywords.append(item)
                keywords.append(self.keyword_item(title, ref))

        if subitems:
            for subitem in subitems:
                keywords.extend(self.build_keywords(subitem[0], subitem[1], []))

        return keywords

    def get_project_files(self, outdir):
        # type: (unicode) -> List[unicode]
        if not outdir.endswith(os.sep):
            outdir += os.sep
        olen = len(outdir)
        project_files = []
        staticdir = path.join(outdir, '_static')
        imagesdir = path.join(outdir, self.imagedir)
        for root, dirs, files in os.walk(outdir):
            resourcedir = root.startswith((staticdir, imagesdir))
            for fn in sorted(files):
                if (resourcedir and not fn.endswith('.js')) or fn.endswith('.html'):
                    filename = path.join(root, fn)[olen:]
                    project_files.append(filename)

        return project_files


def setup(app):
    # type: (Sphinx) -> Dict[unicode, Any]
    app.setup_extension('sphinx.builders.html')
    app.add_builder(QtHelpBuilder)

    app.add_config_value('qthelp_basename', lambda self: make_filename(self.project), None)
    app.add_config_value('qthelp_namespace', None, 'html', string_classes)
    app.add_config_value('qthelp_theme', 'nonav', 'html')
    app.add_config_value('qthelp_theme_options', {}, 'html')

    return {
        'version': 'builtin',
        'parallel_read_safe': True,
        'parallel_write_safe': True,
    }
