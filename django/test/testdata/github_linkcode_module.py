"""
My docstring.
"""

from django.utils.functional import cached_property


class MyClass(object):
    def __init__(self):
        pass

    def my_def(self):
        pass

    @cached_property
    def my_cached_property(self):
        pass


def my_toplevel_def(self):
    pass
