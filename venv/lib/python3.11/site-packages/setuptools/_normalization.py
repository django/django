"""
Helpers for normalization as expected in wheel/sdist/module file names
and core metadata
"""
import re
from pathlib import Path
from typing import Union

from .extern import packaging
from .warnings import SetuptoolsDeprecationWarning

_Path = Union[str, Path]

# https://packaging.python.org/en/latest/specifications/core-metadata/#name
_VALID_NAME = re.compile(r"^([A-Z0-9]|[A-Z0-9][A-Z0-9._-]*[A-Z0-9])$", re.I)
_UNSAFE_NAME_CHARS = re.compile(r"[^A-Z0-9.]+", re.I)
_NON_ALPHANUMERIC = re.compile(r"[^A-Z0-9]+", re.I)


def safe_identifier(name: str) -> str:
    """Make a string safe to be used as Python identifier.
    >>> safe_identifier("12abc")
    '_12abc'
    >>> safe_identifier("__editable__.myns.pkg-78.9.3_local")
    '__editable___myns_pkg_78_9_3_local'
    """
    safe = re.sub(r'\W|^(?=\d)', '_', name)
    assert safe.isidentifier()
    return safe


def safe_name(component: str) -> str:
    """Escape a component used as a project name according to Core Metadata.
    >>> safe_name("hello world")
    'hello-world'
    >>> safe_name("hello?world")
    'hello-world'
    """
    # See pkg_resources.safe_name
    return _UNSAFE_NAME_CHARS.sub("-", component)


def safe_version(version: str) -> str:
    """Convert an arbitrary string into a valid version string.
    >>> safe_version("1988 12 25")
    '1988.12.25'
    >>> safe_version("v0.2.1")
    '0.2.1'
    >>> safe_version("v0.2?beta")
    '0.2b0'
    >>> safe_version("v0.2 beta")
    '0.2b0'
    >>> safe_version("ubuntu lts")
    Traceback (most recent call last):
    ...
    setuptools.extern.packaging.version.InvalidVersion: Invalid version: 'ubuntu.lts'
    """
    v = version.replace(' ', '.')
    try:
        return str(packaging.version.Version(v))
    except packaging.version.InvalidVersion:
        attempt = _UNSAFE_NAME_CHARS.sub("-", v)
        return str(packaging.version.Version(attempt))


def best_effort_version(version: str) -> str:
    """Convert an arbitrary string into a version-like string.
    >>> best_effort_version("v0.2 beta")
    '0.2b0'

    >>> import warnings
    >>> warnings.simplefilter("ignore", category=SetuptoolsDeprecationWarning)
    >>> best_effort_version("ubuntu lts")
    'ubuntu.lts'
    """
    # See pkg_resources.safe_version
    try:
        return safe_version(version)
    except packaging.version.InvalidVersion:
        SetuptoolsDeprecationWarning.emit(
            f"Invalid version: {version!r}.",
            f"""
            Version {version!r} is not valid according to PEP 440.

            Please make sure to specify a valid version for your package.
            Also note that future releases of setuptools may halt the build process
            if an invalid version is given.
            """,
            see_url="https://peps.python.org/pep-0440/",
            due_date=(2023, 9, 26),  # See setuptools/dist _validate_version
        )
        v = version.replace(' ', '.')
        return safe_name(v)


def safe_extra(extra: str) -> str:
    """Normalize extra name according to PEP 685
    >>> safe_extra("_FrIeNdLy-._.-bArD")
    'friendly-bard'
    >>> safe_extra("FrIeNdLy-._.-bArD__._-")
    'friendly-bard'
    """
    return _NON_ALPHANUMERIC.sub("-", extra).strip("-").lower()


def filename_component(value: str) -> str:
    """Normalize each component of a filename (e.g. distribution/version part of wheel)
    Note: ``value`` needs to be already normalized.
    >>> filename_component("my-pkg")
    'my_pkg'
    """
    return value.replace("-", "_").strip("_")


def safer_name(value: str) -> str:
    """Like ``safe_name`` but can be used as filename component for wheel"""
    # See bdist_wheel.safer_name
    return filename_component(safe_name(value))


def safer_best_effort_version(value: str) -> str:
    """Like ``best_effort_version`` but can be used as filename component for wheel"""
    # See bdist_wheel.safer_verion
    # TODO: Replace with only safe_version in the future (no need for best effort)
    return filename_component(best_effort_version(value))
