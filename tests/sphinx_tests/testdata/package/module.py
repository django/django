"""
Example docstring
"""

from django.utils.functional import classproperty
from tests.sphinx_tests.testdata.package.wildcard_module import *  # noqa

from . import other_module  # noqa
from .other_module import MyOtherClass  # noqa


class MyClass(object):
    def __init__(self):
        pass

    def my_method(self):
        pass

    @classproperty
    def my_classproperty(cls):
        pass


def my_function(self):
    pass
