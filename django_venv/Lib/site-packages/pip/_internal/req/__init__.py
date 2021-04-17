from __future__ import absolute_import

import logging

from .req_install import InstallRequirement
from .req_set import RequirementSet
from .req_file import parse_requirements
from pip._internal.utils.logging import indent_log
from pip._internal.utils.typing import MYPY_CHECK_RUNNING

if MYPY_CHECK_RUNNING:
    from typing import Any, List, Sequence

__all__ = [
    "RequirementSet", "InstallRequirement",
    "parse_requirements", "install_given_reqs",
]

logger = logging.getLogger(__name__)


def install_given_reqs(
    to_install,  # type: List[InstallRequirement]
    install_options,  # type: List[str]
    global_options=(),  # type: Sequence[str]
    *args,  # type: Any
    **kwargs  # type: Any
):
    # type: (...) -> List[InstallRequirement]
    """
    Install everything in the given list.

    (to be called after having downloaded and unpacked the packages)
    """

    if to_install:
        logger.info(
            'Installing collected packages: %s',
            ', '.join([req.name for req in to_install]),
        )

    with indent_log():
        for requirement in to_install:
            if requirement.conflicts_with:
                logger.info(
                    'Found existing installation: %s',
                    requirement.conflicts_with,
                )
                with indent_log():
                    uninstalled_pathset = requirement.uninstall(
                        auto_confirm=True
                    )
            try:
                requirement.install(
                    install_options,
                    global_options,
                    *args,
                    **kwargs
                )
            except Exception:
                should_rollback = (
                    requirement.conflicts_with and
                    not requirement.install_succeeded
                )
                # if install did not succeed, rollback previous uninstall
                if should_rollback:
                    uninstalled_pathset.rollback()
                raise
            else:
                should_commit = (
                    requirement.conflicts_with and
                    requirement.install_succeeded
                )
                if should_commit:
                    uninstalled_pathset.commit()
            requirement.remove_temporary_source()

    return to_install
