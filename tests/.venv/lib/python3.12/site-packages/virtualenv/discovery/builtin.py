from __future__ import annotations

import logging
import os
import sys
from contextlib import suppress
from pathlib import Path
from typing import TYPE_CHECKING

from platformdirs import user_data_path

from virtualenv.info import IS_WIN, fs_path_id

from .discover import Discover
from .py_info import PythonInfo
from .py_spec import PythonSpec

if TYPE_CHECKING:
    from argparse import ArgumentParser
    from collections.abc import Callable, Generator, Iterable, Mapping, Sequence

    from virtualenv.app_data.base import AppData
LOGGER = logging.getLogger(__name__)


class Builtin(Discover):
    python_spec: Sequence[str]
    app_data: AppData
    try_first_with: Sequence[str]

    def __init__(self, options) -> None:
        super().__init__(options)
        self.python_spec = options.python or [sys.executable]
        if self._env.get("VIRTUALENV_PYTHON"):
            self.python_spec = self.python_spec[1:] + self.python_spec[:1]  # Rotate the list
        self.app_data = options.app_data
        self.try_first_with = options.try_first_with

    @classmethod
    def add_parser_arguments(cls, parser: ArgumentParser) -> None:
        parser.add_argument(
            "-p",
            "--python",
            dest="python",
            metavar="py",
            type=str,
            action="append",
            default=[],
            help="interpreter based on what to create environment (path/identifier/version-specifier) "
            "- by default use the interpreter where the tool is installed - first found wins. "
            "Version specifiers (e.g., >=3.12, ~=3.11.0, ==3.10) are also supported",
        )
        parser.add_argument(
            "--try-first-with",
            dest="try_first_with",
            metavar="py_exe",
            type=str,
            action="append",
            default=[],
            help="try first these interpreters before starting the discovery",
        )

    def run(self) -> PythonInfo | None:
        for python_spec in self.python_spec:
            result = get_interpreter(python_spec, self.try_first_with, self.app_data, self._env)
            if result is not None:
                return result
        return None

    def __repr__(self) -> str:
        spec = self.python_spec[0] if len(self.python_spec) == 1 else self.python_spec
        return f"{self.__class__.__name__} discover of python_spec={spec!r}"


def get_interpreter(
    key, try_first_with: Iterable[str], app_data: AppData | None = None, env: Mapping[str, str] | None = None
) -> PythonInfo | None:
    spec = PythonSpec.from_string_spec(key)
    LOGGER.info("find interpreter for spec %r", spec)
    proposed_paths = set()
    env = os.environ if env is None else env
    for interpreter, impl_must_match in propose_interpreters(spec, try_first_with, app_data, env):
        key = interpreter.system_executable, impl_must_match
        if key in proposed_paths:
            continue
        LOGGER.info("proposed %s", interpreter)
        if interpreter.satisfies(spec, impl_must_match):
            LOGGER.debug("accepted %s", interpreter)
            return interpreter
        proposed_paths.add(key)
    return None


def propose_interpreters(  # noqa: C901, PLR0912, PLR0915
    spec: PythonSpec,
    try_first_with: Iterable[str],
    app_data: AppData | None = None,
    env: Mapping[str, str] | None = None,
) -> Generator[tuple[PythonInfo, bool], None, None]:
    # 0. if it's a path and exists, and is absolute path, this is the only option we consider
    env = os.environ if env is None else env
    tested_exes: set[str] = set()
    if spec.is_abs:
        try:
            os.lstat(spec.path)  # Windows Store Python does not work with os.path.exists, but does for os.lstat
        except OSError:
            pass
        else:
            exe_raw = os.path.abspath(spec.path)
            exe_id = fs_path_id(exe_raw)
            if exe_id not in tested_exes:
                tested_exes.add(exe_id)
                yield PythonInfo.from_exe(exe_raw, app_data, env=env), True
        return

    # 1. try with first
    for py_exe in try_first_with:
        path = os.path.abspath(py_exe)
        try:
            os.lstat(path)  # Windows Store Python does not work with os.path.exists, but does for os.lstat
        except OSError:
            pass
        else:
            exe_raw = os.path.abspath(path)
            exe_id = fs_path_id(exe_raw)
            if exe_id in tested_exes:
                continue
            tested_exes.add(exe_id)
            yield PythonInfo.from_exe(exe_raw, app_data, env=env), True

    # 1. if it's a path and exists
    if spec.path is not None:
        try:
            os.lstat(spec.path)  # Windows Store Python does not work with os.path.exists, but does for os.lstat
        except OSError:
            pass
        else:
            exe_raw = os.path.abspath(spec.path)
            exe_id = fs_path_id(exe_raw)
            if exe_id not in tested_exes:
                tested_exes.add(exe_id)
                yield PythonInfo.from_exe(exe_raw, app_data, env=env), True
        if spec.is_abs:
            return
    else:
        # 2. otherwise try with the current
        current_python = PythonInfo.current_system(app_data)
        exe_raw = str(current_python.executable)
        exe_id = fs_path_id(exe_raw)
        if exe_id not in tested_exes:
            tested_exes.add(exe_id)
            yield current_python, True

        # 3. otherwise fallback to platform default logic
        if IS_WIN:
            from .windows import propose_interpreters  # noqa: PLC0415

            for interpreter in propose_interpreters(spec, app_data, env):
                exe_raw = str(interpreter.executable)
                exe_id = fs_path_id(exe_raw)
                if exe_id in tested_exes:
                    continue
                tested_exes.add(exe_id)
                yield interpreter, True

    # try to find on path, the path order matters (as the candidates are less easy to control by end user)
    find_candidates = path_exe_finder(spec)
    for pos, path in enumerate(get_paths(env)):
        LOGGER.debug(LazyPathDump(pos, path, env))
        for exe, impl_must_match in find_candidates(path):
            exe_raw = str(exe)
            exe_id = fs_path_id(exe_raw)
            if exe_id in tested_exes:
                continue
            tested_exes.add(exe_id)
            interpreter = PathPythonInfo.from_exe(exe_raw, app_data, raise_on_error=False, env=env)
            if interpreter is not None:
                yield interpreter, impl_must_match

    # otherwise try uv-managed python (~/.local/share/uv/python or platform equivalent)
    if uv_python_dir := os.getenv("UV_PYTHON_INSTALL_DIR"):
        uv_python_path = Path(uv_python_dir).expanduser()
    elif xdg_data_home := os.getenv("XDG_DATA_HOME"):
        uv_python_path = Path(xdg_data_home).expanduser() / "uv" / "python"
    else:
        uv_python_path = user_data_path("uv") / "python"

    for exe_path in uv_python_path.glob("*/bin/python"):
        interpreter = PathPythonInfo.from_exe(str(exe_path), app_data, raise_on_error=False, env=env)
        if interpreter is not None:
            yield interpreter, True


def get_paths(env: Mapping[str, str]) -> Generator[Path, None, None]:
    path = env.get("PATH", None)
    if path is None:
        try:
            path = os.confstr("CS_PATH")
        except (AttributeError, ValueError):
            path = os.defpath
    if path:
        for p in map(Path, path.split(os.pathsep)):
            with suppress(OSError):
                if p.is_dir() and next(p.iterdir(), None):
                    yield p


class LazyPathDump:
    def __init__(self, pos: int, path: Path, env: Mapping[str, str]) -> None:
        self.pos = pos
        self.path = path
        self.env = env

    def __repr__(self) -> str:
        content = f"discover PATH[{self.pos}]={self.path}"
        if self.env.get("_VIRTUALENV_DEBUG"):  # this is the over the board debug
            content += " with =>"
            for file_path in self.path.iterdir():
                try:
                    if file_path.is_dir():
                        continue
                    if IS_WIN:
                        pathext = self.env.get("PATHEXT", ".COM;.EXE;.BAT;.CMD").split(";")
                        if not any(file_path.name.upper().endswith(ext) for ext in pathext):
                            continue
                    elif not (file_path.stat().st_mode & os.X_OK):
                        continue
                except OSError:
                    pass
                content += " "
                content += file_path.name
        return content


def path_exe_finder(spec: PythonSpec) -> Callable[[Path], Generator[tuple[Path, bool], None, None]]:
    """Given a spec, return a function that can be called on a path to find all matching files in it."""
    pat = spec.generate_re(windows=sys.platform == "win32")
    direct = spec.str_spec
    if sys.platform == "win32":
        direct = f"{direct}.exe"

    def path_exes(path: Path) -> Generator[tuple[Path, bool], None, None]:
        # 4. then maybe it's something exact on PATH - if it was direct lookup implementation no longer counts
        direct_path = path / direct
        if direct_path.exists():
            yield direct_path, False

        # 5. or from the spec we can deduce if a name on path matches
        for exe in path.iterdir():
            match = pat.fullmatch(exe.name)
            if match:
                # the implementation must match when we find “python[ver]”
                yield exe.absolute(), match["impl"] == "python"

    return path_exes


class PathPythonInfo(PythonInfo):
    """python info from path."""


__all__ = [
    "Builtin",
    "PathPythonInfo",
    "get_interpreter",
]
