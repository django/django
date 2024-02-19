"""Build input files for the Qt collection generator."""

from __future__ import annotations

import html
import os
import posixpath
import re
from collections.abc import Iterable
from os import path
from typing import Any, cast

from docutils import nodes
from docutils.nodes import Node
from sphinx import addnodes
from sphinx.application import Sphinx
from sphinx.builders.html import StandaloneHTMLBuilder
from sphinx.environment.adapters.indexentries import IndexEntries
from sphinx.locale import get_translation
from sphinx.util import logging
from sphinx.util.nodes import NodeMatcher
from sphinx.util.osutil import canon_path, make_filename
from sphinx.util.template import SphinxRenderer


__version__ = '1.0.7'
__version_info__ = (1, 0, 7)

logger = logging.getLogger(__name__)
package_dir = path.abspath(path.dirname(__file__))

__ = get_translation(__name__, 'console')


_idpattern = re.compile(
    r'(?P<title>.+) (\((class in )?(?P<id>[\w\.]+)( (?P<descr>\w+))?\))$')


section_template = '<section title="%(title)s" ref="%(ref)s"/>'


def render_file(filename: str, **kwargs: Any) -> str:
    pathname = path.join(package_dir, 'templates', filename)
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

    def init(self) -> None:
        super().init()
        # the output files for HTML help must be .html only
        self.out_suffix = '.html'
        self.link_suffix = '.html'
        # self.config.html_style = 'traditional.css'

    def get_theme_config(self) -> tuple[str, dict]:
        return self.config.qthelp_theme, self.config.qthelp_theme_options

    def handle_finish(self) -> None:
        self.epilog = self.epilog % {
            'outdir': '%(outdir)s',
            'project': self.config.qthelp_basename,
        }
        self.build_qhp(self.outdir, self.config.qthelp_basename)

    def build_qhp(self, outdir: str | os.PathLike[str], outname: str) -> None:
        logger.info(__('writing project file...'))

        # sections
        tocdoc = self.env.get_and_resolve_doctree(self.config.master_doc, self,
                                                  prune_toctrees=False)

        sections = []
        matcher = NodeMatcher(addnodes.compact_paragraph, toctree=True)
        for node in tocdoc.traverse(matcher):  # type: addnodes.compact_paragraph
            sections.extend(self.write_toc(node))

        for indexname, indexcls, content, collapse in self.domain_indices:
            item = section_template % {'title': indexcls.localname,
                                       'ref': indexname + self.out_suffix}
            sections.append(' ' * 4 * 4 + item)
        sections = '\n'.join(sections)  # type: ignore

        # keywords
        keywords = []
        index = IndexEntries(self.env).create_index(self, group_entries=False)
        for (key, group) in index:
            for title, (refs, subitems, key_) in group:
                keywords.extend(self.build_keywords(title, refs, subitems))
        keywords = '\n'.join(keywords)  # type: ignore

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
        with open(path.join(outdir, outname + '.qhp'), 'w', encoding='utf-8') as f:
            body = render_file('project.qhp', outname=outname,
                               title=self.config.html_title, version=self.config.version,
                               project=self.config.project, namespace=nspace,
                               master_doc=self.config.master_doc,
                               sections=sections, keywords=keywords,
                               files=self.get_project_files(outdir))
            f.write(body)

        homepage = 'qthelp://' + posixpath.join(
            nspace, 'doc', self.get_target_uri(self.config.master_doc))
        startpage = 'qthelp://' + posixpath.join(nspace, 'doc', 'index%s' % self.link_suffix)

        logger.info(__('writing collection project file...'))
        with open(path.join(outdir, outname + '.qhcp'), 'w', encoding='utf-8') as f:
            body = render_file('project.qhcp', outname=outname,
                               title=self.config.html_short_title,
                               homepage=homepage, startpage=startpage)
            f.write(body)

    def isdocnode(self, node: Node) -> bool:
        if not isinstance(node, nodes.list_item):
            return False
        if len(node.children) != 2:
            return False
        if not isinstance(node[0], addnodes.compact_paragraph):
            return False
        if not isinstance(node[0][0], nodes.reference):
            return False
        if not isinstance(node[1], nodes.bullet_list):
            return False
        return True

    def write_toc(self, node: Node, indentlevel: int = 4) -> list[str]:
        parts: list[str] = []
        if isinstance(node, nodes.list_item) and self.isdocnode(node):
            compact_paragraph = cast(addnodes.compact_paragraph, node[0])
            reference = cast(nodes.reference, compact_paragraph[0])
            link = reference['refuri']
            title = html.escape(reference.astext()).replace('"', '&quot;')
            item = '<section title="%(title)s" ref="%(ref)s">' % \
                {'title': title, 'ref': link}
            parts.append(' ' * 4 * indentlevel + item)

            bullet_list = cast(nodes.bullet_list, node[1])
            list_items = cast(Iterable[nodes.list_item], bullet_list)
            for list_item in list_items:
                parts.extend(self.write_toc(list_item, indentlevel + 1))
            parts.append(' ' * 4 * indentlevel + '</section>')
        elif isinstance(node, nodes.list_item):
            for subnode in node:
                parts.extend(self.write_toc(subnode, indentlevel))
        elif isinstance(node, nodes.reference):
            link = node['refuri']
            title = html.escape(node.astext()).replace('"', '&quot;')
            item = section_template % {'title': title, 'ref': link}
            item = ' ' * 4 * indentlevel + item
            parts.append(item.encode('ascii', 'xmlcharrefreplace').decode())
        elif isinstance(node, nodes.bullet_list):
            for subnode in node:
                parts.extend(self.write_toc(subnode, indentlevel))
        elif isinstance(node, addnodes.compact_paragraph):
            for subnode in node:
                parts.extend(self.write_toc(subnode, indentlevel))

        return parts

    def keyword_item(self, name: str, ref: Any) -> str:
        matchobj = _idpattern.match(name)
        if matchobj:
            groupdict = matchobj.groupdict()
            shortname = groupdict['title']
            id = groupdict.get('id')
            # descr = groupdict.get('descr')
            if shortname.endswith('()'):
                shortname = shortname[:-2]
            id = html.escape('%s.%s' % (id, shortname), True)
        else:
            id = None

        nameattr = html.escape(name, quote=True)
        refattr = html.escape(ref[1], quote=True)
        if id:
            item = ' ' * 12 + '<keyword name="%s" id="%s" ref="%s"/>' % (nameattr, id, refattr)
        else:
            item = ' ' * 12 + '<keyword name="%s" ref="%s"/>' % (nameattr, refattr)
        item.encode('ascii', 'xmlcharrefreplace')
        return item

    def build_keywords(self, title: str, refs: list[Any], subitems: Any) -> list[str]:
        keywords: list[str] = []

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

    def get_project_files(self, outdir: str | os.PathLike[str]) -> list[str]:
        project_files = []
        staticdir = path.join(outdir, '_static')
        imagesdir = path.join(outdir, self.imagedir)
        for root, dirs, files in os.walk(outdir):
            resourcedir = root.startswith((staticdir, imagesdir))
            for fn in sorted(files):
                if (resourcedir and not fn.endswith('.js')) or fn.endswith('.html'):
                    filename = path.relpath(path.join(root, fn), outdir)
                    project_files.append(canon_path(filename))

        return project_files


def setup(app: Sphinx) -> dict[str, Any]:
    app.require_sphinx('5.0')
    app.setup_extension('sphinx.builders.html')
    app.add_builder(QtHelpBuilder)
    app.add_message_catalog(__name__, path.join(package_dir, 'locales'))

    app.add_config_value('qthelp_basename', lambda self: make_filename(self.project), 'html')
    app.add_config_value('qthelp_namespace', None, 'html', [str])
    app.add_config_value('qthelp_theme', 'nonav', 'html')
    app.add_config_value('qthelp_theme_options', {}, 'html')

    return {
        'version': __version__,
        'parallel_read_safe': True,
        'parallel_write_safe': True,
    }
