"""
This file is used to test function is considered module level even if it's not defined
yet because it's covered by a decorator.
"""

from django.tasks.utils import is_module_level_function


@is_module_level_function
def really_module_level_function():
    pass


inner_func_is_module_level_function = None


def main():
    global inner_func_is_module_level_function

    @is_module_level_function
    def inner_func():
        pass

    inner_func_is_module_level_function = inner_func


main()
