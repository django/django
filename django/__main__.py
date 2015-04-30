# -*- coding: utf-8 -*-
"""
Alias to allow the django module to be run as a script.

Example:

    python -m django collectstatic
"""
from django.core import management

if __name__ == "__main__":
    management.execute_from_command_line()
