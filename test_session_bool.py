import base64
import os
import shutil
import string
import tempfile
import unittest
from datetime import timedelta
from http import cookies
from pathlib import Path
from unittest import mock

from django.conf import settings
from django.contrib.sessions.backends.base import SessionBase, UpdateError
from django.contrib.sessions.backends.cache import SessionStore as CacheSession
from django.contrib.sessions.backends.cached_db import SessionStore as CacheDBSession
from django.contrib.sessions.backends.db import SessionStore as DatabaseSession
from django.contrib.sessions.backends.file import SessionStore as FileSession
from django.contrib.sessions.backends.signed_cookies import (
    SessionStore as CookieSession,
)
from django.contrib.sessions.exceptions import InvalidSessionKey, SessionInterrupted
from django.contrib.sessions.middleware import SessionMiddleware
from django.contrib.sessions.models import Session
from django.contrib.sessions.serializers import JSONSerializer
from django.core import management
from django.core.cache import caches
from django.core.cache.backends.base import InvalidCacheBackendError
from django.core.exceptions import ImproperlyConfigured
from django.core.signing import TimestampSigner
from django.http import HttpResponse
from django.test import (
    RequestFactory,
    SimpleTestCase,
    TestCase,
    ignore_warnings,
    override_settings,
)
from django.utils import timezone

from .models import SessionStore as CustomDatabaseSession


class SessionTestsMixin:
    # This does not inherit from TestCase to avoid any tests being run with
    # this class, which wouldn't work, and to allow different TestCase
    # subclasses to be used.

    backend = None  # subclasses must specify

    def setUp(self):
        self.session = self.backend()
        # NB: be careful to delete any sessions created; stale sessions fill up
        # the /tmp (with some backends) and eventually overwhelm it after lots
        # of runs (think buildbots)
        self.addCleanup(self.session.delete)

    def test_bool_empty_session(self):
        """An empty session should evaluate to False."""
        self.assertIs(bool(self.session), False)

    def test_bool_session_with_data(self):
        """A session with data should evaluate to True."""
        self.session["key"] = "value"
        self.assertIs(bool(self.session), True)

    def test_bool_session_after_clear(self):
        """A session should evaluate to False after being cleared."""
        self.session["key"] = "value"
        self.assertIs(bool(self.session), True)
        self.session.clear()
        self.assertIs(bool(self.session), False)
