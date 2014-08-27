from django.utils.importlib import import_module

from ..conf import conf


def get_check(func_path):
    mod_name, func_name = func_path.rsplit(".", 1)
    module = import_module(mod_name)
    return getattr(module, func_name)


def run_checks():
    warnings = set()

    for func_path in conf.SECURE_CHECKS:
        warnings.update(get_check(func_path)())

    return warnings
