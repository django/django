# -*- coding: utf-8 -*-
"""
    sphinx.builders.texinfo
    ~~~~~~~~~~~~~~~~~~~~~~~

    Texinfo builder.

    :copyright: Copyright 2007-2019 by the Sphinx team, see AUTHORS.
    :license: BSD, see LICENSE for details.
"""

import os
from os import path

from docutils import nodes
from docutils.frontend import OptionParser
from docutils.io import FileOutput

from sphinx import addnodes
from sphinx.builders import Builder
from sphinx.environment import NoUri
from sphinx.environment.adapters.asset import ImageAdapter
from sphinx.locale import _, __
from sphinx.util import logging
from sphinx.util import status_iterator
from sphinx.util.console import bold, darkgreen  # type: ignore
from sphinx.util.docutils import new_document
from sphinx.util.fileutil import copy_asset_file
from sphinx.util.nodes import inline_all_toctrees
from sphinx.util.osutil import SEP, make_filename
from sphinx.writers.texinfo import TexinfoWriter, TexinfoTranslator

if False:
    # For type annotation
    from sphinx.application import Sphinx  # NOQA
    from typing import Any, Dict, Iterable, List, Tuple, Union  # NOQA


logger = logging.getLogger(__name__)

TEXINFO_MAKEFILE = '''\
# Makefile for Sphinx Texinfo output

infodir ?= /usr/share/info

MAKEINFO = makeinfo --no-split
MAKEINFO_html = makeinfo --no-split --html
MAKEINFO_plaintext = makeinfo --no-split --plaintext
TEXI2PDF = texi2pdf --batch --expand
INSTALL_INFO = install-info

ALLDOCS = $(basename $(wildcard *.texi))

all: info
info: $(addsuffix .info,$(ALLDOCS))
plaintext: $(addsuffix .txt,$(ALLDOCS))
html: $(addsuffix .html,$(ALLDOCS))
pdf: $(addsuffix .pdf,$(ALLDOCS))

install-info: info
\tfor f in *.info; do \\
\t  cp -t $(infodir) "$$f" && \\
\t  $(INSTALL_INFO) --info-dir=$(infodir) "$$f" ; \\
\tdone

uninstall-info: info
\tfor f in *.info; do \\
\t  rm -f "$(infodir)/$$f"  ; \\
\t  $(INSTALL_INFO) --delete --info-dir=$(infodir) "$$f" ; \\
\tdone

%.info: %.texi
\t$(MAKEINFO) -o '$@' '$<'

%.txt: %.texi
\t$(MAKEINFO_plaintext) -o '$@' '$<'

%.html: %.texi
\t$(MAKEINFO_html) -o '$@' '$<'

%.pdf: %.texi
\t-$(TEXI2PDF) '$<'
\t-$(TEXI2PDF) '$<'
\t-$(TEXI2PDF) '$<'

clean:
\trm -f *.info *.pdf *.txt *.html
\trm -f *.log *.ind *.aux *.toc *.syn *.idx *.out *.ilg *.pla *.ky *.pg
\trm -f *.vr *.tp *.fn *.fns *.def *.defs *.cp *.cps *.ge *.ges *.mo

.PHONY: all info plaintext html pdf install-info uninstall-info clean
'''


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

    def init(self):
        # type: () -> None
        self.docnames = []       # type: Iterable[unicode]
        self.document_data = []  # type: List[Tuple[unicode, unicode, unicode, unicode, unicode, unicode, unicode, bool]]  # NOQA

    def get_outdated_docs(self):
        # type: () -> Union[unicode, List[unicode]]
        return 'all documents'  # for now

    def get_target_uri(self, docname, typ=None):
        # type: (unicode, unicode) -> unicode
        if docname not in self.docnames:
            raise NoUri
        else:
            return '%' + docname

    def get_relative_uri(self, from_, to, typ=None):
        # type: (unicode, unicode, unicode) -> unicode
        # ignore source path
        return self.get_target_uri(to, typ)

    def init_document_data(self):
        # type: () -> None
        preliminary_document_data = [list(x) for x in self.config.texinfo_documents]
        if not preliminary_document_data:
            logger.warning(__('no "texinfo_documents" config value found; no documents '
                              'will be written'))
            return
        # assign subdirs to titles
        self.titles = []  # type: List[Tuple[unicode, unicode]]
        for entry in preliminary_document_data:
            docname = entry[0]
            if docname not in self.env.all_docs:
                logger.warning(__('"texinfo_documents" config value references unknown '
                                  'document %s'), docname)
                continue
            self.document_data.append(entry)  # type: ignore
            if docname.endswith(SEP + 'index'):
                docname = docname[:-5]
            self.titles.append((docname, entry[2]))

    def write(self, *ignored):
        # type: (Any) -> None
        self.init_document_data()
        for entry in self.document_data:
            docname, targetname, title, author = entry[:4]
            targetname += '.texi'
            direntry = description = category = ''  # type: unicode
            if len(entry) > 6:
                direntry, description, category = entry[4:7]
            toctree_only = False
            if len(entry) > 7:
                toctree_only = entry[7]
            destination = FileOutput(
                destination_path=path.join(self.outdir, targetname),
                encoding='utf-8')
            logger.info(__("processing %s..."), targetname, nonl=1)
            doctree = self.assemble_doctree(
                docname, toctree_only,
                appendices=(self.config.texinfo_appendices or []))
            logger.info(__("writing... "), nonl=1)
            self.post_process_images(doctree)
            docwriter = TexinfoWriter(self)
            settings = OptionParser(
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
            logger.info(__("done"))

    def assemble_doctree(self, indexfile, toctree_only, appendices):
        # type: (unicode, bool, List[unicode]) -> nodes.Node
        self.docnames = set([indexfile] + appendices)
        logger.info(darkgreen(indexfile) + " ", nonl=1)
        tree = self.env.get_doctree(indexfile)
        tree['docname'] = indexfile
        if toctree_only:
            # extract toctree nodes from the tree and put them in a
            # fresh document
            new_tree = new_document('<texinfo output>')
            new_sect = nodes.section()
            new_sect += nodes.title(u'<Set title in conf.py>',
                                    u'<Set title in conf.py>')
            new_tree += new_sect
            for node in tree.traverse(addnodes.toctree):
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
        for pendingnode in largetree.traverse(addnodes.pending_xref):
            docname = pendingnode['refdocname']
            sectname = pendingnode['refsectname']
            newnodes = [nodes.emphasis(sectname, sectname)]
            for subdir, title in self.titles:
                if docname.startswith(subdir):
                    newnodes.append(nodes.Text(_(' (in '), _(' (in ')))
                    newnodes.append(nodes.emphasis(title, title))
                    newnodes.append(nodes.Text(')', ')'))
                    break
            else:
                pass
            pendingnode.replace_self(newnodes)
        return largetree

    def finish(self):
        # type: () -> None
        self.copy_image_files()

        logger.info(bold(__('copying Texinfo support files... ')), nonl=True)
        # copy Makefile
        fn = path.join(self.outdir, 'Makefile')
        logger.info(fn, nonl=1)
        try:
            with open(fn, 'w') as mkfile:
                mkfile.write(TEXINFO_MAKEFILE)
        except (IOError, OSError) as err:
            logger.warning(__("error writing file %s: %s"), fn, err)
        logger.info(__(' done'))

    def copy_image_files(self):
        # type: () -> None
        if self.images:
            stringify_func = ImageAdapter(self.app.env).get_original_image_uri
            for src in status_iterator(self.images, __('copying images... '), "brown",
                                       len(self.images), self.app.verbosity,
                                       stringify_func=stringify_func):
                dest = self.images[src]
                try:
                    copy_asset_file(path.join(self.srcdir, src),
                                    path.join(self.outdir, dest))
                except Exception as err:
                    logger.warning(__('cannot copy image file %r: %s'),
                                   path.join(self.srcdir, src), err)


def setup(app):
    # type: (Sphinx) -> Dict[unicode, Any]
    app.add_builder(TexinfoBuilder)

    app.add_config_value('texinfo_documents',
                         lambda self: [(self.master_doc, make_filename(self.project).lower(),
                                        self.project, '', make_filename(self.project),
                                        'The %s reference manual.' %
                                        make_filename(self.project),
                                        'Python')],
                         None)
    app.add_config_value('texinfo_appendices', [], None)
    app.add_config_value('texinfo_elements', {}, None)
    app.add_config_value('texinfo_domain_indices', True, None, [list])
    app.add_config_value('texinfo_show_urls', 'footnote', None)
    app.add_config_value('texinfo_no_detailmenu', False, None)

    return {
        'version': 'builtin',
        'parallel_read_safe': True,
        'parallel_write_safe': True,
    }
