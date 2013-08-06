# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.core.checks import register
from .checks import check_generic_foreign_keys, check_generic_relationships

register(check_generic_foreign_keys)
register(check_generic_relationships)
