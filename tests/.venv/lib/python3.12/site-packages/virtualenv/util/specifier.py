"""Version specifier support using only standard library (PEP 440 compatible)."""

from __future__ import annotations

import contextlib
import operator
import re


class SimpleVersion:
    """Simple PEP 440-like version parser using only standard library."""

    def __init__(self, version_str: str) -> None:
        self.version_str = version_str
        # Parse version string into components
        # Support formats like: "3.11", "3.11.0", "3.11.0a1", "3.11.0b2", "3.11.0rc1"
        match = re.match(
            r"^(\d+)(?:\.(\d+))?(?:\.(\d+))?(?:(a|b|rc)(\d+))?$",
            version_str.strip(),
        )
        if not match:
            msg = f"Invalid version: {version_str}"
            raise ValueError(msg)

        self.major = int(match.group(1))
        self.minor = int(match.group(2)) if match.group(2) else 0
        self.micro = int(match.group(3)) if match.group(3) else 0
        self.pre_type = match.group(4)  # a, b, rc or None
        self.pre_num = int(match.group(5)) if match.group(5) else None
        self.release = (self.major, self.minor, self.micro)

    def __eq__(self, other):
        if not isinstance(other, SimpleVersion):
            return NotImplemented
        return self.release == other.release and self.pre_type == other.pre_type and self.pre_num == other.pre_num

    def __hash__(self):
        return hash((self.release, self.pre_type, self.pre_num))

    def __lt__(self, other):
        if not isinstance(other, SimpleVersion):
            return NotImplemented
        # Compare release tuples first
        if self.release != other.release:
            return self.release < other.release
        return self._compare_prerelease(other)

    def _compare_prerelease(self, other):
        """Compare pre-release versions."""
        # If releases are equal, compare pre-release
        # No pre-release is greater than any pre-release
        if self.pre_type is None and other.pre_type is None:
            return False
        if self.pre_type is None:
            return False  # self is final, other is pre-release
        if other.pre_type is None:
            return True  # self is pre-release, other is final
        # Both are pre-releases, compare type then number
        pre_order = {"a": 1, "b": 2, "rc": 3}
        if pre_order[self.pre_type] != pre_order[other.pre_type]:
            return pre_order[self.pre_type] < pre_order[other.pre_type]
        return (self.pre_num or 0) < (other.pre_num or 0)

    def __le__(self, other):
        return self == other or self < other

    def __gt__(self, other):
        if not isinstance(other, SimpleVersion):
            return NotImplemented
        return not self <= other

    def __ge__(self, other):
        return not self < other

    def __str__(self):
        return self.version_str

    def __repr__(self):
        return f"SimpleVersion('{self.version_str}')"


class SimpleSpecifier:
    """Simple PEP 440-like version specifier using only standard library."""

    __slots__ = (
        "is_wildcard",
        "operator",
        "spec_str",
        "version",
        "version_str",
        "wildcard_precision",
        "wildcard_version",
    )

    def __init__(self, spec_str: str) -> None:
        self.spec_str = spec_str.strip()
        # Parse operator and version
        match = re.match(r"^(===|==|~=|!=|<=|>=|<|>)\s*(.+)$", self.spec_str)
        if not match:
            msg = f"Invalid specifier: {spec_str}"
            raise ValueError(msg)

        self.operator = match.group(1)
        self.version_str = match.group(2).strip()

        # Handle wildcard versions like "3.11.*"
        if self.version_str.endswith(".*"):
            self.is_wildcard = True
            self.wildcard_version = self.version_str[:-2]
            # Count the precision for wildcard matching
            self.wildcard_precision = len(self.wildcard_version.split("."))
            self.version_str = self.wildcard_version
        else:
            self.is_wildcard = False
            self.wildcard_precision = None

        try:
            self.version = SimpleVersion(self.version_str)
        except ValueError:
            # If version parsing fails, store as string for prefix matching
            self.version = None

    def contains(self, version_str: str) -> bool:
        """Check if a version string satisfies this specifier."""
        try:
            candidate = SimpleVersion(version_str) if isinstance(version_str, str) else version_str
        except ValueError:
            return False

        if self.version is None:
            return False

        if self.is_wildcard:
            return self._check_wildcard(candidate)
        return self._check_standard(candidate)

    def _check_wildcard(self, candidate):
        """Check wildcard version matching."""
        if self.operator == "==":
            return candidate.release[: self.wildcard_precision] == self.version.release[: self.wildcard_precision]
        if self.operator == "!=":
            return candidate.release[: self.wildcard_precision] != self.version.release[: self.wildcard_precision]
        # Other operators with wildcards are not standard
        return False

    def _check_standard(self, candidate):
        """Check standard version comparisons."""
        if self.operator == "===":
            return str(candidate) == str(self.version)
        if self.operator == "~=":
            return self._check_compatible_release(candidate)
        # Use operator module for comparisons
        cmp_ops = {
            "==": operator.eq,
            "!=": operator.ne,
            "<": operator.lt,
            "<=": operator.le,
            ">": operator.gt,
            ">=": operator.ge,
        }
        if self.operator in cmp_ops:
            return cmp_ops[self.operator](candidate, self.version)
        return False

    def _check_compatible_release(self, candidate):
        """Check compatible release version (~=)."""
        if candidate < self.version:
            return False
        if len(self.version.release) >= 2:  # noqa: PLR2004
            upper_parts = list(self.version.release[:-1])
            upper_parts[-1] += 1
            upper = SimpleVersion(".".join(str(p) for p in upper_parts))
            return candidate < upper
        return True

    def __eq__(self, other):
        if not isinstance(other, SimpleSpecifier):
            return NotImplemented
        return self.spec_str == other.spec_str

    def __hash__(self):
        return hash(self.spec_str)

    def __str__(self):
        return self.spec_str

    def __repr__(self):
        return f"SimpleSpecifier('{self.spec_str}')"


class SimpleSpecifierSet:
    """Simple PEP 440-like specifier set using only standard library."""

    __slots__ = ("specifiers", "specifiers_str")

    def __init__(self, specifiers_str: str = "") -> None:
        self.specifiers_str = specifiers_str.strip()
        self.specifiers = []

        if self.specifiers_str:
            # Split by comma for compound specifiers
            for spec_item in self.specifiers_str.split(","):
                stripped = spec_item.strip()
                if stripped:
                    with contextlib.suppress(ValueError):
                        self.specifiers.append(SimpleSpecifier(stripped))

    def contains(self, version_str: str) -> bool:
        """Check if a version satisfies all specifiers in the set."""
        if not self.specifiers:
            return True
        # All specifiers must be satisfied
        return all(spec.contains(version_str) for spec in self.specifiers)

    def __iter__(self):
        return iter(self.specifiers)

    def __eq__(self, other):
        if not isinstance(other, SimpleSpecifierSet):
            return NotImplemented
        return self.specifiers_str == other.specifiers_str

    def __hash__(self):
        return hash(self.specifiers_str)

    def __str__(self):
        return self.specifiers_str

    def __repr__(self):
        return f"SimpleSpecifierSet('{self.specifiers_str}')"


__all__ = [
    "SimpleSpecifier",
    "SimpleSpecifierSet",
    "SimpleVersion",
]
