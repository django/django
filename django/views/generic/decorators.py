"Decorators for generic class-based views"

from django.utils.decorators import method_decorator


def view_decorator(decorator):
    """
    Applies a function decorator to the dispatch method of a class, allowing
    view decorators to be applied to class-based views.
    """
    def _dec(cls):
        cls.dispatch = method_decorator(decorator)(cls.dispatch)
        return cls
    return _dec
