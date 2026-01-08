"""A Python specification is an abstract requirement definition of an interpreter."""

from __future__ import annotations

import contextlib
import os
import re

from virtualenv.util.specifier import SimpleSpecifierSet, SimpleVersion

PATTERN = re.compile(r"^(?P<impl>[a-zA-Z]+)?(?P<version>[0-9.]+)?(?P<threaded>t)?(?:-(?P<arch>32|64))?$")
SPECIFIER_PATTERN = re.compile(r"^(?:(?P<impl>[A-Za-z]+)\s*)?(?P<spec>(?:===|==|~=|!=|<=|>=|<|>).+)$")


class PythonSpec:
    """Contains specification about a Python Interpreter."""

    def __init__(  # noqa: PLR0913
        self,
        str_spec: str,
        implementation: str | None,
        major: int | None,
        minor: int | None,
        micro: int | None,
        architecture: int | None,
        path: str | None,
        *,
        free_threaded: bool | None = None,
        version_specifier: SpecifierSet | None = None,
    ) -> None:
        self.str_spec = str_spec
        self.implementation = implementation
        self.major = major
        self.minor = minor
        self.micro = micro
        self.free_threaded = free_threaded
        self.architecture = architecture
        self.path = path
        self.version_specifier = version_specifier

    @classmethod
    def from_string_spec(cls, string_spec: str):  # noqa: C901, PLR0912
        impl, major, minor, micro, threaded, arch, path = None, None, None, None, None, None, None
        version_specifier = None
        if os.path.isabs(string_spec):  # noqa: PLR1702
            path = string_spec
        else:
            ok = False
            match = re.match(PATTERN, string_spec)
            if match:

                def _int_or_none(val):
                    return None if val is None else int(val)

                try:
                    groups = match.groupdict()
                    version = groups["version"]
                    if version is not None:
                        versions = tuple(int(i) for i in version.split(".") if i)
                        if len(versions) > 3:  # noqa: PLR2004
                            raise ValueError  # noqa: TRY301
                        if len(versions) == 3:  # noqa: PLR2004
                            major, minor, micro = versions
                        elif len(versions) == 2:  # noqa: PLR2004
                            major, minor = versions
                        elif len(versions) == 1:
                            version_data = versions[0]
                            major = int(str(version_data)[0])  # first digit major
                            if version_data > 9:  # noqa: PLR2004
                                minor = int(str(version_data)[1:])
                        threaded = bool(groups["threaded"])
                    ok = True
                except ValueError:
                    pass
                else:
                    impl = groups["impl"]
                    if impl in {"py", "python"}:
                        impl = None
                    arch = _int_or_none(groups["arch"])

            if not ok:
                specifier_match = SPECIFIER_PATTERN.match(string_spec.strip())
                if specifier_match and SpecifierSet is not None:
                    impl = specifier_match.group("impl")
                    spec_text = specifier_match.group("spec").strip()
                    try:
                        version_specifier = SpecifierSet(spec_text)
                    except InvalidSpecifier:
                        pass
                    else:
                        if impl in {"py", "python"}:
                            impl = None
                        return cls(
                            string_spec,
                            impl,
                            None,
                            None,
                            None,
                            None,
                            None,
                            free_threaded=None,
                            version_specifier=version_specifier,
                        )
                path = string_spec

        return cls(
            string_spec,
            impl,
            major,
            minor,
            micro,
            arch,
            path,
            free_threaded=threaded,
            version_specifier=version_specifier,
        )

    def generate_re(self, *, windows: bool) -> re.Pattern:
        """Generate a regular expression for matching against a filename."""
        version = r"{}(\.{}(\.{})?)?".format(
            *(r"\d+" if v is None else v for v in (self.major, self.minor, self.micro))
        )
        impl = "python" if self.implementation is None else f"python|{re.escape(self.implementation)}"
        mod = "t?" if self.free_threaded else ""
        suffix = r"\.exe" if windows else ""
        version_conditional = (
            "?"
            # Windows Python executables are almost always unversioned
            if windows
            # Spec is an empty string
            or self.major is None
            else ""
        )
        # Try matching `direct` first, so the `direct` group is filled when possible.
        return re.compile(
            rf"(?P<impl>{impl})(?P<v>{version}{mod}){version_conditional}{suffix}$",
            flags=re.IGNORECASE,
        )

    @property
    def is_abs(self):
        return self.path is not None and os.path.isabs(self.path)

    def _check_version_specifier(self, spec):
        """Check if version specifier is satisfied."""
        components: list[int] = []
        for part in (self.major, self.minor, self.micro):
            if part is None:
                break
            components.append(part)
        if not components:
            return True

        version_str = ".".join(str(part) for part in components)
        with contextlib.suppress(InvalidVersion):
            Version(version_str)
            for item in spec.version_specifier:
                # Check precision requirements
                required_precision = self._get_required_precision(item)
                if required_precision is None or len(components) < required_precision:
                    continue
                if not item.contains(version_str):
                    return False
        return True

    @staticmethod
    def _get_required_precision(item):
        """Get the required precision for a specifier item."""
        with contextlib.suppress(AttributeError, ValueError):
            return len(item.version.release)
        return None

    def satisfies(self, spec):  # noqa: PLR0911
        """Called when there's a candidate metadata spec to see if compatible - e.g. PEP-514 on Windows."""
        if spec.is_abs and self.is_abs and self.path != spec.path:
            return False
        if spec.implementation is not None and spec.implementation.lower() != self.implementation.lower():
            return False
        if spec.architecture is not None and spec.architecture != self.architecture:
            return False
        if spec.free_threaded is not None and spec.free_threaded != self.free_threaded:
            return False

        if spec.version_specifier is not None and not self._check_version_specifier(spec):
            return False

        for our, req in zip((self.major, self.minor, self.micro), (spec.major, spec.minor, spec.micro)):
            if req is not None and our is not None and our != req:
                return False
        return True

    def __repr__(self) -> str:
        name = type(self).__name__
        params = (
            "implementation",
            "major",
            "minor",
            "micro",
            "architecture",
            "path",
            "free_threaded",
            "version_specifier",
        )
        return f"{name}({', '.join(f'{k}={getattr(self, k)}' for k in params if getattr(self, k) is not None)})"


# Create aliases for backward compatibility
SpecifierSet = SimpleSpecifierSet
Version = SimpleVersion
InvalidSpecifier = ValueError
InvalidVersion = ValueError

__all__ = [
    "InvalidSpecifier",
    "InvalidVersion",
    "PythonSpec",
    "SpecifierSet",
    "Version",
]
