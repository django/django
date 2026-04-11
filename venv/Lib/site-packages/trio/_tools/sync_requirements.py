#!/usr/bin/env python3

"""Sync Requirements - Automatically upgrade test requirements pinned
versions from pre-commit config file."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import TYPE_CHECKING

from yaml import load as load_yaml

if TYPE_CHECKING:
    from collections.abc import Generator

    from yaml import CLoader as _CLoader, Loader as _Loader

    Loader: type[_CLoader | _Loader]

try:
    from yaml import CLoader as Loader
except ImportError:
    from yaml import Loader


def yield_pre_commit_version_data(
    pre_commit_text: str,
) -> Generator[tuple[str, str], None, None]:
    """Yield (name, rev) tuples from pre-commit config file."""
    pre_commit_config = load_yaml(pre_commit_text, Loader)
    for repo in pre_commit_config["repos"]:
        if "repo" not in repo or "rev" not in repo:
            continue
        url = repo["repo"]
        name = url.rsplit("/", 1)[-1]
        rev = repo["rev"].removeprefix("v")
        yield name, rev


def update_requirements(
    requirements: Path,
    version_data: dict[str, str],
) -> bool:
    """Return if updated requirements file.

    Update requirements file to match versions in version_data."""
    changed = False
    old_lines = requirements.read_text(encoding="utf-8").splitlines(True)

    with requirements.open("w", encoding="utf-8") as file:
        for line in old_lines:
            # If comment or not version mark line, ignore.
            if line.startswith("#") or "==" not in line:
                file.write(line)
                continue
            name, rest = line.split("==", 1)
            # Maintain extra markers if they exist
            old_version = rest.strip()
            extra = "\n"
            if ";" in rest:
                old_version, extra = rest.split(";", 1)
                old_version = old_version.strip()
                extra = " ;" + extra
            version = version_data.get(name)
            # If does not exist, skip
            if version is None:
                file.write(line)
                continue
            # Otherwise might have changed
            new_line = f"{name}=={version}{extra}"
            if new_line != line:
                if not changed:
                    changed = True
                    print("Changed test requirements version to match pre-commit")
                print(f"{name}=={old_version} -> {name}=={version}")
            file.write(new_line)
    return changed


if __name__ == "__main__":
    source_root = Path.cwd().absolute()

    # Double-check we found the right directory
    assert (source_root / "LICENSE").exists()
    pre_commit = source_root / ".pre-commit-config.yaml"
    test_requirements = source_root / "test-requirements.txt"

    pre_commit_text = pre_commit.read_text(encoding="utf-8")

    # Get tool versions from pre-commit
    # Get correct names
    pre_commit_versions = {
        name.removesuffix("-mirror").removesuffix("-pre-commit"): version
        for name, version in yield_pre_commit_version_data(pre_commit_text)
    }
    changed = update_requirements(test_requirements, pre_commit_versions)
    sys.exit(int(changed))
