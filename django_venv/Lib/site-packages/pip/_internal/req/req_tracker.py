from __future__ import absolute_import

import contextlib
import errno
import hashlib
import logging
import os

from pip._internal.utils.temp_dir import TempDirectory
from pip._internal.utils.typing import MYPY_CHECK_RUNNING

if MYPY_CHECK_RUNNING:
    from types import TracebackType
    from typing import Iterator, Optional, Set, Type
    from pip._internal.req.req_install import InstallRequirement
    from pip._internal.models.link import Link

logger = logging.getLogger(__name__)


class RequirementTracker(object):

    def __init__(self):
        # type: () -> None
        self._root = os.environ.get('PIP_REQ_TRACKER')
        if self._root is None:
            self._temp_dir = TempDirectory(delete=False, kind='req-tracker')
            self._temp_dir.create()
            self._root = os.environ['PIP_REQ_TRACKER'] = self._temp_dir.path
            logger.debug('Created requirements tracker %r', self._root)
        else:
            self._temp_dir = None
            logger.debug('Re-using requirements tracker %r', self._root)
        self._entries = set()  # type: Set[InstallRequirement]

    def __enter__(self):
        # type: () -> RequirementTracker
        return self

    def __exit__(
        self,
        exc_type,  # type: Optional[Type[BaseException]]
        exc_val,  # type: Optional[BaseException]
        exc_tb  # type: Optional[TracebackType]
    ):
        # type: (...) -> None
        self.cleanup()

    def _entry_path(self, link):
        # type: (Link) -> str
        hashed = hashlib.sha224(link.url_without_fragment.encode()).hexdigest()
        return os.path.join(self._root, hashed)

    def add(self, req):
        # type: (InstallRequirement) -> None
        link = req.link
        info = str(req)
        entry_path = self._entry_path(link)
        try:
            with open(entry_path) as fp:
                # Error, these's already a build in progress.
                raise LookupError('%s is already being built: %s'
                                  % (link, fp.read()))
        except IOError as e:
            if e.errno != errno.ENOENT:
                raise
            assert req not in self._entries
            with open(entry_path, 'w') as fp:
                fp.write(info)
            self._entries.add(req)
            logger.debug('Added %s to build tracker %r', req, self._root)

    def remove(self, req):
        # type: (InstallRequirement) -> None
        link = req.link
        self._entries.remove(req)
        os.unlink(self._entry_path(link))
        logger.debug('Removed %s from build tracker %r', req, self._root)

    def cleanup(self):
        # type: () -> None
        for req in set(self._entries):
            self.remove(req)
        remove = self._temp_dir is not None
        if remove:
            self._temp_dir.cleanup()
        logger.debug('%s build tracker %r',
                     'Removed' if remove else 'Cleaned',
                     self._root)

    @contextlib.contextmanager
    def track(self, req):
        # type: (InstallRequirement) -> Iterator[None]
        self.add(req)
        yield
        self.remove(req)
