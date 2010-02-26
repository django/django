import os
import sys
import time

from django.conf import Settings

__test__ = {"API_TESTS": """
Test the globbing of INSTALLED_APPS.

>>> old_sys_path = sys.path
>>> sys.path.append(os.path.dirname(os.path.abspath(__file__)))

>>> old_tz = os.environ.get("TZ")
>>> settings = Settings('test_settings')

>>> settings.INSTALLED_APPS
['parent.app', 'parent.app1', 'parent.app_2']

>>> sys.path = old_sys_path

# Undo a side-effect of installing a new settings object.
>>> if hasattr(time, "tzset") and old_tz:
...     os.environ["TZ"] = old_tz
...     time.tzset()

"""}

