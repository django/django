import glob
import os
import warnings

from django.utils import importlib


def collect_checks():
    base_path = os.path.dirname(__file__)
    check_files = glob.glob(os.path.join(base_path, 'django_*.py'))
    base_files = []

    for check_file in check_files:
        name, ext = os.path.splitext(os.path.basename(check_file))
        base_files.append(name)

    reversed(base_files)
    return base_files


def check_compatibility(check_files=None):
    if check_files is None:
        check_files = collect_checks()

    for check_file in check_files:
        mod_name = 'django.core.compat_checks.' + check_file
        check_module = importlib.import_module(mod_name)
        check = getattr(check_module, 'run_checks', None)

        if check is None:
            warnings.warn(
                "The '%s' module lacks a 'run_checks' method, which is " +
                "needed to verify compatibility."
            )
            continue

        check()
