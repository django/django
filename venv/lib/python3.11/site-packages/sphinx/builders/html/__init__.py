"""Several HTML builders."""

from __future__ import annotations

import contextlib
import hashlib
import html
import os
import posixpath
import re
import sys
import time
import warnings
from os import path
from typing import IO, TYPE_CHECKING, Any
from urllib.parse import quote

import docutils.readers.doctree
from docutils import nodes
from docutils.core import Publisher
from docutils.frontend import OptionParser
from docutils.io import DocTreeInput, StringOutput
from docutils.utils import relative_path

from sphinx import __display_version__, package_dir
from sphinx import version_info as sphinx_version
from sphinx.builders import Builder
from sphinx.builders.html._assets import _CascadingStyleSheet, _file_checksum, _JavaScript
from sphinx.config import ENUM, Config
from sphinx.deprecation import _deprecation_warning
from sphinx.domains import Domain, Index, IndexEntry
from sphinx.environment.adapters.asset import ImageAdapter
from sphinx.environment.adapters.indexentries import IndexEntries
from sphinx.environment.adapters.toctree import document_toc, global_toctree_for_doc
from sphinx.errors import ConfigError, ThemeError
from sphinx.highlighting import PygmentsBridge
from sphinx.locale import _, __
from sphinx.search import js_index
from sphinx.theming import HTMLThemeFactory
from sphinx.util import isurl, logging
from sphinx.util.display import progress_message, status_iterator
from sphinx.util.docutils import new_document
from sphinx.util.fileutil import copy_asset
from sphinx.util.i18n import format_date
from sphinx.util.inventory import InventoryFile
from sphinx.util.matching import DOTFILES, Matcher, patmatch
from sphinx.util.osutil import SEP, copyfile, ensuredir, os_path, relative_uri
from sphinx.writers.html import HTMLWriter
from sphinx.writers.html5 import HTML5Translator

if TYPE_CHECKING:
    from collections.abc import Iterable, Iterator, Sequence

    from docutils.nodes import Node

    from sphinx.application import Sphinx
    from sphinx.environment import BuildEnvironment
    from sphinx.util.tags import Tags

#: the filename for the inventory of objects
INVENTORY_FILENAME = 'objects.inv'

logger = logging.getLogger(__name__)
return_codes_re = re.compile('[\r\n]+')

DOMAIN_INDEX_TYPE = tuple[
    # Index name (e.g. py-modindex)
    str,
    # Index class
    type[Index],
    # list of (heading string, list of index entries) pairs.
    list[tuple[str, list[IndexEntry]]],
    # whether sub-entries should start collapsed
    bool,
]


def get_stable_hash(obj: Any) -> str:
    """
    Return a stable hash for a Python data structure.  We can't just use
    the md5 of str(obj) since for example dictionary items are enumerated
    in unpredictable order due to hash randomization in newer Pythons.
    """
    if isinstance(obj, dict):
        return get_stable_hash(list(obj.items()))
    elif isinstance(obj, (list, tuple)):
        obj = sorted(get_stable_hash(o) for o in obj)
    return hashlib.md5(str(obj).encode(), usedforsecurity=False).hexdigest()


def convert_locale_to_language_tag(locale: str | None) -> str | None:
    """Convert a locale string to a language tag (ex. en_US -> en-US).

    refs: BCP 47 (:rfc:`5646`)
    """
    if locale:
        return locale.replace('_', '-')
    else:
        return None


class BuildInfo:
    """buildinfo file manipulator.

    HTMLBuilder and its family are storing their own envdata to ``.buildinfo``.
    This class is a manipulator for the file.
    """

    @classmethod
    def load(cls, f: IO) -> BuildInfo:
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
            raise ValueError(__('build info file is broken: %r') % exc) from exc

    def __init__(
        self,
        config: Config | None = None,
        tags: Tags | None = None,
        config_categories: Sequence[str] = (),
    ) -> None:
        self.config_hash = ''
        self.tags_hash = ''

        if config:
            values = {c.name: c.value for c in config.filter(config_categories)}
            self.config_hash = get_stable_hash(values)

        if tags:
            self.tags_hash = get_stable_hash(sorted(tags))

    def __eq__(self, other: BuildInfo) -> bool:  # type: ignore[override]
        return (self.config_hash == other.config_hash and
                self.tags_hash == other.tags_hash)

    def dump(self, f: IO) -> None:
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

    default_translator_class = HTML5Translator
    copysource = True
    allow_parallel = True
    out_suffix = '.html'
    link_suffix = '.html'  # defaults to matching out_suffix
    indexer_format: Any = js_index
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

    imgpath: str = ''
    domain_indices: list[DOMAIN_INDEX_TYPE] = []

    def __init__(self, app: Sphinx, env: BuildEnvironment) -> None:
        super().__init__(app, env)

        # CSS files
        self._css_files: list[_CascadingStyleSheet] = []

        # JS files
        self._js_files: list[_JavaScript] = []

        # Cached Publisher for writing doctrees to HTML
        reader = docutils.readers.doctree.Reader(parser_name='restructuredtext')
        pub = Publisher(
            reader=reader,
            parser=reader.parser,
            writer=HTMLWriter(self),
            source_class=DocTreeInput,
            destination=StringOutput(encoding='unicode'),
        )
        if docutils.__version_info__[:2] >= (0, 19):
            pub.get_settings(output_encoding='unicode', traceback=True)
        else:
            op = pub.setup_option_parser(output_encoding='unicode', traceback=True)
            pub.settings = op.get_default_values()
        self._publisher = pub

    def init(self) -> None:
        self.build_info = self.create_build_info()
        # basename of images directory
        self.imagedir = '_images'
        # section numbers for headings in the currently visited document
        self.secnumbers: dict[str, tuple[int, ...]] = {}
        # currently written docname
        self.current_docname: str = ''

        self.init_templates()
        self.init_highlighter()
        self.init_css_files()
        self.init_js_files()

        html_file_suffix = self.get_builder_config('file_suffix', 'html')
        if html_file_suffix is not None:
            self.out_suffix = html_file_suffix

        html_link_suffix = self.get_builder_config('link_suffix', 'html')
        if html_link_suffix is not None:
            self.link_suffix = html_link_suffix
        else:
            self.link_suffix = self.out_suffix

        self.use_index = self.get_builder_config('use_index', 'html')

    def create_build_info(self) -> BuildInfo:
        return BuildInfo(self.config, self.tags, ['html'])

    def _get_translations_js(self) -> str:
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
        return ''

    def _get_style_filenames(self) -> Iterator[str]:
        if isinstance(self.config.html_style, str):
            yield self.config.html_style
        elif self.config.html_style is not None:
            yield from self.config.html_style
        elif self.theme:
            stylesheet = self.theme.get_config('theme', 'stylesheet')
            yield from map(str.strip, stylesheet.split(','))
        else:
            yield 'default.css'

    def get_theme_config(self) -> tuple[str, dict]:
        return self.config.html_theme, self.config.html_theme_options

    def init_templates(self) -> None:
        theme_factory = HTMLThemeFactory(self.app)
        themename, themeoptions = self.get_theme_config()
        self.theme = theme_factory.create(themename)
        self.theme_options = themeoptions.copy()
        self.create_template_bridge()
        self.templates.init(self, self.theme)

    def init_highlighter(self) -> None:
        # determine Pygments style and create the highlighter
        if self.config.pygments_style is not None:
            style = self.config.pygments_style
        elif self.theme:
            style = self.theme.get_config('theme', 'pygments_style', 'none')
        else:
            style = 'sphinx'
        self.highlighter = PygmentsBridge('html', style)

        if self.theme:
            dark_style = self.theme.get_config('theme', 'pygments_dark_style', None)
        else:
            dark_style = None

        self.dark_highlighter: PygmentsBridge | None
        if dark_style is not None:
            self.dark_highlighter = PygmentsBridge('html', dark_style)
            self.app.add_css_file('pygments_dark.css',
                                  media='(prefers-color-scheme: dark)',
                                  id='pygments_dark_css')
        else:
            self.dark_highlighter = None

    @property
    def css_files(self) -> list[_CascadingStyleSheet]:
        _deprecation_warning(__name__, f'{self.__class__.__name__}.css_files', '',
                             remove=(9, 0))
        return self._css_files

    def init_css_files(self) -> None:
        self._css_files = []
        self.add_css_file('pygments.css', priority=200)

        for filename in self._get_style_filenames():
            self.add_css_file(filename, priority=200)

        for filename, attrs in self.app.registry.css_files:
            self.add_css_file(filename, **attrs)

        for filename, attrs in self.get_builder_config('css_files', 'html'):
            attrs.setdefault('priority', 800)  # User's CSSs are loaded after extensions'
            self.add_css_file(filename, **attrs)

    def add_css_file(self, filename: str, **kwargs: Any) -> None:
        if '://' not in filename:
            filename = posixpath.join('_static', filename)

        if (asset := _CascadingStyleSheet(filename, **kwargs)) not in self._css_files:
            self._css_files.append(asset)

    @property
    def script_files(self) -> list[_JavaScript]:
        _deprecation_warning(__name__, f'{self.__class__.__name__}.script_files', '',
                             remove=(9, 0))
        return self._js_files

    def init_js_files(self) -> None:
        self._js_files = []
        self.add_js_file('documentation_options.js', priority=200)
        self.add_js_file('doctools.js', priority=200)
        self.add_js_file('sphinx_highlight.js', priority=200)

        for filename, attrs in self.app.registry.js_files:
            self.add_js_file(filename or '', **attrs)

        for filename, attrs in self.get_builder_config('js_files', 'html'):
            attrs.setdefault('priority', 800)  # User's JSs are loaded after extensions'
            self.add_js_file(filename or '', **attrs)

        if self._get_translations_js():
            self.add_js_file('translations.js')

    def add_js_file(self, filename: str, **kwargs: Any) -> None:
        if filename and '://' not in filename:
            filename = posixpath.join('_static', filename)

        if (asset := _JavaScript(filename, **kwargs)) not in self._js_files:
            self._js_files.append(asset)

    @property
    def math_renderer_name(self) -> str | None:
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

    def get_outdated_docs(self) -> Iterator[str]:
        try:
            with open(path.join(self.outdir, '.buildinfo'), encoding="utf-8") as fp:
                buildinfo = BuildInfo.load(fp)

            if self.build_info != buildinfo:
                logger.debug('[build target] did not match: build_info ')
                yield from self.env.found_docs
                return
        except ValueError as exc:
            logger.warning(__('Failed to read build info file: %r'), exc)
        except OSError:
            # ignore errors on reading
            pass

        if self.templates:
            template_mtime = self.templates.newest_template_mtime()
        else:
            template_mtime = 0
        for docname in self.env.found_docs:
            if docname not in self.env.all_docs:
                logger.debug('[build target] did not in env: %r', docname)
                yield docname
                continue
            targetname = self.get_outfilename(docname)
            try:
                targetmtime = path.getmtime(targetname)
            except Exception:
                targetmtime = 0
            try:
                srcmtime = max(path.getmtime(self.env.doc2path(docname)), template_mtime)
                if srcmtime > targetmtime:
                    logger.debug(
                        '[build target] targetname %r(%s), template(%s), docname %r(%s)',
                        targetname,
                        _format_modified_time(targetmtime),
                        _format_modified_time(template_mtime),
                        docname,
                        _format_modified_time(path.getmtime(self.env.doc2path(docname))),
                    )
                    yield docname
            except OSError:
                # source doesn't exist anymore
                pass

    def get_asset_paths(self) -> list[str]:
        return self.config.html_extra_path + self.config.html_static_path

    def render_partial(self, node: Node | None) -> dict[str, str]:
        """Utility: Render a lone doctree node."""
        if node is None:
            return {'fragment': ''}

        doc = new_document('<partial node>')
        doc.append(node)
        self._publisher.set_source(doc)
        self._publisher.publish()
        return self._publisher.writer.parts  # type: ignore[union-attr]

    def prepare_writing(self, docnames: set[str]) -> None:
        # create the search indexer
        self.indexer = None
        if self.search:
            from sphinx.search import IndexBuilder
            lang = self.config.html_search_language or self.config.language
            self.indexer = IndexBuilder(self.env, lang,
                                        self.config.html_search_options,
                                        self.config.html_search_scorer)
            self.load_indexer(docnames)

        self.docwriter = HTMLWriter(self)
        with warnings.catch_warnings():
            warnings.filterwarnings('ignore', category=DeprecationWarning)
            # DeprecationWarning: The frontend.OptionParser class will be replaced
            # by a subclass of argparse.ArgumentParser in Docutils 0.21 or later.
            self.docsettings: Any = OptionParser(
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
                domain: Domain = self.env.domains[domain_name]
                for indexcls in domain.indices:
                    indexname = f'{domain.name}-{indexcls.name}'
                    if isinstance(indices_config, list):
                        if indexname not in indices_config:
                            continue
                    content, collapse = indexcls(domain).generate()
                    if content:
                        self.domain_indices.append(
                            (indexname, indexcls, content, collapse))

        # format the "last updated on" string, only once is enough since it
        # typically doesn't include the time of day
        self.last_updated: str | None
        lufmt = self.config.html_last_updated_fmt
        if lufmt is not None:
            self.last_updated = format_date(lufmt or _('%b %d, %Y'),
                                            language=self.config.language)
        else:
            self.last_updated = None

        # If the logo or favicon are urls, keep them as-is, otherwise
        # strip the relative path as the files will be copied into _static.
        logo = self.config.html_logo or ''
        favicon = self.config.html_favicon or ''

        if not isurl(logo):
            logo = path.basename(logo)
        if not isurl(favicon):
            favicon = path.basename(favicon)

        self.relations = self.env.collect_relations()

        rellinks: list[tuple[str, str, str, str]] = []
        if self.use_index:
            rellinks.append(('genindex', _('General Index'), 'I', _('index')))
        for indexname, indexcls, _content, _collapse in self.domain_indices:
            # if it has a short name
            if indexcls.shortname:
                rellinks.append((indexname, indexcls.localname,
                                 '', indexcls.shortname))

        # add assets registered after ``Builder.init()``.
        for css_filename, attrs in self.app.registry.css_files:
            self.add_css_file(css_filename, **attrs)
        for js_filename, attrs in self.app.registry.js_files:
            self.add_js_file(js_filename or '', **attrs)

        # back up _css_files and _js_files to allow adding CSS/JS files to a specific page.
        self._orig_css_files = list(dict.fromkeys(self._css_files))
        self._orig_js_files = list(dict.fromkeys(self._js_files))
        styles = list(self._get_style_filenames())

        self.globalcontext = {
            'embedded': self.embedded,
            'project': self.config.project,
            'release': return_codes_re.sub('', self.config.release),
            'version': self.config.version,
            'last_updated': self.last_updated,
            'copyright': self.config.copyright,
            'master_doc': self.config.root_doc,
            'root_doc': self.config.root_doc,
            'use_opensearch': self.config.html_use_opensearch,
            'docstitle': self.config.html_title,
            'shorttitle': self.config.html_short_title,
            'show_copyright': self.config.html_show_copyright,
            'show_search_summary': self.config.html_show_search_summary,
            'show_sphinx': self.config.html_show_sphinx,
            'has_source': self.config.html_copy_source,
            'show_source': self.config.html_show_sourcelink,
            'sourcelink_suffix': self.config.html_sourcelink_suffix,
            'file_suffix': self.out_suffix,
            'link_suffix': self.link_suffix,
            'script_files': self._js_files,
            'language': convert_locale_to_language_tag(self.config.language),
            'css_files': self._css_files,
            'sphinx_version': __display_version__,
            'sphinx_version_tuple': sphinx_version,
            'docutils_version_info': docutils.__version_info__[:5],
            'styles': styles,
            'rellinks': rellinks,
            'builder': self.name,
            'parents': [],
            'logo_url': logo,
            'favicon_url': favicon,
            'html5_doctype': True,
        }
        if self.theme:
            self.globalcontext.update(
                ('theme_' + key, val) for (key, val) in
                self.theme.get_options(self.theme_options).items())
        self.globalcontext.update(self.config.html_context)

    def get_doc_context(self, docname: str, body: str, metatags: str) -> dict[str, Any]:
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
                    'title': self.render_partial(titles[related[2]])['title'],
                }
                rellinks.append((related[2], next['title'], 'N', _('next')))
            except KeyError:
                next = None
        if related and related[1]:
            try:
                prev = {
                    'link': self.get_relative_uri(docname, related[1]),
                    'title': self.render_partial(titles[related[1]])['title'],
                }
                rellinks.append((related[1], prev['title'], 'P', _('previous')))
            except KeyError:
                # the relation is (somehow) not in the TOC tree, handle
                # that gracefully
                prev = None
        while related and related[0]:
            with contextlib.suppress(KeyError):
                parents.append(
                    {'link': self.get_relative_uri(docname, related[0]),
                     'title': self.render_partial(titles[related[0]])['title']})

            related = self.relations.get(related[0])
        if parents:
            # remove link to the master file; we have a generic
            # "back to index" link already
            parents.pop()
        parents.reverse()

        # title rendered as HTML
        title_node = self.env.longtitles.get(docname)
        title = self.render_partial(title_node)['title'] if title_node else ''

        # Suffix for the document
        source_suffix = self.env.doc2path(docname, False)[len(docname):]

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
        self_toc = document_toc(self.env, docname, self.tags)
        toc = self.render_partial(self_toc)['fragment']

        return {
            'parents': parents,
            'prev': prev,
            'next': next,
            'title': title,
            'meta': meta,
            'body': body,
            'metatags': metatags,
            'rellinks': rellinks,
            'sourcename': sourcename,
            'toc': toc,
            # only display a TOC if there's more than one item to show
            'display_toc': (self.env.toc_num_entries[docname] > 1),
            'page_source_suffix': source_suffix,
        }

    def copy_assets(self) -> None:
        self.finish_tasks.add_task(self.copy_download_files)
        self.finish_tasks.add_task(self.copy_static_files)
        self.finish_tasks.add_task(self.copy_extra_files)
        self.finish_tasks.join()

    def write_doc(self, docname: str, doctree: nodes.document) -> None:
        destination = StringOutput(encoding='utf-8')
        doctree.settings = self.docsettings

        self.secnumbers = self.env.toc_secnumbers.get(docname, {})
        self.fignumbers = self.env.toc_fignumbers.get(docname, {})
        self.imgpath = relative_uri(self.get_target_uri(docname), '_images')
        self.dlpath = relative_uri(self.get_target_uri(docname), '_downloads')
        self.current_docname = docname
        self.docwriter.write(doctree, destination)
        self.docwriter.assemble_parts()
        body = self.docwriter.parts['fragment']
        metatags = self.docwriter.clean_meta

        ctx = self.get_doc_context(docname, body, metatags)
        self.handle_page(docname, ctx, event_arg=doctree)

    def write_doc_serialized(self, docname: str, doctree: nodes.document) -> None:
        self.imgpath = relative_uri(self.get_target_uri(docname), self.imagedir)
        self.post_process_images(doctree)
        title_node = self.env.longtitles.get(docname)
        title = self.render_partial(title_node)['title'] if title_node else ''
        self.index_page(docname, doctree, title)

    def finish(self) -> None:
        self.finish_tasks.add_task(self.gen_indices)
        self.finish_tasks.add_task(self.gen_pages_from_extensions)
        self.finish_tasks.add_task(self.gen_additional_pages)
        self.finish_tasks.add_task(self.copy_image_files)
        self.finish_tasks.add_task(self.write_buildinfo)

        # dump the search index
        self.handle_finish()

    @progress_message(__('generating indices'))
    def gen_indices(self) -> None:
        # the global general index
        if self.use_index:
            self.write_genindex()

        # the global domain-specific indices
        self.write_domain_indices()

    def gen_pages_from_extensions(self) -> None:
        # pages from extensions
        for pagelist in self.events.emit('html-collect-pages'):
            for pagename, context, template in pagelist:
                self.handle_page(pagename, context, template)

    @progress_message(__('writing additional pages'))
    def gen_additional_pages(self) -> None:
        # additional pages from conf.py
        for pagename, template in self.config.html_additional_pages.items():
            logger.info(pagename + ' ', nonl=True)
            self.handle_page(pagename, {}, template)

        # the search page
        if self.search:
            logger.info('search ', nonl=True)
            self.handle_page('search', {}, 'search.html')

        # the opensearch xml file
        if self.config.html_use_opensearch and self.search:
            logger.info('opensearch ', nonl=True)
            fn = path.join(self.outdir, '_static', 'opensearch.xml')
            self.handle_page('opensearch', {}, 'opensearch.xml', outfilename=fn)

    def write_genindex(self) -> None:
        # the total count of lines for each index letter, used to distribute
        # the entries into two columns
        genindex = IndexEntries(self.env).create_index(self)
        indexcounts = []
        for _k, entries in genindex:
            indexcounts.append(sum(1 + len(subitems)
                                   for _, (_, subitems, _) in entries))

        genindexcontext = {
            'genindexentries': genindex,
            'genindexcounts': indexcounts,
            'split_index': self.config.html_split_index,
        }
        logger.info('genindex ', nonl=True)

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

    def write_domain_indices(self) -> None:
        for indexname, indexcls, content, collapse in self.domain_indices:
            indexcontext = {
                'indextitle': indexcls.localname,
                'content': content,
                'collapse_index': collapse,
            }
            logger.info(indexname + ' ', nonl=True)
            self.handle_page(indexname, indexcontext, 'domainindex.html')

    def copy_image_files(self) -> None:
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

    def copy_download_files(self) -> None:
        def to_relpath(f: str) -> str:
            return relative_path(self.srcdir, f)  # type: ignore[arg-type]

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
                except OSError as err:
                    logger.warning(__('cannot copy downloadable file %r: %s'),
                                   path.join(self.srcdir, src), err)

    def create_pygments_style_file(self) -> None:
        """create a style file for pygments."""
        with open(path.join(self.outdir, '_static', 'pygments.css'), 'w',
                  encoding="utf-8") as f:
            f.write(self.highlighter.get_stylesheet())

        if self.dark_highlighter:
            with open(path.join(self.outdir, '_static', 'pygments_dark.css'), 'w',
                      encoding="utf-8") as f:
                f.write(self.dark_highlighter.get_stylesheet())

    def copy_translation_js(self) -> None:
        """Copy a JavaScript file for translations."""
        jsfile = self._get_translations_js()
        if jsfile:
            copyfile(jsfile, path.join(self.outdir, '_static', 'translations.js'))

    def copy_stemmer_js(self) -> None:
        """Copy a JavaScript file for stemmer."""
        if self.indexer is not None:
            if hasattr(self.indexer, 'get_js_stemmer_rawcodes'):
                for jsfile in self.indexer.get_js_stemmer_rawcodes():
                    copyfile(jsfile, path.join(self.outdir, '_static', path.basename(jsfile)))
            else:
                if js_stemmer_rawcode := self.indexer.get_js_stemmer_rawcode():
                    copyfile(js_stemmer_rawcode,
                             path.join(self.outdir, '_static', '_stemmer.js'))

    def copy_theme_static_files(self, context: dict[str, Any]) -> None:
        def onerror(filename: str, error: Exception) -> None:
            logger.warning(__('Failed to copy a file in html_static_file: %s: %r'),
                           filename, error)

        if self.theme:
            for entry in self.theme.get_theme_dirs()[::-1]:
                copy_asset(path.join(entry, 'static'),
                           path.join(self.outdir, '_static'),
                           excluded=DOTFILES, context=context,
                           renderer=self.templates, onerror=onerror)

    def copy_html_static_files(self, context: dict) -> None:
        def onerror(filename: str, error: Exception) -> None:
            logger.warning(__('Failed to copy a file in html_static_file: %s: %r'),
                           filename, error)

        excluded = Matcher(self.config.exclude_patterns + ["**/.*"])
        for entry in self.config.html_static_path:
            copy_asset(path.join(self.confdir, entry),
                       path.join(self.outdir, '_static'),
                       excluded, context=context, renderer=self.templates, onerror=onerror)

    def copy_html_logo(self) -> None:
        if self.config.html_logo and not isurl(self.config.html_logo):
            copy_asset(path.join(self.confdir, self.config.html_logo),
                       path.join(self.outdir, '_static'))

    def copy_html_favicon(self) -> None:
        if self.config.html_favicon and not isurl(self.config.html_favicon):
            copy_asset(path.join(self.confdir, self.config.html_favicon),
                       path.join(self.outdir, '_static'))

    def copy_static_files(self) -> None:
        try:
            with progress_message(__('copying static files')):
                ensuredir(path.join(self.outdir, '_static'))

                # prepare context for templates
                context = self.globalcontext.copy()
                if self.indexer is not None:
                    context.update(self.indexer.context_for_searchtool())

                self.create_pygments_style_file()
                self.copy_translation_js()
                self.copy_stemmer_js()
                self.copy_theme_static_files(context)
                self.copy_html_static_files(context)
                self.copy_html_logo()
                self.copy_html_favicon()
        except OSError as err:
            logger.warning(__('cannot copy static file %r'), err)

    def copy_extra_files(self) -> None:
        """copy html_extra_path files."""
        try:
            with progress_message(__('copying extra files')):
                excluded = Matcher(self.config.exclude_patterns)
                for extra_path in self.config.html_extra_path:
                    entry = path.join(self.confdir, extra_path)
                    copy_asset(entry, self.outdir, excluded)
        except OSError as err:
            logger.warning(__('cannot copy extra file %r'), err)

    def write_buildinfo(self) -> None:
        try:
            with open(path.join(self.outdir, '.buildinfo'), 'w', encoding="utf-8") as fp:
                self.build_info.dump(fp)
        except OSError as exc:
            logger.warning(__('Failed to write build info file: %r'), exc)

    def cleanup(self) -> None:
        # clean up theme stuff
        if self.theme:
            self.theme.cleanup()

    def post_process_images(self, doctree: Node) -> None:
        """Pick the best candidate for an image and link down-scaled images to
        their high res version.
        """
        super().post_process_images(doctree)

        if self.config.html_scaled_image_link and self.html_scaled_image_link:
            for node in doctree.findall(nodes.image):
                if not any((key in node) for key in ['scale', 'width', 'height']):
                    # resizing options are not given. scaled image link is available
                    # only for resized images.
                    continue
                if isinstance(node.parent, nodes.reference):
                    # A image having hyperlink target
                    continue
                if 'no-scaled-link' in node['classes']:
                    # scaled image link is disabled for this node
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

    def load_indexer(self, docnames: Iterable[str]) -> None:
        assert self.indexer is not None
        keep = set(self.env.all_docs) - set(docnames)
        try:
            searchindexfn = path.join(self.outdir, self.searchindex_filename)
            if self.indexer_dumps_unicode:
                with open(searchindexfn, encoding='utf-8') as ft:
                    self.indexer.load(ft, self.indexer_format)
            else:
                with open(searchindexfn, 'rb') as fb:
                    self.indexer.load(fb, self.indexer_format)
        except (OSError, ValueError):
            if keep:
                logger.warning(__("search index couldn't be loaded, but not all "
                                  'documents will be built: the index will be '
                                  'incomplete.'))
        # delete all entries for files that will be rebuilt
        self.indexer.prune(keep)

    def index_page(self, pagename: str, doctree: nodes.document, title: str) -> None:
        # only index pages with title
        if self.indexer is not None and title:
            filename = self.env.doc2path(pagename, base=False)
            metadata = self.env.metadata.get(pagename, {})
            if 'nosearch' in metadata:
                self.indexer.feed(pagename, filename, '', new_document(''))
            else:
                self.indexer.feed(pagename, filename, title, doctree)

    def _get_local_toctree(self, docname: str, collapse: bool = True, **kwargs: Any) -> str:
        if 'includehidden' not in kwargs:
            kwargs['includehidden'] = False
        if kwargs.get('maxdepth') == '':
            kwargs.pop('maxdepth')
        toctree = global_toctree_for_doc(self.env, docname, self, collapse=collapse, **kwargs)
        return self.render_partial(toctree)['fragment']

    def get_outfilename(self, pagename: str) -> str:
        return path.join(self.outdir, os_path(pagename) + self.out_suffix)

    def add_sidebars(self, pagename: str, ctx: dict) -> None:
        def has_wildcard(pattern: str) -> bool:
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
        for pattern, patsidebars in html_sidebars.items():
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

        ctx['sidebars'] = sidebars
        ctx['customsidebar'] = customsidebar

    # --------- these are overwritten by the serialization builder

    def get_target_uri(self, docname: str, typ: str | None = None) -> str:
        return quote(docname) + self.link_suffix

    def handle_page(self, pagename: str, addctx: dict, templatename: str = 'page.html',
                    outfilename: str | None = None, event_arg: Any = None) -> None:
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

        def pathto(
            otheruri: str, resource: bool = False, baseuri: str = default_baseuri,
        ) -> str:
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

        def hasdoc(name: str) -> bool:
            if name in self.env.all_docs:
                return True
            if name == 'search' and self.search:
                return True
            if name == 'genindex' and self.get_builder_config('use_index', 'html'):
                return True
            return False
        ctx['hasdoc'] = hasdoc

        ctx['toctree'] = lambda **kwargs: self._get_local_toctree(pagename, **kwargs)
        self.add_sidebars(pagename, ctx)
        ctx.update(addctx)

        # 'blah.html' should have content_root = './' not ''.
        ctx['content_root'] = (f'..{SEP}' * default_baseuri.count(SEP)) or f'.{SEP}'

        outdir = self.app.outdir

        def css_tag(css: _CascadingStyleSheet) -> str:
            attrs = []
            for key, value in css.attributes.items():
                if value is not None:
                    attrs.append(f'{key}="{html.escape(value, quote=True)}"')
            uri = pathto(os.fspath(css.filename), resource=True)
            if checksum := _file_checksum(outdir, css.filename):
                uri += f'?v={checksum}'
            return f'<link {" ".join(sorted(attrs))} href="{uri}" />'

        ctx['css_tag'] = css_tag

        def js_tag(js: _JavaScript | str) -> str:
            if not isinstance(js, _JavaScript):
                # str value (old styled)
                return f'<script src="{pathto(js, resource=True)}"></script>'

            attrs = []
            body = js.attributes.get('body', '')
            for key, value in js.attributes.items():
                if key == 'body':
                    continue
                if value is not None:
                    attrs.append(f'{key}="{html.escape(value, quote=True)}"')

            if not js.filename:
                if attrs:
                    return f'<script {" ".join(sorted(attrs))}>{body}</script>'
                return f'<script>{body}</script>'

            uri = pathto(os.fspath(js.filename), resource=True)
            if 'MathJax.js?' in os.fspath(js.filename):
                # MathJax v2 reads a ``?config=...`` query parameter,
                # special case this and just skip adding the checksum.
                # https://docs.mathjax.org/en/v2.7-latest/configuration.html#considerations-for-using-combined-configuration-files
                # https://github.com/sphinx-doc/sphinx/issues/11658
                pass
            elif checksum := _file_checksum(outdir, js.filename):
                uri += f'?v={checksum}'
            if attrs:
                return f'<script {" ".join(sorted(attrs))} src="{uri}"></script>'
            return f'<script src="{uri}"></script>'

        ctx['js_tag'] = js_tag

        # revert _css_files and _js_files
        self._css_files[:] = self._orig_css_files
        self._js_files[:] = self._orig_js_files

        self.update_page_context(pagename, templatename, ctx, event_arg)
        newtmpl = self.app.emit_firstresult('html-page-context', pagename,
                                            templatename, ctx, event_arg)
        if newtmpl:
            templatename = newtmpl

        # sort JS/CSS before rendering HTML
        try:  # NoQA: SIM105
            # Convert script_files to list to support non-list script_files (refs: #8889)
            ctx['script_files'] = sorted(ctx['script_files'], key=lambda js: js.priority)
        except AttributeError:
            # Skip sorting if users modifies script_files directly (maybe via `html_context`).
            # refs: #8885
            #
            # Note: priority sorting feature will not work in this case.
            pass

        with contextlib.suppress(AttributeError):
            ctx['css_files'] = sorted(ctx['css_files'], key=lambda css: css.priority)

        try:
            output = self.templates.render(templatename, ctx)
        except UnicodeError:
            logger.warning(__("a Unicode error occurred when rendering the page %s. "
                              "Please make sure all config values that contain "
                              "non-ASCII content are Unicode strings."), pagename)
            return
        except Exception as exc:
            raise ThemeError(__("An error happened in rendering the page %s.\nReason: %r") %
                             (pagename, exc)) from exc

        if not outfilename:
            outfilename = self.get_outfilename(pagename)
        # outfilename's path is in general different from self.outdir
        ensuredir(path.dirname(outfilename))
        try:
            with open(outfilename, 'w', encoding=ctx['encoding'],
                      errors='xmlcharrefreplace') as f:
                f.write(output)
        except OSError as err:
            logger.warning(__("error writing file %s: %s"), outfilename, err)
        if self.copysource and ctx.get('sourcename'):
            # copy the source file for the "show source" link
            source_name = path.join(self.outdir, '_sources',
                                    os_path(ctx['sourcename']))
            ensuredir(path.dirname(source_name))
            copyfile(self.env.doc2path(pagename), source_name)

    def update_page_context(self, pagename: str, templatename: str,
                            ctx: dict, event_arg: Any) -> None:
        pass

    def handle_finish(self) -> None:
        self.finish_tasks.add_task(self.dump_search_index)
        self.finish_tasks.add_task(self.dump_inventory)

    @progress_message(__('dumping object inventory'))
    def dump_inventory(self) -> None:
        InventoryFile.dump(path.join(self.outdir, INVENTORY_FILENAME), self.env, self)

    def dump_search_index(self) -> None:
        if self.indexer is None:
            return

        with progress_message(__('dumping search index in %s') % self.indexer.label()):
            self.indexer.prune(self.env.all_docs)
            searchindexfn = path.join(self.outdir, self.searchindex_filename)
            # first write to a temporary file, so that if dumping fails,
            # the existing index won't be overwritten
            if self.indexer_dumps_unicode:
                with open(searchindexfn + '.tmp', 'w', encoding='utf-8') as ft:
                    self.indexer.dump(ft, self.indexer_format)
            else:
                with open(searchindexfn + '.tmp', 'wb') as fb:
                    self.indexer.dump(fb, self.indexer_format)
            os.replace(searchindexfn + '.tmp', searchindexfn)


def convert_html_css_files(app: Sphinx, config: Config) -> None:
    """This converts string styled html_css_files to tuple styled one."""
    html_css_files: list[tuple[str, dict]] = []
    for entry in config.html_css_files:
        if isinstance(entry, str):
            html_css_files.append((entry, {}))
        else:
            try:
                filename, attrs = entry
                html_css_files.append((filename, attrs))
            except Exception:
                logger.warning(__('invalid css_file: %r, ignored'), entry)
                continue

    config.html_css_files = html_css_files  # type: ignore[attr-defined]


def _format_modified_time(timestamp: float) -> str:
    """Return an RFC 3339 formatted string representing the given timestamp."""
    seconds, fraction = divmod(timestamp, 1)
    return time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime(seconds)) + f'.{fraction:.3f}'


def convert_html_js_files(app: Sphinx, config: Config) -> None:
    """This converts string styled html_js_files to tuple styled one."""
    html_js_files: list[tuple[str, dict]] = []
    for entry in config.html_js_files:
        if isinstance(entry, str):
            html_js_files.append((entry, {}))
        else:
            try:
                filename, attrs = entry
                html_js_files.append((filename, attrs))
            except Exception:
                logger.warning(__('invalid js_file: %r, ignored'), entry)
                continue

    config.html_js_files = html_js_files  # type: ignore[attr-defined]


def setup_resource_paths(app: Sphinx, pagename: str, templatename: str,
                         context: dict, doctree: Node) -> None:
    """Set up relative resource paths."""
    pathto = context['pathto']

    # favicon_url
    favicon_url = context.get('favicon_url')
    if favicon_url and not isurl(favicon_url):
        context['favicon_url'] = pathto('_static/' + favicon_url, resource=True)

    # logo_url
    logo_url = context.get('logo_url')
    if logo_url and not isurl(logo_url):
        context['logo_url'] = pathto('_static/' + logo_url, resource=True)


def validate_math_renderer(app: Sphinx) -> None:
    if app.builder.format != 'html':
        return

    name = app.builder.math_renderer_name  # type: ignore[attr-defined]
    if name is None:
        raise ConfigError(__('Many math_renderers are registered. '
                             'But no math_renderer is selected.'))
    if name not in app.registry.html_inline_math_renderers:
        raise ConfigError(__('Unknown math_renderer %r is given.') % name)


def validate_html_extra_path(app: Sphinx, config: Config) -> None:
    """Check html_extra_paths setting."""
    for entry in config.html_extra_path[:]:
        extra_path = path.normpath(path.join(app.confdir, entry))
        if not path.exists(extra_path):
            logger.warning(__('html_extra_path entry %r does not exist'), entry)
            config.html_extra_path.remove(entry)
        elif (path.splitdrive(app.outdir)[0] == path.splitdrive(extra_path)[0] and
              path.commonpath((app.outdir, extra_path)) == path.normpath(app.outdir)):
            logger.warning(__('html_extra_path entry %r is placed inside outdir'), entry)
            config.html_extra_path.remove(entry)


def validate_html_static_path(app: Sphinx, config: Config) -> None:
    """Check html_static_paths setting."""
    for entry in config.html_static_path[:]:
        static_path = path.normpath(path.join(app.confdir, entry))
        if not path.exists(static_path):
            logger.warning(__('html_static_path entry %r does not exist'), entry)
            config.html_static_path.remove(entry)
        elif (path.splitdrive(app.outdir)[0] == path.splitdrive(static_path)[0] and
              path.commonpath((app.outdir, static_path)) == path.normpath(app.outdir)):
            logger.warning(__('html_static_path entry %r is placed inside outdir'), entry)
            config.html_static_path.remove(entry)


def validate_html_logo(app: Sphinx, config: Config) -> None:
    """Check html_logo setting."""
    if (config.html_logo and
            not path.isfile(path.join(app.confdir, config.html_logo)) and
            not isurl(config.html_logo)):
        logger.warning(__('logo file %r does not exist'), config.html_logo)
        config.html_logo = None  # type: ignore[attr-defined]


def validate_html_favicon(app: Sphinx, config: Config) -> None:
    """Check html_favicon setting."""
    if (config.html_favicon and
            not path.isfile(path.join(app.confdir, config.html_favicon)) and
            not isurl(config.html_favicon)):
        logger.warning(__('favicon file %r does not exist'), config.html_favicon)
        config.html_favicon = None  # type: ignore[attr-defined]


def error_on_html_4(_app: Sphinx, config: Config) -> None:
    """Error on HTML 4."""
    if config.html4_writer:
        raise ConfigError(_(
            'HTML 4 is no longer supported by Sphinx. '
            '("html4_writer=True" detected in configuration options)',
        ))


def setup(app: Sphinx) -> dict[str, Any]:
    # builders
    app.add_builder(StandaloneHTMLBuilder)

    # config values
    app.add_config_value('html_theme', 'alabaster', 'html')
    app.add_config_value('html_theme_path', [], 'html')
    app.add_config_value('html_theme_options', {}, 'html')
    app.add_config_value('html_title',
                         lambda self: _('%s %s documentation') % (self.project, self.release),
                         'html', [str])
    app.add_config_value('html_short_title', lambda self: self.html_title, 'html')
    app.add_config_value('html_style', None, 'html', [list, str])
    app.add_config_value('html_logo', None, 'html', [str])
    app.add_config_value('html_favicon', None, 'html', [str])
    app.add_config_value('html_css_files', [], 'html')
    app.add_config_value('html_js_files', [], 'html')
    app.add_config_value('html_static_path', [], 'html')
    app.add_config_value('html_extra_path', [], 'html')
    app.add_config_value('html_last_updated_fmt', None, 'html', [str])
    app.add_config_value('html_sidebars', {}, 'html')
    app.add_config_value('html_additional_pages', {}, 'html')
    app.add_config_value('html_domain_indices', True, 'html', [list])
    app.add_config_value('html_permalinks', True, 'html')
    app.add_config_value('html_permalinks_icon', '¶', 'html')
    app.add_config_value('html_use_index', True, 'html')
    app.add_config_value('html_split_index', False, 'html')
    app.add_config_value('html_copy_source', True, 'html')
    app.add_config_value('html_show_sourcelink', True, 'html')
    app.add_config_value('html_sourcelink_suffix', '.txt', 'html')
    app.add_config_value('html_use_opensearch', '', 'html')
    app.add_config_value('html_file_suffix', None, 'html', [str])
    app.add_config_value('html_link_suffix', None, 'html', [str])
    app.add_config_value('html_show_copyright', True, 'html')
    app.add_config_value('html_show_search_summary', True, 'html')
    app.add_config_value('html_show_sphinx', True, 'html')
    app.add_config_value('html_context', {}, 'html')
    app.add_config_value('html_output_encoding', 'utf-8', 'html')
    app.add_config_value('html_compact_lists', True, 'html')
    app.add_config_value('html_secnumber_suffix', '. ', 'html')
    app.add_config_value('html_search_language', None, 'html', [str])
    app.add_config_value('html_search_options', {}, 'html')
    app.add_config_value('html_search_scorer', '', '')
    app.add_config_value('html_scaled_image_link', True, 'html')
    app.add_config_value('html_baseurl', '', 'html')
    app.add_config_value('html_codeblock_linenos_style', 'inline', 'html',  # RemovedInSphinx70Warning  # noqa: E501
                         ENUM('table', 'inline'))
    app.add_config_value('html_math_renderer', None, 'env')
    app.add_config_value('html4_writer', False, 'html')

    # events
    app.add_event('html-collect-pages')
    app.add_event('html-page-context')

    # event handlers
    app.connect('config-inited', convert_html_css_files, priority=800)
    app.connect('config-inited', convert_html_js_files, priority=800)
    app.connect('config-inited', validate_html_extra_path, priority=800)
    app.connect('config-inited', validate_html_static_path, priority=800)
    app.connect('config-inited', validate_html_logo, priority=800)
    app.connect('config-inited', validate_html_favicon, priority=800)
    app.connect('config-inited', error_on_html_4, priority=800)
    app.connect('builder-inited', validate_math_renderer)
    app.connect('html-page-context', setup_resource_paths)

    # load default math renderer
    app.setup_extension('sphinx.ext.mathjax')

    # load transforms for HTML builder
    app.setup_extension('sphinx.builders.html.transforms')

    return {
        'version': 'builtin',
        'parallel_read_safe': True,
        'parallel_write_safe': True,
    }


# deprecated name -> (object to return, canonical path or empty string)
_DEPRECATED_OBJECTS = {
    'Stylesheet': (_CascadingStyleSheet, 'sphinx.builders.html._assets._CascadingStyleSheet', (9, 0)),  # NoQA: E501
    'JavaScript': (_JavaScript, 'sphinx.builders.html._assets._JavaScript', (9, 0)),
}


def __getattr__(name):
    if name not in _DEPRECATED_OBJECTS:
        msg = f'module {__name__!r} has no attribute {name!r}'
        raise AttributeError(msg)

    from sphinx.deprecation import _deprecation_warning

    deprecated_object, canonical_name, remove = _DEPRECATED_OBJECTS[name]
    _deprecation_warning(__name__, name, canonical_name, remove=remove)
    return deprecated_object
