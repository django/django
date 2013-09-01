# -*- coding: utf8 -*-
from __future__ import unicode_literals

from .messages import (CheckMessage,
        Debug, Info, Warning, Error, Critical,
        DEBUG, INFO, WARNING, ERROR, CRITICAL)
from .registration import register, run_checks, tag, tag_exists
from .default_checks import check_all_models, check_1_6_compatibility


register(check_all_models)
register(check_1_6_compatibility)
