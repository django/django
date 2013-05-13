import glob
import os
import warnings

from django.utils import importlib


def collect_checks():
    base_path = os.path.dirname(__file__)
    check_files = glob.glob(os.path.join(base_path, 'django_*.py'))
    check_names = []

    for check_file in check_files:
        name, ext = os.path.splitext(os.path.basename(check_file))
        check_names.append(name)

    return reversed(check_names)


def check_compatibility(check_names=None):
    if check_names is None:
        check_names = collect_checks()

    for check_name in check_names:
        mod_name = 'django.core.compat_checks.' + check_name
        check_module = importlib.import_module(mod_name)
        check = getattr(check_module, 'run_checks', None)

        if check is None:
            warnings.warn(
                "The '%s' module lacks a 'run_checks' method, which is " +
                "needed to verify compatibility."
            )
            continue

        check()
