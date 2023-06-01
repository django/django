"""
Example docstring
"""
from django.utils.functional import cached_property

from . import other_module
from .other_module import MyOtherClass

# This file should never get imported. If it is, then something failed already.
raise Exception

__all__ = ["other_module", "MyOtherClass"]


class MyClass(object):
    def __init__(self):
        pass

    def my_method(self):
        pass

    @cached_property
    def my_cached_property(self):
        pass


def my_function(self):
    pass
