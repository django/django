"""
This file is used to test function is considered global even if it's not defined yet
because it's covered by a decorator.
"""

from django.tasks.utils import is_global_function


@is_global_function
def really_global_function() -> None:
    pass


inner_func_is_global_function = None


def main() -> None:
    global inner_func_is_global_function

    @is_global_function
    def inner_func() -> None:
        pass

    inner_func_is_global_function = inner_func


main()
