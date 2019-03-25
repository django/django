# -*- coding: utf-8 -*-
"""
    sphinx.builders.latex
    ~~~~~~~~~~~~~~~~~~~~~

    LaTeX builder.

    :copyright: Copyright 2007-2019 by the Sphinx team, see AUTHORS.
    :license: BSD, see LICENSE for details.
"""

import os
from os import path

from docutils.frontend import OptionParser
from six import text_type

from sphinx import package_dir, addnodes, highlighting
from sphinx.builders import Builder
from sphinx.builders.latex.transforms import (
    BibliographyTransform, CitationReferenceTransform, MathReferenceTransform,
    FootnoteDocnameUpdater, LaTeXFootnoteTransform, LiteralBlockTransform,
    ShowUrlsTransform, DocumentTargetTransform, IndexInSectionTitleTransform,
)
from sphinx.config import string_classes, ENUM
from sphinx.environment import NoUri
from sphinx.environment.adapters.asset import ImageAdapter
from sphinx.errors import SphinxError, ConfigError
from sphinx.locale import _, __
from sphinx.transforms import SphinxTransformer
from sphinx.util import texescape, logging, status_iterator
from sphinx.util.console import bold, darkgreen  # type: ignore
from sphinx.util.docutils import SphinxFileOutput, new_document
from sphinx.util.fileutil import copy_asset_file
from sphinx.util.nodes import inline_all_toctrees
from sphinx.util.osutil import SEP, make_filename
from sphinx.writers.latex import DEFAULT_SETTINGS, LaTeXWriter, LaTeXTranslator

if False:
    # For type annotation
    from docutils import nodes  # NOQA
    from typing import Any, Dict, Iterable, List, Tuple, Union  # NOQA
    from sphinx.application import Sphinx  # NOQA
    from sphinx.config import Config  # NOQA


XINDY_LANG_OPTIONS = {
    # language codes from docutils.writers.latex2e.Babel
    # ! xindy language names may differ from those in use by LaTeX/babel
    # ! xindy does not support all Latin scripts as recognized by LaTeX/babel
    # ! not all xindy-supported languages appear in Babel.language_codes
    # cd /usr/local/texlive/2018/texmf-dist/xindy/modules/lang
    # find . -name '*utf8.xdy'
    # LATIN
    'sq': '-L albanian -C utf8 ',
    'hr': '-L croatian -C utf8 ',
    'cs': '-L czech -C utf8 ',
    'da': '-L danish -C utf8 ',
    'nl': '-L dutch -C ij-as-ij-utf8 ',
    'en': '-L english -C utf8 ',
    'eo': '-L esperanto -C utf8 ',
    'et': '-L estonian -C utf8 ',
    'fi': '-L finnish -C utf8 ',
    'fr': '-L french -C utf8 ',
    'de': '-L german -C din5007-utf8 ',
    'is': '-L icelandic -C utf8 ',
    'it': '-L italian -C utf8 ',
    'la': '-L latin -C utf8 ',
    'lv': '-L latvian -C utf8 ',
    'lt': '-L lithuanian -C utf8 ',
    'dsb': '-L lower-sorbian -C utf8 ',
    'ds': '-L lower-sorbian -C utf8 ',   # trick, no conflict
    'nb': '-L norwegian -C utf8 ',
    'no': '-L norwegian -C utf8 ',       # and what about nynorsk?
    'pl': '-L polish -C utf8 ',
    'pt': '-L portuguese -C utf8 ',
    'ro': '-L romanian -C utf8 ',
    'sk': '-L slovak -C small-utf8 ',    # there is also slovak-large
    'sl': '-L slovenian -C utf8 ',
    'es': '-L spanish -C modern-utf8 ',  # there is also spanish-traditional
    'sv': '-L swedish -C utf8 ',
    'tr': '-L turkish -C utf8 ',
    'hsb': '-L upper-sorbian -C utf8 ',
    'hs': '-L upper-sorbian -C utf8 ',   # trick, no conflict
    'vi': '-L vietnamese -C utf8 ',
    # CYRILLIC
    # for usage with pdflatex, needs also cyrLICRutf8.xdy module
    'be': '-L belarusian -C utf8 ',
    'bg': '-L bulgarian -C utf8 ',
    'mk': '-L macedonian -C utf8 ',
    'mn': '-L mongolian -C cyrillic-utf8 ',
    'ru': '-L russian -C utf8 ',
    'sr': '-L serbian -C utf8 ',
    'sh-cyrl': '-L serbian -C utf8 ',
    'sh': '-L serbian -C utf8 ',         # trick, no conflict
    'uk': '-L ukrainian -C utf8 ',
    # GREEK
    # can work only with xelatex/lualatex, not supported by texindy+pdflatex
    'el': '-L greek -C utf8 ',
    # FIXME, not compatible with [:2] slice but does Sphinx support Greek ?
    'el-polyton': '-L greek -C polytonic-utf8 ',
}  # type: Dict[unicode, unicode]

XINDY_CYRILLIC_SCRIPTS = [
    'be', 'bg', 'mk', 'mn', 'ru', 'sr', 'sh', 'uk',
]  # type: List[unicode]

logger = logging.getLogger(__name__)


class LaTeXBuilder(Builder):
    """
    Builds LaTeX output to create PDF.
    """
    name = 'latex'
    format = 'latex'
    epilog = __('The LaTeX files are in %(outdir)s.')
    if os.name == 'posix':
        epilog += __("\nRun 'make' in that directory to run these through "
                     "(pdf)latex\n"
                     "(use `make latexpdf' here to do that automatically).")

    supported_image_types = ['application/pdf', 'image/png', 'image/jpeg']
    supported_remote_images = False
    default_translator_class = LaTeXTranslator

    def init(self):
        # type: () -> None
        self.docnames = []          # type: Iterable[unicode]
        self.document_data = []     # type: List[Tuple[unicode, unicode, unicode, unicode, unicode, bool]]  # NOQA
        self.usepackages = self.app.registry.latex_packages
        texescape.init()

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
        preliminary_document_data = [list(x) for x in self.config.latex_documents]
        if not preliminary_document_data:
            logger.warning(__('no "latex_documents" config value found; no documents '
                              'will be written'))
            return
        # assign subdirs to titles
        self.titles = []  # type: List[Tuple[unicode, unicode]]
        for entry in preliminary_document_data:
            docname = entry[0]
            if docname not in self.env.all_docs:
                logger.warning(__('"latex_documents" config value references unknown '
                                  'document %s'), docname)
                continue
            self.document_data.append(entry)  # type: ignore
            if docname.endswith(SEP + 'index'):
                docname = docname[:-5]
            self.titles.append((docname, entry[2]))

    def write_stylesheet(self):
        # type: () -> None
        highlighter = highlighting.PygmentsBridge('latex', self.config.pygments_style)
        stylesheet = path.join(self.outdir, 'sphinxhighlight.sty')
        with open(stylesheet, 'w') as f:
            f.write('\\NeedsTeXFormat{LaTeX2e}[1995/12/01]\n')
            f.write('\\ProvidesPackage{sphinxhighlight}'
                    '[2016/05/29 stylesheet for highlighting with pygments]\n\n')
            f.write(highlighter.get_stylesheet())  # type: ignore

    def write(self, *ignored):
        # type: (Any) -> None
        docwriter = LaTeXWriter(self)
        docsettings = OptionParser(
            defaults=self.env.settings,
            components=(docwriter,),
            read_config_files=True).get_default_values()

        self.init_document_data()
        self.write_stylesheet()

        for entry in self.document_data:
            docname, targetname, title, author, docclass = entry[:5]
            toctree_only = False
            if len(entry) > 5:
                toctree_only = entry[5]
            destination = SphinxFileOutput(destination_path=path.join(self.outdir, targetname),
                                           encoding='utf-8', overwrite_if_changed=True)
            logger.info(__("processing %s..."), targetname, nonl=1)
            toctrees = self.env.get_doctree(docname).traverse(addnodes.toctree)
            if toctrees:
                if toctrees[0].get('maxdepth') > 0:
                    tocdepth = toctrees[0].get('maxdepth')
                else:
                    tocdepth = None
            else:
                tocdepth = None
            doctree = self.assemble_doctree(
                docname, toctree_only,
                appendices=((docclass != 'howto') and self.config.latex_appendices or []))
            doctree['tocdepth'] = tocdepth
            self.apply_transforms(doctree)
            self.post_process_images(doctree)
            logger.info(__("writing... "), nonl=1)
            doctree.settings = docsettings
            doctree.settings.author = author
            doctree.settings.title = title
            doctree.settings.contentsname = self.get_contentsname(docname)
            doctree.settings.docname = docname
            doctree.settings.docclass = docclass
            docwriter.write(doctree, destination)
            logger.info("done")

    def get_contentsname(self, indexfile):
        # type: (unicode) -> unicode
        tree = self.env.get_doctree(indexfile)
        contentsname = None
        for toctree in tree.traverse(addnodes.toctree):
            if 'caption' in toctree:
                contentsname = toctree['caption']
                break

        return contentsname

    def assemble_doctree(self, indexfile, toctree_only, appendices):
        # type: (unicode, bool, List[unicode]) -> nodes.Node
        from docutils import nodes  # NOQA
        self.docnames = set([indexfile] + appendices)
        logger.info(darkgreen(indexfile) + " ", nonl=1)
        tree = self.env.get_doctree(indexfile)
        tree['docname'] = indexfile
        if toctree_only:
            # extract toctree nodes from the tree and put them in a
            # fresh document
            new_tree = new_document('<latex output>')
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
        # resolve :ref:s to distant tex files -- we can't add a cross-reference,
        # but append the document name
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

    def apply_transforms(self, doctree):
        # type: (nodes.document) -> None
        transformer = SphinxTransformer(doctree)
        transformer.set_environment(self.env)
        transformer.add_transforms([BibliographyTransform,
                                    ShowUrlsTransform,
                                    LaTeXFootnoteTransform,
                                    LiteralBlockTransform,
                                    DocumentTargetTransform,
                                    IndexInSectionTitleTransform])
        transformer.apply_transforms()

    def finish(self):
        # type: () -> None
        self.copy_image_files()

        # copy TeX support files from texinputs
        # configure usage of xindy (impacts Makefile and latexmkrc)
        # FIXME: convert this rather to a confval with suitable default
        #        according to language ? but would require extra documentation
        if self.config.language:
            xindy_lang_option = \
                XINDY_LANG_OPTIONS.get(self.config.language[:2],
                                       '-L general -C utf8 ')
            xindy_cyrillic = self.config.language[:2] in XINDY_CYRILLIC_SCRIPTS
        else:
            xindy_lang_option = '-L english -C utf8 '
            xindy_cyrillic = False
        context = {
            'latex_engine':      self.config.latex_engine,
            'xindy_use':         self.config.latex_use_xindy,
            'xindy_lang_option': xindy_lang_option,
            'xindy_cyrillic':    xindy_cyrillic,
        }
        logger.info(bold(__('copying TeX support files...')))
        staticdirname = path.join(package_dir, 'texinputs')
        for filename in os.listdir(staticdirname):
            if not filename.startswith('.'):
                copy_asset_file(path.join(staticdirname, filename),
                                self.outdir, context=context)

        # use pre-1.6.x Makefile for make latexpdf on Windows
        if os.name == 'nt':
            staticdirname = path.join(package_dir, 'texinputs_win')
            copy_asset_file(path.join(staticdirname, 'Makefile_t'),
                            self.outdir, context=context)

        # copy additional files
        if self.config.latex_additional_files:
            logger.info(bold(__('copying additional files...')), nonl=1)
            for filename in self.config.latex_additional_files:
                logger.info(' ' + filename, nonl=1)
                copy_asset_file(path.join(self.confdir, filename), self.outdir)
            logger.info('')

        # the logo is handled differently
        if self.config.latex_logo:
            if not path.isfile(path.join(self.confdir, self.config.latex_logo)):
                raise SphinxError(__('logo file %r does not exist') % self.config.latex_logo)
            else:
                copy_asset_file(path.join(self.confdir, self.config.latex_logo), self.outdir)
        logger.info(__('done'))

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


def validate_config_values(app, config):
    # type: (Sphinx, Config) -> None
    for document in config.latex_documents:
        try:
            text_type(document[2])
        except UnicodeDecodeError:
            raise ConfigError(
                __('Invalid latex_documents.title found (might contain non-ASCII chars. '
                   'Please use u"..." notation instead): %r') % (document,)
            )

        try:
            text_type(document[3])
        except UnicodeDecodeError:
            raise ConfigError(
                __('Invalid latex_documents.author found (might contain non-ASCII chars. '
                   'Please use u"..." notation instead): %r') % (document,)
            )

    for key in list(config.latex_elements):
        if key not in DEFAULT_SETTINGS:
            msg = __("Unknown configure key: latex_elements[%r]. ignored.")
            logger.warning(msg % (key,))
            config.latex_elements.pop(key)


def default_latex_engine(config):
    # type: (Config) -> unicode
    """ Better default latex_engine settings for specific languages. """
    if config.language == 'ja':
        return 'platex'
    else:
        return 'pdflatex'


def default_latex_docclass(config):
    # type: (Config) -> Dict[unicode, unicode]
    """ Better default latex_docclass settings for specific languages. """
    if config.language == 'ja':
        return {'manual': 'jsbook',
                'howto': 'jreport'}
    else:
        return {}


def default_latex_use_xindy(config):
    # type: (Config) -> bool
    """ Better default latex_use_xindy settings for specific engines. """
    return config.latex_engine in {'xelatex', 'lualatex'}


def setup(app):
    # type: (Sphinx) -> Dict[unicode, Any]
    app.add_builder(LaTeXBuilder)
    app.add_post_transform(CitationReferenceTransform)
    app.add_post_transform(MathReferenceTransform)
    app.connect('config-inited', validate_config_values)
    app.add_transform(FootnoteDocnameUpdater)

    app.add_config_value('latex_engine', default_latex_engine, None,
                         ENUM('pdflatex', 'xelatex', 'lualatex', 'platex'))
    app.add_config_value('latex_documents',
                         lambda self: [(self.master_doc, make_filename(self.project) + '.tex',
                                        self.project, '', 'manual')],
                         None)
    app.add_config_value('latex_logo', None, None, string_classes)
    app.add_config_value('latex_appendices', [], None)
    app.add_config_value('latex_use_latex_multicolumn', False, None)
    app.add_config_value('latex_use_xindy', default_latex_use_xindy, None)
    app.add_config_value('latex_toplevel_sectioning', None, None,
                         ENUM(None, 'part', 'chapter', 'section'))
    app.add_config_value('latex_domain_indices', True, None, [list])
    app.add_config_value('latex_show_urls', 'no', None)
    app.add_config_value('latex_show_pagerefs', False, None)
    app.add_config_value('latex_elements', {}, None)
    app.add_config_value('latex_additional_files', [], None)

    app.add_config_value('latex_docclass', default_latex_docclass, None)

    return {
        'version': 'builtin',
        'parallel_read_safe': True,
        'parallel_write_safe': True,
    }
