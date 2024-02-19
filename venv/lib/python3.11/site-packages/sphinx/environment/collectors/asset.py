"""The image collector for sphinx.environment."""

from __future__ import annotations

import os
from glob import glob
from os import path
from typing import TYPE_CHECKING, Any

from docutils import nodes
from docutils.utils import relative_path

from sphinx import addnodes
from sphinx.environment.collectors import EnvironmentCollector
from sphinx.locale import __
from sphinx.util import logging
from sphinx.util.i18n import get_image_filename_for_language, search_image_for_language
from sphinx.util.images import guess_mimetype

if TYPE_CHECKING:
    from docutils.nodes import Node

    from sphinx.application import Sphinx
    from sphinx.environment import BuildEnvironment

logger = logging.getLogger(__name__)


class ImageCollector(EnvironmentCollector):
    """Image files collector for sphinx.environment."""

    def clear_doc(self, app: Sphinx, env: BuildEnvironment, docname: str) -> None:
        env.images.purge_doc(docname)

    def merge_other(self, app: Sphinx, env: BuildEnvironment,
                    docnames: set[str], other: BuildEnvironment) -> None:
        env.images.merge_other(docnames, other.images)

    def process_doc(self, app: Sphinx, doctree: nodes.document) -> None:
        """Process and rewrite image URIs."""
        docname = app.env.docname

        for node in doctree.findall(nodes.image):
            # Map the mimetype to the corresponding image.  The writer may
            # choose the best image from these candidates.  The special key * is
            # set if there is only single candidate to be used by a writer.
            # The special key ? is set for nonlocal URIs.
            candidates: dict[str, str] = {}
            node['candidates'] = candidates
            imguri = node['uri']
            if imguri.startswith('data:'):
                candidates['?'] = imguri
                continue
            if imguri.find('://') != -1:
                candidates['?'] = imguri
                continue

            if imguri.endswith(os.extsep + '*'):
                # Update `node['uri']` to a relative path from srcdir
                # from a relative path from current document.
                rel_imgpath, full_imgpath = app.env.relfn2path(imguri, docname)
                node['uri'] = rel_imgpath

                # Search language-specific figures at first
                i18n_imguri = get_image_filename_for_language(imguri, app.env)
                _, full_i18n_imgpath = app.env.relfn2path(i18n_imguri, docname)
                self.collect_candidates(app.env, full_i18n_imgpath, candidates, node)

                self.collect_candidates(app.env, full_imgpath, candidates, node)
            else:
                # substitute imguri by figure_language_filename
                # (ex. foo.png -> foo.en.png)
                imguri = search_image_for_language(imguri, app.env)

                # Update `node['uri']` to a relative path from srcdir
                # from a relative path from current document.
                original_uri = node['uri']
                node['uri'], _ = app.env.relfn2path(imguri, docname)
                candidates['*'] = node['uri']
                if node['uri'] != original_uri:
                    node['original_uri'] = original_uri

            # map image paths to unique image names (so that they can be put
            # into a single directory)
            for imgpath in candidates.values():
                app.env.dependencies[docname].add(imgpath)
                if not os.access(path.join(app.srcdir, imgpath), os.R_OK):
                    logger.warning(__('image file not readable: %s') % imgpath,
                                   location=node, type='image', subtype='not_readable')
                    continue
                app.env.images.add_file(docname, imgpath)

    def collect_candidates(self, env: BuildEnvironment, imgpath: str,
                           candidates: dict[str, str], node: Node) -> None:
        globbed: dict[str, list[str]] = {}
        for filename in glob(imgpath):
            new_imgpath = relative_path(path.join(env.srcdir, 'dummy'),
                                        filename)
            try:
                mimetype = guess_mimetype(filename)
                if mimetype is None:
                    basename, suffix = path.splitext(filename)
                    mimetype = 'image/x-' + suffix[1:]
                if mimetype not in candidates:
                    globbed.setdefault(mimetype, []).append(new_imgpath)
            except OSError as err:
                logger.warning(__('image file %s not readable: %s') % (filename, err),
                               location=node, type='image', subtype='not_readable')
        for key, files in globbed.items():
            candidates[key] = sorted(files, key=len)[0]  # select by similarity


class DownloadFileCollector(EnvironmentCollector):
    """Download files collector for sphinx.environment."""

    def clear_doc(self, app: Sphinx, env: BuildEnvironment, docname: str) -> None:
        env.dlfiles.purge_doc(docname)

    def merge_other(self, app: Sphinx, env: BuildEnvironment,
                    docnames: set[str], other: BuildEnvironment) -> None:
        env.dlfiles.merge_other(docnames, other.dlfiles)

    def process_doc(self, app: Sphinx, doctree: nodes.document) -> None:
        """Process downloadable file paths. """
        for node in doctree.findall(addnodes.download_reference):
            targetname = node['reftarget']
            if '://' in targetname:
                node['refuri'] = targetname
            else:
                rel_filename, filename = app.env.relfn2path(targetname, app.env.docname)
                app.env.dependencies[app.env.docname].add(rel_filename)
                if not os.access(filename, os.R_OK):
                    logger.warning(__('download file not readable: %s') % filename,
                                   location=node, type='download', subtype='not_readable')
                    continue
                node['filename'] = app.env.dlfiles.add_file(app.env.docname, rel_filename)


def setup(app: Sphinx) -> dict[str, Any]:
    app.add_env_collector(ImageCollector)
    app.add_env_collector(DownloadFileCollector)

    return {
        'version': 'builtin',
        'parallel_read_safe': True,
        'parallel_write_safe': True,
    }
