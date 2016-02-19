import doctest
from unittest import TestCase

from django.test import SimpleTestCase, TestCase as DjangoTestCase, tag

from . import doctests


class TestVanillaUnittest(TestCase):

    def test_sample(self):
        self.assertEqual(1, 1)


class TestDjangoTestCase(DjangoTestCase):

    def test_sample(self):
        self.assertEqual(1, 1)


class TestZimpleTestCase(SimpleTestCase):
    # Z is used to trick this test case to appear after Vanilla in default suite

    def test_sample(self):
        self.assertEqual(1, 1)


class EmptyTestCase(TestCase):
    pass


@tag('slow')
class TaggedTestCase(TestCase):

    @tag('fast')
    def test_single_tag(self):
        self.assertEqual(1, 1)

    @tag('fast', 'core')
    def test_multiple_tags(self):
        self.assertEqual(1, 1)


def load_tests(loader, tests, ignore):
    tests.addTests(doctest.DocTestSuite(doctests))
    return tests
