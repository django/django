# -*- coding: utf-8 -*-
"""
    sphinx.builders.websupport
    ~~~~~~~~~~~~~~~~~~~~~~~~~~

    Builder for the web support package.

    :copyright: Copyright 2007-2016 by the Sphinx team, see AUTHORS.
    :license: BSD, see LICENSE for details.
"""

from os import path
import posixpath
import shutil

from docutils.io import StringOutput

from sphinx.jinja2glue import BuiltinTemplateLoader
from sphinx.util.osutil import os_path, relative_uri, ensuredir, copyfile
from sphinx.builders.html import PickleHTMLBuilder

from .writer import WebSupportTranslator


if False:
    # For type annotation
    from typing import Any, Dict, Iterable, Tuple  # NOQA
    from docutils import nodes  # NOQA
    from sphinx.application import Sphinx  # NOQA


class WebSupportBuilder(PickleHTMLBuilder):
    """
    Builds documents for the web support package.
    """
    name = 'websupport'
    versioning_method = 'commentable'
    versioning_compare = True  # for commentable node's uuid stability.
    default_translator_class = WebSupportTranslator

    def init(self):
        # type: () -> None
        PickleHTMLBuilder.init(self)
        # templates are needed for this builder, but the serializing
        # builder does not initialize them
        self.init_templates()
        if not isinstance(self.templates, BuiltinTemplateLoader):
            raise RuntimeError('websupport builder must be used with '
                               'the builtin templates')
        # add our custom JS
        self.script_files.append('_static/websupport.js')

    def set_webinfo(self, staticdir, virtual_staticdir, search, storage):
        # type: (unicode, unicode, Any, unicode) -> None
        self.staticdir = staticdir
        self.virtual_staticdir = virtual_staticdir
        self.search = search
        self.storage = storage

    def prepare_writing(self, docnames):
        # type: (Iterable[unicode]) -> None
        PickleHTMLBuilder.prepare_writing(self, docnames)
        self.globalcontext['no_search_suffix'] = True

    def write_doc(self, docname, doctree):
        # type: (unicode, nodes.Node) -> None
        destination = StringOutput(encoding='utf-8')
        doctree.settings = self.docsettings

        self.secnumbers = self.env.toc_secnumbers.get(docname, {})
        self.fignumbers = self.env.toc_fignumbers.get(docname, {})
        self.imgpath = '/' + posixpath.join(self.virtual_staticdir, self.imagedir)
        self.dlpath = '/' + posixpath.join(self.virtual_staticdir, '_downloads')
        self.current_docname = docname
        self.docwriter.write(doctree, destination)
        self.docwriter.assemble_parts()
        body = self.docwriter.parts['fragment']
        metatags = self.docwriter.clean_meta

        ctx = self.get_doc_context(docname, body, metatags)
        self.handle_page(docname, ctx, event_arg=doctree)

    def write_doc_serialized(self, docname, doctree):
        # type: (unicode, nodes.Node) -> None
        self.imgpath = '/' + posixpath.join(self.virtual_staticdir, self.imagedir)
        self.post_process_images(doctree)
        title = self.env.longtitles.get(docname)
        title = title and self.render_partial(title)['title'] or ''
        self.index_page(docname, doctree, title)

    def load_indexer(self, docnames):
        # type: (Iterable[unicode]) -> None
        self.indexer = self.search  # type: ignore
        self.indexer.init_indexing(changed=docnames)  # type: ignore

    def _render_page(self, pagename, addctx, templatename, event_arg=None):
        # type: (unicode, Dict, unicode, unicode) -> Tuple[Dict, Dict]
        # This is mostly copied from StandaloneHTMLBuilder. However, instead
        # of rendering the template and saving the html, create a context
        # dict and pickle it.
        ctx = self.globalcontext.copy()
        ctx['pagename'] = pagename

        def pathto(otheruri, resource=False,
                   baseuri=self.get_target_uri(pagename)):
            # type: (unicode, bool, unicode) -> unicode
            if resource and '://' in otheruri:
                return otheruri
            elif not resource:
                otheruri = self.get_target_uri(otheruri)
                return relative_uri(baseuri, otheruri) or '#'
            else:
                return '/' + posixpath.join(self.virtual_staticdir, otheruri)
        ctx['pathto'] = pathto
        ctx['hasdoc'] = lambda name: name in self.env.all_docs
        ctx['encoding'] = self.config.html_output_encoding
        ctx['toctree'] = lambda **kw: self._get_local_toctree(pagename, **kw)
        self.add_sidebars(pagename, ctx)
        ctx.update(addctx)

        newtmpl = self.app.emit_firstresult('html-page-context', pagename,
                                            templatename, ctx, event_arg)
        if newtmpl:
            templatename = newtmpl

        # create a dict that will be pickled and used by webapps
        doc_ctx = {
            'body': ctx.get('body', ''),
            'title': ctx.get('title', ''),
            'css': ctx.get('css', ''),
            'script': ctx.get('script', ''),
        }
        # partially render the html template to get at interesting macros
        template = self.templates.environment.get_template(templatename)
        template_module = template.make_module(ctx)
        for item in ['sidebar', 'relbar', 'script', 'css']:
            if hasattr(template_module, item):
                doc_ctx[item] = getattr(template_module, item)()

        return ctx, doc_ctx

    def handle_page(self, pagename, addctx, templatename='page.html',
                    outfilename=None, event_arg=None):
        # type: (unicode, Dict, unicode, unicode, unicode) -> None
        ctx, doc_ctx = self._render_page(pagename, addctx,
                                         templatename, event_arg)

        if not outfilename:
            outfilename = path.join(self.outdir, 'pickles',
                                    os_path(pagename) + self.out_suffix)
        ensuredir(path.dirname(outfilename))
        self.dump_context(doc_ctx, outfilename)

        # if there is a source file, copy the source file for the
        # "show source" link
        if ctx.get('sourcename'):
            source_name = path.join(self.staticdir,
                                    '_sources', os_path(ctx['sourcename']))
            ensuredir(path.dirname(source_name))
            copyfile(self.env.doc2path(pagename), source_name)

    def handle_finish(self):
        # type: () -> None
        # get global values for css and script files
        _, doc_ctx = self._render_page('tmp', {}, 'page.html')
        self.globalcontext['css'] = doc_ctx['css']
        self.globalcontext['script'] = doc_ctx['script']

        PickleHTMLBuilder.handle_finish(self)

        # move static stuff over to separate directory
        directories = [self.imagedir, '_static']
        for directory in directories:
            src = path.join(self.outdir, directory)
            dst = path.join(self.staticdir, directory)
            if path.isdir(src):
                if path.isdir(dst):
                    shutil.rmtree(dst)
                shutil.move(src, dst)

    def dump_search_index(self):
        # type: () -> None
        self.indexer.finish_indexing()  # type: ignore


def setup(app):
    # type: (Sphinx) -> Dict[unicode, Any]
    app.add_builder(WebSupportBuilder)

    return {
        'version': 'builtin',
        'parallel_read_safe': True,
        'parallel_write_safe': True,
    }
