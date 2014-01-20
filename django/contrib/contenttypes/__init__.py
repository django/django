# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.contrib.contenttypes.checks  import check_generic_foreign_keys
from django.core import checks


checks.register('models')(check_generic_foreign_keys)
