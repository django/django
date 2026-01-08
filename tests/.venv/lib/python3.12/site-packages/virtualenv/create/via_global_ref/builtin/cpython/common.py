from __future__ import annotations

import re
from abc import ABC
from collections import OrderedDict
from pathlib import Path

from virtualenv.create.describe import PosixSupports, WindowsSupports
from virtualenv.create.via_global_ref.builtin.ref import RefMust, RefWhen
from virtualenv.create.via_global_ref.builtin.via_global_self_do import ViaGlobalRefVirtualenvBuiltin


class CPython(ViaGlobalRefVirtualenvBuiltin, ABC):
    @classmethod
    def can_describe(cls, interpreter):
        return interpreter.implementation == "CPython" and super().can_describe(interpreter)

    @classmethod
    def exe_stem(cls):
        return "python"


class CPythonPosix(CPython, PosixSupports, ABC):
    """Create a CPython virtual environment on POSIX platforms."""

    @classmethod
    def _executables(cls, interpreter):
        host_exe = Path(interpreter.system_executable)
        major, minor = interpreter.version_info.major, interpreter.version_info.minor
        targets = OrderedDict((i, None) for i in ["python", f"python{major}", f"python{major}.{minor}", host_exe.name])
        yield host_exe, list(targets.keys()), RefMust.NA, RefWhen.ANY


class CPythonWindows(CPython, WindowsSupports, ABC):
    @classmethod
    def _executables(cls, interpreter):
        # symlink of the python executables does not work reliably, copy always instead
        # - https://bugs.python.org/issue42013
        # - venv
        host = cls.host_python(interpreter)
        names = {"python.exe", host.name}
        if interpreter.version_info.major == 3:  # noqa: PLR2004
            names.update({"python3.exe", "python3"})
        for path in (host.parent / n for n in names):
            yield host, [path.name], RefMust.COPY, RefWhen.ANY
        # for more info on pythonw.exe see https://stackoverflow.com/a/30313091
        python_w = host.parent / "pythonw.exe"
        yield python_w, [python_w.name], RefMust.COPY, RefWhen.ANY

    @classmethod
    def host_python(cls, interpreter):
        return Path(interpreter.system_executable)


def is_mac_os_framework(interpreter):
    if interpreter.platform == "darwin":
        return interpreter.sysconfig_vars.get("PYTHONFRAMEWORK") == "Python3"
    return False


def is_macos_brew(interpreter):
    return interpreter.platform == "darwin" and _BREW.fullmatch(interpreter.system_prefix) is not None


_BREW = re.compile(
    r"/(usr/local|opt/homebrew)/(opt/python@3\.\d{1,2}|Cellar/python@3\.\d{1,2}/3\.\d{1,2}\.\d{1,2})/Frameworks/"
    r"Python\.framework/Versions/3\.\d{1,2}",
)

__all__ = [
    "CPython",
    "CPythonPosix",
    "CPythonWindows",
    "is_mac_os_framework",
    "is_macos_brew",
]
