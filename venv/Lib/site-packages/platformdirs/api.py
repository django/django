"""Base API."""

from __future__ import annotations

import os
from abc import ABC, abstractmethod
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Iterator
    from typing import Literal


class PlatformDirsABC(ABC):  # noqa: PLR0904
    """Abstract base class defining all platform directory properties, their :class:`~pathlib.Path` variants, and iterators.

    Platform-specific subclasses (e.g. :class:`~platformdirs.windows.Windows`, :class:`~platformdirs.macos.MacOS`,
    :class:`~platformdirs.unix.Unix`) implement the abstract properties to return the appropriate paths for each
    operating system.

    """

    def __init__(  # noqa: PLR0913, PLR0917
        self,
        appname: str | None = None,
        appauthor: str | Literal[False] | None = None,
        version: str | None = None,
        roaming: bool = False,  # noqa: FBT001, FBT002
        multipath: bool = False,  # noqa: FBT001, FBT002
        opinion: bool = True,  # noqa: FBT001, FBT002
        ensure_exists: bool = False,  # noqa: FBT001, FBT002
        use_site_for_root: bool = False,  # noqa: FBT001, FBT002
    ) -> None:
        """Create a new platform directory.

        :param appname: See `appname`.
        :param appauthor: See `appauthor`.
        :param version: See `version`.
        :param roaming: See `roaming`.
        :param multipath: See `multipath`.
        :param opinion: See `opinion`.
        :param ensure_exists: See `ensure_exists`.
        :param use_site_for_root: See `use_site_for_root`.

        """
        self.appname = appname  #: The name of the application.
        self.appauthor = appauthor
        """The name of the app author or distributing body for this application.

        Typically, it is the owning company name. Defaults to `appname`. You may pass ``False`` to disable it.

        """
        self.version = version
        """An optional version path element to append to the path.

        You might want to use this if you want multiple versions of your app to be able to run independently. If used,
        this would typically be ``<major>.<minor>``.

        """
        self.roaming = roaming
        """Whether to use the roaming appdata directory on Windows.

        That means that for users on a Windows network setup for roaming profiles, this user data will be synced on
        login (see `here <https://technet.microsoft.com/en-us/library/cc766489(WS.10).aspx>`_).

        """
        self.multipath = multipath
        """An optional parameter which indicates that the entire list of data dirs should be returned.

        By default, the first item would only be returned. Only affects ``site_data_dir`` and ``site_config_dir`` on
        Unix and macOS.

        """
        self.opinion = opinion
        """Whether to use opinionated values.

        When enabled, appends an additional subdirectory for certain directories: e.g. ``Cache`` for cache and ``Logs``
        for logs on Windows, ``log`` for logs on Unix.

        """
        self.ensure_exists = ensure_exists
        """Optionally create the directory (and any missing parents) upon access if it does not exist.

        By default, no directories are created.

        """
        self.use_site_for_root = use_site_for_root
        """Whether to redirect ``user_*_dir`` calls to their ``site_*_dir`` equivalents when running as root (uid 0).

        Only has an effect on Unix. Disabled by default for backwards compatibility. When enabled, XDG user environment
        variables (e.g. ``XDG_DATA_HOME``) are bypassed for the redirected directories.

        """

    def _append_app_name_and_version(self, *base: str) -> str:
        params = list(base[1:])
        if self.appname:
            params.append(self.appname)
            if self.version:
                params.append(self.version)
        path = os.path.join(base[0], *params)  # noqa: PTH118
        self._optionally_create_directory(path)
        return path

    def _optionally_create_directory(self, path: str) -> None:
        if self.ensure_exists:
            Path(path).mkdir(parents=True, exist_ok=True)

    def _first_item_as_path_if_multipath(self, directory: str) -> Path:
        if self.multipath:
            # If multipath is True, the first path is returned.
            directory = directory.partition(os.pathsep)[0]
        return Path(directory)

    @property
    @abstractmethod
    def user_data_dir(self) -> str:
        """:returns: data directory tied to the user"""

    @property
    @abstractmethod
    def site_data_dir(self) -> str:
        """:returns: data directory shared by users"""

    @property
    @abstractmethod
    def user_config_dir(self) -> str:
        """:returns: config directory tied to the user"""

    @property
    @abstractmethod
    def site_config_dir(self) -> str:
        """:returns: config directory shared by users"""

    @property
    @abstractmethod
    def user_cache_dir(self) -> str:
        """:returns: cache directory tied to the user"""

    @property
    @abstractmethod
    def site_cache_dir(self) -> str:
        """:returns: cache directory shared by users"""

    @property
    @abstractmethod
    def user_state_dir(self) -> str:
        """:returns: state directory tied to the user"""

    @property
    @abstractmethod
    def site_state_dir(self) -> str:
        """:returns: state directory shared by users"""

    @property
    @abstractmethod
    def user_log_dir(self) -> str:
        """:returns: log directory tied to the user"""

    @property
    @abstractmethod
    def site_log_dir(self) -> str:
        """:returns: log directory shared by users"""

    @property
    @abstractmethod
    def user_documents_dir(self) -> str:
        """:returns: documents directory tied to the user"""

    @property
    @abstractmethod
    def user_downloads_dir(self) -> str:
        """:returns: downloads directory tied to the user"""

    @property
    @abstractmethod
    def user_pictures_dir(self) -> str:
        """:returns: pictures directory tied to the user"""

    @property
    @abstractmethod
    def user_videos_dir(self) -> str:
        """:returns: videos directory tied to the user"""

    @property
    @abstractmethod
    def user_music_dir(self) -> str:
        """:returns: music directory tied to the user"""

    @property
    @abstractmethod
    def user_desktop_dir(self) -> str:
        """:returns: desktop directory tied to the user"""

    @property
    @abstractmethod
    def user_bin_dir(self) -> str:
        """:returns: bin directory tied to the user"""

    @property
    @abstractmethod
    def site_bin_dir(self) -> str:
        """:returns: bin directory shared by users"""

    @property
    @abstractmethod
    def user_applications_dir(self) -> str:
        """:returns: applications directory tied to the user"""

    @property
    @abstractmethod
    def site_applications_dir(self) -> str:
        """:returns: applications directory shared by users"""

    @property
    @abstractmethod
    def user_runtime_dir(self) -> str:
        """:returns: runtime directory tied to the user"""

    @property
    @abstractmethod
    def site_runtime_dir(self) -> str:
        """:returns: runtime directory shared by users"""

    @property
    def user_data_path(self) -> Path:
        """:returns: data path tied to the user"""
        return Path(self.user_data_dir)

    @property
    def site_data_path(self) -> Path:
        """:returns: data path shared by users"""
        return Path(self.site_data_dir)

    @property
    def user_config_path(self) -> Path:
        """:returns: config path tied to the user"""
        return Path(self.user_config_dir)

    @property
    def site_config_path(self) -> Path:
        """:returns: config path shared by users"""
        return Path(self.site_config_dir)

    @property
    def user_cache_path(self) -> Path:
        """:returns: cache path tied to the user"""
        return Path(self.user_cache_dir)

    @property
    def site_cache_path(self) -> Path:
        """:returns: cache path shared by users"""
        return Path(self.site_cache_dir)

    @property
    def user_state_path(self) -> Path:
        """:returns: state path tied to the user"""
        return Path(self.user_state_dir)

    @property
    def site_state_path(self) -> Path:
        """:returns: state path shared by users"""
        return Path(self.site_state_dir)

    @property
    def user_log_path(self) -> Path:
        """:returns: log path tied to the user"""
        return Path(self.user_log_dir)

    @property
    def site_log_path(self) -> Path:
        """:returns: log path shared by users"""
        return Path(self.site_log_dir)

    @property
    def user_documents_path(self) -> Path:
        """:returns: documents path tied to the user"""
        return Path(self.user_documents_dir)

    @property
    def user_downloads_path(self) -> Path:
        """:returns: downloads path tied to the user"""
        return Path(self.user_downloads_dir)

    @property
    def user_pictures_path(self) -> Path:
        """:returns: pictures path tied to the user"""
        return Path(self.user_pictures_dir)

    @property
    def user_videos_path(self) -> Path:
        """:returns: videos path tied to the user"""
        return Path(self.user_videos_dir)

    @property
    def user_music_path(self) -> Path:
        """:returns: music path tied to the user"""
        return Path(self.user_music_dir)

    @property
    def user_desktop_path(self) -> Path:
        """:returns: desktop path tied to the user"""
        return Path(self.user_desktop_dir)

    @property
    def user_bin_path(self) -> Path:
        """:returns: bin path tied to the user"""
        return Path(self.user_bin_dir)

    @property
    def site_bin_path(self) -> Path:
        """:returns: bin path shared by users"""
        return Path(self.site_bin_dir)

    @property
    def user_applications_path(self) -> Path:
        """:returns: applications path tied to the user"""
        return Path(self.user_applications_dir)

    @property
    def site_applications_path(self) -> Path:
        """:returns: applications path shared by users"""
        return Path(self.site_applications_dir)

    @property
    def user_runtime_path(self) -> Path:
        """:returns: runtime path tied to the user"""
        return Path(self.user_runtime_dir)

    @property
    def site_runtime_path(self) -> Path:
        """:returns: runtime path shared by users"""
        return Path(self.site_runtime_dir)

    def iter_config_dirs(self) -> Iterator[str]:
        """:yield: all user and site configuration directories."""
        yield self.user_config_dir
        yield self.site_config_dir

    def iter_data_dirs(self) -> Iterator[str]:
        """:yield: all user and site data directories."""
        yield self.user_data_dir
        yield self.site_data_dir

    def iter_cache_dirs(self) -> Iterator[str]:
        """:yield: all user and site cache directories."""
        yield self.user_cache_dir
        yield self.site_cache_dir

    def iter_state_dirs(self) -> Iterator[str]:
        """:yield: all user and site state directories."""
        yield self.user_state_dir
        yield self.site_state_dir

    def iter_log_dirs(self) -> Iterator[str]:
        """:yield: all user and site log directories."""
        yield self.user_log_dir
        yield self.site_log_dir

    def iter_runtime_dirs(self) -> Iterator[str]:
        """:yield: all user and site runtime directories."""
        yield self.user_runtime_dir
        yield self.site_runtime_dir

    def iter_config_paths(self) -> Iterator[Path]:
        """:yield: all user and site configuration paths."""
        for path in self.iter_config_dirs():
            yield Path(path)

    def iter_data_paths(self) -> Iterator[Path]:
        """:yield: all user and site data paths."""
        for path in self.iter_data_dirs():
            yield Path(path)

    def iter_cache_paths(self) -> Iterator[Path]:
        """:yield: all user and site cache paths."""
        for path in self.iter_cache_dirs():
            yield Path(path)

    def iter_state_paths(self) -> Iterator[Path]:
        """:yield: all user and site state paths."""
        for path in self.iter_state_dirs():
            yield Path(path)

    def iter_log_paths(self) -> Iterator[Path]:
        """:yield: all user and site log paths."""
        for path in self.iter_log_dirs():
            yield Path(path)

    def iter_runtime_paths(self) -> Iterator[Path]:
        """:yield: all user and site runtime paths."""
        for path in self.iter_runtime_dirs():
            yield Path(path)
