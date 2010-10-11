"""
Django Unit Test and Doctest framework.
"""

from django.test.client import Client
from django.test.testcases import TestCase, TransactionTestCase, skipIfDBFeature, skipUnlessDBFeature
from django.test.utils import Approximate
