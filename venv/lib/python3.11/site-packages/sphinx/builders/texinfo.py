"""Texinfo builder."""

from __future__ import annotations

import os
import warnings
from os import path
from typing import TYPE_CHECKING, Any

from docutils import nodes
from docutils.frontend import OptionParser
from docutils.io import FileOutput

from sphinx import addnodes, package_dir
from sphinx.builders import Builder
from sphinx.environment.adapters.asset import ImageAdapter
from sphinx.errors import NoUri
from sphinx.locale import _, __
from sphinx.util import logging
from sphinx.util.console import darkgreen  # type: ignore[attr-defined]
from sphinx.util.display import progress_message, status_iterator
from sphinx.util.docutils import new_document
from sphinx.util.fileutil import copy_asset_file
from sphinx.util.nodes import inline_all_toctrees
from sphinx.util.osutil import SEP, ensuredir, make_filename_from_project
from sphinx.writers.texinfo import TexinfoTranslator, TexinfoWriter

if TYPE_CHECKING:
    from collections.abc import Iterable

    from docutils.nodes import Node

    from sphinx.application import Sphinx
    from sphinx.config import Config

logger = logging.getLogger(__name__)
template_dir = os.path.join(package_dir, 'templates', 'texinfo')


class TexinfoBuilder(Builder):
    """
    Builds Texinfo output to create Info documentation.
    """
    name = 'texinfo'
    format = 'texinfo'
    epilog = __('The Texinfo files are in %(outdir)s.')
    if os.name == 'posix':
        epilog += __("\nRun 'make' in that directory to run these through "
                     "makeinfo\n"
                     "(use 'make info' here to do that automatically).")

    supported_image_types = ['image/png', 'image/jpeg',
                             'image/gif']
    default_translator_class = TexinfoTranslator

    def init(self) -> None:
        self.docnames: Iterable[str] = []
        self.document_data: list[tuple[str, str, str, str, str, str, str, bool]] = []

    def get_outdated_docs(self) -> str | list[str]:
        return 'all documents'  # for now

    def get_target_uri(self, docname: str, typ: str | None = None) -> str:
        if docname not in self.docnames:
            raise NoUri(docname, typ)
        return '%' + docname

    def get_relative_uri(self, from_: str, to: str, typ: str | None = None) -> str:
        # ignore source path
        return self.get_target_uri(to, typ)

    def init_document_data(self) -> None:
        preliminary_document_data = [list(x) for x in self.config.texinfo_documents]
        if not preliminary_document_data:
            logger.warning(__('no "texinfo_documents" config value found; no documents '
                              'will be written'))
            return
        # assign subdirs to titles
        self.titles: list[tuple[str, str]] = []
        for entry in preliminary_document_data:
            docname = entry[0]
            if docname not in self.env.all_docs:
                logger.warning(__('"texinfo_documents" config value references unknown '
                                  'document %s'), docname)
                continue
            self.document_data.append(entry)  # type: ignore[arg-type]
            if docname.endswith(SEP + 'index'):
                docname = docname[:-5]
            self.titles.append((docname, entry[2]))

    def write(self, *ignored: Any) -> None:
        self.init_document_data()
        self.copy_assets()
        for entry in self.document_data:
            docname, targetname, title, author = entry[:4]
            targetname += '.texi'
            direntry = description = category = ''
            if len(entry) > 6:
                direntry, description, category = entry[4:7]
            toctree_only = False
            if len(entry) > 7:
                toctree_only = entry[7]
            destination = FileOutput(
                destination_path=path.join(self.outdir, targetname),
                encoding='utf-8')
            with progress_message(__("processing %s") % targetname):
                appendices = self.config.texinfo_appendices or []
                doctree = self.assemble_doctree(docname, toctree_only, appendices=appendices)

            with progress_message(__("writing")):
                self.post_process_images(doctree)
                docwriter = TexinfoWriter(self)
                with warnings.catch_warnings():
                    warnings.filterwarnings('ignore', category=DeprecationWarning)
                    # DeprecationWarning: The frontend.OptionParser class will be replaced
                    # by a subclass of argparse.ArgumentParser in Docutils 0.21 or later.
                    settings: Any = OptionParser(
                        defaults=self.env.settings,
                        components=(docwriter,),
                        read_config_files=True).get_default_values()
                settings.author = author
                settings.title = title
                settings.texinfo_filename = targetname[:-5] + '.info'
                settings.texinfo_elements = self.config.texinfo_elements
                settings.texinfo_dir_entry = direntry or ''
                settings.texinfo_dir_category = category or ''
                settings.texinfo_dir_description = description or ''
                settings.docname = docname
                doctree.settings = settings
                docwriter.write(doctree, destination)
                self.copy_image_files(targetname[:-5])

    def assemble_doctree(
        self, indexfile: str, toctree_only: bool, appendices: list[str],
    ) -> nodes.document:
        self.docnames = set([indexfile] + appendices)
        logger.info(darkgreen(indexfile) + " ", nonl=True)
        tree = self.env.get_doctree(indexfile)
        tree['docname'] = indexfile
        if toctree_only:
            # extract toctree nodes from the tree and put them in a
            # fresh document
            new_tree = new_document('<texinfo output>')
            new_sect = nodes.section()
            new_sect += nodes.title('<Set title in conf.py>',
                                    '<Set title in conf.py>')
            new_tree += new_sect
            for node in tree.findall(addnodes.toctree):
                new_sect += node
            tree = new_tree
        largetree = inline_all_toctrees(self, self.docnames, indexfile, tree,
                                        darkgreen, [indexfile])
        largetree['docname'] = indexfile
        for docname in appendices:
            appendix = self.env.get_doctree(docname)
            appendix['docname'] = docname
            largetree.append(appendix)
        logger.info('')
        logger.info(__("resolving references..."))
        self.env.resolve_references(largetree, indexfile, self)
        # TODO: add support for external :ref:s
        for pendingnode in largetree.findall(addnodes.pending_xref):
            docname = pendingnode['refdocname']
            sectname = pendingnode['refsectname']
            newnodes: list[Node] = [nodes.emphasis(sectname, sectname)]
            for subdir, title in self.titles:
                if docname.startswith(subdir):
                    newnodes.append(nodes.Text(_(' (in ')))
                    newnodes.append(nodes.emphasis(title, title))
                    newnodes.append(nodes.Text(')'))
                    break
            else:
                pass
            pendingnode.replace_self(newnodes)
        return largetree

    def copy_assets(self) -> None:
        self.copy_support_files()

    def copy_image_files(self, targetname: str) -> None:
        if self.images:
            stringify_func = ImageAdapter(self.app.env).get_original_image_uri
            for src in status_iterator(self.images, __('copying images... '), "brown",
                                       len(self.images), self.app.verbosity,
                                       stringify_func=stringify_func):
                dest = self.images[src]
                try:
                    imagedir = path.join(self.outdir, targetname + '-figures')
                    ensuredir(imagedir)
                    copy_asset_file(path.join(self.srcdir, src),
                                    path.join(imagedir, dest))
                except Exception as err:
                    logger.warning(__('cannot copy image file %r: %s'),
                                   path.join(self.srcdir, src), err)

    def copy_support_files(self) -> None:
        try:
            with progress_message(__('copying Texinfo support files')):
                logger.info('Makefile ', nonl=True)
                copy_asset_file(os.path.join(template_dir, 'Makefile'), self.outdir)
        except OSError as err:
            logger.warning(__("error writing file Makefile: %s"), err)


def default_texinfo_documents(
    config: Config,
) -> list[tuple[str, str, str, str, str, str, str]]:
    """ Better default texinfo_documents settings. """
    filename = make_filename_from_project(config.project)
    return [(config.root_doc, filename, config.project, config.author, filename,
             'One line description of project', 'Miscellaneous')]


def setup(app: Sphinx) -> dict[str, Any]:
    app.add_builder(TexinfoBuilder)

    app.add_config_value('texinfo_documents', default_texinfo_documents, False)
    app.add_config_value('texinfo_appendices', [], False)
    app.add_config_value('texinfo_elements', {}, False)
    app.add_config_value('texinfo_domain_indices', True, False, [list])
    app.add_config_value('texinfo_show_urls', 'footnote', False)
    app.add_config_value('texinfo_no_detailmenu', False, False)
    app.add_config_value('texinfo_cross_references', True, False)

    return {
        'version': 'builtin',
        'parallel_read_safe': True,
        'parallel_write_safe': True,
    }
