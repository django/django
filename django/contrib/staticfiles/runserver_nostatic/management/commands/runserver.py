"""
This file exists solely to shadow the `runserver` command provided by
`django.contrib.staticfiles` and restore the original `runserver` behaviour
"""
from django.core.management.commands.runserver import Command

# Keep flake8 happy
__all__ = ['Command']
