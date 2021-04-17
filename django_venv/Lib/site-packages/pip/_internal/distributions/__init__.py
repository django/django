from pip._internal.distributions.source import SourceDistribution
from pip._internal.distributions.wheel import WheelDistribution

from pip._internal.utils.typing import MYPY_CHECK_RUNNING

if MYPY_CHECK_RUNNING:
    from pip._internal.distributions.base import AbstractDistribution
    from pip._internal.req.req_install import InstallRequirement


def make_distribution_for_install_requirement(install_req):
    # type: (InstallRequirement) -> AbstractDistribution
    """Returns a Distribution for the given InstallRequirement
    """
    # If it's not an editable, is a wheel, it's a WheelDistribution
    if install_req.editable:
        return SourceDistribution(install_req)

    if install_req.link and install_req.is_wheel:
        return WheelDistribution(install_req)

    # Otherwise, a SourceDistribution
    return SourceDistribution(install_req)
