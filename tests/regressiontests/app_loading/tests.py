"""
Test the globbing of INSTALLED_APPS.

>>> import os, sys
>>> old_sys_path = sys.path
>>> sys.path.append(os.path.dirname(os.path.abspath(__file__)))

>>> from django.conf import Settings

>>> s = Settings('test_settings')

>>> s.INSTALLED_APPS
['parent.app', 'parent.app1']

>>> sys.path = old_sys_path

"""

