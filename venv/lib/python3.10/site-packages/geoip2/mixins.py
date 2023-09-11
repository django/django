"""This package contains utility mixins"""
# pylint: disable=too-few-public-methods
from abc import ABCMeta
from typing import Any


class SimpleEquality(metaclass=ABCMeta):
    """Naive __dict__ equality mixin"""

    def __eq__(self, other: Any) -> bool:
        return isinstance(other, self.__class__) and self.__dict__ == other.__dict__

    def __ne__(self, other):
        return not self.__eq__(other)
