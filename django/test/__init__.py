"""
Django Unit Test and Doctest framework.
"""

from django.test.client import Client
from django.test.testcases import TestCase, TransactionTestCase

class SkippedTest(Exception):
    def __init__(self, reason):
        self.reason = reason

    def __str__(self):
        return self.reason