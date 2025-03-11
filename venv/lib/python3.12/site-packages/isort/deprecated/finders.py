"""Finders try to find right section for passed module name"""

import importlib.machinery
import inspect
import os
import os.path
import re
import sys
import sysconfig
from abc import ABCMeta, abstractmethod
from contextlib import contextmanager
from fnmatch import fnmatch
from functools import lru_cache
from glob import glob
from pathlib import Path
from typing import Dict, Iterable, Iterator, List, Optional, Pattern, Sequence, Tuple, Type

from isort import sections
from isort.settings import KNOWN_SECTION_MAPPING, Config
from isort.utils import exists_case_sensitive

try:
    from pipreqs import pipreqs  # type: ignore

except ImportError:
    pipreqs = None

try:
    from pip_api import parse_requirements  # type: ignore

except ImportError:
    parse_requirements = None  # type: ignore[assignment]


@contextmanager
def chdir(path: str) -> Iterator[None]:
    """Context manager for changing dir and restoring previous workdir after exit."""
    curdir = os.getcwd()
    os.chdir(path)
    try:
        yield
    finally:
        os.chdir(curdir)


class BaseFinder(metaclass=ABCMeta):
    def __init__(self, config: Config) -> None:
        self.config = config

    @abstractmethod
    def find(self, module_name: str) -> Optional[str]:
        raise NotImplementedError


class ForcedSeparateFinder(BaseFinder):
    def find(self, module_name: str) -> Optional[str]:
        for forced_separate in self.config.forced_separate:
            # Ensure all forced_separate patterns will match to end of string
            path_glob = forced_separate
            if not forced_separate.endswith("*"):
                path_glob = f"{forced_separate}*"

            if fnmatch(module_name, path_glob) or fnmatch(module_name, "." + path_glob):
                return forced_separate
        return None


class LocalFinder(BaseFinder):
    def find(self, module_name: str) -> Optional[str]:
        if module_name.startswith("."):
            return "LOCALFOLDER"
        return None


class KnownPatternFinder(BaseFinder):
    def __init__(self, config: Config) -> None:
        super().__init__(config)

        self.known_patterns: List[Tuple[Pattern[str], str]] = []
        for placement in reversed(config.sections):
            known_placement = KNOWN_SECTION_MAPPING.get(placement, placement).lower()
            config_key = f"known_{known_placement}"
            known_patterns = list(
                getattr(self.config, config_key, self.config.known_other.get(known_placement, []))
            )
            known_patterns = [
                pattern
                for known_pattern in known_patterns
                for pattern in self._parse_known_pattern(known_pattern)
            ]
            for known_pattern in known_patterns:
                regexp = "^" + known_pattern.replace("*", ".*").replace("?", ".?") + "$"
                self.known_patterns.append((re.compile(regexp), placement))

    def _parse_known_pattern(self, pattern: str) -> List[str]:
        """Expand pattern if identified as a directory and return found sub packages"""
        if pattern.endswith(os.path.sep):
            patterns = [
                filename
                for filename in os.listdir(os.path.join(self.config.directory, pattern))
                if os.path.isdir(os.path.join(self.config.directory, pattern, filename))
            ]
        else:
            patterns = [pattern]

        return patterns

    def find(self, module_name: str) -> Optional[str]:
        # Try to find most specific placement instruction match (if any)
        parts = module_name.split(".")
        module_names_to_check = (".".join(parts[:first_k]) for first_k in range(len(parts), 0, -1))
        for module_name_to_check in module_names_to_check:
            for pattern, placement in self.known_patterns:
                if pattern.match(module_name_to_check):
                    return placement
        return None


class PathFinder(BaseFinder):
    def __init__(self, config: Config, path: str = ".") -> None:
        super().__init__(config)

        # restore the original import path (i.e. not the path to bin/isort)
        root_dir = os.path.abspath(path)
        src_dir = f"{root_dir}/src"
        self.paths = [root_dir, src_dir]

        # virtual env
        self.virtual_env = self.config.virtual_env or os.environ.get("VIRTUAL_ENV")
        if self.virtual_env:
            self.virtual_env = os.path.realpath(self.virtual_env)
        self.virtual_env_src = ""
        if self.virtual_env:
            self.virtual_env_src = f"{self.virtual_env}/src/"
            for venv_path in glob(f"{self.virtual_env}/lib/python*/site-packages"):
                if venv_path not in self.paths:
                    self.paths.append(venv_path)
            for nested_venv_path in glob(f"{self.virtual_env}/lib/python*/*/site-packages"):
                if nested_venv_path not in self.paths:
                    self.paths.append(nested_venv_path)
            for venv_src_path in glob(f"{self.virtual_env}/src/*"):
                if os.path.isdir(venv_src_path):
                    self.paths.append(venv_src_path)

        # conda
        self.conda_env = self.config.conda_env or os.environ.get("CONDA_PREFIX") or ""
        if self.conda_env:
            self.conda_env = os.path.realpath(self.conda_env)
            for conda_path in glob(f"{self.conda_env}/lib/python*/site-packages"):
                if conda_path not in self.paths:
                    self.paths.append(conda_path)
            for nested_conda_path in glob(f"{self.conda_env}/lib/python*/*/site-packages"):
                if nested_conda_path not in self.paths:
                    self.paths.append(nested_conda_path)

        # handle case-insensitive paths on windows
        self.stdlib_lib_prefix = os.path.normcase(sysconfig.get_paths()["stdlib"])
        if self.stdlib_lib_prefix not in self.paths:
            self.paths.append(self.stdlib_lib_prefix)

        # add system paths
        for system_path in sys.path[1:]:
            if system_path not in self.paths:
                self.paths.append(system_path)

    def find(self, module_name: str) -> Optional[str]:
        for prefix in self.paths:
            package_path = "/".join((prefix, module_name.split(".")[0]))
            path_obj = Path(package_path).resolve()
            is_module = (
                exists_case_sensitive(package_path + ".py")
                or any(
                    exists_case_sensitive(package_path + ext_suffix)
                    for ext_suffix in importlib.machinery.EXTENSION_SUFFIXES
                )
                or exists_case_sensitive(package_path + "/__init__.py")
            )
            is_package = exists_case_sensitive(package_path) and os.path.isdir(package_path)
            if is_module or is_package:
                if (
                    "site-packages" in prefix
                    or "dist-packages" in prefix
                    or (self.virtual_env and self.virtual_env_src in prefix)
                ):
                    return sections.THIRDPARTY
                if os.path.normcase(prefix) == self.stdlib_lib_prefix:
                    return sections.STDLIB
                if self.conda_env and self.conda_env in prefix:
                    return sections.THIRDPARTY
                for src_path in self.config.src_paths:
                    if src_path in path_obj.parents and not self.config.is_skipped(path_obj):
                        return sections.FIRSTPARTY

                if os.path.normcase(prefix).startswith(self.stdlib_lib_prefix):
                    return sections.STDLIB  # pragma: no cover - edge case for one OS. Hard to test.

                return self.config.default_section
        return None


class ReqsBaseFinder(BaseFinder):
    enabled = False

    def __init__(self, config: Config, path: str = ".") -> None:
        super().__init__(config)
        self.path = path
        if self.enabled:
            self.mapping = self._load_mapping()
            self.names = self._load_names()

    @abstractmethod
    def _get_names(self, path: str) -> Iterator[str]:
        raise NotImplementedError

    @abstractmethod
    def _get_files_from_dir(self, path: str) -> Iterator[str]:
        raise NotImplementedError

    @staticmethod
    def _load_mapping() -> Optional[Dict[str, str]]:
        """Return list of mappings `package_name -> module_name`

        Example:
            django-haystack -> haystack
        """
        if not pipreqs:
            return None
        path = os.path.dirname(inspect.getfile(pipreqs))
        path = os.path.join(path, "mapping")
        with open(path) as f:
            mappings: Dict[str, str] = {}  # pypi_name: import_name
            for line in f:
                import_name, _, pypi_name = line.strip().partition(":")
                mappings[pypi_name] = import_name
            return mappings

    def _load_names(self) -> List[str]:
        """Return list of thirdparty modules from requirements"""
        names: List[str] = []
        for path in self._get_files():
            names.extend(self._normalize_name(name) for name in self._get_names(path))
        return names

    @staticmethod
    def _get_parents(path: str) -> Iterator[str]:
        prev = ""
        while path != prev:
            prev = path
            yield path
            path = os.path.dirname(path)

    def _get_files(self) -> Iterator[str]:
        """Return paths to all requirements files"""
        path = os.path.abspath(self.path)
        if os.path.isfile(path):
            path = os.path.dirname(path)

        for path in self._get_parents(path):  # noqa
            yield from self._get_files_from_dir(path)

    def _normalize_name(self, name: str) -> str:
        """Convert package name to module name

        Examples:
            Django -> django
            django-haystack -> django_haystack
            Flask-RESTFul -> flask_restful
        """
        if self.mapping:
            name = self.mapping.get(name.replace("-", "_"), name)
        return name.lower().replace("-", "_")

    def find(self, module_name: str) -> Optional[str]:
        # required lib not installed yet
        if not self.enabled:
            return None

        module_name, _sep, _submodules = module_name.partition(".")
        module_name = module_name.lower()
        if not module_name:
            return None

        for name in self.names:
            if module_name == name:
                return sections.THIRDPARTY
        return None


class RequirementsFinder(ReqsBaseFinder):
    exts = (".txt", ".in")
    enabled = bool(parse_requirements)

    def _get_files_from_dir(self, path: str) -> Iterator[str]:
        """Return paths to requirements files from passed dir."""
        yield from self._get_files_from_dir_cached(path)

    @classmethod
    @lru_cache(maxsize=16)
    def _get_files_from_dir_cached(cls, path: str) -> List[str]:
        results: List[str] = []

        for fname in os.listdir(path):
            if "requirements" not in fname:
                continue
            full_path = os.path.join(path, fname)

            # *requirements*/*.{txt,in}
            if os.path.isdir(full_path):
                for subfile_name in os.listdir(full_path):
                    results.extend(
                        os.path.join(full_path, subfile_name)
                        for ext in cls.ext  # type: ignore[attr-defined]
                        if subfile_name.endswith(ext)
                    )
                continue

            # *requirements*.{txt,in}
            if os.path.isfile(full_path):
                for ext in cls.exts:
                    if fname.endswith(ext):
                        results.append(full_path)
                        break

        return results

    def _get_names(self, path: str) -> Iterator[str]:
        """Load required packages from path to requirements file"""
        yield from self._get_names_cached(path)

    @classmethod
    @lru_cache(maxsize=16)
    def _get_names_cached(cls, path: str) -> List[str]:
        result: List[str] = []

        with chdir(os.path.dirname(path)):
            requirements = parse_requirements(Path(path))
            result.extend(req.name for req in requirements.values() if req.name)

        return result


class DefaultFinder(BaseFinder):
    def find(self, module_name: str) -> Optional[str]:
        return self.config.default_section


class FindersManager:
    _default_finders_classes: Sequence[Type[BaseFinder]] = (
        ForcedSeparateFinder,
        LocalFinder,
        KnownPatternFinder,
        PathFinder,
        RequirementsFinder,
        DefaultFinder,
    )

    def __init__(
        self, config: Config, finder_classes: Optional[Iterable[Type[BaseFinder]]] = None
    ) -> None:
        self.verbose: bool = config.verbose

        if finder_classes is None:
            finder_classes = self._default_finders_classes
        finders: List[BaseFinder] = []
        for finder_cls in finder_classes:
            try:
                finders.append(finder_cls(config))
            except Exception as exception:
                # if one finder fails to instantiate isort can continue using the rest
                if self.verbose:
                    print(
                        (
                            f"{finder_cls.__name__} encountered an error ({exception}) during "
                            "instantiation and cannot be used"
                        )
                    )
        self.finders: Tuple[BaseFinder, ...] = tuple(finders)

    def find(self, module_name: str) -> Optional[str]:
        for finder in self.finders:
            try:
                section = finder.find(module_name)
                if section is not None:
                    return section
            except Exception as exception:
                # isort has to be able to keep trying to identify the correct
                # import section even if one approach fails
                if self.verbose:
                    print(
                        f"{finder.__class__.__name__} encountered an error ({exception}) while "
                        f"trying to identify the {module_name} module"
                    )
        return None
