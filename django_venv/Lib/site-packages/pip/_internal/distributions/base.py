import abc

from pip._vendor.six import add_metaclass


@add_metaclass(abc.ABCMeta)
class AbstractDistribution(object):
    """A base class for handling installable artifacts.

    The requirements for anything installable are as follows:

     - we must be able to determine the requirement name
       (or we can't correctly handle the non-upgrade case).

     - for packages with setup requirements, we must also be able
       to determine their requirements without installing additional
       packages (for the same reason as run-time dependencies)

     - we must be able to create a Distribution object exposing the
       above metadata.
    """

    def __init__(self, req):
        super(AbstractDistribution, self).__init__()
        self.req = req

    @abc.abstractmethod
    def get_pkg_resources_distribution(self):
        raise NotImplementedError()

    @abc.abstractmethod
    def prepare_distribution_metadata(self, finder, build_isolation):
        raise NotImplementedError()
