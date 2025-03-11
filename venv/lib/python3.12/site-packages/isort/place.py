"""Contains all logic related to placing an import within a certain section."""

import importlib
from fnmatch import fnmatch
from functools import lru_cache
from pathlib import Path
from typing import FrozenSet, Iterable, Optional, Tuple

from isort import sections
from isort.settings import DEFAULT_CONFIG, Config
from isort.utils import exists_case_sensitive

LOCAL = "LOCALFOLDER"


def module(name: str, config: Config = DEFAULT_CONFIG) -> str:
    """Returns the section placement for the given module name."""
    return module_with_reason(name, config)[0]


@lru_cache(maxsize=1000)
def module_with_reason(name: str, config: Config = DEFAULT_CONFIG) -> Tuple[str, str]:
    """Returns the section placement for the given module name alongside the reasoning."""
    return (
        _forced_separate(name, config)
        or _local(name, config)
        or _known_pattern(name, config)
        or _src_path(name, config)
        or (config.default_section, "Default option in Config or universal default.")
    )


def _forced_separate(name: str, config: Config) -> Optional[Tuple[str, str]]:
    for forced_separate in config.forced_separate:
        # Ensure all forced_separate patterns will match to end of string
        path_glob = forced_separate
        if not forced_separate.endswith("*"):
            path_glob = f"{forced_separate}*"

        if fnmatch(name, path_glob) or fnmatch(name, "." + path_glob):
            return (forced_separate, f"Matched forced_separate ({forced_separate}) config value.")

    return None


def _local(name: str, config: Config) -> Optional[Tuple[str, str]]:
    if name.startswith("."):
        return (LOCAL, "Module name started with a dot.")

    return None


def _known_pattern(name: str, config: Config) -> Optional[Tuple[str, str]]:
    parts = name.split(".")
    module_names_to_check = (".".join(parts[:first_k]) for first_k in range(len(parts), 0, -1))
    for module_name_to_check in module_names_to_check:
        for pattern, placement in config.known_patterns:
            if placement in config.sections and pattern.match(module_name_to_check):
                return (placement, f"Matched configured known pattern {pattern}")

    return None


def _src_path(
    name: str,
    config: Config,
    src_paths: Optional[Iterable[Path]] = None,
    prefix: Tuple[str, ...] = (),
) -> Optional[Tuple[str, str]]:
    if src_paths is None:
        src_paths = config.src_paths

    root_module_name, *nested_module = name.split(".", 1)
    new_prefix = (*prefix, root_module_name)
    namespace = ".".join(new_prefix)

    for src_path in src_paths:
        module_path = (src_path / root_module_name).resolve()
        if not prefix and not module_path.is_dir() and src_path.name == root_module_name:
            module_path = src_path.resolve()
        if nested_module and (
            namespace in config.namespace_packages
            or (
                config.auto_identify_namespace_packages
                and _is_namespace_package(module_path, config.supported_extensions)
            )
        ):
            return _src_path(nested_module[0], config, (module_path,), new_prefix)
        if (
            _is_module(module_path)
            or _is_package(module_path)
            or _src_path_is_module(src_path, root_module_name)
        ):
            return (sections.FIRSTPARTY, f"Found in one of the configured src_paths: {src_path}.")

    return None


def _is_module(path: Path) -> bool:
    return (
        exists_case_sensitive(str(path.with_suffix(".py")))
        or any(
            exists_case_sensitive(str(path.with_suffix(ext_suffix)))
            for ext_suffix in importlib.machinery.EXTENSION_SUFFIXES
        )
        or exists_case_sensitive(str(path / "__init__.py"))
    )


def _is_package(path: Path) -> bool:
    return exists_case_sensitive(str(path)) and path.is_dir()


def _is_namespace_package(path: Path, src_extensions: FrozenSet[str]) -> bool:
    if not _is_package(path):
        return False

    init_file = path / "__init__.py"
    if not init_file.exists():
        filenames = [
            filepath
            for filepath in path.iterdir()
            if filepath.suffix.lstrip(".") in src_extensions
            or filepath.name.lower() in ("setup.cfg", "pyproject.toml")
        ]
        if filenames:
            return False
    else:
        with init_file.open("rb") as open_init_file:
            file_start = open_init_file.read(4096)
            if (
                b"__import__('pkg_resources').declare_namespace(__name__)" not in file_start
                and b'__import__("pkg_resources").declare_namespace(__name__)' not in file_start
                and b"__path__ = __import__('pkgutil').extend_path(__path__, __name__)"
                not in file_start
                and b'__path__ = __import__("pkgutil").extend_path(__path__, __name__)'
                not in file_start
            ):
                return False
    return True


def _src_path_is_module(src_path: Path, module_name: str) -> bool:
    return (
        module_name == src_path.name and src_path.is_dir() and exists_case_sensitive(str(src_path))
    )
