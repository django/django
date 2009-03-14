#!/usr/bin/env python

"""
Daily cleanup job.

Can be run as a cronjob to clean out old data from the database (only expired
sessions at the moment).
"""

from django.core import management

if __name__ == "__main__":
    management.call_command('cleanup')
