import glob
import os
import sys
from typing import Any, Iterator
from warnings import warn

import setuptools

from . import api
from .settings import DEFAULT_CONFIG


class ISortCommand(setuptools.Command):
    """The :class:`ISortCommand` class is used by setuptools to perform
    imports checks on registered modules.
    """

    description = "Run isort on modules registered in setuptools"
    # Potentially unused variable - check if can be safely removed
    user_options: list[Any] = []  # type: ignore[misc]

    def initialize_options(self) -> None:
        default_settings = vars(DEFAULT_CONFIG).copy()
        for key, value in default_settings.items():
            setattr(self, key, value)

    def finalize_options(self) -> None:
        """Get options from config files."""
        self.arguments: dict[str, Any] = {}  # skipcq: PYL-W0201
        self.arguments["settings_path"] = os.getcwd()

    def distribution_files(self) -> Iterator[str]:
        """Find distribution packages."""
        # This is verbatim from flake8
        if self.distribution.packages:  # pragma: no cover
            package_dirs = self.distribution.package_dir or {}
            for package in self.distribution.packages:
                pkg_dir = package
                if package in package_dirs:
                    pkg_dir = package_dirs[package]
                elif "" in package_dirs:  # pragma: no cover
                    pkg_dir = package_dirs[""] + os.path.sep + pkg_dir
                yield pkg_dir.replace(".", os.path.sep)

        if self.distribution.py_modules:
            for filename in self.distribution.py_modules:
                yield f"{filename}.py"
        # Don't miss the setup.py file itself
        yield "setup.py"

    def run(self) -> None:
        arguments = self.arguments
        wrong_sorted_files = False
        for path in self.distribution_files():
            for python_file in glob.iglob(os.path.join(path, "*.py")):
                try:
                    if not api.check_file(python_file, **arguments):
                        wrong_sorted_files = True  # pragma: no cover
                except OSError as error:  # pragma: no cover
                    warn(f"Unable to parse file {python_file} due to {error}", stacklevel=2)
        if wrong_sorted_files:
            sys.exit(1)  # pragma: no cover
