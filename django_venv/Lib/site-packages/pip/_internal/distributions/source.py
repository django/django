import logging

from pip._internal.build_env import BuildEnvironment
from pip._internal.distributions.base import AbstractDistribution
from pip._internal.exceptions import InstallationError

logger = logging.getLogger(__name__)


class SourceDistribution(AbstractDistribution):
    """Represents a source distribution.

    The preparation step for these needs metadata for the packages to be
    generated, either using PEP 517 or using the legacy `setup.py egg_info`.

    NOTE from @pradyunsg (14 June 2019)
    I expect SourceDistribution class will need to be split into
    `legacy_source` (setup.py based) and `source` (PEP 517 based) when we start
    bringing logic for preparation out of InstallRequirement into this class.
    """

    def get_pkg_resources_distribution(self):
        return self.req.get_dist()

    def prepare_distribution_metadata(self, finder, build_isolation):
        # Prepare for building. We need to:
        #   1. Load pyproject.toml (if it exists)
        #   2. Set up the build environment

        self.req.load_pyproject_toml()
        should_isolate = self.req.use_pep517 and build_isolation

        def _raise_conflicts(conflicting_with, conflicting_reqs):
            raise InstallationError(
                "Some build dependencies for %s conflict with %s: %s." % (
                    self.req, conflicting_with, ', '.join(
                        '%s is incompatible with %s' % (installed, wanted)
                        for installed, wanted in sorted(conflicting))))

        if should_isolate:
            # Isolate in a BuildEnvironment and install the build-time
            # requirements.
            self.req.build_env = BuildEnvironment()
            self.req.build_env.install_requirements(
                finder, self.req.pyproject_requires, 'overlay',
                "Installing build dependencies"
            )
            conflicting, missing = self.req.build_env.check_requirements(
                self.req.requirements_to_check
            )
            if conflicting:
                _raise_conflicts("PEP 517/518 supported requirements",
                                 conflicting)
            if missing:
                logger.warning(
                    "Missing build requirements in pyproject.toml for %s.",
                    self.req,
                )
                logger.warning(
                    "The project does not specify a build backend, and "
                    "pip cannot fall back to setuptools without %s.",
                    " and ".join(map(repr, sorted(missing)))
                )
            # Install any extra build dependencies that the backend requests.
            # This must be done in a second pass, as the pyproject.toml
            # dependencies must be installed before we can call the backend.
            with self.req.build_env:
                # We need to have the env active when calling the hook.
                self.req.spin_message = "Getting requirements to build wheel"
                reqs = self.req.pep517_backend.get_requires_for_build_wheel()
            conflicting, missing = self.req.build_env.check_requirements(reqs)
            if conflicting:
                _raise_conflicts("the backend dependencies", conflicting)
            self.req.build_env.install_requirements(
                finder, missing, 'normal',
                "Installing backend dependencies"
            )

        self.req.prepare_metadata()
        self.req.assert_source_matches_version()
