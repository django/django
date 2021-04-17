from __future__ import absolute_import

import logging
import os
import shutil
import sys
import sysconfig
import zipfile
from distutils.util import change_root

from pip._vendor import pkg_resources, six
from pip._vendor.packaging.requirements import Requirement
from pip._vendor.packaging.utils import canonicalize_name
from pip._vendor.packaging.version import Version
from pip._vendor.packaging.version import parse as parse_version
from pip._vendor.pep517.wrappers import Pep517HookCaller

from pip._internal import wheel
from pip._internal.build_env import NoOpBuildEnvironment
from pip._internal.exceptions import InstallationError
from pip._internal.models.link import Link
from pip._internal.pyproject import load_pyproject_toml, make_pyproject_path
from pip._internal.req.req_uninstall import UninstallPathSet
from pip._internal.utils.compat import native_str
from pip._internal.utils.hashes import Hashes
from pip._internal.utils.logging import indent_log
from pip._internal.utils.marker_files import PIP_DELETE_MARKER_FILENAME
from pip._internal.utils.misc import (
    _make_build_dir, ask_path_exists, backup_dir, call_subprocess,
    display_path, dist_in_site_packages, dist_in_usersite, ensure_dir,
    get_installed_version, redact_password_from_url, rmtree,
)
from pip._internal.utils.packaging import get_metadata
from pip._internal.utils.setuptools_build import make_setuptools_shim_args
from pip._internal.utils.temp_dir import TempDirectory
from pip._internal.utils.typing import MYPY_CHECK_RUNNING
from pip._internal.utils.ui import open_spinner
from pip._internal.utils.virtualenv import running_under_virtualenv
from pip._internal.vcs import vcs

if MYPY_CHECK_RUNNING:
    from typing import (
        Any, Dict, Iterable, List, Mapping, Optional, Sequence, Union,
    )
    from pip._internal.build_env import BuildEnvironment
    from pip._internal.cache import WheelCache
    from pip._internal.index import PackageFinder
    from pip._vendor.pkg_resources import Distribution
    from pip._vendor.packaging.specifiers import SpecifierSet
    from pip._vendor.packaging.markers import Marker


logger = logging.getLogger(__name__)


class InstallRequirement(object):
    """
    Represents something that may be installed later on, may have information
    about where to fetch the relevant requirement and also contains logic for
    installing the said requirement.
    """

    def __init__(
        self,
        req,  # type: Optional[Requirement]
        comes_from,  # type: Optional[Union[str, InstallRequirement]]
        source_dir=None,  # type: Optional[str]
        editable=False,  # type: bool
        link=None,  # type: Optional[Link]
        update=True,  # type: bool
        markers=None,  # type: Optional[Marker]
        use_pep517=None,  # type: Optional[bool]
        isolated=False,  # type: bool
        options=None,  # type: Optional[Dict[str, Any]]
        wheel_cache=None,  # type: Optional[WheelCache]
        constraint=False,  # type: bool
        extras=()  # type: Iterable[str]
    ):
        # type: (...) -> None
        assert req is None or isinstance(req, Requirement), req
        self.req = req
        self.comes_from = comes_from
        self.constraint = constraint
        if source_dir is None:
            self.source_dir = None  # type: Optional[str]
        else:
            self.source_dir = os.path.normpath(os.path.abspath(source_dir))
        self.editable = editable

        self._wheel_cache = wheel_cache
        if link is None and req and req.url:
            # PEP 508 URL requirement
            link = Link(req.url)
        self.link = self.original_link = link

        if extras:
            self.extras = extras
        elif req:
            self.extras = {
                pkg_resources.safe_extra(extra) for extra in req.extras
            }
        else:
            self.extras = set()
        if markers is None and req:
            markers = req.marker
        self.markers = markers

        self._egg_info_path = None  # type: Optional[str]
        # This holds the pkg_resources.Distribution object if this requirement
        # is already available:
        self.satisfied_by = None
        # This hold the pkg_resources.Distribution object if this requirement
        # conflicts with another installed distribution:
        self.conflicts_with = None
        # Temporary build location
        self._temp_build_dir = TempDirectory(kind="req-build")
        # Used to store the global directory where the _temp_build_dir should
        # have been created. Cf _correct_build_location method.
        self._ideal_build_dir = None  # type: Optional[str]
        # True if the editable should be updated:
        self.update = update
        # Set to True after successful installation
        self.install_succeeded = None  # type: Optional[bool]
        # UninstallPathSet of uninstalled distribution (for possible rollback)
        self.uninstalled_pathset = None
        self.options = options if options else {}
        # Set to True after successful preparation of this requirement
        self.prepared = False
        self.is_direct = False

        self.isolated = isolated
        self.build_env = NoOpBuildEnvironment()  # type: BuildEnvironment

        # For PEP 517, the directory where we request the project metadata
        # gets stored. We need this to pass to build_wheel, so the backend
        # can ensure that the wheel matches the metadata (see the PEP for
        # details).
        self.metadata_directory = None  # type: Optional[str]

        # The static build requirements (from pyproject.toml)
        self.pyproject_requires = None  # type: Optional[List[str]]

        # Build requirements that we will check are available
        self.requirements_to_check = []  # type: List[str]

        # The PEP 517 backend we should use to build the project
        self.pep517_backend = None  # type: Optional[Pep517HookCaller]

        # Are we using PEP 517 for this requirement?
        # After pyproject.toml has been loaded, the only valid values are True
        # and False. Before loading, None is valid (meaning "use the default").
        # Setting an explicit value before loading pyproject.toml is supported,
        # but after loading this flag should be treated as read only.
        self.use_pep517 = use_pep517

    def __str__(self):
        # type: () -> str
        if self.req:
            s = str(self.req)
            if self.link:
                s += ' from %s' % redact_password_from_url(self.link.url)
        elif self.link:
            s = redact_password_from_url(self.link.url)
        else:
            s = '<InstallRequirement>'
        if self.satisfied_by is not None:
            s += ' in %s' % display_path(self.satisfied_by.location)
        if self.comes_from:
            if isinstance(self.comes_from, six.string_types):
                comes_from = self.comes_from  # type: Optional[str]
            else:
                comes_from = self.comes_from.from_path()
            if comes_from:
                s += ' (from %s)' % comes_from
        return s

    def __repr__(self):
        # type: () -> str
        return '<%s object: %s editable=%r>' % (
            self.__class__.__name__, str(self), self.editable)

    def format_debug(self):
        # type: () -> str
        """An un-tested helper for getting state, for debugging.
        """
        attributes = vars(self)
        names = sorted(attributes)

        state = (
            "{}={!r}".format(attr, attributes[attr]) for attr in sorted(names)
        )
        return '<{name} object: {{{state}}}>'.format(
            name=self.__class__.__name__,
            state=", ".join(state),
        )

    def populate_link(self, finder, upgrade, require_hashes):
        # type: (PackageFinder, bool, bool) -> None
        """Ensure that if a link can be found for this, that it is found.

        Note that self.link may still be None - if Upgrade is False and the
        requirement is already installed.

        If require_hashes is True, don't use the wheel cache, because cached
        wheels, always built locally, have different hashes than the files
        downloaded from the index server and thus throw false hash mismatches.
        Furthermore, cached wheels at present have undeterministic contents due
        to file modification times.
        """
        if self.link is None:
            self.link = finder.find_requirement(self, upgrade)
        if self._wheel_cache is not None and not require_hashes:
            old_link = self.link
            self.link = self._wheel_cache.get(self.link, self.name)
            if old_link != self.link:
                logger.debug('Using cached wheel link: %s', self.link)

    # Things that are valid for all kinds of requirements?
    @property
    def name(self):
        # type: () -> Optional[str]
        if self.req is None:
            return None
        return native_str(pkg_resources.safe_name(self.req.name))

    @property
    def specifier(self):
        # type: () -> SpecifierSet
        return self.req.specifier

    @property
    def is_pinned(self):
        # type: () -> bool
        """Return whether I am pinned to an exact version.

        For example, some-package==1.2 is pinned; some-package>1.2 is not.
        """
        specifiers = self.specifier
        return (len(specifiers) == 1 and
                next(iter(specifiers)).operator in {'==', '==='})

    @property
    def installed_version(self):
        # type: () -> Optional[str]
        return get_installed_version(self.name)

    def match_markers(self, extras_requested=None):
        # type: (Optional[Iterable[str]]) -> bool
        if not extras_requested:
            # Provide an extra to safely evaluate the markers
            # without matching any extra
            extras_requested = ('',)
        if self.markers is not None:
            return any(
                self.markers.evaluate({'extra': extra})
                for extra in extras_requested)
        else:
            return True

    @property
    def has_hash_options(self):
        # type: () -> bool
        """Return whether any known-good hashes are specified as options.

        These activate --require-hashes mode; hashes specified as part of a
        URL do not.

        """
        return bool(self.options.get('hashes', {}))

    def hashes(self, trust_internet=True):
        # type: (bool) -> Hashes
        """Return a hash-comparer that considers my option- and URL-based
        hashes to be known-good.

        Hashes in URLs--ones embedded in the requirements file, not ones
        downloaded from an index server--are almost peers with ones from
        flags. They satisfy --require-hashes (whether it was implicitly or
        explicitly activated) but do not activate it. md5 and sha224 are not
        allowed in flags, which should nudge people toward good algos. We
        always OR all hashes together, even ones from URLs.

        :param trust_internet: Whether to trust URL-based (#md5=...) hashes
            downloaded from the internet, as by populate_link()

        """
        good_hashes = self.options.get('hashes', {}).copy()
        link = self.link if trust_internet else self.original_link
        if link and link.hash:
            good_hashes.setdefault(link.hash_name, []).append(link.hash)
        return Hashes(good_hashes)

    def from_path(self):
        # type: () -> Optional[str]
        """Format a nice indicator to show where this "comes from"
        """
        if self.req is None:
            return None
        s = str(self.req)
        if self.comes_from:
            if isinstance(self.comes_from, six.string_types):
                comes_from = self.comes_from
            else:
                comes_from = self.comes_from.from_path()
            if comes_from:
                s += '->' + comes_from
        return s

    def build_location(self, build_dir):
        # type: (str) -> str
        assert build_dir is not None
        if self._temp_build_dir.path is not None:
            return self._temp_build_dir.path
        if self.req is None:
            # for requirement via a path to a directory: the name of the
            # package is not available yet so we create a temp directory
            # Once run_egg_info will have run, we'll be able
            # to fix it via _correct_build_location
            # Some systems have /tmp as a symlink which confuses custom
            # builds (such as numpy). Thus, we ensure that the real path
            # is returned.
            self._temp_build_dir.create()
            self._ideal_build_dir = build_dir

            return self._temp_build_dir.path
        if self.editable:
            name = self.name.lower()
        else:
            name = self.name
        # FIXME: Is there a better place to create the build_dir? (hg and bzr
        # need this)
        if not os.path.exists(build_dir):
            logger.debug('Creating directory %s', build_dir)
            _make_build_dir(build_dir)
        return os.path.join(build_dir, name)

    def _correct_build_location(self):
        # type: () -> None
        """Move self._temp_build_dir to self._ideal_build_dir/self.req.name

        For some requirements (e.g. a path to a directory), the name of the
        package is not available until we run egg_info, so the build_location
        will return a temporary directory and store the _ideal_build_dir.

        This is only called by self.run_egg_info to fix the temporary build
        directory.
        """
        if self.source_dir is not None:
            return
        assert self.req is not None
        assert self._temp_build_dir.path
        assert (self._ideal_build_dir is not None and
                self._ideal_build_dir.path)  # type: ignore
        old_location = self._temp_build_dir.path
        self._temp_build_dir.path = None

        new_location = self.build_location(self._ideal_build_dir)
        if os.path.exists(new_location):
            raise InstallationError(
                'A package already exists in %s; please remove it to continue'
                % display_path(new_location))
        logger.debug(
            'Moving package %s from %s to new location %s',
            self, display_path(old_location), display_path(new_location),
        )
        shutil.move(old_location, new_location)
        self._temp_build_dir.path = new_location
        self._ideal_build_dir = None
        self.source_dir = os.path.normpath(os.path.abspath(new_location))
        self._egg_info_path = None

        # Correct the metadata directory, if it exists
        if self.metadata_directory:
            old_meta = self.metadata_directory
            rel = os.path.relpath(old_meta, start=old_location)
            new_meta = os.path.join(new_location, rel)
            new_meta = os.path.normpath(os.path.abspath(new_meta))
            self.metadata_directory = new_meta

    def remove_temporary_source(self):
        # type: () -> None
        """Remove the source files from this requirement, if they are marked
        for deletion"""
        if self.source_dir and os.path.exists(
                os.path.join(self.source_dir, PIP_DELETE_MARKER_FILENAME)):
            logger.debug('Removing source in %s', self.source_dir)
            rmtree(self.source_dir)
        self.source_dir = None
        self._temp_build_dir.cleanup()
        self.build_env.cleanup()

    def check_if_exists(self, use_user_site):
        # type: (bool) -> bool
        """Find an installed distribution that satisfies or conflicts
        with this requirement, and set self.satisfied_by or
        self.conflicts_with appropriately.
        """
        if self.req is None:
            return False
        try:
            # get_distribution() will resolve the entire list of requirements
            # anyway, and we've already determined that we need the requirement
            # in question, so strip the marker so that we don't try to
            # evaluate it.
            no_marker = Requirement(str(self.req))
            no_marker.marker = None
            self.satisfied_by = pkg_resources.get_distribution(str(no_marker))
            if self.editable and self.satisfied_by:
                self.conflicts_with = self.satisfied_by
                # when installing editables, nothing pre-existing should ever
                # satisfy
                self.satisfied_by = None
                return True
        except pkg_resources.DistributionNotFound:
            return False
        except pkg_resources.VersionConflict:
            existing_dist = pkg_resources.get_distribution(
                self.req.name
            )
            if use_user_site:
                if dist_in_usersite(existing_dist):
                    self.conflicts_with = existing_dist
                elif (running_under_virtualenv() and
                        dist_in_site_packages(existing_dist)):
                    raise InstallationError(
                        "Will not install to the user site because it will "
                        "lack sys.path precedence to %s in %s" %
                        (existing_dist.project_name, existing_dist.location)
                    )
            else:
                self.conflicts_with = existing_dist
        return True

    # Things valid for wheels
    @property
    def is_wheel(self):
        # type: () -> bool
        if not self.link:
            return False
        return self.link.is_wheel

    def move_wheel_files(
        self,
        wheeldir,  # type: str
        root=None,  # type: Optional[str]
        home=None,  # type: Optional[str]
        prefix=None,  # type: Optional[str]
        warn_script_location=True,  # type: bool
        use_user_site=False,  # type: bool
        pycompile=True  # type: bool
    ):
        # type: (...) -> None
        wheel.move_wheel_files(
            self.name, self.req, wheeldir,
            user=use_user_site,
            home=home,
            root=root,
            prefix=prefix,
            pycompile=pycompile,
            isolated=self.isolated,
            warn_script_location=warn_script_location,
        )

    # Things valid for sdists
    @property
    def setup_py_dir(self):
        # type: () -> str
        return os.path.join(
            self.source_dir,
            self.link and self.link.subdirectory_fragment or '')

    @property
    def setup_py_path(self):
        # type: () -> str
        assert self.source_dir, "No source dir for %s" % self

        setup_py = os.path.join(self.setup_py_dir, 'setup.py')

        # Python2 __file__ should not be unicode
        if six.PY2 and isinstance(setup_py, six.text_type):
            setup_py = setup_py.encode(sys.getfilesystemencoding())

        return setup_py

    @property
    def pyproject_toml_path(self):
        # type: () -> str
        assert self.source_dir, "No source dir for %s" % self

        return make_pyproject_path(self.setup_py_dir)

    def load_pyproject_toml(self):
        # type: () -> None
        """Load the pyproject.toml file.

        After calling this routine, all of the attributes related to PEP 517
        processing for this requirement have been set. In particular, the
        use_pep517 attribute can be used to determine whether we should
        follow the PEP 517 or legacy (setup.py) code path.
        """
        pyproject_toml_data = load_pyproject_toml(
            self.use_pep517,
            self.pyproject_toml_path,
            self.setup_py_path,
            str(self)
        )

        self.use_pep517 = (pyproject_toml_data is not None)

        if not self.use_pep517:
            return

        requires, backend, check = pyproject_toml_data
        self.requirements_to_check = check
        self.pyproject_requires = requires
        self.pep517_backend = Pep517HookCaller(self.setup_py_dir, backend)

        # Use a custom function to call subprocesses
        self.spin_message = ""

        def runner(
            cmd,  # type: List[str]
            cwd=None,  # type: Optional[str]
            extra_environ=None  # type: Optional[Mapping[str, Any]]
        ):
            # type: (...) -> None
            with open_spinner(self.spin_message) as spinner:
                call_subprocess(
                    cmd,
                    cwd=cwd,
                    extra_environ=extra_environ,
                    spinner=spinner
                )
            self.spin_message = ""

        self.pep517_backend._subprocess_runner = runner

    def prepare_metadata(self):
        # type: () -> None
        """Ensure that project metadata is available.

        Under PEP 517, call the backend hook to prepare the metadata.
        Under legacy processing, call setup.py egg-info.
        """
        assert self.source_dir

        with indent_log():
            if self.use_pep517:
                self.prepare_pep517_metadata()
            else:
                self.run_egg_info()

        if not self.req:
            if isinstance(parse_version(self.metadata["Version"]), Version):
                op = "=="
            else:
                op = "==="
            self.req = Requirement(
                "".join([
                    self.metadata["Name"],
                    op,
                    self.metadata["Version"],
                ])
            )
            self._correct_build_location()
        else:
            metadata_name = canonicalize_name(self.metadata["Name"])
            if canonicalize_name(self.req.name) != metadata_name:
                logger.warning(
                    'Generating metadata for package %s '
                    'produced metadata for project name %s. Fix your '
                    '#egg=%s fragments.',
                    self.name, metadata_name, self.name
                )
                self.req = Requirement(metadata_name)

    def prepare_pep517_metadata(self):
        # type: () -> None
        assert self.pep517_backend is not None

        metadata_dir = os.path.join(
            self.setup_py_dir,
            'pip-wheel-metadata'
        )
        ensure_dir(metadata_dir)

        with self.build_env:
            # Note that Pep517HookCaller implements a fallback for
            # prepare_metadata_for_build_wheel, so we don't have to
            # consider the possibility that this hook doesn't exist.
            backend = self.pep517_backend
            self.spin_message = "Preparing wheel metadata"
            distinfo_dir = backend.prepare_metadata_for_build_wheel(
                metadata_dir
            )

        self.metadata_directory = os.path.join(metadata_dir, distinfo_dir)

    def run_egg_info(self):
        # type: () -> None
        if self.name:
            logger.debug(
                'Running setup.py (path:%s) egg_info for package %s',
                self.setup_py_path, self.name,
            )
        else:
            logger.debug(
                'Running setup.py (path:%s) egg_info for package from %s',
                self.setup_py_path, self.link,
            )
        base_cmd = make_setuptools_shim_args(self.setup_py_path)
        if self.isolated:
            base_cmd += ["--no-user-cfg"]
        egg_info_cmd = base_cmd + ['egg_info']
        # We can't put the .egg-info files at the root, because then the
        # source code will be mistaken for an installed egg, causing
        # problems
        if self.editable:
            egg_base_option = []  # type: List[str]
        else:
            egg_info_dir = os.path.join(self.setup_py_dir, 'pip-egg-info')
            ensure_dir(egg_info_dir)
            egg_base_option = ['--egg-base', 'pip-egg-info']
        with self.build_env:
            call_subprocess(
                egg_info_cmd + egg_base_option,
                cwd=self.setup_py_dir,
                command_desc='python setup.py egg_info')

    @property
    def egg_info_path(self):
        # type: () -> str
        if self._egg_info_path is None:
            if self.editable:
                base = self.source_dir
            else:
                base = os.path.join(self.setup_py_dir, 'pip-egg-info')
            filenames = os.listdir(base)
            if self.editable:
                filenames = []
                for root, dirs, files in os.walk(base):
                    for dir in vcs.dirnames:
                        if dir in dirs:
                            dirs.remove(dir)
                    # Iterate over a copy of ``dirs``, since mutating
                    # a list while iterating over it can cause trouble.
                    # (See https://github.com/pypa/pip/pull/462.)
                    for dir in list(dirs):
                        # Don't search in anything that looks like a virtualenv
                        # environment
                        if (
                                os.path.lexists(
                                    os.path.join(root, dir, 'bin', 'python')
                                ) or
                                os.path.exists(
                                    os.path.join(
                                        root, dir, 'Scripts', 'Python.exe'
                                    )
                                )):
                            dirs.remove(dir)
                        # Also don't search through tests
                        elif dir == 'test' or dir == 'tests':
                            dirs.remove(dir)
                    filenames.extend([os.path.join(root, dir)
                                      for dir in dirs])
                filenames = [f for f in filenames if f.endswith('.egg-info')]

            if not filenames:
                raise InstallationError(
                    "Files/directories not found in %s" % base
                )
            # if we have more than one match, we pick the toplevel one.  This
            # can easily be the case if there is a dist folder which contains
            # an extracted tarball for testing purposes.
            if len(filenames) > 1:
                filenames.sort(
                    key=lambda x: x.count(os.path.sep) +
                    (os.path.altsep and x.count(os.path.altsep) or 0)
                )
            self._egg_info_path = os.path.join(base, filenames[0])
        return self._egg_info_path

    @property
    def metadata(self):
        # type: () -> Any
        if not hasattr(self, '_metadata'):
            self._metadata = get_metadata(self.get_dist())

        return self._metadata

    def get_dist(self):
        # type: () -> Distribution
        """Return a pkg_resources.Distribution for this requirement"""
        if self.metadata_directory:
            dist_dir = self.metadata_directory
            dist_cls = pkg_resources.DistInfoDistribution
        else:
            dist_dir = self.egg_info_path.rstrip(os.path.sep)
            # https://github.com/python/mypy/issues/1174
            dist_cls = pkg_resources.Distribution  # type: ignore

        # dist_dir_name can be of the form "<project>.dist-info" or
        # e.g. "<project>.egg-info".
        base_dir, dist_dir_name = os.path.split(dist_dir)
        dist_name = os.path.splitext(dist_dir_name)[0]
        metadata = pkg_resources.PathMetadata(base_dir, dist_dir)

        return dist_cls(
            base_dir,
            project_name=dist_name,
            metadata=metadata,
        )

    def assert_source_matches_version(self):
        # type: () -> None
        assert self.source_dir
        version = self.metadata['version']
        if self.req.specifier and version not in self.req.specifier:
            logger.warning(
                'Requested %s, but installing version %s',
                self,
                version,
            )
        else:
            logger.debug(
                'Source in %s has version %s, which satisfies requirement %s',
                display_path(self.source_dir),
                version,
                self,
            )

    # For both source distributions and editables
    def ensure_has_source_dir(self, parent_dir):
        # type: (str) -> str
        """Ensure that a source_dir is set.

        This will create a temporary build dir if the name of the requirement
        isn't known yet.

        :param parent_dir: The ideal pip parent_dir for the source_dir.
            Generally src_dir for editables and build_dir for sdists.
        :return: self.source_dir
        """
        if self.source_dir is None:
            self.source_dir = self.build_location(parent_dir)
        return self.source_dir

    # For editable installations
    def install_editable(
        self,
        install_options,  # type: List[str]
        global_options=(),  # type: Sequence[str]
        prefix=None  # type: Optional[str]
    ):
        # type: (...) -> None
        logger.info('Running setup.py develop for %s', self.name)

        if self.isolated:
            global_options = list(global_options) + ["--no-user-cfg"]

        if prefix:
            prefix_param = ['--prefix={}'.format(prefix)]
            install_options = list(install_options) + prefix_param

        with indent_log():
            # FIXME: should we do --install-headers here too?
            with self.build_env:
                call_subprocess(
                    make_setuptools_shim_args(self.setup_py_path) +
                    list(global_options) +
                    ['develop', '--no-deps'] +
                    list(install_options),

                    cwd=self.setup_py_dir,
                )

        self.install_succeeded = True

    def update_editable(self, obtain=True):
        # type: (bool) -> None
        if not self.link:
            logger.debug(
                "Cannot update repository at %s; repository location is "
                "unknown",
                self.source_dir,
            )
            return
        assert self.editable
        assert self.source_dir
        if self.link.scheme == 'file':
            # Static paths don't get updated
            return
        assert '+' in self.link.url, "bad url: %r" % self.link.url
        if not self.update:
            return
        vc_type, url = self.link.url.split('+', 1)
        vcs_backend = vcs.get_backend(vc_type)
        if vcs_backend:
            url = self.link.url
            if obtain:
                vcs_backend.obtain(self.source_dir, url=url)
            else:
                vcs_backend.export(self.source_dir, url=url)
        else:
            assert 0, (
                'Unexpected version control type (in %s): %s'
                % (self.link, vc_type))

    # Top-level Actions
    def uninstall(self, auto_confirm=False, verbose=False,
                  use_user_site=False):
        # type: (bool, bool, bool) -> Optional[UninstallPathSet]
        """
        Uninstall the distribution currently satisfying this requirement.

        Prompts before removing or modifying files unless
        ``auto_confirm`` is True.

        Refuses to delete or modify files outside of ``sys.prefix`` -
        thus uninstallation within a virtual environment can only
        modify that virtual environment, even if the virtualenv is
        linked to global site-packages.

        """
        if not self.check_if_exists(use_user_site):
            logger.warning("Skipping %s as it is not installed.", self.name)
            return None
        dist = self.satisfied_by or self.conflicts_with

        uninstalled_pathset = UninstallPathSet.from_dist(dist)
        uninstalled_pathset.remove(auto_confirm, verbose)
        return uninstalled_pathset

    def _clean_zip_name(self, name, prefix):  # only used by archive.
        # type: (str, str) -> str
        assert name.startswith(prefix + os.path.sep), (
            "name %r doesn't start with prefix %r" % (name, prefix)
        )
        name = name[len(prefix) + 1:]
        name = name.replace(os.path.sep, '/')
        return name

    def _get_archive_name(self, path, parentdir, rootdir):
        # type: (str, str, str) -> str
        path = os.path.join(parentdir, path)
        name = self._clean_zip_name(path, rootdir)
        return self.name + '/' + name

    # TODO: Investigate if this should be kept in InstallRequirement
    #       Seems to be used only when VCS + downloads
    def archive(self, build_dir):
        # type: (str) -> None
        assert self.source_dir
        create_archive = True
        archive_name = '%s-%s.zip' % (self.name, self.metadata["version"])
        archive_path = os.path.join(build_dir, archive_name)
        if os.path.exists(archive_path):
            response = ask_path_exists(
                'The file %s exists. (i)gnore, (w)ipe, (b)ackup, (a)bort ' %
                display_path(archive_path), ('i', 'w', 'b', 'a'))
            if response == 'i':
                create_archive = False
            elif response == 'w':
                logger.warning('Deleting %s', display_path(archive_path))
                os.remove(archive_path)
            elif response == 'b':
                dest_file = backup_dir(archive_path)
                logger.warning(
                    'Backing up %s to %s',
                    display_path(archive_path),
                    display_path(dest_file),
                )
                shutil.move(archive_path, dest_file)
            elif response == 'a':
                sys.exit(-1)
        if create_archive:
            zip = zipfile.ZipFile(
                archive_path, 'w', zipfile.ZIP_DEFLATED,
                allowZip64=True
            )
            dir = os.path.normcase(os.path.abspath(self.setup_py_dir))
            for dirpath, dirnames, filenames in os.walk(dir):
                if 'pip-egg-info' in dirnames:
                    dirnames.remove('pip-egg-info')
                for dirname in dirnames:
                    dir_arcname = self._get_archive_name(dirname,
                                                         parentdir=dirpath,
                                                         rootdir=dir)
                    zipdir = zipfile.ZipInfo(dir_arcname + '/')
                    zipdir.external_attr = 0x1ED << 16  # 0o755
                    zip.writestr(zipdir, '')
                for filename in filenames:
                    if filename == PIP_DELETE_MARKER_FILENAME:
                        continue
                    file_arcname = self._get_archive_name(filename,
                                                          parentdir=dirpath,
                                                          rootdir=dir)
                    filename = os.path.join(dirpath, filename)
                    zip.write(filename, file_arcname)
            zip.close()
            logger.info('Saved %s', display_path(archive_path))

    def install(
        self,
        install_options,  # type: List[str]
        global_options=None,  # type: Optional[Sequence[str]]
        root=None,  # type: Optional[str]
        home=None,  # type: Optional[str]
        prefix=None,  # type: Optional[str]
        warn_script_location=True,  # type: bool
        use_user_site=False,  # type: bool
        pycompile=True  # type: bool
    ):
        # type: (...) -> None
        global_options = global_options if global_options is not None else []
        if self.editable:
            self.install_editable(
                install_options, global_options, prefix=prefix,
            )
            return
        if self.is_wheel:
            version = wheel.wheel_version(self.source_dir)
            wheel.check_compatibility(version, self.name)

            self.move_wheel_files(
                self.source_dir, root=root, prefix=prefix, home=home,
                warn_script_location=warn_script_location,
                use_user_site=use_user_site, pycompile=pycompile,
            )
            self.install_succeeded = True
            return

        # Extend the list of global and install options passed on to
        # the setup.py call with the ones from the requirements file.
        # Options specified in requirements file override those
        # specified on the command line, since the last option given
        # to setup.py is the one that is used.
        global_options = list(global_options) + \
            self.options.get('global_options', [])
        install_options = list(install_options) + \
            self.options.get('install_options', [])

        if self.isolated:
            # https://github.com/python/mypy/issues/1174
            global_options = global_options + ["--no-user-cfg"]  # type: ignore

        with TempDirectory(kind="record") as temp_dir:
            record_filename = os.path.join(temp_dir.path, 'install-record.txt')
            install_args = self.get_install_args(
                global_options, record_filename, root, prefix, pycompile,
            )
            msg = 'Running setup.py install for %s' % (self.name,)
            with open_spinner(msg) as spinner:
                with indent_log():
                    with self.build_env:
                        call_subprocess(
                            install_args + install_options,
                            cwd=self.setup_py_dir,
                            spinner=spinner,
                        )

            if not os.path.exists(record_filename):
                logger.debug('Record file %s not found', record_filename)
                return
            self.install_succeeded = True

            def prepend_root(path):
                # type: (str) -> str
                if root is None or not os.path.isabs(path):
                    return path
                else:
                    return change_root(root, path)

            with open(record_filename) as f:
                for line in f:
                    directory = os.path.dirname(line)
                    if directory.endswith('.egg-info'):
                        egg_info_dir = prepend_root(directory)
                        break
                else:
                    logger.warning(
                        'Could not find .egg-info directory in install record'
                        ' for %s',
                        self,
                    )
                    # FIXME: put the record somewhere
                    # FIXME: should this be an error?
                    return
            new_lines = []
            with open(record_filename) as f:
                for line in f:
                    filename = line.strip()
                    if os.path.isdir(filename):
                        filename += os.path.sep
                    new_lines.append(
                        os.path.relpath(prepend_root(filename), egg_info_dir)
                    )
            new_lines.sort()
            ensure_dir(egg_info_dir)
            inst_files_path = os.path.join(egg_info_dir, 'installed-files.txt')
            with open(inst_files_path, 'w') as f:
                f.write('\n'.join(new_lines) + '\n')

    def get_install_args(
        self,
        global_options,  # type: Sequence[str]
        record_filename,  # type: str
        root,  # type: Optional[str]
        prefix,  # type: Optional[str]
        pycompile  # type: bool
    ):
        # type: (...) -> List[str]
        install_args = make_setuptools_shim_args(self.setup_py_path,
                                                 unbuffered_output=True)
        install_args += list(global_options) + \
            ['install', '--record', record_filename]
        install_args += ['--single-version-externally-managed']

        if root is not None:
            install_args += ['--root', root]
        if prefix is not None:
            install_args += ['--prefix', prefix]

        if pycompile:
            install_args += ["--compile"]
        else:
            install_args += ["--no-compile"]

        if running_under_virtualenv():
            py_ver_str = 'python' + sysconfig.get_python_version()
            install_args += ['--install-headers',
                             os.path.join(sys.prefix, 'include', 'site',
                                          py_ver_str, self.name)]

        return install_args
