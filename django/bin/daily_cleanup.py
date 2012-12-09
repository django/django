#!/usr/bin/env python

"""
Daily cleanup job.

Can be run as a cronjob to clean out old data from the database (only expired
sessions at the moment).
"""

import warnings

from django.core import management

if __name__ == "__main__":
    warnings.warn(
        "The `daily_cleanup` script has been deprecated "
        "in favor of `django-admin.py clearsessions`.",
        PendingDeprecationWarning)
    management.call_command('clearsessions')
