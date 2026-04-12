"""Windows."""

from __future__ import annotations

import os
import sys
from typing import TYPE_CHECKING, Final

from .api import PlatformDirsABC

if TYPE_CHECKING:
    from collections.abc import Callable

# Not exposed by CPython; defined in the Windows SDK (shlobj_core.h)
_KF_FLAG_DONT_VERIFY: Final[int] = 0x00004000


class Windows(PlatformDirsABC):  # noqa: PLR0904
    """`MSDN on where to store app data files <https://learn.microsoft.com/en-us/windows/win32/shell/knownfolderid>`_.

    Makes use of the `appname <platformdirs.api.PlatformDirsABC.appname>`, `appauthor
    <platformdirs.api.PlatformDirsABC.appauthor>`, `version <platformdirs.api.PlatformDirsABC.version>`, `roaming
    <platformdirs.api.PlatformDirsABC.roaming>`, `opinion <platformdirs.api.PlatformDirsABC.opinion>`, `ensure_exists
    <platformdirs.api.PlatformDirsABC.ensure_exists>`.

    """

    @property
    def user_data_dir(self) -> str:
        r""":returns: data directory tied to the user, e.g. ``%USERPROFILE%\AppData\Local\$appauthor\$appname`` (not roaming) or ``%USERPROFILE%\AppData\Roaming\$appauthor\$appname`` (roaming)"""
        const = "CSIDL_APPDATA" if self.roaming else "CSIDL_LOCAL_APPDATA"
        path = os.path.normpath(get_win_folder(const))
        return self._append_parts(path)

    def _append_parts(self, path: str, *, opinion_value: str | None = None) -> str:
        params = []
        if self.appname:
            if self.appauthor is not False:
                author = self.appauthor or self.appname
                params.append(author)
            params.append(self.appname)
            if opinion_value is not None and self.opinion:
                params.append(opinion_value)
            if self.version:
                params.append(self.version)
        path = os.path.join(path, *params)  # noqa: PTH118
        self._optionally_create_directory(path)
        return path

    @property
    def site_data_dir(self) -> str:
        r""":returns: data directory shared by users, e.g. ``C:\ProgramData\$appauthor\$appname``"""
        path = os.path.normpath(get_win_folder("CSIDL_COMMON_APPDATA"))
        return self._append_parts(path)

    @property
    def user_config_dir(self) -> str:
        """:returns: config directory tied to the user, same as `user_data_dir`"""
        return self.user_data_dir

    @property
    def site_config_dir(self) -> str:
        """:returns: config directory shared by users, same as `site_data_dir`"""
        return self.site_data_dir

    @property
    def user_cache_dir(self) -> str:
        r""":returns: cache directory tied to the user (if opinionated with ``Cache`` folder within ``$appname``) e.g. ``%USERPROFILE%\AppData\Local\$appauthor\$appname\Cache\$version``"""
        path = os.path.normpath(get_win_folder("CSIDL_LOCAL_APPDATA"))
        return self._append_parts(path, opinion_value="Cache")

    @property
    def site_cache_dir(self) -> str:
        r""":returns: cache directory shared by users, e.g. ``C:\ProgramData\$appauthor\$appname\Cache\$version``"""
        path = os.path.normpath(get_win_folder("CSIDL_COMMON_APPDATA"))
        return self._append_parts(path, opinion_value="Cache")

    @property
    def user_state_dir(self) -> str:
        """:returns: state directory tied to the user, same as `user_data_dir`"""
        return self.user_data_dir

    @property
    def site_state_dir(self) -> str:
        """:returns: state directory shared by users, same as `site_data_dir`"""
        return self.site_data_dir

    @property
    def user_log_dir(self) -> str:
        """:returns: log directory tied to the user, same as `user_data_dir` if not opinionated else ``Logs`` in it"""
        path = self.user_data_dir
        if self.opinion:
            path = os.path.join(path, "Logs")  # noqa: PTH118
            self._optionally_create_directory(path)
        return path

    @property
    def site_log_dir(self) -> str:
        """:returns: log directory shared by users, same as `site_data_dir` if not opinionated else ``Logs`` in it"""
        path = self.site_data_dir
        if self.opinion:
            path = os.path.join(path, "Logs")  # noqa: PTH118
            self._optionally_create_directory(path)
        return path

    @property
    def user_documents_dir(self) -> str:
        r""":returns: documents directory tied to the user e.g. ``%USERPROFILE%\Documents``"""
        return os.path.normpath(get_win_folder("CSIDL_PERSONAL"))

    @property
    def user_downloads_dir(self) -> str:
        r""":returns: downloads directory tied to the user e.g. ``%USERPROFILE%\Downloads``"""
        return os.path.normpath(get_win_folder("CSIDL_DOWNLOADS"))

    @property
    def user_pictures_dir(self) -> str:
        r""":returns: pictures directory tied to the user e.g. ``%USERPROFILE%\Pictures``"""
        return os.path.normpath(get_win_folder("CSIDL_MYPICTURES"))

    @property
    def user_videos_dir(self) -> str:
        r""":returns: videos directory tied to the user e.g. ``%USERPROFILE%\Videos``"""
        return os.path.normpath(get_win_folder("CSIDL_MYVIDEO"))

    @property
    def user_music_dir(self) -> str:
        r""":returns: music directory tied to the user e.g. ``%USERPROFILE%\Music``"""
        return os.path.normpath(get_win_folder("CSIDL_MYMUSIC"))

    @property
    def user_desktop_dir(self) -> str:
        r""":returns: desktop directory tied to the user, e.g. ``%USERPROFILE%\Desktop``"""
        return os.path.normpath(get_win_folder("CSIDL_DESKTOPDIRECTORY"))

    @property
    def user_bin_dir(self) -> str:
        r""":returns: bin directory tied to the user, e.g. ``%LOCALAPPDATA%\Programs``"""
        return os.path.normpath(os.path.join(get_win_folder("CSIDL_LOCAL_APPDATA"), "Programs"))  # noqa: PTH118

    @property
    def site_bin_dir(self) -> str:
        """:returns: bin directory shared by users, e.g. ``C:\\ProgramData\bin``"""
        return os.path.normpath(os.path.join(get_win_folder("CSIDL_COMMON_APPDATA"), "bin"))  # noqa: PTH118

    @property
    def user_applications_dir(self) -> str:
        r""":returns: applications directory tied to the user, e.g. ``Start Menu\Programs``"""
        return os.path.normpath(get_win_folder("CSIDL_PROGRAMS"))

    @property
    def site_applications_dir(self) -> str:
        r""":returns: applications directory shared by users, e.g. ``C:\ProgramData\Microsoft\Windows\Start Menu\Programs``"""
        return os.path.normpath(get_win_folder("CSIDL_COMMON_PROGRAMS"))

    @property
    def user_runtime_dir(self) -> str:
        r""":returns: runtime directory tied to the user, e.g. ``%USERPROFILE%\AppData\Local\Temp\$appauthor\$appname``"""
        path = os.path.normpath(os.path.join(get_win_folder("CSIDL_LOCAL_APPDATA"), "Temp"))  # noqa: PTH118
        return self._append_parts(path)

    @property
    def site_runtime_dir(self) -> str:
        """:returns: runtime directory shared by users, same as `user_runtime_dir`"""
        return self.user_runtime_dir


def get_win_folder_from_env_vars(csidl_name: str) -> str:
    """Get folder from environment variables."""
    result = get_win_folder_if_csidl_name_not_env_var(csidl_name)
    if result is not None:
        return result

    env_var_name = {
        "CSIDL_APPDATA": "APPDATA",
        "CSIDL_COMMON_APPDATA": "ALLUSERSPROFILE",
        "CSIDL_LOCAL_APPDATA": "LOCALAPPDATA",
    }.get(csidl_name)
    if env_var_name is None:
        msg = f"Unknown CSIDL name: {csidl_name}"
        raise ValueError(msg)
    result = os.environ.get(env_var_name)
    if result is None:
        msg = f"Unset environment variable: {env_var_name}"
        raise ValueError(msg)
    return result


def get_win_folder_if_csidl_name_not_env_var(csidl_name: str) -> str | None:  # noqa: PLR0911
    """Get a folder for a CSIDL name that does not exist as an environment variable."""
    if csidl_name == "CSIDL_PERSONAL":
        return os.path.join(os.path.normpath(os.environ["USERPROFILE"]), "Documents")  # noqa: PTH118

    if csidl_name == "CSIDL_DOWNLOADS":
        return os.path.join(os.path.normpath(os.environ["USERPROFILE"]), "Downloads")  # noqa: PTH118

    if csidl_name == "CSIDL_MYPICTURES":
        return os.path.join(os.path.normpath(os.environ["USERPROFILE"]), "Pictures")  # noqa: PTH118

    if csidl_name == "CSIDL_MYVIDEO":
        return os.path.join(os.path.normpath(os.environ["USERPROFILE"]), "Videos")  # noqa: PTH118

    if csidl_name == "CSIDL_MYMUSIC":
        return os.path.join(os.path.normpath(os.environ["USERPROFILE"]), "Music")  # noqa: PTH118

    if csidl_name == "CSIDL_PROGRAMS":
        return os.path.join(  # noqa: PTH118
            os.path.normpath(os.environ["APPDATA"]),
            "Microsoft",
            "Windows",
            "Start Menu",
            "Programs",
        )

    if csidl_name == "CSIDL_COMMON_PROGRAMS":
        return os.path.join(  # noqa: PTH118
            os.path.normpath(os.environ.get("PROGRAMDATA", os.environ.get("ALLUSERSPROFILE", "C:\\ProgramData"))),
            "Microsoft",
            "Windows",
            "Start Menu",
            "Programs",
        )
    return None


def get_win_folder_from_registry(csidl_name: str) -> str:
    """Get folder from the registry.

    This is a fallback technique at best. I'm not sure if using the registry for these guarantees us the correct answer
    for all CSIDL_* names.

    """
    machine_names = {
        "CSIDL_COMMON_APPDATA",
        "CSIDL_COMMON_PROGRAMS",
    }
    shell_folder_name = {
        "CSIDL_APPDATA": "AppData",
        "CSIDL_COMMON_APPDATA": "Common AppData",
        "CSIDL_LOCAL_APPDATA": "Local AppData",
        "CSIDL_PERSONAL": "Personal",
        "CSIDL_DOWNLOADS": "{374DE290-123F-4565-9164-39C4925E467B}",
        "CSIDL_MYPICTURES": "My Pictures",
        "CSIDL_MYVIDEO": "My Video",
        "CSIDL_MYMUSIC": "My Music",
        "CSIDL_PROGRAMS": "Programs",
        "CSIDL_COMMON_PROGRAMS": "Common Programs",
    }.get(csidl_name)
    if shell_folder_name is None:
        msg = f"Unknown CSIDL name: {csidl_name}"
        raise ValueError(msg)
    if sys.platform != "win32":  # only needed for mypy type checker to know that this code runs only on Windows
        raise NotImplementedError
    import winreg  # noqa: PLC0415

    # Use HKEY_LOCAL_MACHINE for system-wide folders, HKEY_CURRENT_USER for user-specific folders
    hkey = winreg.HKEY_LOCAL_MACHINE if csidl_name in machine_names else winreg.HKEY_CURRENT_USER

    key = winreg.OpenKey(hkey, r"Software\Microsoft\Windows\CurrentVersion\Explorer\Shell Folders")
    directory, _ = winreg.QueryValueEx(key, shell_folder_name)
    return str(directory)


_KNOWN_FOLDER_GUIDS: dict[str, str] = {
    "CSIDL_APPDATA": "{3EB685DB-65F9-4CF6-A03A-E3EF65729F3D}",
    "CSIDL_COMMON_APPDATA": "{62AB5D82-FDC1-4DC3-A9DD-070D1D495D97}",
    "CSIDL_LOCAL_APPDATA": "{F1B32785-6FBA-4FCF-9D55-7B8E7F157091}",
    "CSIDL_PERSONAL": "{FDD39AD0-238F-46AF-ADB4-6C85480369C7}",
    "CSIDL_MYPICTURES": "{33E28130-4E1E-4676-835A-98395C3BC3BB}",
    "CSIDL_MYVIDEO": "{18989B1D-99B5-455B-841C-AB7C74E4DDFC}",
    "CSIDL_MYMUSIC": "{4BD8D571-6D19-48D3-BE97-422220080E43}",
    "CSIDL_DOWNLOADS": "{374DE290-123F-4565-9164-39C4925E467B}",
    "CSIDL_DESKTOPDIRECTORY": "{B4BFCC3A-DB2C-424C-B029-7FE99A87C641}",
    "CSIDL_PROGRAMS": "{A77F5D77-2E2B-44C3-A6A2-ABA601054A51}",
    "CSIDL_COMMON_PROGRAMS": "{0139D44E-6AFE-49F2-8690-3DAFCAE6FFB8}",
}


def get_win_folder_via_ctypes(csidl_name: str) -> str:
    """Get folder via :func:`SHGetKnownFolderPath`.

    See https://learn.microsoft.com/en-us/windows/win32/api/shlobj_core/nf-shlobj_core-shgetknownfolderpath.

    """
    if sys.platform != "win32":  # only needed for type checker to know that this code runs only on Windows
        raise NotImplementedError
    from ctypes import HRESULT, POINTER, Structure, WinDLL, byref, create_unicode_buffer, wintypes  # noqa: PLC0415

    class _GUID(Structure):
        _fields_ = [
            ("Data1", wintypes.DWORD),
            ("Data2", wintypes.WORD),
            ("Data3", wintypes.WORD),
            ("Data4", wintypes.BYTE * 8),
        ]

    ole32 = WinDLL("ole32")
    ole32.CLSIDFromString.restype = HRESULT
    ole32.CLSIDFromString.argtypes = [wintypes.LPCOLESTR, POINTER(_GUID)]
    ole32.CoTaskMemFree.restype = None
    ole32.CoTaskMemFree.argtypes = [wintypes.LPVOID]

    shell32 = WinDLL("shell32")
    shell32.SHGetKnownFolderPath.restype = HRESULT
    shell32.SHGetKnownFolderPath.argtypes = [POINTER(_GUID), wintypes.DWORD, wintypes.HANDLE, POINTER(wintypes.LPWSTR)]

    kernel32 = WinDLL("kernel32")
    kernel32.GetShortPathNameW.restype = wintypes.DWORD
    kernel32.GetShortPathNameW.argtypes = [wintypes.LPWSTR, wintypes.LPWSTR, wintypes.DWORD]

    folder_guid = _KNOWN_FOLDER_GUIDS.get(csidl_name)
    if folder_guid is None:
        msg = f"Unknown CSIDL name: {csidl_name}"
        raise ValueError(msg)

    guid = _GUID()
    ole32.CLSIDFromString(folder_guid, byref(guid))

    path_ptr = wintypes.LPWSTR()
    shell32.SHGetKnownFolderPath(byref(guid), _KF_FLAG_DONT_VERIFY, None, byref(path_ptr))
    result = path_ptr.value
    ole32.CoTaskMemFree(path_ptr)

    if result is None:
        msg = f"SHGetKnownFolderPath returned NULL for {csidl_name}"
        raise ValueError(msg)

    if any(ord(c) > 255 for c in result):  # noqa: PLR2004
        buf = create_unicode_buffer(1024)
        if kernel32.GetShortPathNameW(result, buf, 1024):
            result = buf.value

    return result


def _pick_get_win_folder() -> Callable[[str], str]:
    """Select the best method to resolve Windows folder paths: ctypes, then registry, then environment variables."""
    try:
        import ctypes  # noqa: PLC0415, F401
    except ImportError:
        pass
    else:
        return get_win_folder_via_ctypes
    try:
        import winreg  # noqa: PLC0415, F401
    except ImportError:
        return get_win_folder_from_env_vars
    else:
        return get_win_folder_from_registry


_resolve_win_folder = _pick_get_win_folder()


def get_win_folder(csidl_name: str) -> str:
    """Get a Windows folder path, checking for ``WIN_PD_OVERRIDE_*`` environment variable overrides first.

    For example, ``CSIDL_LOCAL_APPDATA`` can be overridden by setting ``WIN_PD_OVERRIDE_LOCAL_APPDATA``.

    """
    env_var = f"WIN_PD_OVERRIDE_{csidl_name.removeprefix('CSIDL_')}"
    if override := os.environ.get(env_var, "").strip():
        return override
    return _resolve_win_folder(csidl_name)


__all__ = [
    "Windows",
]
