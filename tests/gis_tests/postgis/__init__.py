import unittest

from django.db import connection
from django.test import TestCase, override_settings, skipUnlessDBFeature


@skipUnlessDBFeature("gis_enabled")
@unittest.skipUnless(connection.vendor == 'postgresql', "PostgreSQL specific tests")
class PostgisTestCase(TestCase):
    pass
