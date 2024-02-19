"""Build HTML help support files."""

from __future__ import annotations

import html
import os
from os import path
from typing import Any

from docutils import nodes
from docutils.nodes import Element, Node, document

import sphinx
from sphinx import addnodes
from sphinx.application import Sphinx
from sphinx.builders.html import StandaloneHTMLBuilder
from sphinx.config import Config
from sphinx.environment.adapters.indexentries import IndexEntries
from sphinx.locale import get_translation
from sphinx.util import logging
from sphinx.util.fileutil import copy_asset_file
from sphinx.util.nodes import NodeMatcher
from sphinx.util.osutil import make_filename_from_project, relpath
from sphinx.util.template import SphinxRenderer

if sphinx.version_info[:2] >= (6, 1):
    from sphinx.util.display import progress_message
else:
    from sphinx.util import progress_message  # type: ignore[attr-defined,no-redef]

__version__ = '2.0.5'
__version_info__ = (2, 0, 5)

logger = logging.getLogger(__name__)
__ = get_translation(__name__, 'console')

package_dir = path.abspath(path.dirname(__file__))
template_dir = path.join(package_dir, 'templates')


# The following list includes only languages supported by Sphinx. See
# https://docs.microsoft.com/en-us/previous-versions/windows/embedded/ms930130(v=msdn.10)
# for more.
chm_locales = {
    # lang:   LCID,  encoding
    'ca':    (0x403, 'cp1252'),
    'cs':    (0x405, 'cp1250'),
    'da':    (0x406, 'cp1252'),
    'de':    (0x407, 'cp1252'),
    'en':    (0x409, 'cp1252'),
    'es':    (0x40a, 'cp1252'),
    'et':    (0x425, 'cp1257'),
    'fa':    (0x429, 'cp1256'),
    'fi':    (0x40b, 'cp1252'),
    'fr':    (0x40c, 'cp1252'),
    'hr':    (0x41a, 'cp1250'),
    'hu':    (0x40e, 'cp1250'),
    'it':    (0x410, 'cp1252'),
    'ja':    (0x411, 'cp932'),
    'ko':    (0x412, 'cp949'),
    'lt':    (0x427, 'cp1257'),
    'lv':    (0x426, 'cp1257'),
    'nl':    (0x413, 'cp1252'),
    'no_NB': (0x414, 'cp1252'),
    'pl':    (0x415, 'cp1250'),
    'pt_BR': (0x416, 'cp1252'),
    'ru':    (0x419, 'windows-1251'),  # emit as <meta chaset='...'>
    'sk':    (0x41b, 'cp1250'),
    'sl':    (0x424, 'cp1250'),
    'sv':    (0x41d, 'cp1252'),
    'tr':    (0x41f, 'cp1254'),
    'uk_UA': (0x422, 'cp1251'),
    'zh_CN': (0x804, 'cp936'),
    'zh_TW': (0x404, 'cp950'),
}


def chm_htmlescape(s: str, quote: bool = True) -> str:
    """
    chm_htmlescape() is a wrapper of html.escape().
    .hhc/.hhk files don't recognize hex escaping, we need convert
    hex escaping to decimal escaping. for example: ``&#x27;`` -> ``&#39;``
    html.escape() may generates a hex escaping ``&#x27;`` for single
    quote ``'``, this wrapper fixes this.
    """
    s = html.escape(s, quote)
    s = s.replace('&#x27;', '&#39;')    # re-escape as decimal
    return s


class ToCTreeVisitor(nodes.NodeVisitor):
    def __init__(self, document: document) -> None:
        super().__init__(document)
        self.body: list[str] = []
        self.depth = 0

    def append(self, text: str) -> None:
        self.body.append(text)

    def astext(self) -> str:
        return '\n'.join(self.body)

    def unknown_visit(self, node: Node) -> None:
        pass

    def unknown_departure(self, node: Node) -> None:
        pass

    def visit_bullet_list(self, node: Element) -> None:
        if self.depth > 0:
            self.append('<UL>')

        self.depth += 1

    def depart_bullet_list(self, node: Element) -> None:
        self.depth -= 1
        if self.depth > 0:
            self.append('</UL>')

    def visit_list_item(self, node: Element) -> None:
        self.append('<LI> <OBJECT type="text/sitemap">')
        self.depth += 1

    def depart_list_item(self, node: Element) -> None:
        self.depth -= 1

    def visit_reference(self, node: Element) -> None:
        title = chm_htmlescape(node.astext(), True)
        self.append('    <param name="Name" value="%s">' % title)
        self.append('    <param name="Local" value="%s">' % node['refuri'])
        self.append('</OBJECT>')
        raise nodes.SkipNode


class HTMLHelpBuilder(StandaloneHTMLBuilder):
    """
    Builder that also outputs Windows HTML help project, contents and
    index files.  Adapted from the original Doc/tools/prechm.py.
    """
    name = 'htmlhelp'
    epilog = __('You can now run HTML Help Workshop with the .htp file in '
                '%(outdir)s.')

    # don't copy the reST source
    copysource = False
    supported_image_types = ['image/png', 'image/gif', 'image/jpeg']

    # don't add links
    add_permalinks = False
    # don't add sidebar etc.
    embedded = True

    # don't generate search index or include search page
    search = False

    lcid = 0x409
    encoding = 'cp1252'

    def init(self) -> None:
        # the output files for HTML help is .html by default
        self.out_suffix = '.html'
        self.link_suffix = '.html'
        super().init()
        # determine the correct locale setting
        locale = chm_locales.get(self.config.language)
        if locale is not None:
            self.lcid, self.encoding = locale

    def prepare_writing(self, docnames: set[str]) -> None:
        super().prepare_writing(docnames)
        self.globalcontext['html5_doctype'] = False

    def update_page_context(self, pagename: str, templatename: str, ctx: dict, event_arg: str) -> None:  # NOQA
        ctx['encoding'] = self.encoding

    def handle_finish(self) -> None:
        self.copy_stopword_list()
        self.build_project_file()
        self.build_toc_file()
        self.build_hhx(self.outdir, self.config.htmlhelp_basename)

    def write_doc(self, docname: str, doctree: document) -> None:
        for node in doctree.traverse(nodes.reference):
            # add ``target=_blank`` attributes to external links
            if node.get('internal') is None and 'refuri' in node:
                node['target'] = '_blank'

        super().write_doc(docname, doctree)

    def render(self, name: str, context: dict) -> str:
        template = SphinxRenderer(template_dir)
        return template.render(name, context)

    @progress_message(__('copying stopword list'))
    def copy_stopword_list(self) -> None:
        """Copy a stopword list (.stp) to outdir.

        The stopword list contains a list of words the full text search facility
        shouldn't index.  Note that this list must be pretty small.  Different
        versions of the MS docs claim the file has a maximum size of 256 or 512
        bytes (including \r\n at the end of each line).  Note that "and", "or",
        "not" and "near" are operators in the search language, so no point
        indexing them even if we wanted to.
        """
        template = path.join(template_dir, 'project.stp')
        filename = path.join(self.outdir, self.config.htmlhelp_basename + '.stp')
        copy_asset_file(template, filename)

    @progress_message(__('writing project file'))
    def build_project_file(self) -> None:
        """Create a project file (.hhp) on outdir."""
        # scan project files
        project_files: list[str] = []
        for root, dirs, files in os.walk(self.outdir):
            dirs.sort()
            files.sort()
            in_staticdir = root.startswith(path.join(self.outdir, '_static'))
            for fn in sorted(files):
                if (in_staticdir and not fn.endswith('.js')) or fn.endswith('.html'):
                    fn = relpath(path.join(root, fn), self.outdir)
                    project_files.append(fn.replace(os.sep, '\\'))

        filename = path.join(self.outdir, self.config.htmlhelp_basename + '.hhp')
        with open(filename, 'w', encoding=self.encoding, errors='xmlcharrefreplace') as f:
            context = {
                'outname': self.config.htmlhelp_basename,
                'title': self.config.html_title,
                'version': self.config.version,
                'project': self.config.project,
                'lcid': self.lcid,
                'master_doc': self.config.master_doc + self.out_suffix,
                'files': project_files,
            }
            body = self.render('project.hhp', context)
            f.write(body)

    @progress_message(__('writing TOC file'))
    def build_toc_file(self) -> None:
        """Create a ToC file (.hhp) on outdir."""
        filename = path.join(self.outdir, self.config.htmlhelp_basename + '.hhc')
        with open(filename, 'w', encoding=self.encoding, errors='xmlcharrefreplace') as f:
            toctree = self.env.get_and_resolve_doctree(self.config.master_doc, self,
                                                       prune_toctrees=False)
            visitor = ToCTreeVisitor(toctree)
            matcher = NodeMatcher(addnodes.compact_paragraph, toctree=True)
            for node in toctree.traverse(matcher):  # type: addnodes.compact_paragraph
                node.walkabout(visitor)

            context = {
                'body': visitor.astext(),
                'suffix': self.out_suffix,
                'short_title': self.config.html_short_title,
                'master_doc': self.config.master_doc,
                'domain_indices': self.domain_indices,
            }
            f.write(self.render('project.hhc', context))

    def build_hhx(self, outdir: str | os.PathLike[str], outname: str) -> None:
        logger.info(__('writing index file...'))
        index = IndexEntries(self.env).create_index(self)
        filename = path.join(outdir, outname + '.hhk')
        with open(filename, 'w', encoding=self.encoding, errors='xmlcharrefreplace') as f:
            f.write('<UL>\n')

            def write_index(title: str, refs: list[tuple[str, str]], subitems: list[tuple[str, list[tuple[str, str]]]]) -> None:  # NOQA
                def write_param(name: str, value: str) -> None:
                    item = '    <param name="%s" value="%s">\n' % (name, value)
                    f.write(item)
                title = chm_htmlescape(title, True)
                f.write('<LI> <OBJECT type="text/sitemap">\n')
                write_param('Keyword', title)
                if len(refs) == 0:
                    write_param('See Also', title)
                elif len(refs) == 1:
                    write_param('Local', refs[0][1])
                else:
                    for i, ref in enumerate(refs):
                        # XXX: better title?
                        write_param('Name', '[%d] %s' % (i, ref[1]))
                        write_param('Local', ref[1])
                f.write('</OBJECT>\n')
                if subitems:
                    f.write('<UL> ')
                    for subitem in subitems:
                        write_index(subitem[0], subitem[1], [])
                    f.write('</UL>')
            for (key, group) in index:
                for title, (refs, subitems, key_) in group:
                    write_index(title, refs, subitems)
            f.write('</UL>\n')


def default_htmlhelp_basename(config: Config) -> str:
    """Better default htmlhelp_basename setting."""
    return make_filename_from_project(config.project) + 'doc'


def setup(app: Sphinx) -> dict[str, Any]:
    app.require_sphinx('5.0')
    app.setup_extension('sphinx.builders.html')
    app.add_builder(HTMLHelpBuilder)
    app.add_message_catalog(__name__, path.join(package_dir, 'locales'))

    app.add_config_value('htmlhelp_basename', default_htmlhelp_basename, '')
    app.add_config_value('htmlhelp_file_suffix', None, 'html', [str])
    app.add_config_value('htmlhelp_link_suffix', None, 'html', [str])

    return {
        'version': __version__,
        'parallel_read_safe': True,
        'parallel_write_safe': True,
    }
