"""This package contains utility mixins"""
# pylint: disable=too-few-public-methods
from abc import ABCMeta


class SimpleEquality(object):
    """Naive __dict__ equality mixin"""

    __metaclass__ = ABCMeta

    def __eq__(self, other):
        return (isinstance(other, self.__class__)
                and self.__dict__ == other.__dict__)

    def __ne__(self, other):
        return not self.__eq__(other)
