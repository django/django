#!/usr/bin/env python3
import os
import sys

sys.path.append(os.path.abspath(os.path.join('..', '..', '..')))

if __name__ == "__main__":
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "sampleproject.settings")

    from django.core.management import execute_from_command_line

    execute_from_command_line(sys.argv)
