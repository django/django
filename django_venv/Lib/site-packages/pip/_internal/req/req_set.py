from __future__ import absolute_import

import logging
from collections import OrderedDict

from pip._internal.exceptions import InstallationError
from pip._internal.utils.logging import indent_log
from pip._internal.utils.typing import MYPY_CHECK_RUNNING
from pip._internal.wheel import Wheel

if MYPY_CHECK_RUNNING:
    from typing import Dict, Iterable, List, Optional, Tuple
    from pip._internal.req.req_install import InstallRequirement


logger = logging.getLogger(__name__)


class RequirementSet(object):

    def __init__(self, require_hashes=False, check_supported_wheels=True):
        # type: (bool, bool) -> None
        """Create a RequirementSet.
        """

        self.requirements = OrderedDict()  # type: Dict[str, InstallRequirement]  # noqa: E501
        self.require_hashes = require_hashes
        self.check_supported_wheels = check_supported_wheels

        # Mapping of alias: real_name
        self.requirement_aliases = {}  # type: Dict[str, str]
        self.unnamed_requirements = []  # type: List[InstallRequirement]
        self.successfully_downloaded = []  # type: List[InstallRequirement]
        self.reqs_to_cleanup = []  # type: List[InstallRequirement]

    def __str__(self):
        # type: () -> str
        reqs = [req for req in self.requirements.values()
                if not req.comes_from]
        reqs.sort(key=lambda req: req.name.lower())
        return ' '.join([str(req.req) for req in reqs])

    def __repr__(self):
        # type: () -> str
        reqs = [req for req in self.requirements.values()]
        reqs.sort(key=lambda req: req.name.lower())
        reqs_str = ', '.join([str(req.req) for req in reqs])
        return ('<%s object; %d requirement(s): %s>'
                % (self.__class__.__name__, len(reqs), reqs_str))

    def add_requirement(
        self,
        install_req,  # type: InstallRequirement
        parent_req_name=None,  # type: Optional[str]
        extras_requested=None  # type: Optional[Iterable[str]]
    ):
        # type: (...) -> Tuple[List[InstallRequirement], Optional[InstallRequirement]]  # noqa: E501
        """Add install_req as a requirement to install.

        :param parent_req_name: The name of the requirement that needed this
            added. The name is used because when multiple unnamed requirements
            resolve to the same name, we could otherwise end up with dependency
            links that point outside the Requirements set. parent_req must
            already be added. Note that None implies that this is a user
            supplied requirement, vs an inferred one.
        :param extras_requested: an iterable of extras used to evaluate the
            environment markers.
        :return: Additional requirements to scan. That is either [] if
            the requirement is not applicable, or [install_req] if the
            requirement is applicable and has just been added.
        """
        name = install_req.name

        # If the markers do not match, ignore this requirement.
        if not install_req.match_markers(extras_requested):
            logger.info(
                "Ignoring %s: markers '%s' don't match your environment",
                name, install_req.markers,
            )
            return [], None

        # If the wheel is not supported, raise an error.
        # Should check this after filtering out based on environment markers to
        # allow specifying different wheels based on the environment/OS, in a
        # single requirements file.
        if install_req.link and install_req.link.is_wheel:
            wheel = Wheel(install_req.link.filename)
            if self.check_supported_wheels and not wheel.supported():
                raise InstallationError(
                    "%s is not a supported wheel on this platform." %
                    wheel.filename
                )

        # This next bit is really a sanity check.
        assert install_req.is_direct == (parent_req_name is None), (
            "a direct req shouldn't have a parent and also, "
            "a non direct req should have a parent"
        )

        # Unnamed requirements are scanned again and the requirement won't be
        # added as a dependency until after scanning.
        if not name:
            # url or path requirement w/o an egg fragment
            self.unnamed_requirements.append(install_req)
            return [install_req], None

        try:
            existing_req = self.get_requirement(name)
        except KeyError:
            existing_req = None

        has_conflicting_requirement = (
            parent_req_name is None and
            existing_req and
            not existing_req.constraint and
            existing_req.extras == install_req.extras and
            existing_req.req.specifier != install_req.req.specifier
        )
        if has_conflicting_requirement:
            raise InstallationError(
                "Double requirement given: %s (already in %s, name=%r)"
                % (install_req, existing_req, name)
            )

        # When no existing requirement exists, add the requirement as a
        # dependency and it will be scanned again after.
        if not existing_req:
            self.requirements[name] = install_req
            # FIXME: what about other normalizations?  E.g., _ vs. -?
            if name.lower() != name:
                self.requirement_aliases[name.lower()] = name
            # We'd want to rescan this requirements later
            return [install_req], install_req

        # Assume there's no need to scan, and that we've already
        # encountered this for scanning.
        if install_req.constraint or not existing_req.constraint:
            return [], existing_req

        does_not_satisfy_constraint = (
            install_req.link and
            not (
                existing_req.link and
                install_req.link.path == existing_req.link.path
            )
        )
        if does_not_satisfy_constraint:
            self.reqs_to_cleanup.append(install_req)
            raise InstallationError(
                "Could not satisfy constraints for '%s': "
                "installation from path or url cannot be "
                "constrained to a version" % name,
            )
        # If we're now installing a constraint, mark the existing
        # object for real installation.
        existing_req.constraint = False
        existing_req.extras = tuple(sorted(
            set(existing_req.extras) | set(install_req.extras)
        ))
        logger.debug(
            "Setting %s extras to: %s",
            existing_req, existing_req.extras,
        )
        # Return the existing requirement for addition to the parent and
        # scanning again.
        return [existing_req], existing_req

    def has_requirement(self, project_name):
        # type: (str) -> bool
        name = project_name.lower()
        if (name in self.requirements and
           not self.requirements[name].constraint or
           name in self.requirement_aliases and
           not self.requirements[self.requirement_aliases[name]].constraint):
            return True
        return False

    def get_requirement(self, project_name):
        # type: (str) -> InstallRequirement
        for name in project_name, project_name.lower():
            if name in self.requirements:
                return self.requirements[name]
            if name in self.requirement_aliases:
                return self.requirements[self.requirement_aliases[name]]
        raise KeyError("No project with the name %r" % project_name)

    def cleanup_files(self):
        # type: () -> None
        """Clean up files, remove builds."""
        logger.debug('Cleaning up...')
        with indent_log():
            for req in self.reqs_to_cleanup:
                req.remove_temporary_source()
