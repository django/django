from pip._vendor import pkg_resources

from pip._internal.distributions.base import AbstractDistribution


class WheelDistribution(AbstractDistribution):
    """Represents a wheel distribution.

    This does not need any preparation as wheels can be directly unpacked.
    """

    def get_pkg_resources_distribution(self):
        return list(pkg_resources.find_distributions(
                    self.req.source_dir))[0]

    def prepare_distribution_metadata(self, finder, build_isolation):
        pass
