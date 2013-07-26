# -*- coding: utf8 -*-
from __future__ import unicode_literals

from .messages import Error, Warning
from .registration import register, run_checks
from .default_checks import check_all_models


register(check_all_models)
