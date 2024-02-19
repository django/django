"""Utilities for Sphinx extensions."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from packaging.version import InvalidVersion, Version

from sphinx.errors import VersionRequirementError
from sphinx.locale import __
from sphinx.util import logging

if TYPE_CHECKING:
    from sphinx.application import Sphinx
    from sphinx.config import Config

logger = logging.getLogger(__name__)


class Extension:
    def __init__(self, name: str, module: Any, **kwargs: Any) -> None:
        self.name = name
        self.module = module
        self.metadata = kwargs
        self.version = kwargs.pop('version', 'unknown version')

        # The extension supports parallel read or not.  The default value
        # is ``None``.  It means the extension does not tell the status.
        # It will be warned on parallel reading.
        self.parallel_read_safe = kwargs.pop('parallel_read_safe', None)

        # The extension supports parallel write or not.  The default value
        # is ``True``.  Sphinx writes parallelly documents even if
        # the extension does not tell its status.
        self.parallel_write_safe = kwargs.pop('parallel_write_safe', True)


def verify_needs_extensions(app: Sphinx, config: Config) -> None:
    """Check that extensions mentioned in :confval:`needs_extensions` satisfy the version
    requirement, and warn if an extension is not loaded.

    Warns if an extension in :confval:`needs_extension` is not loaded.

    :raises VersionRequirementError: if the version of an extension in
    :confval:`needs_extension` is unknown or older than the required version.
    """
    if config.needs_extensions is None:
        return

    for extname, reqversion in config.needs_extensions.items():
        extension = app.extensions.get(extname)
        if extension is None:
            logger.warning(__('The %s extension is required by needs_extensions settings, '
                              'but it is not loaded.'), extname)
            continue

        fulfilled = True
        if extension.version == 'unknown version':
            fulfilled = False
        else:
            try:
                if Version(reqversion) > Version(extension.version):
                    fulfilled = False
            except InvalidVersion:
                if reqversion > extension.version:
                    fulfilled = False

        if not fulfilled:
            raise VersionRequirementError(__('This project needs the extension %s at least in '
                                             'version %s and therefore cannot be built with '
                                             'the loaded version (%s).') %
                                          (extname, reqversion, extension.version))


def setup(app: Sphinx) -> dict[str, Any]:
    app.connect('config-inited', verify_needs_extensions, priority=800)

    return {
        'version': 'builtin',
        'parallel_read_safe': True,
        'parallel_write_safe': True,
    }
