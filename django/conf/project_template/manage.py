#!/usr/bin/env python
import os
import sys
import warnings


if __name__ == "__main__":
    # Python 2.7+ (and 3.2+) have silenced DeprecationWarning by default
    # Restore the old behavior when running Django via manage.py
    warnings.simplefilter("default", DeprecationWarning)

    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "{{ project_name }}.settings")

    from django.core.management import execute_from_command_line

    execute_from_command_line(sys.argv)
