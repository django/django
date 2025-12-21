import functools
from importlib import import_module

from django.core.exceptions import ViewDoesNotExist
from django.utils.module_loading import module_has_submodule


@functools.cache
def get_callable(lookup_view):
    """
    Return a callable corresponding to lookup_view.
    * If lookup_view is already a callable, return it.
    * If lookup_view is a string import path that can be resolved to a
      callable, import that callable and return it, otherwise raise an
      exception (ImportError or ViewDoesNotExist).
    """
    if callable(lookup_view):
        return lookup_view

    if not isinstance(lookup_view, str):
        raise ViewDoesNotExist(
            f"'{lookup_view}' is not a callable or a dot-notation path"
        )

    mod_name, func_name = get_mod_func(lookup_view)
    if not func_name:  # No '.' in lookup_view
        raise ImportError(
            f"Could not import '{lookup_view}'. The path must be fully qualified."
        )

    try:
        mod = import_module(mod_name)
    except ImportError:
        parentmod, submod = get_mod_func(mod_name)
        if submod and not module_has_submodule(import_module(parentmod), submod):
            raise ViewDoesNotExist(
                f"Could not import '{lookup_view}'. Parent module {mod_name} does not exist."
            )
        else:
            raise
    else:
        try:
            view_func = getattr(mod, func_name)
        except AttributeError:
            raise ViewDoesNotExist(
                f"Could not import '{lookup_view}'. View does not exist in module {mod_name}."
            )
        else:
            if not callable(view_func):
                raise ViewDoesNotExist(
                    f"Could not import '{mod_name}.{func_name}'. View is not callable."
                )
            return view_func


def get_mod_func(callback):
    # Convert 'django.views.news.stories.story_detail' to
    # ['django.views.news.stories', 'story_detail']
    try:
        dot = callback.rindex(".")
    except ValueError:
        return callback, ""
    return callback[:dot], callback[dot + 1 :]
