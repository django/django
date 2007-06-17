#!/usr/bin/env python

"""
Daily cleanup job.

Can be run as a cronjob to clean out old data from the database (only expired
sessions at the moment).
"""

import datetime
from django.db import transaction
from django.contrib.sessions.models import Session

def clean_up():
    """Clean up expired sessions."""
    Session.objects.filter(expire_date__lt=datetime.datetime.now()).delete()
    transaction.commit_unless_managed()

if __name__ == "__main__":
    clean_up()
