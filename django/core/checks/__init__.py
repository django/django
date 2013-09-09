# -*- coding: utf8 -*-
from __future__ import unicode_literals

from .messages import (CheckMessage,
        Debug, Info, Warning, Error, Critical,
        DEBUG, INFO, WARNING, ERROR, CRITICAL)
from .registration import register, run_checks, tag_exists
import django.core.checks.default_checks
