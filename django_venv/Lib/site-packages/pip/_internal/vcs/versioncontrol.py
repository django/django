"""Handles all VCS (version control) support"""
from __future__ import absolute_import

import errno
import logging
import os
import shutil
import sys

from pip._vendor import pkg_resources
from pip._vendor.six.moves.urllib import parse as urllib_parse

from pip._internal.exceptions import BadCommand
from pip._internal.utils.misc import (
    ask_path_exists, backup_dir, call_subprocess, display_path, rmtree,
)
from pip._internal.utils.typing import MYPY_CHECK_RUNNING

if MYPY_CHECK_RUNNING:
    from typing import (
        Any, Dict, Iterable, List, Mapping, Optional, Text, Tuple, Type
    )
    from pip._internal.utils.ui import SpinnerInterface

    AuthInfo = Tuple[Optional[str], Optional[str]]

__all__ = ['vcs']


logger = logging.getLogger(__name__)


def make_vcs_requirement_url(repo_url, rev, project_name, subdir=None):
    """
    Return the URL for a VCS requirement.

    Args:
      repo_url: the remote VCS url, with any needed VCS prefix (e.g. "git+").
      project_name: the (unescaped) project name.
    """
    egg_project_name = pkg_resources.to_filename(project_name)
    req = '{}@{}#egg={}'.format(repo_url, rev, egg_project_name)
    if subdir:
        req += '&subdirectory={}'.format(subdir)

    return req


class RemoteNotFoundError(Exception):
    pass


class RevOptions(object):

    """
    Encapsulates a VCS-specific revision to install, along with any VCS
    install options.

    Instances of this class should be treated as if immutable.
    """

    def __init__(
        self,
        vc_class,  # type: Type[VersionControl]
        rev=None,  # type: Optional[str]
        extra_args=None,  # type: Optional[List[str]]
    ):
        # type: (...) -> None
        """
        Args:
          vc_class: a VersionControl subclass.
          rev: the name of the revision to install.
          extra_args: a list of extra options.
        """
        if extra_args is None:
            extra_args = []

        self.extra_args = extra_args
        self.rev = rev
        self.vc_class = vc_class

    def __repr__(self):
        return '<RevOptions {}: rev={!r}>'.format(self.vc_class.name, self.rev)

    @property
    def arg_rev(self):
        # type: () -> Optional[str]
        if self.rev is None:
            return self.vc_class.default_arg_rev

        return self.rev

    def to_args(self):
        # type: () -> List[str]
        """
        Return the VCS-specific command arguments.
        """
        args = []  # type: List[str]
        rev = self.arg_rev
        if rev is not None:
            args += self.vc_class.get_base_rev_args(rev)
        args += self.extra_args

        return args

    def to_display(self):
        # type: () -> str
        if not self.rev:
            return ''

        return ' (to revision {})'.format(self.rev)

    def make_new(self, rev):
        # type: (str) -> RevOptions
        """
        Make a copy of the current instance, but with a new rev.

        Args:
          rev: the name of the revision for the new object.
        """
        return self.vc_class.make_rev_options(rev, extra_args=self.extra_args)


class VcsSupport(object):
    _registry = {}  # type: Dict[str, VersionControl]
    schemes = ['ssh', 'git', 'hg', 'bzr', 'sftp', 'svn']

    def __init__(self):
        # type: () -> None
        # Register more schemes with urlparse for various version control
        # systems
        urllib_parse.uses_netloc.extend(self.schemes)
        # Python >= 2.7.4, 3.3 doesn't have uses_fragment
        if getattr(urllib_parse, 'uses_fragment', None):
            urllib_parse.uses_fragment.extend(self.schemes)
        super(VcsSupport, self).__init__()

    def __iter__(self):
        return self._registry.__iter__()

    @property
    def backends(self):
        # type: () -> List[VersionControl]
        return list(self._registry.values())

    @property
    def dirnames(self):
        # type: () -> List[str]
        return [backend.dirname for backend in self.backends]

    @property
    def all_schemes(self):
        # type: () -> List[str]
        schemes = []  # type: List[str]
        for backend in self.backends:
            schemes.extend(backend.schemes)
        return schemes

    def register(self, cls):
        # type: (Type[VersionControl]) -> None
        if not hasattr(cls, 'name'):
            logger.warning('Cannot register VCS %s', cls.__name__)
            return
        if cls.name not in self._registry:
            self._registry[cls.name] = cls()
            logger.debug('Registered VCS backend: %s', cls.name)

    def unregister(self, name):
        # type: (str) -> None
        if name in self._registry:
            del self._registry[name]

    def get_backend_for_dir(self, location):
        # type: (str) -> Optional[VersionControl]
        """
        Return a VersionControl object if a repository of that type is found
        at the given directory.
        """
        for vcs_backend in self._registry.values():
            if vcs_backend.controls_location(location):
                logger.debug('Determine that %s uses VCS: %s',
                             location, vcs_backend.name)
                return vcs_backend
        return None

    def get_backend(self, name):
        # type: (str) -> Optional[VersionControl]
        """
        Return a VersionControl object or None.
        """
        name = name.lower()
        return self._registry.get(name)


vcs = VcsSupport()


class VersionControl(object):
    name = ''
    dirname = ''
    repo_name = ''
    # List of supported schemes for this Version Control
    schemes = ()  # type: Tuple[str, ...]
    # Iterable of environment variable names to pass to call_subprocess().
    unset_environ = ()  # type: Tuple[str, ...]
    default_arg_rev = None  # type: Optional[str]

    @classmethod
    def should_add_vcs_url_prefix(cls, remote_url):
        """
        Return whether the vcs prefix (e.g. "git+") should be added to a
        repository's remote url when used in a requirement.
        """
        return not remote_url.lower().startswith('{}:'.format(cls.name))

    @classmethod
    def get_subdirectory(cls, repo_dir):
        """
        Return the path to setup.py, relative to the repo root.
        """
        return None

    @classmethod
    def get_requirement_revision(cls, repo_dir):
        """
        Return the revision string that should be used in a requirement.
        """
        return cls.get_revision(repo_dir)

    @classmethod
    def get_src_requirement(cls, repo_dir, project_name):
        """
        Return the requirement string to use to redownload the files
        currently at the given repository directory.

        Args:
          project_name: the (unescaped) project name.

        The return value has a form similar to the following:

            {repository_url}@{revision}#egg={project_name}
        """
        repo_url = cls.get_remote_url(repo_dir)
        if repo_url is None:
            return None

        if cls.should_add_vcs_url_prefix(repo_url):
            repo_url = '{}+{}'.format(cls.name, repo_url)

        revision = cls.get_requirement_revision(repo_dir)
        subdir = cls.get_subdirectory(repo_dir)
        req = make_vcs_requirement_url(repo_url, revision, project_name,
                                       subdir=subdir)

        return req

    @staticmethod
    def get_base_rev_args(rev):
        """
        Return the base revision arguments for a vcs command.

        Args:
          rev: the name of a revision to install.  Cannot be None.
        """
        raise NotImplementedError

    @classmethod
    def make_rev_options(cls, rev=None, extra_args=None):
        # type: (Optional[str], Optional[List[str]]) -> RevOptions
        """
        Return a RevOptions object.

        Args:
          rev: the name of a revision to install.
          extra_args: a list of extra options.
        """
        return RevOptions(cls, rev, extra_args=extra_args)

    @classmethod
    def _is_local_repository(cls, repo):
        # type: (str) -> bool
        """
           posix absolute paths start with os.path.sep,
           win32 ones start with drive (like c:\\folder)
        """
        drive, tail = os.path.splitdrive(repo)
        return repo.startswith(os.path.sep) or bool(drive)

    def export(self, location, url):
        """
        Export the repository at the url to the destination location
        i.e. only download the files, without vcs informations

        :param url: the repository URL starting with a vcs prefix.
        """
        raise NotImplementedError

    @classmethod
    def get_netloc_and_auth(cls, netloc, scheme):
        """
        Parse the repository URL's netloc, and return the new netloc to use
        along with auth information.

        Args:
          netloc: the original repository URL netloc.
          scheme: the repository URL's scheme without the vcs prefix.

        This is mainly for the Subversion class to override, so that auth
        information can be provided via the --username and --password options
        instead of through the URL.  For other subclasses like Git without
        such an option, auth information must stay in the URL.

        Returns: (netloc, (username, password)).
        """
        return netloc, (None, None)

    @classmethod
    def get_url_rev_and_auth(cls, url):
        # type: (str) -> Tuple[str, Optional[str], AuthInfo]
        """
        Parse the repository URL to use, and return the URL, revision,
        and auth info to use.

        Returns: (url, rev, (username, password)).
        """
        scheme, netloc, path, query, frag = urllib_parse.urlsplit(url)
        if '+' not in scheme:
            raise ValueError(
                "Sorry, {!r} is a malformed VCS url. "
                "The format is <vcs>+<protocol>://<url>, "
                "e.g. svn+http://myrepo/svn/MyApp#egg=MyApp".format(url)
            )
        # Remove the vcs prefix.
        scheme = scheme.split('+', 1)[1]
        netloc, user_pass = cls.get_netloc_and_auth(netloc, scheme)
        rev = None
        if '@' in path:
            path, rev = path.rsplit('@', 1)
        url = urllib_parse.urlunsplit((scheme, netloc, path, query, ''))
        return url, rev, user_pass

    @staticmethod
    def make_rev_args(username, password):
        """
        Return the RevOptions "extra arguments" to use in obtain().
        """
        return []

    def get_url_rev_options(self, url):
        # type: (str) -> Tuple[str, RevOptions]
        """
        Return the URL and RevOptions object to use in obtain() and in
        some cases export(), as a tuple (url, rev_options).
        """
        url, rev, user_pass = self.get_url_rev_and_auth(url)
        username, password = user_pass
        extra_args = self.make_rev_args(username, password)
        rev_options = self.make_rev_options(rev, extra_args=extra_args)

        return url, rev_options

    @staticmethod
    def normalize_url(url):
        # type: (str) -> str
        """
        Normalize a URL for comparison by unquoting it and removing any
        trailing slash.
        """
        return urllib_parse.unquote(url).rstrip('/')

    @classmethod
    def compare_urls(cls, url1, url2):
        # type: (str, str) -> bool
        """
        Compare two repo URLs for identity, ignoring incidental differences.
        """
        return (cls.normalize_url(url1) == cls.normalize_url(url2))

    def fetch_new(self, dest, url, rev_options):
        """
        Fetch a revision from a repository, in the case that this is the
        first fetch from the repository.

        Args:
          dest: the directory to fetch the repository to.
          rev_options: a RevOptions object.
        """
        raise NotImplementedError

    def switch(self, dest, url, rev_options):
        """
        Switch the repo at ``dest`` to point to ``URL``.

        Args:
          rev_options: a RevOptions object.
        """
        raise NotImplementedError

    def update(self, dest, url, rev_options):
        """
        Update an already-existing repo to the given ``rev_options``.

        Args:
          rev_options: a RevOptions object.
        """
        raise NotImplementedError

    @classmethod
    def is_commit_id_equal(cls, dest, name):
        """
        Return whether the id of the current commit equals the given name.

        Args:
          dest: the repository directory.
          name: a string name.
        """
        raise NotImplementedError

    def obtain(self, dest, url):
        # type: (str, str) -> None
        """
        Install or update in editable mode the package represented by this
        VersionControl object.

        :param dest: the repository directory in which to install or update.
        :param url: the repository URL starting with a vcs prefix.
        """
        url, rev_options = self.get_url_rev_options(url)

        if not os.path.exists(dest):
            self.fetch_new(dest, url, rev_options)
            return

        rev_display = rev_options.to_display()
        if self.is_repository_directory(dest):
            existing_url = self.get_remote_url(dest)
            if self.compare_urls(existing_url, url):
                logger.debug(
                    '%s in %s exists, and has correct URL (%s)',
                    self.repo_name.title(),
                    display_path(dest),
                    url,
                )
                if not self.is_commit_id_equal(dest, rev_options.rev):
                    logger.info(
                        'Updating %s %s%s',
                        display_path(dest),
                        self.repo_name,
                        rev_display,
                    )
                    self.update(dest, url, rev_options)
                else:
                    logger.info('Skipping because already up-to-date.')
                return

            logger.warning(
                '%s %s in %s exists with URL %s',
                self.name,
                self.repo_name,
                display_path(dest),
                existing_url,
            )
            prompt = ('(s)witch, (i)gnore, (w)ipe, (b)ackup ',
                      ('s', 'i', 'w', 'b'))
        else:
            logger.warning(
                'Directory %s already exists, and is not a %s %s.',
                dest,
                self.name,
                self.repo_name,
            )
            # https://github.com/python/mypy/issues/1174
            prompt = ('(i)gnore, (w)ipe, (b)ackup ',  # type: ignore
                      ('i', 'w', 'b'))

        logger.warning(
            'The plan is to install the %s repository %s',
            self.name,
            url,
        )
        response = ask_path_exists('What to do?  %s' % prompt[0], prompt[1])

        if response == 'a':
            sys.exit(-1)

        if response == 'w':
            logger.warning('Deleting %s', display_path(dest))
            rmtree(dest)
            self.fetch_new(dest, url, rev_options)
            return

        if response == 'b':
            dest_dir = backup_dir(dest)
            logger.warning(
                'Backing up %s to %s', display_path(dest), dest_dir,
            )
            shutil.move(dest, dest_dir)
            self.fetch_new(dest, url, rev_options)
            return

        # Do nothing if the response is "i".
        if response == 's':
            logger.info(
                'Switching %s %s to %s%s',
                self.repo_name,
                display_path(dest),
                url,
                rev_display,
            )
            self.switch(dest, url, rev_options)

    def unpack(self, location, url):
        # type: (str, str) -> None
        """
        Clean up current location and download the url repository
        (and vcs infos) into location

        :param url: the repository URL starting with a vcs prefix.
        """
        if os.path.exists(location):
            rmtree(location)
        self.obtain(location, url=url)

    @classmethod
    def get_remote_url(cls, location):
        """
        Return the url used at location

        Raises RemoteNotFoundError if the repository does not have a remote
        url configured.
        """
        raise NotImplementedError

    @classmethod
    def get_revision(cls, location):
        """
        Return the current commit id of the files at the given location.
        """
        raise NotImplementedError

    @classmethod
    def run_command(
        cls,
        cmd,  # type: List[str]
        show_stdout=True,  # type: bool
        cwd=None,  # type: Optional[str]
        on_returncode='raise',  # type: str
        extra_ok_returncodes=None,  # type: Optional[Iterable[int]]
        command_desc=None,  # type: Optional[str]
        extra_environ=None,  # type: Optional[Mapping[str, Any]]
        spinner=None  # type: Optional[SpinnerInterface]
    ):
        # type: (...) -> Text
        """
        Run a VCS subcommand
        This is simply a wrapper around call_subprocess that adds the VCS
        command name, and checks that the VCS is available
        """
        cmd = [cls.name] + cmd
        try:
            return call_subprocess(cmd, show_stdout, cwd,
                                   on_returncode=on_returncode,
                                   extra_ok_returncodes=extra_ok_returncodes,
                                   command_desc=command_desc,
                                   extra_environ=extra_environ,
                                   unset_environ=cls.unset_environ,
                                   spinner=spinner)
        except OSError as e:
            # errno.ENOENT = no such file or directory
            # In other words, the VCS executable isn't available
            if e.errno == errno.ENOENT:
                raise BadCommand(
                    'Cannot find command %r - do you have '
                    '%r installed and in your '
                    'PATH?' % (cls.name, cls.name))
            else:
                raise  # re-raise exception if a different error occurred

    @classmethod
    def is_repository_directory(cls, path):
        # type: (str) -> bool
        """
        Return whether a directory path is a repository directory.
        """
        logger.debug('Checking in %s for %s (%s)...',
                     path, cls.dirname, cls.name)
        return os.path.exists(os.path.join(path, cls.dirname))

    @classmethod
    def controls_location(cls, location):
        # type: (str) -> bool
        """
        Check if a location is controlled by the vcs.
        It is meant to be overridden to implement smarter detection
        mechanisms for specific vcs.

        This can do more than is_repository_directory() alone.  For example,
        the Git override checks that Git is actually available.
        """
        return cls.is_repository_directory(location)
