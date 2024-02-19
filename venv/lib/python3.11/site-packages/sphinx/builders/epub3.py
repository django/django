"""Build epub3 files.

Originally derived from epub.py.
"""

from __future__ import annotations

import html
import os
import re
import time
from os import path
from typing import TYPE_CHECKING, Any, NamedTuple

from sphinx import package_dir
from sphinx.builders import _epub_base
from sphinx.config import ENUM, Config
from sphinx.locale import __
from sphinx.util import logging
from sphinx.util.fileutil import copy_asset_file
from sphinx.util.osutil import make_filename

if TYPE_CHECKING:
    from sphinx.application import Sphinx

logger = logging.getLogger(__name__)


class NavPoint(NamedTuple):
    text: str
    refuri: str
    children: list[NavPoint]


# writing modes
PAGE_PROGRESSION_DIRECTIONS = {
    'horizontal': 'ltr',
    'vertical': 'rtl',
}
IBOOK_SCROLL_AXIS = {
    'horizontal': 'vertical',
    'vertical': 'horizontal',
}
THEME_WRITING_MODES = {
    'vertical': 'vertical-rl',
    'horizontal': 'horizontal-tb',
}

DOCTYPE = '''<!DOCTYPE html>'''

HTML_TAG = (
    '<html xmlns="http://www.w3.org/1999/xhtml" '
    'xmlns:epub="http://www.idpf.org/2007/ops">'
)

# https://www.w3.org/TR/REC-xml/#NT-Name
_xml_name_start_char = (
    ':|[A-Z]|_|[a-z]|[\u00C0-\u00D6]'
    '|[\u00D8-\u00F6]|[\u00F8-\u02FF]|[\u0370-\u037D]'
    '|[\u037F-\u1FFF]|[\u200C-\u200D]|[\u2070-\u218F]'
    '|[\u2C00-\u2FEF]|[\u3001-\uD7FF]|[\uF900-\uFDCF]'
    '|[\uFDF0-\uFFFD]|[\U00010000-\U000EFFFF]'
)
_xml_name_char = (
    _xml_name_start_char + r'\-|\.' '|[0-9]|\u00B7|[\u0300-\u036F]|[\u203F-\u2040]'
)
_XML_NAME_PATTERN = re.compile(f'({_xml_name_start_char})({_xml_name_char})*')


class Epub3Builder(_epub_base.EpubBuilder):
    """
    Builder that outputs epub3 files.

    It creates the metainfo files content.opf, nav.xhtml, toc.ncx, mimetype,
    and META-INF/container.xml. Afterwards, all necessary files are zipped to
    an epub file.
    """
    name = 'epub'
    epilog = __('The ePub file is in %(outdir)s.')

    supported_remote_images = False
    template_dir = path.join(package_dir, 'templates', 'epub3')
    doctype = DOCTYPE
    html_tag = HTML_TAG
    use_meta_charset = True

    # Finish by building the epub file
    def handle_finish(self) -> None:
        """Create the metainfo files and finally the epub."""
        self.get_toc()
        self.build_mimetype()
        self.build_container()
        self.build_content()
        self.build_navigation_doc()
        self.build_toc()
        self.build_epub()

    def content_metadata(self) -> dict[str, Any]:
        """Create a dictionary with all metadata for the content.opf
        file properly escaped.
        """
        writing_mode = self.config.epub_writing_mode

        if (source_date_epoch := os.getenv('SOURCE_DATE_EPOCH')) is not None:
            time_tuple = time.gmtime(int(source_date_epoch))
        else:
            time_tuple = time.gmtime()

        metadata = super().content_metadata()
        metadata['description'] = html.escape(self.config.epub_description)
        metadata['contributor'] = html.escape(self.config.epub_contributor)
        metadata['page_progression_direction'] = PAGE_PROGRESSION_DIRECTIONS.get(writing_mode)
        metadata['ibook_scroll_axis'] = IBOOK_SCROLL_AXIS.get(writing_mode)
        metadata['date'] = html.escape(time.strftime("%Y-%m-%dT%H:%M:%SZ", time_tuple))
        metadata['version'] = html.escape(self.config.version)
        metadata['epub_version'] = self.config.epub_version
        return metadata

    def prepare_writing(self, docnames: set[str]) -> None:
        super().prepare_writing(docnames)

        writing_mode = self.config.epub_writing_mode
        self.globalcontext['theme_writing_mode'] = THEME_WRITING_MODES.get(writing_mode)
        self.globalcontext['html_tag'] = self.html_tag
        self.globalcontext['use_meta_charset'] = self.use_meta_charset
        self.globalcontext['skip_ua_compatible'] = True

    def build_navlist(self, navnodes: list[dict[str, Any]]) -> list[NavPoint]:
        """Create the toc navigation structure.

        This method is almost same as build_navpoints method in epub.py.
        This is because the logical navigation structure of epub3 is not
        different from one of epub2.

        The difference from build_navpoints method is templates which are used
        when generating navigation documents.
        """
        navstack: list[NavPoint] = []
        navstack.append(NavPoint('', '', []))
        level = 0
        for node in navnodes:
            if not node['text']:
                continue
            file = node['refuri'].split('#')[0]
            if file in self.ignored_files:
                continue
            if node['level'] > self.config.epub_tocdepth:
                continue

            navpoint = NavPoint(node['text'], node['refuri'], [])
            if node['level'] == level:
                navstack.pop()
                navstack[-1].children.append(navpoint)
                navstack.append(navpoint)
            elif node['level'] == level + 1:
                level += 1
                navstack[-1].children.append(navpoint)
                navstack.append(navpoint)
            elif node['level'] < level:
                while node['level'] < len(navstack):
                    navstack.pop()
                level = node['level']
                navstack[-1].children.append(navpoint)
                navstack.append(navpoint)
            else:
                unreachable = 'Should never reach here. It might be a bug.'
                raise RuntimeError(unreachable)

        return navstack[0].children

    def navigation_doc_metadata(self, navlist: list[NavPoint]) -> dict[str, Any]:
        """Create a dictionary with all metadata for the nav.xhtml file
        properly escaped.
        """
        return {
            'lang': html.escape(self.config.epub_language),
            'toc_locale': html.escape(self.guide_titles['toc']),
            'navlist': navlist,
        }

    def build_navigation_doc(self) -> None:
        """Write the metainfo file nav.xhtml."""
        logger.info(__('writing nav.xhtml file...'))

        if self.config.epub_tocscope == 'default':
            doctree = self.env.get_and_resolve_doctree(
                self.config.root_doc, self,
                prune_toctrees=False, includehidden=False)
            refnodes = self.get_refnodes(doctree, [])
            self.toc_add_files(refnodes)
        else:
            # 'includehidden'
            refnodes = self.refnodes
        navlist = self.build_navlist(refnodes)
        copy_asset_file(path.join(self.template_dir, 'nav.xhtml_t'), self.outdir,
                        self.navigation_doc_metadata(navlist))

        # Add nav.xhtml to epub file
        if 'nav.xhtml' not in self.files:
            self.files.append('nav.xhtml')


def validate_config_values(app: Sphinx) -> None:
    if app.builder.name != 'epub':
        return

    # <package> lang attribute, dc:language
    if not app.config.epub_language:
        logger.warning(__('conf value "epub_language" (or "language") '
                          'should not be empty for EPUB3'))
    # <package> unique-identifier attribute
    if not _XML_NAME_PATTERN.match(app.config.epub_uid):
        logger.warning(__('conf value "epub_uid" should be XML NAME for EPUB3'))
    # dc:title
    if not app.config.epub_title:
        logger.warning(__('conf value "epub_title" (or "html_title") '
                          'should not be empty for EPUB3'))
    # dc:creator
    if not app.config.epub_author:
        logger.warning(__('conf value "epub_author" should not be empty for EPUB3'))
    # dc:contributor
    if not app.config.epub_contributor:
        logger.warning(__('conf value "epub_contributor" should not be empty for EPUB3'))
    # dc:description
    if not app.config.epub_description:
        logger.warning(__('conf value "epub_description" should not be empty for EPUB3'))
    # dc:publisher
    if not app.config.epub_publisher:
        logger.warning(__('conf value "epub_publisher" should not be empty for EPUB3'))
    # dc:rights
    if not app.config.epub_copyright:
        logger.warning(__('conf value "epub_copyright" (or "copyright")'
                          'should not be empty for EPUB3'))
    # dc:identifier
    if not app.config.epub_identifier:
        logger.warning(__('conf value "epub_identifier" should not be empty for EPUB3'))
    # meta ibooks:version
    if not app.config.version:
        logger.warning(__('conf value "version" should not be empty for EPUB3'))


def convert_epub_css_files(app: Sphinx, config: Config) -> None:
    """This converts string styled epub_css_files to tuple styled one."""
    epub_css_files: list[tuple[str, dict[str, Any]]] = []
    for entry in config.epub_css_files:
        if isinstance(entry, str):
            epub_css_files.append((entry, {}))
        else:
            try:
                filename, attrs = entry
                epub_css_files.append((filename, attrs))
            except Exception:
                logger.warning(__('invalid css_file: %r, ignored'), entry)
                continue

    config.epub_css_files = epub_css_files  # type: ignore[attr-defined]


def setup(app: Sphinx) -> dict[str, Any]:
    app.add_builder(Epub3Builder)

    # config values
    app.add_config_value('epub_basename', lambda self: make_filename(self.project), False)
    app.add_config_value('epub_version', 3.0, 'epub')  # experimental
    app.add_config_value('epub_theme', 'epub', 'epub')
    app.add_config_value('epub_theme_options', {}, 'epub')
    app.add_config_value('epub_title', lambda self: self.project, 'epub')
    app.add_config_value('epub_author', lambda self: self.author, 'epub')
    app.add_config_value('epub_language', lambda self: self.language or 'en', 'epub')
    app.add_config_value('epub_publisher', lambda self: self.author, 'epub')
    app.add_config_value('epub_copyright', lambda self: self.copyright, 'epub')
    app.add_config_value('epub_identifier', 'unknown', 'epub')
    app.add_config_value('epub_scheme', 'unknown', 'epub')
    app.add_config_value('epub_uid', 'unknown', 'env')
    app.add_config_value('epub_cover', (), 'env')
    app.add_config_value('epub_guide', (), 'env')
    app.add_config_value('epub_pre_files', [], 'env')
    app.add_config_value('epub_post_files', [], 'env')
    app.add_config_value('epub_css_files', lambda config: config.html_css_files, 'epub')
    app.add_config_value('epub_exclude_files', [], 'env')
    app.add_config_value('epub_tocdepth', 3, 'env')
    app.add_config_value('epub_tocdup', True, 'env')
    app.add_config_value('epub_tocscope', 'default', 'env')
    app.add_config_value('epub_fix_images', False, 'env')
    app.add_config_value('epub_max_image_width', 0, 'env')
    app.add_config_value('epub_show_urls', 'inline', 'epub')
    app.add_config_value('epub_use_index', lambda self: self.html_use_index, 'epub')
    app.add_config_value('epub_description', 'unknown', 'epub')
    app.add_config_value('epub_contributor', 'unknown', 'epub')
    app.add_config_value('epub_writing_mode', 'horizontal', 'epub',
                         ENUM('horizontal', 'vertical'))

    # event handlers
    app.connect('config-inited', convert_epub_css_files, priority=800)
    app.connect('builder-inited', validate_config_values)

    return {
        'version': 'builtin',
        'parallel_read_safe': True,
        'parallel_write_safe': True,
    }
