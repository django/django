# -*- coding: utf-8 -*-
"""
    sphinx.builders.html
    ~~~~~~~~~~~~~~~~~~~~

    Several HTML builders.

    :copyright: Copyright 2007-2019 by the Sphinx team, see AUTHORS.
    :license: BSD, see LICENSE for details.
"""

import codecs
import posixpath
import re
import sys
import types
import warnings
from hashlib import md5
from os import path

import docutils
from docutils import nodes
from docutils.core import Publisher
from docutils.frontend import OptionParser
from docutils.io import DocTreeInput, StringOutput
from docutils.readers.doctree import Reader as DoctreeReader
from docutils.utils import relative_path
from six import iteritems, text_type, string_types
from six.moves import cPickle as pickle

from sphinx import package_dir, __display_version__
from sphinx.application import ENV_PICKLE_FILENAME
from sphinx.builders import Builder
from sphinx.config import string_classes
from sphinx.deprecation import RemovedInSphinx20Warning, RemovedInSphinx30Warning
from sphinx.environment.adapters.asset import ImageAdapter
from sphinx.environment.adapters.indexentries import IndexEntries
from sphinx.environment.adapters.toctree import TocTree
from sphinx.errors import ConfigError, ThemeError
from sphinx.highlighting import PygmentsBridge
from sphinx.locale import _, __
from sphinx.search import js_index
from sphinx.theming import HTMLThemeFactory
from sphinx.util import jsonimpl, logging, status_iterator
from sphinx.util.console import bold, darkgreen  # type: ignore
from sphinx.util.docutils import is_html5_writer_available, new_document
from sphinx.util.fileutil import copy_asset
from sphinx.util.i18n import format_date
from sphinx.util.inventory import InventoryFile
from sphinx.util.matching import patmatch, Matcher, DOTFILES
from sphinx.util.nodes import inline_all_toctrees
from sphinx.util.osutil import SEP, os_path, relative_uri, ensuredir, \
    movefile, copyfile
from sphinx.util.pycompat import htmlescape
from sphinx.writers.html import HTMLWriter, HTMLTranslator

if False:
    # For type annotation
    from typing import Any, Dict, IO, Iterable, Iterator, List, Type, Tuple, Union  # NOQA
    from sphinx.application import Sphinx  # NOQA
    from sphinx.config import Config  # NOQA
    from sphinx.domains import Domain, Index  # NOQA
    from sphinx.util.tags import Tags  # NOQA

# Experimental HTML5 Writer
if is_html5_writer_available():
    from sphinx.writers.html5 import HTML5Translator
    html5_ready = True
else:
    html5_ready = False

#: the filename for the inventory of objects
INVENTORY_FILENAME = 'objects.inv'
#: the filename for the "last build" file (for serializing builders)
LAST_BUILD_FILENAME = 'last_build'

logger = logging.getLogger(__name__)
return_codes_re = re.compile('[\r\n]+')


def get_stable_hash(obj):
    # type: (Any) -> unicode
    """
    Return a stable hash for a Python data structure.  We can't just use
    the md5 of str(obj) since for example dictionary items are enumerated
    in unpredictable order due to hash randomization in newer Pythons.
    """
    if isinstance(obj, dict):
        return get_stable_hash(list(obj.items()))
    elif isinstance(obj, (list, tuple)):
        obj = sorted(get_stable_hash(o) for o in obj)
    return md5(text_type(obj).encode('utf8')).hexdigest()


class CSSContainer(list):
    """The container for stylesheets.

    To support the extensions which access the container directly, this wraps
    the entry with Stylesheet class.
    """
    def append(self, obj):
        # type: (Union[unicode, Stylesheet]) -> None
        if isinstance(obj, Stylesheet):
            super(CSSContainer, self).append(obj)
        else:
            super(CSSContainer, self).append(Stylesheet(obj))

    def insert(self, index, obj):
        # type: (int, Union[unicode, Stylesheet]) -> None
        warnings.warn('builder.css_files is deprecated. '
                      'Please use app.add_stylesheet() instead.',
                      RemovedInSphinx20Warning, stacklevel=2)
        if isinstance(obj, Stylesheet):
            super(CSSContainer, self).insert(index, obj)
        else:
            super(CSSContainer, self).insert(index, Stylesheet(obj))

    def extend(self, other):  # type: ignore
        # type: (List[Union[unicode, Stylesheet]]) -> None
        warnings.warn('builder.css_files is deprecated. '
                      'Please use app.add_stylesheet() instead.',
                      RemovedInSphinx20Warning, stacklevel=2)
        for item in other:
            self.append(item)

    def __iadd__(self, other):  # type: ignore
        # type: (List[Union[unicode, Stylesheet]]) -> CSSContainer
        warnings.warn('builder.css_files is deprecated. '
                      'Please use app.add_stylesheet() instead.',
                      RemovedInSphinx20Warning, stacklevel=2)
        for item in other:
            self.append(item)
        return self

    def __add__(self, other):
        # type: (List[Union[unicode, Stylesheet]]) -> CSSContainer
        ret = CSSContainer(self)
        ret += other
        return ret


class Stylesheet(text_type):
    """A metadata of stylesheet.

    To keep compatibility with old themes, an instance of stylesheet behaves as
    its filename (str).
    """

    attributes = None   # type: Dict[unicode, unicode]
    filename = None     # type: unicode

    def __new__(cls, filename, *args, **attributes):
        # type: (unicode, unicode, unicode) -> None
        self = text_type.__new__(cls, filename)  # type: ignore
        self.filename = filename
        self.attributes = attributes
        self.attributes.setdefault('rel', 'stylesheet')
        self.attributes.setdefault('type', 'text/css')
        if args:  # old style arguments (rel, title)
            self.attributes['rel'] = args[0]
            self.attributes['title'] = args[1]

        return self


class JSContainer(list):
    """The container for JavaScript scripts."""
    def insert(self, index, obj):
        # type: (int, unicode) -> None
        warnings.warn('builder.script_files is deprecated. '
                      'Please use app.add_js_file() instead.',
                      RemovedInSphinx30Warning, stacklevel=2)
        super(JSContainer, self).insert(index, obj)

    def extend(self, other):  # type: ignore
        # type: (List[unicode]) -> None
        warnings.warn('builder.script_files is deprecated. '
                      'Please use app.add_js_file() instead.',
                      RemovedInSphinx30Warning, stacklevel=2)
        for item in other:
            self.append(item)

    def __iadd__(self, other):  # type: ignore
        # type: (List[unicode]) -> JSContainer
        warnings.warn('builder.script_files is deprecated. '
                      'Please use app.add_js_file() instead.',
                      RemovedInSphinx30Warning, stacklevel=2)
        for item in other:
            self.append(item)
        return self

    def __add__(self, other):
        # type: (List[unicode]) -> JSContainer
        ret = JSContainer(self)
        ret += other
        return ret


class JavaScript(text_type):
    """A metadata of javascript file.

    To keep compatibility with old themes, an instance of javascript behaves as
    its filename (str).
    """

    attributes = None   # type: Dict[unicode, unicode]
    filename = None     # type: unicode

    def __new__(cls, filename, **attributes):
        # type: (unicode, **unicode) -> None
        self = text_type.__new__(cls, filename)  # type: ignore
        self.filename = filename
        self.attributes = attributes
        self.attributes.setdefault('type', 'text/javascript')

        return self


class BuildInfo(object):
    """buildinfo file manipulator.

    HTMLBuilder and its family are storing their own envdata to ``.buildinfo``.
    This class is a manipulator for the file.
    """

    @classmethod
    def load(cls, f):
        # type: (IO) -> BuildInfo
        try:
            lines = f.readlines()
            assert lines[0].rstrip() == '# Sphinx build info version 1'
            assert lines[2].startswith('config: ')
            assert lines[3].startswith('tags: ')

            build_info = BuildInfo()
            build_info.config_hash = lines[2].split()[1].strip()
            build_info.tags_hash = lines[3].split()[1].strip()
            return build_info
        except Exception as exc:
            raise ValueError(__('build info file is broken: %r') % exc)

    def __init__(self, config=None, tags=None, config_categories=[]):
        # type: (Config, Tags, List[unicode]) -> None
        self.config_hash = u''
        self.tags_hash = u''

        if config:
            values = dict((c.name, c.value) for c in config.filter(config_categories))
            self.config_hash = get_stable_hash(values)

        if tags:
            self.tags_hash = get_stable_hash(sorted(tags))

    def __eq__(self, other):  # type: ignore
        # type: (BuildInfo) -> bool
        return (self.config_hash == other.config_hash and
                self.tags_hash == other.tags_hash)

    def __ne__(self, other):  # type: ignore
        # type: (BuildInfo) -> bool
        return not (self == other)  # for py27

    def dump(self, f):
        # type: (IO) -> None
        f.write('# Sphinx build info version 1\n'
                '# This file hashes the configuration used when building these files.'
                ' When it is not found, a full rebuild will be done.\n'
                'config: %s\n'
                'tags: %s\n' %
                (self.config_hash, self.tags_hash))


class StandaloneHTMLBuilder(Builder):
    """
    Builds standalone HTML docs.
    """
    name = 'html'
    format = 'html'
    epilog = __('The HTML pages are in %(outdir)s.')

    copysource = True
    allow_parallel = True
    out_suffix = '.html'
    link_suffix = '.html'  # defaults to matching out_suffix
    indexer_format = js_index  # type: Any
    indexer_dumps_unicode = True
    # create links to original images from images [True/False]
    html_scaled_image_link = True
    supported_image_types = ['image/svg+xml', 'image/png',
                             'image/gif', 'image/jpeg']
    supported_remote_images = True
    supported_data_uri_images = True
    searchindex_filename = 'searchindex.js'
    add_permalinks = True
    allow_sharp_as_current_path = True
    embedded = False  # for things like HTML help or Qt help: suppresses sidebar
    search = True  # for things like HTML help and Apple help: suppress search
    use_index = False
    download_support = True  # enable download role
    # use html5 translator by default
    default_html5_translator = False

    imgpath = None          # type: unicode
    domain_indices = []     # type: List[Tuple[unicode, Type[Index], List[Tuple[unicode, List[List[Union[unicode, int]]]]], bool]]  # NOQA

    # cached publisher object for snippets
    _publisher = None

    def __init__(self, app):
        # type: (Sphinx) -> None
        super(StandaloneHTMLBuilder, self).__init__(app)

        # CSS files
        self.css_files = CSSContainer()  # type: List[Dict[unicode, unicode]]

        # JS files
        self.script_files = JSContainer()  # type: List[JavaScript]

    def init(self):
        # type: () -> None
        self.build_info = self.create_build_info()
        # basename of images directory
        self.imagedir = '_images'
        # section numbers for headings in the currently visited document
        self.secnumbers = {}  # type: Dict[unicode, Tuple[int, ...]]
        # currently written docname
        self.current_docname = None  # type: unicode

        self.init_templates()
        self.init_highlighter()
        self.init_css_files()
        self.init_js_files()
        if self.config.html_file_suffix is not None:
            self.out_suffix = self.config.html_file_suffix

        if self.config.html_link_suffix is not None:
            self.link_suffix = self.config.html_link_suffix
        else:
            self.link_suffix = self.out_suffix

        self.use_index = self.get_builder_config('use_index', 'html')

        if self.config.html_experimental_html5_writer and not html5_ready:
            self.app.warn(('html_experimental_html5_writer is set, but current version '
                           'is old. Docutils\' version should be 0.13 or newer, but %s.') %
                          docutils.__version__)

    def create_build_info(self):
        # type: () -> BuildInfo
        return BuildInfo(self.config, self.tags, ['html'])

    def _get_translations_js(self):
        # type: () -> unicode
        candidates = [path.join(dir, self.config.language,
                                'LC_MESSAGES', 'sphinx.js')
                      for dir in self.config.locale_dirs] + \
                     [path.join(package_dir, 'locale', self.config.language,
                                'LC_MESSAGES', 'sphinx.js'),
                      path.join(sys.prefix, 'share/sphinx/locale',
                                self.config.language, 'sphinx.js')]

        for jsfile in candidates:
            if path.isfile(jsfile):
                return jsfile
        return None

    def get_theme_config(self):
        # type: () -> Tuple[unicode, Dict]
        return self.config.html_theme, self.config.html_theme_options

    def init_templates(self):
        # type: () -> None
        theme_factory = HTMLThemeFactory(self.app)
        themename, themeoptions = self.get_theme_config()
        self.theme = theme_factory.create(themename)
        self.theme_options = themeoptions.copy()
        self.create_template_bridge()
        self.templates.init(self, self.theme)

    def init_highlighter(self):
        # type: () -> None
        # determine Pygments style and create the highlighter
        if self.config.pygments_style is not None:
            style = self.config.pygments_style
        elif self.theme:
            style = self.theme.get_config('theme', 'pygments_style', 'none')
        else:
            style = 'sphinx'
        self.highlighter = PygmentsBridge('html', style)

    def init_css_files(self):
        # type: () -> None
        for filename, attrs in self.app.registry.css_files:
            self.add_css_file(filename, **attrs)

        for filename, attrs in self.get_builder_config('css_files', 'html'):
            self.add_css_file(filename, **attrs)

    def add_css_file(self, filename, **kwargs):
        # type: (unicode, **unicode) -> None
        if '://' not in filename:
            filename = posixpath.join('_static', filename)

        self.css_files.append(Stylesheet(filename, **kwargs))  # type: ignore

    def init_js_files(self):
        # type: () -> None
        self.add_js_file('jquery.js')
        self.add_js_file('underscore.js')
        self.add_js_file('doctools.js')
        self.add_js_file('language_data.js')

        for filename, attrs in self.app.registry.js_files:
            self.add_js_file(filename, **attrs)

        for filename, attrs in self.get_builder_config('js_files', 'html'):
            self.add_js_file(filename, **attrs)

        if self.config.language and self._get_translations_js():
            self.add_js_file('translations.js')

    def add_js_file(self, filename, **kwargs):
        # type: (unicode, **unicode) -> None
        if filename and '://' not in filename:
            filename = posixpath.join('_static', filename)

        self.script_files.append(JavaScript(filename, **kwargs))

    @property
    def default_translator_class(self):
        # type: () -> nodes.NodeVisitor
        use_html5_writer = self.config.html_experimental_html5_writer
        if use_html5_writer is None:
            use_html5_writer = self.default_html5_translator

        if use_html5_writer and html5_ready:
            return HTML5Translator
        else:
            return HTMLTranslator

    @property
    def math_renderer_name(self):
        # type: () -> unicode
        name = self.get_builder_config('math_renderer', 'html')
        if name is not None:
            # use given name
            return name
        else:
            # not given: choose a math_renderer from registered ones as possible
            renderers = list(self.app.registry.html_inline_math_renderers)
            if len(renderers) == 1:
                # only default math_renderer (mathjax) is registered
                return renderers[0]
            elif len(renderers) == 2:
                # default and another math_renderer are registered; prior the another
                renderers.remove('mathjax')
                return renderers[0]
            else:
                # many math_renderers are registered. can't choose automatically!
                return None

    def get_outdated_docs(self):
        # type: () -> Iterator[unicode]
        try:
            with open(path.join(self.outdir, '.buildinfo')) as fp:
                buildinfo = BuildInfo.load(fp)

            if self.build_info != buildinfo:
                for docname in self.env.found_docs:
                    yield docname
                return
        except ValueError as exc:
            logger.warning(__('Failed to read build info file: %r'), exc)
        except IOError:
            # ignore errors on reading
            pass

        if self.templates:
            template_mtime = self.templates.newest_template_mtime()
        else:
            template_mtime = 0
        for docname in self.env.found_docs:
            if docname not in self.env.all_docs:
                yield docname
                continue
            targetname = self.get_outfilename(docname)
            try:
                targetmtime = path.getmtime(targetname)
            except Exception:
                targetmtime = 0
            try:
                srcmtime = max(path.getmtime(self.env.doc2path(docname)),
                               template_mtime)
                if srcmtime > targetmtime:
                    yield docname
            except EnvironmentError:
                # source doesn't exist anymore
                pass

    def get_asset_paths(self):
        # type: () -> List[unicode]
        return self.config.html_extra_path + self.config.html_static_path

    def render_partial(self, node):
        # type: (nodes.Nodes) -> Dict[unicode, unicode]
        """Utility: Render a lone doctree node."""
        if node is None:
            return {'fragment': ''}
        doc = new_document(b'<partial node>')
        doc.append(node)

        if self._publisher is None:
            self._publisher = Publisher(
                source_class = DocTreeInput,
                destination_class=StringOutput)
            self._publisher.set_components('standalone',
                                           'restructuredtext', 'pseudoxml')

        pub = self._publisher

        pub.reader = DoctreeReader()
        pub.writer = HTMLWriter(self)
        pub.process_programmatic_settings(
            None, {'output_encoding': 'unicode'}, None)
        pub.set_source(doc, None)
        pub.set_destination(None, None)
        pub.publish()
        return pub.writer.parts

    def prepare_writing(self, docnames):
        # type: (Iterable[unicode]) -> nodes.Node
        # create the search indexer
        self.indexer = None
        if self.search:
            from sphinx.search import IndexBuilder
            lang = self.config.html_search_language or self.config.language
            if not lang:
                lang = 'en'
            self.indexer = IndexBuilder(self.env, lang,
                                        self.config.html_search_options,
                                        self.config.html_search_scorer)
            self.load_indexer(docnames)

        self.docwriter = HTMLWriter(self)
        self.docsettings = OptionParser(
            defaults=self.env.settings,
            components=(self.docwriter,),
            read_config_files=True).get_default_values()
        self.docsettings.compact_lists = bool(self.config.html_compact_lists)

        # determine the additional indices to include
        self.domain_indices = []
        # html_domain_indices can be False/True or a list of index names
        indices_config = self.config.html_domain_indices
        if indices_config:
            for domain_name in sorted(self.env.domains):
                domain = None  # type: Domain
                domain = self.env.domains[domain_name]
                for indexcls in domain.indices:
                    indexname = '%s-%s' % (domain.name, indexcls.name)  # type: unicode
                    if isinstance(indices_config, list):
                        if indexname not in indices_config:
                            continue
                    content, collapse = indexcls(domain).generate()
                    if content:
                        self.domain_indices.append(
                            (indexname, indexcls, content, collapse))

        # format the "last updated on" string, only once is enough since it
        # typically doesn't include the time of day
        lufmt = self.config.html_last_updated_fmt
        if lufmt is not None:
            self.last_updated = format_date(lufmt or _('%b %d, %Y'),
                                            language=self.config.language)
        else:
            self.last_updated = None

        logo = self.config.html_logo and \
            path.basename(self.config.html_logo) or ''

        favicon = self.config.html_favicon and \
            path.basename(self.config.html_favicon) or ''

        if not isinstance(self.config.html_use_opensearch, string_types):
            logger.warning(__('html_use_opensearch config value must now be a string'))

        self.relations = self.env.collect_relations()

        rellinks = []  # type: List[Tuple[unicode, unicode, unicode, unicode]]
        if self.use_index:
            rellinks.append(('genindex', _('General Index'), 'I', _('index')))
        for indexname, indexcls, content, collapse in self.domain_indices:
            # if it has a short name
            if indexcls.shortname:
                rellinks.append((indexname, indexcls.localname,
                                 '', indexcls.shortname))

        if self.config.html_style is not None:
            stylename = self.config.html_style
        elif self.theme:
            stylename = self.theme.get_config('theme', 'stylesheet')
        else:
            stylename = 'default.css'

        self.globalcontext = dict(
            embedded = self.embedded,
            project = self.config.project,
            release = return_codes_re.sub('', self.config.release),
            version = self.config.version,
            last_updated = self.last_updated,
            copyright = self.config.copyright,
            master_doc = self.config.master_doc,
            use_opensearch = self.config.html_use_opensearch,
            docstitle = self.config.html_title,
            shorttitle = self.config.html_short_title,
            show_copyright = self.config.html_show_copyright,
            show_sphinx = self.config.html_show_sphinx,
            has_source = self.config.html_copy_source,
            show_source = self.config.html_show_sourcelink,
            sourcelink_suffix = self.config.html_sourcelink_suffix,
            file_suffix = self.out_suffix,
            script_files = self.script_files,
            language = self.config.language,
            css_files = self.css_files,
            sphinx_version = __display_version__,
            style = stylename,
            rellinks = rellinks,
            builder = self.name,
            parents = [],
            logo = logo,
            favicon = favicon,
            html5_doctype = self.config.html_experimental_html5_writer and html5_ready,
        )  # type: Dict[unicode, Any]
        if self.theme:
            self.globalcontext.update(
                ('theme_' + key, val) for (key, val) in
                iteritems(self.theme.get_options(self.theme_options)))
        self.globalcontext.update(self.config.html_context)

    def get_doc_context(self, docname, body, metatags):
        # type: (unicode, unicode, Dict) -> Dict[unicode, Any]
        """Collect items for the template context of a page."""
        # find out relations
        prev = next = None
        parents = []
        rellinks = self.globalcontext['rellinks'][:]
        related = self.relations.get(docname)
        titles = self.env.titles
        if related and related[2]:
            try:
                next = {
                    'link': self.get_relative_uri(docname, related[2]),
                    'title': self.render_partial(titles[related[2]])['title']
                }
                rellinks.append((related[2], next['title'], 'N', _('next')))
            except KeyError:
                next = None
        if related and related[1]:
            try:
                prev = {
                    'link': self.get_relative_uri(docname, related[1]),
                    'title': self.render_partial(titles[related[1]])['title']
                }
                rellinks.append((related[1], prev['title'], 'P', _('previous')))
            except KeyError:
                # the relation is (somehow) not in the TOC tree, handle
                # that gracefully
                prev = None
        while related and related[0]:
            try:
                parents.append(
                    {'link': self.get_relative_uri(docname, related[0]),
                     'title': self.render_partial(titles[related[0]])['title']})
            except KeyError:
                pass
            related = self.relations.get(related[0])
        if parents:
            # remove link to the master file; we have a generic
            # "back to index" link already
            parents.pop()
        parents.reverse()

        # title rendered as HTML
        title = self.env.longtitles.get(docname)
        title = title and self.render_partial(title)['title'] or ''

        # Suffix for the document
        source_suffix = path.splitext(self.env.doc2path(docname))[1]

        # the name for the copied source
        if self.config.html_copy_source:
            sourcename = docname + source_suffix
            if source_suffix != self.config.html_sourcelink_suffix:
                sourcename += self.config.html_sourcelink_suffix
        else:
            sourcename = ''

        # metadata for the document
        meta = self.env.metadata.get(docname)

        # local TOC and global TOC tree
        self_toc = TocTree(self.env).get_toc_for(docname, self)
        toc = self.render_partial(self_toc)['fragment']

        return dict(
            parents = parents,
            prev = prev,
            next = next,
            title = title,
            meta = meta,
            body = body,
            metatags = metatags,
            rellinks = rellinks,
            sourcename = sourcename,
            toc = toc,
            # only display a TOC if there's more than one item to show
            display_toc = (self.env.toc_num_entries[docname] > 1),
            page_source_suffix = source_suffix,
        )

    def write_doc(self, docname, doctree):
        # type: (unicode, nodes.Node) -> None
        destination = StringOutput(encoding='utf-8')
        doctree.settings = self.docsettings

        self.secnumbers = self.env.toc_secnumbers.get(docname, {})
        self.fignumbers = self.env.toc_fignumbers.get(docname, {})  # type: Dict[unicode, Dict[unicode, Tuple[int, ...]]]  # NOQA
        self.imgpath = relative_uri(self.get_target_uri(docname), '_images')
        self.dlpath = relative_uri(self.get_target_uri(docname), '_downloads')  # type: unicode
        self.current_docname = docname
        self.docwriter.write(doctree, destination)
        self.docwriter.assemble_parts()
        body = self.docwriter.parts['fragment']
        metatags = self.docwriter.clean_meta

        ctx = self.get_doc_context(docname, body, metatags)
        self.handle_page(docname, ctx, event_arg=doctree)

    def write_doc_serialized(self, docname, doctree):
        # type: (unicode, nodes.Node) -> None
        self.imgpath = relative_uri(self.get_target_uri(docname), self.imagedir)
        self.post_process_images(doctree)
        title = self.env.longtitles.get(docname)
        title = title and self.render_partial(title)['title'] or ''
        self.index_page(docname, doctree, title)

    def finish(self):
        # type: () -> None
        self.finish_tasks.add_task(self.gen_indices)
        self.finish_tasks.add_task(self.gen_additional_pages)
        self.finish_tasks.add_task(self.copy_image_files)
        self.finish_tasks.add_task(self.copy_download_files)
        self.finish_tasks.add_task(self.copy_static_files)
        self.finish_tasks.add_task(self.copy_extra_files)
        self.finish_tasks.add_task(self.write_buildinfo)

        # dump the search index
        self.handle_finish()

    def gen_indices(self):
        # type: () -> None
        logger.info(bold(__('generating indices...')), nonl=1)

        # the global general index
        if self.use_index:
            self.write_genindex()

        # the global domain-specific indices
        self.write_domain_indices()

        logger.info('')

    def gen_additional_pages(self):
        # type: () -> None
        # pages from extensions
        for pagelist in self.app.emit('html-collect-pages'):
            for pagename, context, template in pagelist:
                self.handle_page(pagename, context, template)

        logger.info(bold(__('writing additional pages...')), nonl=1)

        # additional pages from conf.py
        for pagename, template in self.config.html_additional_pages.items():
            logger.info(' ' + pagename, nonl=1)
            self.handle_page(pagename, {}, template)

        # the search page
        if self.search:
            logger.info(' search', nonl=1)
            self.handle_page('search', {}, 'search.html')

        # the opensearch xml file
        if self.config.html_use_opensearch and self.search:
            logger.info(' opensearch', nonl=1)
            fn = path.join(self.outdir, '_static', 'opensearch.xml')
            self.handle_page('opensearch', {}, 'opensearch.xml', outfilename=fn)

        logger.info('')

    def write_genindex(self):
        # type: () -> None
        # the total count of lines for each index letter, used to distribute
        # the entries into two columns
        genindex = IndexEntries(self.env).create_index(self)
        indexcounts = []
        for _k, entries in genindex:
            indexcounts.append(sum(1 + len(subitems)
                                   for _, (_, subitems, _) in entries))

        genindexcontext = dict(
            genindexentries = genindex,
            genindexcounts = indexcounts,
            split_index = self.config.html_split_index,
        )
        logger.info(' genindex', nonl=1)

        if self.config.html_split_index:
            self.handle_page('genindex', genindexcontext,
                             'genindex-split.html')
            self.handle_page('genindex-all', genindexcontext,
                             'genindex.html')
            for (key, entries), count in zip(genindex, indexcounts):
                ctx = {'key': key, 'entries': entries, 'count': count,
                       'genindexentries': genindex}
                self.handle_page('genindex-' + key, ctx,
                                 'genindex-single.html')
        else:
            self.handle_page('genindex', genindexcontext, 'genindex.html')

    def write_domain_indices(self):
        # type: () -> None
        for indexname, indexcls, content, collapse in self.domain_indices:
            indexcontext = dict(
                indextitle = indexcls.localname,
                content = content,
                collapse_index = collapse,
            )
            logger.info(' ' + indexname, nonl=1)
            self.handle_page(indexname, indexcontext, 'domainindex.html')

    def copy_image_files(self):
        # type: () -> None
        if self.images:
            stringify_func = ImageAdapter(self.app.env).get_original_image_uri
            ensuredir(path.join(self.outdir, self.imagedir))
            for src in status_iterator(self.images, __('copying images... '), "brown",
                                       len(self.images), self.app.verbosity,
                                       stringify_func=stringify_func):
                dest = self.images[src]
                try:
                    copyfile(path.join(self.srcdir, src),
                             path.join(self.outdir, self.imagedir, dest))
                except Exception as err:
                    logger.warning(__('cannot copy image file %r: %s'),
                                   path.join(self.srcdir, src), err)

    def copy_download_files(self):
        # type: () -> None
        def to_relpath(f):
            # type: (unicode) -> unicode
            return relative_path(self.srcdir, f)
        # copy downloadable files
        if self.env.dlfiles:
            ensuredir(path.join(self.outdir, '_downloads'))
            for src in status_iterator(self.env.dlfiles, __('copying downloadable files... '),
                                       "brown", len(self.env.dlfiles), self.app.verbosity,
                                       stringify_func=to_relpath):
                try:
                    dest = path.join(self.outdir, '_downloads', self.env.dlfiles[src][1])
                    ensuredir(path.dirname(dest))
                    copyfile(path.join(self.srcdir, src), dest)
                except EnvironmentError as err:
                    logger.warning(__('cannot copy downloadable file %r: %s'),
                                   path.join(self.srcdir, src), err)

    def copy_static_files(self):
        # type: () -> None
        try:
            # copy static files
            logger.info(bold(__('copying static files... ')), nonl=True)
            ensuredir(path.join(self.outdir, '_static'))
            # first, create pygments style file
            with open(path.join(self.outdir, '_static', 'pygments.css'), 'w') as f:
                f.write(self.highlighter.get_stylesheet())  # type: ignore
            # then, copy translations JavaScript file
            if self.config.language is not None:
                jsfile = self._get_translations_js()
                if jsfile:
                    copyfile(jsfile, path.join(self.outdir, '_static',
                                               'translations.js'))

            # copy non-minified stemmer JavaScript file
            if self.indexer is not None:
                jsfile = self.indexer.get_js_stemmer_rawcode()
                if jsfile:
                    copyfile(jsfile, path.join(self.outdir, '_static', '_stemmer.js'))

            ctx = self.globalcontext.copy()

            # add context items for search function used in searchtools.js_t
            if self.indexer is not None:
                ctx.update(self.indexer.context_for_searchtool())

            # then, copy over theme-supplied static files
            if self.theme:
                for theme_path in self.theme.get_theme_dirs()[::-1]:
                    entry = path.join(theme_path, 'static')
                    copy_asset(entry, path.join(self.outdir, '_static'), excluded=DOTFILES,
                               context=ctx, renderer=self.templates)
            # then, copy over all user-supplied static files
            excluded = Matcher(self.config.exclude_patterns + ["**/.*"])
            for static_path in self.config.html_static_path:
                entry = path.join(self.confdir, static_path)
                if not path.exists(entry):
                    logger.warning(__('html_static_path entry %r does not exist'), entry)
                    continue
                copy_asset(entry, path.join(self.outdir, '_static'), excluded,
                           context=ctx, renderer=self.templates)
            # copy logo and favicon files if not already in static path
            if self.config.html_logo:
                logobase = path.basename(self.config.html_logo)
                logotarget = path.join(self.outdir, '_static', logobase)
                if not path.isfile(path.join(self.confdir, self.config.html_logo)):
                    logger.warning(__('logo file %r does not exist'), self.config.html_logo)
                elif not path.isfile(logotarget):
                    copyfile(path.join(self.confdir, self.config.html_logo),
                             logotarget)
            if self.config.html_favicon:
                iconbase = path.basename(self.config.html_favicon)
                icontarget = path.join(self.outdir, '_static', iconbase)
                if not path.isfile(path.join(self.confdir, self.config.html_favicon)):
                    logger.warning(__('favicon file %r does not exist'),
                                   self.config.html_favicon)
                elif not path.isfile(icontarget):
                    copyfile(path.join(self.confdir, self.config.html_favicon),
                             icontarget)
            logger.info('done')
        except EnvironmentError as err:
            # TODO: In py3, EnvironmentError (and IOError) was merged into OSError.
            # So it should be replaced by IOError on dropping py2 support
            logger.warning(__('cannot copy static file %r'), err)

    def copy_extra_files(self):
        # type: () -> None
        try:
            # copy html_extra_path files
            logger.info(bold(__('copying extra files... ')), nonl=True)
            excluded = Matcher(self.config.exclude_patterns)

            for extra_path in self.config.html_extra_path:
                entry = path.join(self.confdir, extra_path)
                if not path.exists(entry):
                    logger.warning(__('html_extra_path entry %r does not exist'), entry)
                    continue

                copy_asset(entry, self.outdir, excluded)
            logger.info(__('done'))
        except EnvironmentError as err:
            logger.warning(__('cannot copy extra file %r'), err)

    def write_buildinfo(self):
        # type: () -> None
        try:
            with open(path.join(self.outdir, '.buildinfo'), 'w') as fp:
                self.build_info.dump(fp)
        except IOError as exc:
            logger.warning(__('Failed to write build info file: %r'), exc)

    def cleanup(self):
        # type: () -> None
        # clean up theme stuff
        if self.theme:
            self.theme.cleanup()

    def post_process_images(self, doctree):
        # type: (nodes.Node) -> None
        """Pick the best candidate for an image and link down-scaled images to
        their high res version.
        """
        Builder.post_process_images(self, doctree)

        if self.config.html_scaled_image_link and self.html_scaled_image_link:
            for node in doctree.traverse(nodes.image):
                scale_keys = ('scale', 'width', 'height')
                if not any((key in node) for key in scale_keys) or \
                   isinstance(node.parent, nodes.reference):
                    # docutils does unfortunately not preserve the
                    # ``target`` attribute on images, so we need to check
                    # the parent node here.
                    continue
                uri = node['uri']
                reference = nodes.reference('', '', internal=True)
                if uri in self.images:
                    reference['refuri'] = posixpath.join(self.imgpath,
                                                         self.images[uri])
                else:
                    reference['refuri'] = uri
                node.replace_self(reference)
                reference.append(node)

    def load_indexer(self, docnames):
        # type: (Iterable[unicode]) -> None
        keep = set(self.env.all_docs) - set(docnames)
        try:
            searchindexfn = path.join(self.outdir, self.searchindex_filename)
            if self.indexer_dumps_unicode:
                f = codecs.open(searchindexfn, 'r', encoding='utf-8')  # type: ignore
            else:
                f = open(searchindexfn, 'rb')  # type: ignore
            with f:
                self.indexer.load(f, self.indexer_format)
        except (IOError, OSError, ValueError):
            if keep:
                logger.warning(__('search index couldn\'t be loaded, but not all '
                                  'documents will be built: the index will be '
                                  'incomplete.'))
        # delete all entries for files that will be rebuilt
        self.indexer.prune(keep)

    def index_page(self, pagename, doctree, title):
        # type: (unicode, nodes.Node, unicode) -> None
        # only index pages with title
        if self.indexer is not None and title:
            filename = self.env.doc2path(pagename, base=None)
            try:
                self.indexer.feed(pagename, filename, title, doctree)
            except TypeError:
                # fallback for old search-adapters
                self.indexer.feed(pagename, title, doctree)  # type: ignore

    def _get_local_toctree(self, docname, collapse=True, **kwds):
        # type: (unicode, bool, Any) -> unicode
        if 'includehidden' not in kwds:
            kwds['includehidden'] = False
        return self.render_partial(TocTree(self.env).get_toctree_for(
            docname, self, collapse, **kwds))['fragment']

    def get_outfilename(self, pagename):
        # type: (unicode) -> unicode
        return path.join(self.outdir, os_path(pagename) + self.out_suffix)

    def add_sidebars(self, pagename, ctx):
        # type: (unicode, Dict) -> None
        def has_wildcard(pattern):
            # type: (unicode) -> bool
            return any(char in pattern for char in '*?[')
        sidebars = None
        matched = None
        customsidebar = None

        # default sidebars settings for selected theme
        if self.theme.name == 'alabaster':
            # provide default settings for alabaster (for compatibility)
            # Note: this will be removed before Sphinx-2.0
            try:
                # get default sidebars settings from alabaster (if defined)
                theme_default_sidebars = self.theme.config.get('theme', 'sidebars')
                if theme_default_sidebars:
                    sidebars = [name.strip() for name in theme_default_sidebars.split(',')]
            except Exception:
                # fallback to better default settings
                sidebars = ['about.html', 'navigation.html', 'relations.html',
                            'searchbox.html', 'donate.html']
        else:
            theme_default_sidebars = self.theme.get_config('theme', 'sidebars', None)
            if theme_default_sidebars:
                sidebars = [name.strip() for name in theme_default_sidebars.split(',')]

        # user sidebar settings
        html_sidebars = self.get_builder_config('sidebars', 'html')
        for pattern, patsidebars in iteritems(html_sidebars):
            if patmatch(pagename, pattern):
                if matched:
                    if has_wildcard(pattern):
                        # warn if both patterns contain wildcards
                        if has_wildcard(matched):
                            logger.warning(__('page %s matches two patterns in '
                                              'html_sidebars: %r and %r'),
                                           pagename, matched, pattern)
                        # else the already matched pattern is more specific
                        # than the present one, because it contains no wildcard
                        continue
                matched = pattern
                sidebars = patsidebars

        if sidebars is None:
            # keep defaults
            pass
        elif isinstance(sidebars, string_types):
            # 0.x compatible mode: insert custom sidebar before searchbox
            customsidebar = sidebars
            sidebars = None
            warnings.warn('Now html_sidebars only allows list of sidebar '
                          'templates as a value. Support for a string value '
                          'will be removed at Sphinx-2.0.',
                          RemovedInSphinx20Warning, stacklevel=2)

        ctx['sidebars'] = sidebars
        ctx['customsidebar'] = customsidebar

    # --------- these are overwritten by the serialization builder

    def get_target_uri(self, docname, typ=None):
        # type: (unicode, unicode) -> unicode
        return docname + self.link_suffix

    def handle_page(self, pagename, addctx, templatename='page.html',
                    outfilename=None, event_arg=None):
        # type: (unicode, Dict, unicode, unicode, Any) -> None
        ctx = self.globalcontext.copy()
        # current_page_name is backwards compatibility
        ctx['pagename'] = ctx['current_page_name'] = pagename
        ctx['encoding'] = self.config.html_output_encoding
        default_baseuri = self.get_target_uri(pagename)
        # in the singlehtml builder, default_baseuri still contains an #anchor
        # part, which relative_uri doesn't really like...
        default_baseuri = default_baseuri.rsplit('#', 1)[0]

        if self.config.html_baseurl:
            ctx['pageurl'] = posixpath.join(self.config.html_baseurl,
                                            pagename + self.out_suffix)
        else:
            ctx['pageurl'] = None

        def pathto(otheruri, resource=False, baseuri=default_baseuri):
            # type: (unicode, bool, unicode) -> unicode
            if resource and '://' in otheruri:
                # allow non-local resources given by scheme
                return otheruri
            elif not resource:
                otheruri = self.get_target_uri(otheruri)
            uri = relative_uri(baseuri, otheruri) or '#'
            if uri == '#' and not self.allow_sharp_as_current_path:
                uri = baseuri
            return uri
        ctx['pathto'] = pathto

        def css_tag(css):
            # type: (Stylesheet) -> unicode
            attrs = []
            for key in sorted(css.attributes):
                value = css.attributes[key]
                if value is not None:
                    attrs.append('%s="%s"' % (key, htmlescape(value, True)))
            attrs.append('href="%s"' % pathto(css.filename, resource=True))
            return '<link %s />' % ' '.join(attrs)
        ctx['css_tag'] = css_tag

        def hasdoc(name):
            # type: (unicode) -> bool
            if name in self.env.all_docs:
                return True
            elif name == 'search' and self.search:
                return True
            elif name == 'genindex' and self.get_builder_config('use_index', 'html'):
                return True
            return False
        ctx['hasdoc'] = hasdoc

        def warn(*args, **kwargs):
            # type: (Any, Any) -> unicode
            """Simple warn() wrapper for themes."""
            warnings.warn('The template function warn() was deprecated. '
                          'Use warning() instead.',
                          RemovedInSphinx30Warning, stacklevel=2)
            self.warn(*args, **kwargs)
            return ''  # return empty string
        ctx['warn'] = warn

        ctx['toctree'] = lambda **kw: self._get_local_toctree(pagename, **kw)
        self.add_sidebars(pagename, ctx)
        ctx.update(addctx)

        self.update_page_context(pagename, templatename, ctx, event_arg)
        newtmpl = self.app.emit_firstresult('html-page-context', pagename,
                                            templatename, ctx, event_arg)
        if newtmpl:
            templatename = newtmpl

        try:
            output = self.templates.render(templatename, ctx)
        except UnicodeError:
            logger.warning(__("a Unicode error occurred when rendering the page %s. "
                              "Please make sure all config values that contain "
                              "non-ASCII content are Unicode strings."), pagename)
            return
        except Exception as exc:
            raise ThemeError(__("An error happened in rendering the page %s.\nReason: %r") %
                             (pagename, exc))

        if not outfilename:
            outfilename = self.get_outfilename(pagename)
        # outfilename's path is in general different from self.outdir
        ensuredir(path.dirname(outfilename))
        try:
            with codecs.open(outfilename, 'w', ctx['encoding'], 'xmlcharrefreplace') as f:  # type: ignore  # NOQA
                f.write(output)
        except (IOError, OSError) as err:
            logger.warning(__("error writing file %s: %s"), outfilename, err)
        if self.copysource and ctx.get('sourcename'):
            # copy the source file for the "show source" link
            source_name = path.join(self.outdir, '_sources',
                                    os_path(ctx['sourcename']))
            ensuredir(path.dirname(source_name))
            copyfile(self.env.doc2path(pagename), source_name)

    def update_page_context(self, pagename, templatename, ctx, event_arg):
        # type: (unicode, unicode, Dict, Any) -> None
        pass

    def handle_finish(self):
        # type: () -> None
        if self.indexer:
            self.finish_tasks.add_task(self.dump_search_index)
        self.finish_tasks.add_task(self.dump_inventory)

    def dump_inventory(self):
        # type: () -> None
        logger.info(bold(__('dumping object inventory... ')), nonl=True)
        InventoryFile.dump(path.join(self.outdir, INVENTORY_FILENAME), self.env, self)
        logger.info(__('done'))

    def dump_search_index(self):
        # type: () -> None
        logger.info(
            bold(__('dumping search index in %s ... ') % self.indexer.label()),
            nonl=True)
        self.indexer.prune(self.env.all_docs)
        searchindexfn = path.join(self.outdir, self.searchindex_filename)
        # first write to a temporary file, so that if dumping fails,
        # the existing index won't be overwritten
        if self.indexer_dumps_unicode:
            f = codecs.open(searchindexfn + '.tmp', 'w', encoding='utf-8')  # type: ignore
        else:
            f = open(searchindexfn + '.tmp', 'wb')  # type: ignore
        with f:
            self.indexer.dump(f, self.indexer_format)
        movefile(searchindexfn + '.tmp', searchindexfn)
        logger.info(__('done'))


class DirectoryHTMLBuilder(StandaloneHTMLBuilder):
    """
    A StandaloneHTMLBuilder that creates all HTML pages as "index.html" in
    a directory given by their pagename, so that generated URLs don't have
    ``.html`` in them.
    """
    name = 'dirhtml'

    def get_target_uri(self, docname, typ=None):
        # type: (unicode, unicode) -> unicode
        if docname == 'index':
            return ''
        if docname.endswith(SEP + 'index'):
            return docname[:-5]  # up to sep
        return docname + SEP

    def get_outfilename(self, pagename):
        # type: (unicode) -> unicode
        if pagename == 'index' or pagename.endswith(SEP + 'index'):
            outfilename = path.join(self.outdir, os_path(pagename) +
                                    self.out_suffix)
        else:
            outfilename = path.join(self.outdir, os_path(pagename),
                                    'index' + self.out_suffix)

        return outfilename

    def prepare_writing(self, docnames):
        # type: (Iterable[unicode]) -> None
        StandaloneHTMLBuilder.prepare_writing(self, docnames)
        self.globalcontext['no_search_suffix'] = True


class SingleFileHTMLBuilder(StandaloneHTMLBuilder):
    """
    A StandaloneHTMLBuilder subclass that puts the whole document tree on one
    HTML page.
    """
    name = 'singlehtml'
    epilog = __('The HTML page is in %(outdir)s.')

    copysource = False

    def get_outdated_docs(self):  # type: ignore
        # type: () -> Union[unicode, List[unicode]]
        return 'all documents'

    def get_target_uri(self, docname, typ=None):
        # type: (unicode, unicode) -> unicode
        if docname in self.env.all_docs:
            # all references are on the same page...
            return self.config.master_doc + self.out_suffix + \
                '#document-' + docname
        else:
            # chances are this is a html_additional_page
            return docname + self.out_suffix

    def get_relative_uri(self, from_, to, typ=None):
        # type: (unicode, unicode, unicode) -> unicode
        # ignore source
        return self.get_target_uri(to, typ)

    def fix_refuris(self, tree):
        # type: (nodes.Node) -> None
        # fix refuris with double anchor
        fname = self.config.master_doc + self.out_suffix
        for refnode in tree.traverse(nodes.reference):
            if 'refuri' not in refnode:
                continue
            refuri = refnode['refuri']
            hashindex = refuri.find('#')
            if hashindex < 0:
                continue
            hashindex = refuri.find('#', hashindex + 1)
            if hashindex >= 0:
                refnode['refuri'] = fname + refuri[hashindex:]

    def _get_local_toctree(self, docname, collapse=True, **kwds):
        # type: (unicode, bool, Any) -> unicode
        if 'includehidden' not in kwds:
            kwds['includehidden'] = False
        toctree = TocTree(self.env).get_toctree_for(docname, self, collapse, **kwds)
        if toctree is not None:
            self.fix_refuris(toctree)
        return self.render_partial(toctree)['fragment']

    def assemble_doctree(self):
        # type: () -> nodes.Node
        master = self.config.master_doc
        tree = self.env.get_doctree(master)
        tree = inline_all_toctrees(self, set(), master, tree, darkgreen, [master])
        tree['docname'] = master
        self.env.resolve_references(tree, master, self)
        self.fix_refuris(tree)
        return tree

    def assemble_toc_secnumbers(self):
        # type: () -> Dict[unicode, Dict[unicode, Tuple[int, ...]]]
        # Assemble toc_secnumbers to resolve section numbers on SingleHTML.
        # Merge all secnumbers to single secnumber.
        #
        # Note: current Sphinx has refid confliction in singlehtml mode.
        #       To avoid the problem, it replaces key of secnumbers to
        #       tuple of docname and refid.
        #
        #       There are related codes in inline_all_toctres() and
        #       HTMLTranslter#add_secnumber().
        new_secnumbers = {}  # type: Dict[unicode, Tuple[int, ...]]
        for docname, secnums in iteritems(self.env.toc_secnumbers):
            for id, secnum in iteritems(secnums):
                alias = "%s/%s" % (docname, id)
                new_secnumbers[alias] = secnum

        return {self.config.master_doc: new_secnumbers}

    def assemble_toc_fignumbers(self):
        # type: () -> Dict[unicode, Dict[unicode, Dict[unicode, Tuple[int, ...]]]]  # NOQA
        # Assemble toc_fignumbers to resolve figure numbers on SingleHTML.
        # Merge all fignumbers to single fignumber.
        #
        # Note: current Sphinx has refid confliction in singlehtml mode.
        #       To avoid the problem, it replaces key of secnumbers to
        #       tuple of docname and refid.
        #
        #       There are related codes in inline_all_toctres() and
        #       HTMLTranslter#add_fignumber().
        new_fignumbers = {}  # type: Dict[unicode, Dict[unicode, Tuple[int, ...]]]
        # {u'foo': {'figure': {'id2': (2,), 'id1': (1,)}}, u'bar': {'figure': {'id1': (3,)}}}
        for docname, fignumlist in iteritems(self.env.toc_fignumbers):
            for figtype, fignums in iteritems(fignumlist):
                alias = "%s/%s" % (docname, figtype)
                new_fignumbers.setdefault(alias, {})
                for id, fignum in iteritems(fignums):
                    new_fignumbers[alias][id] = fignum

        return {self.config.master_doc: new_fignumbers}

    def get_doc_context(self, docname, body, metatags):
        # type: (unicode, unicode, Dict) -> Dict
        # no relation links...
        toc = TocTree(self.env).get_toctree_for(self.config.master_doc,
                                                self, False)
        # if there is no toctree, toc is None
        if toc:
            self.fix_refuris(toc)
            toc = self.render_partial(toc)['fragment']
            display_toc = True
        else:
            toc = ''
            display_toc = False
        return dict(
            parents = [],
            prev = None,
            next = None,
            docstitle = None,
            title = self.config.html_title,
            meta = None,
            body = body,
            metatags = metatags,
            rellinks = [],
            sourcename = '',
            toc = toc,
            display_toc = display_toc,
        )

    def write(self, *ignored):
        # type: (Any) -> None
        docnames = self.env.all_docs

        logger.info(bold(__('preparing documents... ')), nonl=True)
        self.prepare_writing(docnames)
        logger.info(__('done'))

        logger.info(bold(__('assembling single document... ')), nonl=True)
        doctree = self.assemble_doctree()
        self.env.toc_secnumbers = self.assemble_toc_secnumbers()
        self.env.toc_fignumbers = self.assemble_toc_fignumbers()
        logger.info('')
        logger.info(bold(__('writing... ')), nonl=True)
        self.write_doc_serialized(self.config.master_doc, doctree)
        self.write_doc(self.config.master_doc, doctree)
        logger.info(__('done'))

    def finish(self):
        # type: () -> None
        # no indices or search pages are supported
        logger.info(bold(__('writing additional files...')), nonl=1)

        # additional pages from conf.py
        for pagename, template in self.config.html_additional_pages.items():
            logger.info(' ' + pagename, nonl=1)
            self.handle_page(pagename, {}, template)

        if self.config.html_use_opensearch:
            logger.info(' opensearch', nonl=1)
            fn = path.join(self.outdir, '_static', 'opensearch.xml')
            self.handle_page('opensearch', {}, 'opensearch.xml', outfilename=fn)

        logger.info('')

        self.copy_image_files()
        self.copy_download_files()
        self.copy_static_files()
        self.copy_extra_files()
        self.write_buildinfo()
        self.dump_inventory()


class SerializingHTMLBuilder(StandaloneHTMLBuilder):
    """
    An abstract builder that serializes the generated HTML.
    """
    #: the serializing implementation to use.  Set this to a module that
    #: implements a `dump`, `load`, `dumps` and `loads` functions
    #: (pickle, simplejson etc.)
    implementation = None  # type: Any
    implementation_dumps_unicode = False
    #: additional arguments for dump()
    additional_dump_args = ()  # type: Tuple

    #: the filename for the global context file
    globalcontext_filename = None  # type: unicode

    supported_image_types = ['image/svg+xml', 'image/png',
                             'image/gif', 'image/jpeg']

    def init(self):
        # type: () -> None
        self.build_info = BuildInfo(self.config, self.tags)
        self.imagedir = '_images'
        self.current_docname = None
        self.theme = None       # no theme necessary
        self.templates = None   # no template bridge necessary
        self.init_templates()
        self.init_highlighter()
        self.init_css_files()
        self.init_js_files()
        self.use_index = self.get_builder_config('use_index', 'html')

    def get_target_uri(self, docname, typ=None):
        # type: (unicode, unicode) -> unicode
        if docname == 'index':
            return ''
        if docname.endswith(SEP + 'index'):
            return docname[:-5]  # up to sep
        return docname + SEP

    def dump_context(self, context, filename):
        # type: (Dict, unicode) -> None
        if self.implementation_dumps_unicode:
            f = codecs.open(filename, 'w', encoding='utf-8')  # type: ignore
        else:
            f = open(filename, 'wb')  # type: ignore
        with f:
            self.implementation.dump(context, f, *self.additional_dump_args)

    def handle_page(self, pagename, ctx, templatename='page.html',
                    outfilename=None, event_arg=None):
        # type: (unicode, Dict, unicode, unicode, Any) -> None
        ctx['current_page_name'] = pagename
        self.add_sidebars(pagename, ctx)

        if not outfilename:
            outfilename = path.join(self.outdir,
                                    os_path(pagename) + self.out_suffix)

        # we're not taking the return value here, since no template is
        # actually rendered
        self.app.emit('html-page-context', pagename, templatename, ctx, event_arg)

        # make context object serializable
        for key in list(ctx):
            if isinstance(ctx[key], types.FunctionType):
                del ctx[key]

        ensuredir(path.dirname(outfilename))
        self.dump_context(ctx, outfilename)

        # if there is a source file, copy the source file for the
        # "show source" link
        if ctx.get('sourcename'):
            source_name = path.join(self.outdir, '_sources',
                                    os_path(ctx['sourcename']))
            ensuredir(path.dirname(source_name))
            copyfile(self.env.doc2path(pagename), source_name)

    def handle_finish(self):
        # type: () -> None
        # dump the global context
        outfilename = path.join(self.outdir, self.globalcontext_filename)
        self.dump_context(self.globalcontext, outfilename)

        # super here to dump the search index
        StandaloneHTMLBuilder.handle_finish(self)

        # copy the environment file from the doctree dir to the output dir
        # as needed by the web app
        copyfile(path.join(self.doctreedir, ENV_PICKLE_FILENAME),
                 path.join(self.outdir, ENV_PICKLE_FILENAME))

        # touch 'last build' file, used by the web application to determine
        # when to reload its environment and clear the cache
        open(path.join(self.outdir, LAST_BUILD_FILENAME), 'w').close()


class PickleHTMLBuilder(SerializingHTMLBuilder):
    """
    A Builder that dumps the generated HTML into pickle files.
    """
    name = 'pickle'
    epilog = __('You can now process the pickle files in %(outdir)s.')

    implementation = pickle
    implementation_dumps_unicode = False
    additional_dump_args = (pickle.HIGHEST_PROTOCOL,)
    indexer_format = pickle
    indexer_dumps_unicode = False
    out_suffix = '.fpickle'
    globalcontext_filename = 'globalcontext.pickle'
    searchindex_filename = 'searchindex.pickle'


# compatibility alias
WebHTMLBuilder = PickleHTMLBuilder


class JSONHTMLBuilder(SerializingHTMLBuilder):
    """
    A builder that dumps the generated HTML into JSON files.
    """
    name = 'json'
    epilog = __('You can now process the JSON files in %(outdir)s.')

    implementation = jsonimpl
    implementation_dumps_unicode = True
    indexer_format = jsonimpl
    indexer_dumps_unicode = True
    out_suffix = '.fjson'
    globalcontext_filename = 'globalcontext.json'
    searchindex_filename = 'searchindex.json'

    def init(self):
        # type: () -> None
        SerializingHTMLBuilder.init(self)


def convert_html_css_files(app, config):
    # type: (Sphinx, Config) -> None
    """This converts string styled html_css_files to tuple styled one."""
    html_css_files = []  # type: List[Tuple[unicode, Dict]]
    for entry in config.html_css_files:
        if isinstance(entry, string_types):
            html_css_files.append((entry, {}))
        else:
            try:
                filename, attrs = entry
                html_css_files.append((filename, attrs))
            except Exception:
                logger.warning(__('invalid css_file: %r, ignored'), entry)
                continue

    config.html_css_files = html_css_files  # type: ignore


def convert_html_js_files(app, config):
    # type: (Sphinx, Config) -> None
    """This converts string styled html_js_files to tuple styled one."""
    html_js_files = []  # type: List[Tuple[unicode, Dict]]
    for entry in config.html_js_files:
        if isinstance(entry, string_types):
            html_js_files.append((entry, {}))
        else:
            try:
                filename, attrs = entry
                html_js_files.append((filename, attrs))
            except Exception:
                logger.warning(__('invalid js_file: %r, ignored'), entry)
                continue

    config.html_js_files = html_js_files  # type: ignore


def setup_js_tag_helper(app, pagename, templatexname, context, doctree):
    # type: (Sphinx, unicode, unicode, Dict, nodes.Node) -> None
    """Set up js_tag() template helper.

    .. note:: This set up function is added to keep compatibility with webhelper.
    """
    pathto = context.get('pathto')

    def js_tag(js):
        # type: (JavaScript) -> unicode
        attrs = []
        body = ''  # type: unicode
        if isinstance(js, JavaScript):
            for key in sorted(js.attributes):
                value = js.attributes[key]
                if value is not None:
                    if key == 'body':
                        body = value
                    else:
                        attrs.append('%s="%s"' % (key, htmlescape(value, True)))
            if js.filename:
                attrs.append('src="%s"' % pathto(js.filename, resource=True))
        else:
            # str value (old styled)
            attrs.append('type="text/javascript"')
            attrs.append('src="%s"' % pathto(js, resource=True))
        return '<script %s>%s</script>' % (' '.join(attrs), body)

    context['js_tag'] = js_tag


def validate_math_renderer(app):
    # type: (Sphinx) -> None
    if app.builder.format != 'html':
        return

    name = app.builder.math_renderer_name  # type: ignore
    if name is None:
        raise ConfigError(__('Many math_renderers are registered. '
                             'But no math_renderer is selected.'))
    elif name not in app.registry.html_inline_math_renderers:
        raise ConfigError(__('Unknown math_renderer %r is given.') % name)


def setup(app):
    # type: (Sphinx) -> Dict[unicode, Any]
    # builders
    app.add_builder(StandaloneHTMLBuilder)
    app.add_builder(DirectoryHTMLBuilder)
    app.add_builder(SingleFileHTMLBuilder)
    app.add_builder(PickleHTMLBuilder)
    app.add_builder(JSONHTMLBuilder)

    # config values
    app.add_config_value('html_theme', 'alabaster', 'html')
    app.add_config_value('html_theme_path', [], 'html')
    app.add_config_value('html_theme_options', {}, 'html')
    app.add_config_value('html_title',
                         lambda self: _('%s %s documentation') % (self.project, self.release),
                         'html', string_classes)
    app.add_config_value('html_short_title', lambda self: self.html_title, 'html')
    app.add_config_value('html_style', None, 'html', string_classes)
    app.add_config_value('html_logo', None, 'html', string_classes)
    app.add_config_value('html_favicon', None, 'html', string_classes)
    app.add_config_value('html_css_files', [], 'html')
    app.add_config_value('html_js_files', [], 'html')
    app.add_config_value('html_static_path', [], 'html')
    app.add_config_value('html_extra_path', [], 'html')
    app.add_config_value('html_last_updated_fmt', None, 'html', string_classes)
    app.add_config_value('html_sidebars', {}, 'html')
    app.add_config_value('html_additional_pages', {}, 'html')
    app.add_config_value('html_domain_indices', True, 'html', [list])
    app.add_config_value('html_add_permalinks', u'\u00B6', 'html')
    app.add_config_value('html_use_index', True, 'html')
    app.add_config_value('html_split_index', False, 'html')
    app.add_config_value('html_copy_source', True, 'html')
    app.add_config_value('html_show_sourcelink', True, 'html')
    app.add_config_value('html_sourcelink_suffix', '.txt', 'html')
    app.add_config_value('html_use_opensearch', '', 'html')
    app.add_config_value('html_file_suffix', None, 'html', string_classes)
    app.add_config_value('html_link_suffix', None, 'html', string_classes)
    app.add_config_value('html_show_copyright', True, 'html')
    app.add_config_value('html_show_sphinx', True, 'html')
    app.add_config_value('html_context', {}, 'html')
    app.add_config_value('html_output_encoding', 'utf-8', 'html')
    app.add_config_value('html_compact_lists', True, 'html')
    app.add_config_value('html_secnumber_suffix', '. ', 'html')
    app.add_config_value('html_search_language', None, 'html', string_classes)
    app.add_config_value('html_search_options', {}, 'html')
    app.add_config_value('html_search_scorer', '', None)
    app.add_config_value('html_scaled_image_link', True, 'html')
    app.add_config_value('html_experimental_html5_writer', None, 'html')
    app.add_config_value('html_baseurl', '', 'html')
    app.add_config_value('html_math_renderer', None, 'env')

    app.add_config_value('singlehtml_sidebars', lambda self: self.html_sidebars, 'html')

    # event handlers
    app.connect('config-inited', convert_html_css_files)
    app.connect('config-inited', convert_html_js_files)
    app.connect('builder-inited', validate_math_renderer)
    app.connect('html-page-context', setup_js_tag_helper)

    # load default math renderer
    app.setup_extension('sphinx.ext.mathjax')

    return {
        'version': 'builtin',
        'parallel_read_safe': True,
        'parallel_write_safe': True,
    }
