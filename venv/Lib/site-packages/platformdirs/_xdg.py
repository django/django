"""XDG environment variable mixin for Unix and macOS."""

from __future__ import annotations

import os

from .api import PlatformDirsABC


class XDGMixin(PlatformDirsABC):
    """Mixin that checks XDG environment variables, falling back to platform-specific defaults via ``super()``."""

    @property
    def user_data_dir(self) -> str:
        """:returns: data directory tied to the user, from ``$XDG_DATA_HOME`` if set, else platform default"""
        if path := os.environ.get("XDG_DATA_HOME", "").strip():
            return self._append_app_name_and_version(path)
        return super().user_data_dir

    @property
    def _site_data_dirs(self) -> list[str]:
        if xdg_dirs := os.environ.get("XDG_DATA_DIRS", "").strip():
            return [self._append_app_name_and_version(p) for p in xdg_dirs.split(os.pathsep) if p.strip()]
        return super()._site_data_dirs  # type: ignore[misc]

    @property
    def site_data_dir(self) -> str:
        """:returns: data directories shared by users, from ``$XDG_DATA_DIRS`` if set, else platform default"""
        dirs = self._site_data_dirs
        return os.pathsep.join(dirs) if self.multipath else dirs[0]

    @property
    def user_config_dir(self) -> str:
        """:returns: config directory tied to the user, from ``$XDG_CONFIG_HOME`` if set, else platform default"""
        if path := os.environ.get("XDG_CONFIG_HOME", "").strip():
            return self._append_app_name_and_version(path)
        return super().user_config_dir

    @property
    def _site_config_dirs(self) -> list[str]:
        if xdg_dirs := os.environ.get("XDG_CONFIG_DIRS", "").strip():
            return [self._append_app_name_and_version(p) for p in xdg_dirs.split(os.pathsep) if p.strip()]
        return super()._site_config_dirs  # type: ignore[misc]

    @property
    def site_config_dir(self) -> str:
        """:returns: config directories shared by users, from ``$XDG_CONFIG_DIRS`` if set, else platform default"""
        dirs = self._site_config_dirs
        return os.pathsep.join(dirs) if self.multipath else dirs[0]

    @property
    def user_cache_dir(self) -> str:
        """:returns: cache directory tied to the user, from ``$XDG_CACHE_HOME`` if set, else platform default"""
        if path := os.environ.get("XDG_CACHE_HOME", "").strip():
            return self._append_app_name_and_version(path)
        return super().user_cache_dir

    @property
    def user_state_dir(self) -> str:
        """:returns: state directory tied to the user, from ``$XDG_STATE_HOME`` if set, else platform default"""
        if path := os.environ.get("XDG_STATE_HOME", "").strip():
            return self._append_app_name_and_version(path)
        return super().user_state_dir

    @property
    def user_runtime_dir(self) -> str:
        """:returns: runtime directory tied to the user, from ``$XDG_RUNTIME_DIR`` if set, else platform default"""
        if path := os.environ.get("XDG_RUNTIME_DIR", "").strip():
            return self._append_app_name_and_version(path)
        return super().user_runtime_dir

    @property
    def site_runtime_dir(self) -> str:
        """:returns: runtime directory shared by users, from ``$XDG_RUNTIME_DIR`` if set, else platform default"""
        if path := os.environ.get("XDG_RUNTIME_DIR", "").strip():
            return self._append_app_name_and_version(path)
        return super().site_runtime_dir

    @property
    def user_documents_dir(self) -> str:
        """:returns: documents directory tied to the user, from ``$XDG_DOCUMENTS_DIR`` if set, else platform default"""
        if path := os.environ.get("XDG_DOCUMENTS_DIR", "").strip():
            return os.path.expanduser(path)  # noqa: PTH111
        return super().user_documents_dir

    @property
    def user_downloads_dir(self) -> str:
        """:returns: downloads directory tied to the user, from ``$XDG_DOWNLOAD_DIR`` if set, else platform default"""
        if path := os.environ.get("XDG_DOWNLOAD_DIR", "").strip():
            return os.path.expanduser(path)  # noqa: PTH111
        return super().user_downloads_dir

    @property
    def user_pictures_dir(self) -> str:
        """:returns: pictures directory tied to the user, from ``$XDG_PICTURES_DIR`` if set, else platform default"""
        if path := os.environ.get("XDG_PICTURES_DIR", "").strip():
            return os.path.expanduser(path)  # noqa: PTH111
        return super().user_pictures_dir

    @property
    def user_videos_dir(self) -> str:
        """:returns: videos directory tied to the user, from ``$XDG_VIDEOS_DIR`` if set, else platform default"""
        if path := os.environ.get("XDG_VIDEOS_DIR", "").strip():
            return os.path.expanduser(path)  # noqa: PTH111
        return super().user_videos_dir

    @property
    def user_music_dir(self) -> str:
        """:returns: music directory tied to the user, from ``$XDG_MUSIC_DIR`` if set, else platform default"""
        if path := os.environ.get("XDG_MUSIC_DIR", "").strip():
            return os.path.expanduser(path)  # noqa: PTH111
        return super().user_music_dir

    @property
    def user_desktop_dir(self) -> str:
        """:returns: desktop directory tied to the user, from ``$XDG_DESKTOP_DIR`` if set, else platform default"""
        if path := os.environ.get("XDG_DESKTOP_DIR", "").strip():
            return os.path.expanduser(path)  # noqa: PTH111
        return super().user_desktop_dir

    @property
    def user_applications_dir(self) -> str:
        """:returns: applications directory tied to the user, from ``$XDG_DATA_HOME`` if set, else platform default"""
        if path := os.environ.get("XDG_DATA_HOME", "").strip():
            return os.path.join(os.path.expanduser(path), "applications")  # noqa: PTH111, PTH118
        return super().user_applications_dir

    @property
    def _site_applications_dirs(self) -> list[str]:
        if xdg_dirs := os.environ.get("XDG_DATA_DIRS", "").strip():
            return [os.path.join(p, "applications") for p in xdg_dirs.split(os.pathsep) if p.strip()]  # noqa: PTH118
        return super()._site_applications_dirs  # type: ignore[misc]

    @property
    def site_applications_dir(self) -> str:
        """:returns: applications directories shared by users, from ``$XDG_DATA_DIRS`` if set, else platform default"""
        dirs = self._site_applications_dirs
        return os.pathsep.join(dirs) if self.multipath else dirs[0]


__all__ = [
    "XDGMixin",
]
