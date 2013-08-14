# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.core import checks


# This check is registered in __init__.py file.
def check_model_admin(**kwargs):
    return []