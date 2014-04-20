# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from .messages import (CheckMessage,
        Debug, Info, Warning, Error, Critical,
        DEBUG, INFO, WARNING, ERROR, CRITICAL)
from .registry import register, run_checks, tag_exists, Tags

# Import these to force registration of checks
import django.core.checks.compatibility.django_1_6_0  # NOQA
import django.core.checks.compatibility.django_1_7_0  # NOQA
import django.core.checks.model_checks  # NOQA

__all__ = [
    'CheckMessage',
    'Debug', 'Info', 'Warning', 'Error', 'Critical',
    'DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL',
    'register', 'run_checks', 'tag_exists', 'Tags',
]
