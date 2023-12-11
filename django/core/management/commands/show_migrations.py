"""
An alias to the `showmigrations` command

All other `show*` management commands contain an underscore except this one, which makes
it harder for muscle memory to call this command correctly.
"""
# flake8: noqa
from .showmigrations import Command
