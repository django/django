# -*- coding: utf-8 -*-
"""
    sphinx.environment.collectors.asset
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    The image collector for sphinx.environment.

    :copyright: Copyright 2007-2019 by the Sphinx team, see AUTHORS.
    :license: BSD, see LICENSE for details.
"""

import os
from glob import glob
from os import path

from docutils import nodes
from docutils.utils import relative_path
from six import iteritems, itervalues

from sphinx import addnodes
from sphinx.environment.collectors import EnvironmentCollector
from sphinx.locale import __
from sphinx.util import logging
from sphinx.util.i18n import get_image_filename_for_language, search_image_for_language
from sphinx.util.images import guess_mimetype

if False:
    # For type annotation
    from typing import Dict, List, Set, Tuple  # NOQA
    from docutils import nodes  # NOQA
    from sphinx.sphinx import Sphinx  # NOQA
    from sphinx.environment import BuildEnvironment  # NOQA

logger = logging.getLogger(__name__)


class ImageCollector(EnvironmentCollector):
    """Image files collector for sphinx.environment."""

    def clear_doc(self, app, env, docname):
        # type: (Sphinx, BuildEnvironment, unicode) -> None
        env.images.purge_doc(docname)

    def merge_other(self, app, env, docnames, other):
        # type: (Sphinx, BuildEnvironment, Set[unicode], BuildEnvironment) -> None
        env.images.merge_other(docnames, other.images)

    def process_doc(self, app, doctree):
        # type: (Sphinx, nodes.Node) -> None
        """Process and rewrite image URIs."""
        docname = app.env.docname

        for node in doctree.traverse(nodes.image):
            # Map the mimetype to the corresponding image.  The writer may
            # choose the best image from these candidates.  The special key * is
            # set if there is only single candidate to be used by a writer.
            # The special key ? is set for nonlocal URIs.
            candidates = {}  # type: Dict[unicode, unicode]
            node['candidates'] = candidates
            imguri = node['uri']
            if imguri.startswith('data:'):
                candidates['?'] = imguri
                continue
            elif imguri.find('://') != -1:
                candidates['?'] = imguri
                continue
            rel_imgpath, full_imgpath = app.env.relfn2path(imguri, docname)
            if app.config.language:
                # substitute figures (ex. foo.png -> foo.en.png)
                i18n_full_imgpath = search_image_for_language(full_imgpath, app.env)
                if i18n_full_imgpath != full_imgpath:
                    full_imgpath = i18n_full_imgpath
                    rel_imgpath = relative_path(path.join(app.srcdir, 'dummy'),
                                                i18n_full_imgpath)
            # set imgpath as default URI
            node['uri'] = rel_imgpath
            if rel_imgpath.endswith(os.extsep + '*'):
                if app.config.language:
                    # Search language-specific figures at first
                    i18n_imguri = get_image_filename_for_language(imguri, app.env)
                    _, full_i18n_imgpath = app.env.relfn2path(i18n_imguri, docname)
                    self.collect_candidates(app.env, full_i18n_imgpath, candidates, node)

                self.collect_candidates(app.env, full_imgpath, candidates, node)
            else:
                candidates['*'] = rel_imgpath

            # map image paths to unique image names (so that they can be put
            # into a single directory)
            for imgpath in itervalues(candidates):
                app.env.dependencies[docname].add(imgpath)
                if not os.access(path.join(app.srcdir, imgpath), os.R_OK):
                    logger.warning(__('image file not readable: %s') % imgpath,
                                   location=node, type='image', subtype='not_readable')
                    continue
                app.env.images.add_file(docname, imgpath)

    def collect_candidates(self, env, imgpath, candidates, node):
        # type: (BuildEnvironment, unicode, Dict[unicode, unicode], nodes.Node) -> None
        globbed = {}  # type: Dict[unicode, List[unicode]]
        for filename in glob(imgpath):
            new_imgpath = relative_path(path.join(env.srcdir, 'dummy'),
                                        filename)
            try:
                mimetype = guess_mimetype(filename)
                if mimetype not in candidates:
                    globbed.setdefault(mimetype, []).append(new_imgpath)
            except (OSError, IOError) as err:
                logger.warning(__('image file %s not readable: %s') % (filename, err),
                               location=node, type='image', subtype='not_readable')
        for key, files in iteritems(globbed):
            candidates[key] = sorted(files, key=len)[0]  # select by similarity


class DownloadFileCollector(EnvironmentCollector):
    """Download files collector for sphinx.environment."""

    def clear_doc(self, app, env, docname):
        # type: (Sphinx, BuildEnvironment, unicode) -> None
        env.dlfiles.purge_doc(docname)

    def merge_other(self, app, env, docnames, other):
        # type: (Sphinx, BuildEnvironment, Set[unicode], BuildEnvironment) -> None
        env.dlfiles.merge_other(docnames, other.dlfiles)

    def process_doc(self, app, doctree):
        # type: (Sphinx, nodes.Node) -> None
        """Process downloadable file paths. """
        for node in doctree.traverse(addnodes.download_reference):
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
                node['filename'] = app.env.dlfiles.add_file(app.env.docname, filename)


def setup(app):
    # type: (Sphinx) -> Dict
    app.add_env_collector(ImageCollector)
    app.add_env_collector(DownloadFileCollector)

    return {
        'version': 'builtin',
        'parallel_read_safe': True,
        'parallel_write_safe': True,
    }
