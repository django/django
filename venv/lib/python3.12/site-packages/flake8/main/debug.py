"""Module containing the logic for our debugging logic."""
from __future__ import annotations

import platform
from typing import Any

from flake8.plugins.finder import Plugins


def information(version: str, plugins: Plugins) -> dict[str, Any]:
    """Generate the information to be printed for the bug report."""
    versions = sorted(
        {
            (loaded.plugin.package, loaded.plugin.version)
            for loaded in plugins.all_plugins()
            if loaded.plugin.package not in {"flake8", "local"}
        }
    )
    return {
        "version": version,
        "plugins": [
            {"plugin": plugin, "version": version}
            for plugin, version in versions
        ],
        "platform": {
            "python_implementation": platform.python_implementation(),
            "python_version": platform.python_version(),
            "system": platform.system(),
        },
    }
