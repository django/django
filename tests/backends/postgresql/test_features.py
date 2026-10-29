import unittest

from django.db import connection
from django.test import TestCase


@unittest.skipUnless(connection.vendor == "postgresql", "PostgreSQL tests")
class FeaturesTests(TestCase):
    def test_max_query_params_respects_server_side_params(self):
        if connection.features.uses_server_side_binding:
            limit = 2**16 - 1
        else:
            limit = None
        self.assertEqual(connection.features.max_query_params, limit)
