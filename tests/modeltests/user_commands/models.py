"""
38. User-registered management commands

The ``manage.py`` utility provides a number of useful commands for managing a
Django project. If you want to add a utility command of your own, you can.

The user-defined command ``dance`` is defined in the management/commands
subdirectory of this test application. It is a simple command that responds
with a printed message when invoked.

For more details on how to define your own ``manage.py`` commands, look at the
``django.core.management.commands`` directory. This directory contains the
definitions for the base Django ``manage.py`` commands.
"""

__test__ = {'API_TESTS': """
>>> from django.core import management

# Invoke a simple user-defined command
>>> management.call_command('dance')
I don't feel like dancing.

# Invoke a command that doesn't exist
>>> management.call_command('explode')
Traceback (most recent call last):
...
CommandError: Unknown command: 'explode'


"""}
