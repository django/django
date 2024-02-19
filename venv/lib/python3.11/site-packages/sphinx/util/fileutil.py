"""File utility functions for Sphinx."""

from __future__ import annotations

import os
import posixpath
from typing import TYPE_CHECKING, Callable

from docutils.utils import relative_path

from sphinx.util.osutil import copyfile, ensuredir

if TYPE_CHECKING:
    from sphinx.util.template import BaseRenderer
    from sphinx.util.typing import PathMatcher


def copy_asset_file(source: str | os.PathLike[str], destination: str | os.PathLike[str],
                    context: dict | None = None,
                    renderer: BaseRenderer | None = None) -> None:
    """Copy an asset file to destination.

    On copying, it expands the template variables if context argument is given and
    the asset is a template file.

    :param source: The path to source file
    :param destination: The path to destination file or directory
    :param context: The template variables.  If not given, template files are simply copied
    :param renderer: The template engine.  If not given, SphinxRenderer is used by default
    """
    if not os.path.exists(source):
        return

    if os.path.isdir(destination):
        # Use source filename if destination points a directory
        destination = os.path.join(destination, os.path.basename(source))
    else:
        destination = str(destination)

    if os.path.basename(source).endswith(('_t', '_T')) and context is not None:
        if renderer is None:
            from sphinx.util.template import SphinxRenderer
            renderer = SphinxRenderer()

        with open(source, encoding='utf-8') as fsrc:
            if destination.endswith(('_t', '_T')):
                destination = destination[:-2]
            with open(destination, 'w', encoding='utf-8') as fdst:
                fdst.write(renderer.render_string(fsrc.read(), context))
    else:
        copyfile(source, destination)


def copy_asset(source: str | os.PathLike[str], destination: str | os.PathLike[str],
               excluded: PathMatcher = lambda path: False,
               context: dict | None = None, renderer: BaseRenderer | None = None,
               onerror: Callable[[str, Exception], None] | None = None) -> None:
    """Copy asset files to destination recursively.

    On copying, it expands the template variables if context argument is given and
    the asset is a template file.

    :param source: The path to source file or directory
    :param destination: The path to destination directory
    :param excluded: The matcher to determine the given path should be copied or not
    :param context: The template variables.  If not given, template files are simply copied
    :param renderer: The template engine.  If not given, SphinxRenderer is used by default
    :param onerror: The error handler.
    """
    if not os.path.exists(source):
        return

    if renderer is None:
        from sphinx.util.template import SphinxRenderer
        renderer = SphinxRenderer()

    ensuredir(destination)
    if os.path.isfile(source):
        copy_asset_file(source, destination, context, renderer)
        return

    for root, dirs, files in os.walk(source, followlinks=True):
        reldir = relative_path(source, root)  # type: ignore[arg-type]
        for dir in dirs[:]:
            if excluded(posixpath.join(reldir, dir)):
                dirs.remove(dir)
            else:
                ensuredir(posixpath.join(destination, reldir, dir))

        for filename in files:
            if not excluded(posixpath.join(reldir, filename)):
                try:
                    copy_asset_file(posixpath.join(root, filename),
                                    posixpath.join(destination, reldir),
                                    context, renderer)
                except Exception as exc:
                    if onerror:
                        onerror(posixpath.join(root, filename), exc)
                    else:
                        raise
