# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from .messages import (
    CRITICAL, DEBUG, ERROR, INFO, WARNING, CheckMessage, Critical, Debug,
    Error, Info, Warning,
)
from .registry import Tags, register, run_checks, tag_exists

# Import these to force registration of checks
import django.core.checks.caches  # NOQA isort:skip
import django.core.checks.compatibility.django_1_8_0  # NOQA isort:skip
import django.core.checks.compatibility.django_1_10  # NOQA isort:skip
import django.core.checks.database  # NOQA isort:skip
import django.core.checks.model_checks  # NOQA isort:skip
import django.core.checks.security.base  # NOQA isort:skip
import django.core.checks.security.csrf  # NOQA isort:skip
import django.core.checks.security.sessions  # NOQA isort:skip
import django.core.checks.templates  # NOQA isort:skip
import django.core.checks.urls  # NOQA isort:skip


__all__ = [
    'CheckMessage',
    'Debug', 'Info', 'Warning', 'Error', 'Critical',
    'DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL',
    'register', 'run_checks', 'tag_exists', 'Tags',
]
